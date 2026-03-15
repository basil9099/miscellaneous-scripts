#!/usr/bin/env python3
"""
Bank Statement Categorizer
Parses Australian bank statement PDFs, normalises descriptions,
categorises transactions using editable regex rules, and outputs CSV + summary.

Usage:
    python categorize.py statement.pdf [statement2.pdf ...]
    python categorize.py *.pdf --rules categories.yaml --out results.csv --bank commbank
"""

import argparse
import os
import platform
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import pdfplumber
import yaml
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Common date patterns used across bank formats
# ---------------------------------------------------------------------------
DATE_PATTERNS = [
    # DD Mon YYYY  or  DD Mon YY
    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4})",
    # DD/MM/YYYY or DD/MM/YY
    r"(\d{1,2}/\d{1,2}/\d{2,4})",
    # YYYY-MM-DD
    r"(\d{4}-\d{2}-\d{2})",
    # DD-MM-YYYY
    r"(\d{1,2}-\d{1,2}-\d{4})",
]
DATE_RE = re.compile("|".join(DATE_PATTERNS), re.IGNORECASE)

AMOUNT_RE = re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)")

# Prefixes stripped during normalisation
STRIP_PREFIXES = re.compile(
    r"^(eftpos\s+|visa\s+(?:purchase\s+)?|purchase\s+|pos\s+|recurring\s+"
    r"|direct\s+debit\s+|direct\s+credit\s+|card\s+xx\d+\s+)",
    re.IGNORECASE,
)

# Noise tokens stripped during normalisation (card numbers, refs, trailing dates)
NOISE_RE = re.compile(
    r"\b\d{6,}\b"          # long digit strings (card/ref numbers)
    r"|#\w+"               # hashtag references
    r"|\bref\s*\w+"        # ref codes
    r"|\bxxxx\w*"          # masked card fragments
    r"|\bvalue date.*$"    # trailing "value date …"
    r"|\bauthorisation.*$" # trailing auth codes
    r"|\s{2,}",            # multiple spaces (replaced later)
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------

def load_rules(path: str) -> dict[str, re.Pattern]:
    """Load categories.yaml and compile each category's patterns into one regex."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    compiled: dict[str, re.Pattern | None] = {}
    for category, patterns in data.get("categories", {}).items():
        if patterns:
            combined = "|".join(f"(?:{p})" for p in patterns)
            compiled[category] = re.compile(combined, re.IGNORECASE)
        else:
            compiled[category] = None  # catch-all (misc)
    return compiled


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalise(text: str) -> str:
    """Lowercase, strip noise, strip common prefixes, collapse whitespace."""
    text = text.lower().strip()
    text = STRIP_PREFIXES.sub("", text)
    text = NOISE_RE.sub(" ", text)
    text = text.strip()
    return text


# ---------------------------------------------------------------------------
# Categorisation
# ---------------------------------------------------------------------------

def categorise(description: str, rules: dict[str, re.Pattern | None]) -> str:
    """Return the first matching category, or 'misc' if none match."""
    for category, pattern in rules.items():
        if pattern is None:
            return category  # catch-all
        if pattern.search(description):
            return category
    return "misc"


# ---------------------------------------------------------------------------
# Amount helpers
# ---------------------------------------------------------------------------

def _parse_amount(text: str) -> float | None:
    """Parse a dollar amount string to float, or None if not found."""
    if not text:
        return None
    text = text.strip().replace(",", "").replace("$", "").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return None


def _amounts_from_cells(cells: list[str]) -> tuple[float | None, float | None, float | None]:
    """Given a row of cells, extract (debit, credit, balance) by position heuristic."""
    # Try to collect all numeric-looking cells
    amounts = []
    for c in cells:
        v = _parse_amount(c)
        if v is not None:
            amounts.append(v)
    if len(amounts) >= 3:
        return amounts[-3], amounts[-2], amounts[-1]
    if len(amounts) == 2:
        return amounts[0], None, amounts[1]
    if len(amounts) == 1:
        return None, None, amounts[0]
    return None, None, None


# ---------------------------------------------------------------------------
# PDF extraction — table strategy
# ---------------------------------------------------------------------------

def _extract_via_table(page) -> list[dict]:
    """Try pdfplumber table extraction. Returns list of row dicts."""
    tables = page.extract_tables()
    if not tables:
        return []

    rows = []
    for table in tables:
        for row in table:
            if not row:
                continue
            # Find a date cell
            date_val = None
            date_idx = -1
            for i, cell in enumerate(row):
                if cell and DATE_RE.search(str(cell)):
                    date_val = str(cell).strip()
                    date_idx = i
                    break
            if date_val is None or date_idx < 0:
                continue

            # Description = cell after date (or second non-empty cell after date)
            description = ""
            for j in range(date_idx + 1, len(row)):
                cell = row[j]
                if cell and str(cell).strip():
                    description = str(cell).strip()
                    break

            if not description:
                continue

            # Amounts from remaining cells
            remaining = [str(c) if c else "" for c in row[date_idx + 1:]]
            debit, credit, balance = _amounts_from_cells(remaining)

            rows.append({
                "date": date_val,
                "description": description,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            })
    return rows


# ---------------------------------------------------------------------------
# PDF extraction — line parsing fallback
# ---------------------------------------------------------------------------

# Generic line pattern: optional date, then text, then 1–3 amounts
LINE_RE = re.compile(
    r"^(?P<date>\d{1,2}[\s/\-]\w+[\s/\-]\d{2,4}|\d{4}-\d{2}-\d{2})?\s*"
    r"(?P<desc>.+?)\s+"
    r"(?P<amounts>(?:\$?\s*[\d,]+\.\d{2}\s*){1,3})$",
    re.IGNORECASE,
)

# CBA-style: "01 Jan 2024   Description text   1,234.56   5,678.90   10,000.00"
CBA_RE = re.compile(
    r"^(?P<date>\d{1,2}\s+\w{3}\s+\d{4})\s+"
    r"(?P<desc>.+?)\s{2,}"
    r"(?P<amounts>(?:\$?\s*[\d,]+\.\d{2}\s*){1,3})$",
)


def _parse_line(line: str) -> dict | None:
    """Attempt to parse a single text line into a transaction dict."""
    line = line.strip()
    if len(line) < 10:
        return None

    for pattern in (CBA_RE, LINE_RE):
        m = pattern.match(line)
        if m:
            groups = m.groupdict()
            date_val = groups.get("date", "").strip()
            description = groups.get("desc", "").strip()
            amounts_str = groups.get("amounts", "")
            amount_vals = [_parse_amount(a) for a in AMOUNT_RE.findall(amounts_str)]
            amount_vals = [v for v in amount_vals if v is not None]

            if not description:
                continue

            debit, credit, balance = None, None, None
            if len(amount_vals) >= 3:
                debit, credit, balance = amount_vals[-3], amount_vals[-2], amount_vals[-1]
            elif len(amount_vals) == 2:
                debit, balance = amount_vals[0], amount_vals[1]
            elif len(amount_vals) == 1:
                balance = amount_vals[0]

            return {
                "date": date_val or "",
                "description": description,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            }
    return None


def _extract_via_lines(page) -> list[dict]:
    """Fall back to line-by-line text parsing."""
    text = page.extract_text()
    if not text:
        return []

    rows = []
    pending_date = ""

    for line in text.splitlines():
        # Carry forward a date-only line to the next description line
        date_only = DATE_RE.fullmatch(line.strip())
        if date_only:
            pending_date = line.strip()
            continue

        result = _parse_line(line)
        if result:
            if not result["date"] and pending_date:
                result["date"] = pending_date
            pending_date = ""
            rows.append(result)

    return rows


# ---------------------------------------------------------------------------
# Top-level extraction
# ---------------------------------------------------------------------------

def extract_transactions(pdf_path: str, bank_hint: str = "auto") -> list[dict]:
    """Extract transactions from a PDF using table or line-parsing strategy."""
    rows: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Strategy 1: table extraction
            table_rows = _extract_via_table(page)
            if table_rows:
                rows.extend(table_rows)
                continue

            # Strategy 2: line parsing
            line_rows = _extract_via_lines(page)
            rows.extend(line_rows)

    return rows


def _pdf_worker(args: tuple[str, str]) -> tuple[str, list[dict], str]:
    """
    Module-level worker so ProcessPoolExecutor can pickle it.
    Returns (pdf_name, rows, error_message).
    """
    pdf_path, bank_hint = args
    try:
        rows = extract_transactions(pdf_path, bank_hint)
        return Path(pdf_path).name, rows, ""
    except Exception as exc:  # noqa: BLE001
        return Path(pdf_path).name, [], str(exc)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarise(df: pd.DataFrame) -> None:
    """Print a rich summary table: category | count | total spent | % of total."""
    debits = df[df["debit"].notna() & (df["debit"] > 0)].copy()
    if debits.empty:
        console.print("[yellow]No debit transactions found for summary.[/yellow]")
        return

    grouped = (
        debits.groupby("category")["debit"]
        .agg(count="count", total="sum")
        .reset_index()
        .sort_values("total", ascending=False)
    )
    grand_total = grouped["total"].sum()

    table = Table(title="Spending Summary", show_footer=True)
    table.add_column("Category", style="cyan")
    table.add_column("Transactions", justify="right")
    table.add_column("Total Spent", justify="right", style="green",
                     footer=f"${grand_total:,.2f}")
    table.add_column("% of Total", justify="right")

    for _, row in grouped.iterrows():
        pct = row["total"] / grand_total * 100 if grand_total else 0
        table.add_row(
            row["category"],
            str(int(row["count"])),
            f"${row['total']:,.2f}",
            f"{pct:.1f}%",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    script_dir = Path(__file__).parent
    default_rules = script_dir / "categories.yaml"
    default_out = f"transactions_{date.today().isoformat()}.csv"

    parser = argparse.ArgumentParser(
        description="Parse and categorise Australian bank statement PDFs."
    )
    parser.add_argument("pdfs", nargs="+", metavar="PDF", help="Input PDF file(s)")
    parser.add_argument(
        "--rules", default=str(default_rules), metavar="YAML",
        help=f"Path to categories YAML (default: {default_rules})",
    )
    parser.add_argument(
        "--out", default=default_out, metavar="CSV",
        help=f"Output CSV path (default: {default_out})",
    )
    parser.add_argument(
        "--no-summary", dest="summary", action="store_false",
        help="Suppress terminal summary table",
    )
    parser.add_argument(
        "--bank", default="auto",
        choices=["auto", "commbank", "anz", "nab", "westpac"],
        help="Bank format hint (default: auto)",
    )
    parser.add_argument(
        "--open", dest="open_after", action="store_true", default=False,
        help="Open the CSV in the default app (Numbers/Excel) after saving (macOS only)",
    )
    parser.add_argument(
        "--workers", type=int, default=None, metavar="N",
        help="Number of parallel worker processes for PDF extraction "
             "(default: CPU count, capped at number of PDFs)",
    )
    args = parser.parse_args()

    # Load rules
    rules_path = Path(args.rules)
    if not rules_path.exists():
        console.print(f"[red]Rules file not found:[/red] {rules_path}")
        sys.exit(1)
    rules = load_rules(str(rules_path))
    console.print(f"Loaded [bold]{len(rules)}[/bold] categories from {rules_path.name}")

    # Validate PDF paths upfront
    valid_pdfs: list[Path] = []
    for pdf_path in args.pdfs:
        p = Path(pdf_path).expanduser()
        if not p.exists():
            console.print(f"[red]File not found, skipping:[/red] {p}")
        else:
            valid_pdfs.append(p)

    if not valid_pdfs:
        console.print("[yellow]No valid PDF files provided.[/yellow]")
        sys.exit(1)

    # Process PDFs — parallel when more than one, sequential otherwise
    all_rows: list[dict] = []
    n_workers = min(args.workers or os.cpu_count() or 1, len(valid_pdfs))
    use_parallel = len(valid_pdfs) > 1

    work_items = [(str(p), args.bank) for p in valid_pdfs]

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    )

    with progress:
        task = progress.add_task("Extracting transactions…", total=len(valid_pdfs))

        if use_parallel:
            futures_map: dict = {}
            with ProcessPoolExecutor(max_workers=n_workers) as pool:
                for item in work_items:
                    fut = pool.submit(_pdf_worker, item)
                    futures_map[fut] = Path(item[0]).name

                for fut in as_completed(futures_map):
                    pdf_name, rows, err = fut.result()
                    if err:
                        console.print(f"[red]Error in {pdf_name}:[/red] {err}")
                    else:
                        for row in rows:
                            row["source_file"] = pdf_name
                        all_rows.extend(rows)
                        console.print(f"  [dim]{pdf_name}[/dim] → {len(rows)} transactions")
                    progress.advance(task)
        else:
            pdf_name, rows, err = _pdf_worker(work_items[0])
            if err:
                console.print(f"[red]Error in {pdf_name}:[/red] {err}")
            else:
                for row in rows:
                    row["source_file"] = pdf_name
                all_rows.extend(rows)
                console.print(f"  [dim]{pdf_name}[/dim] → {len(rows)} transactions")
            progress.advance(task)

    if not all_rows:
        console.print("[yellow]No transactions found across all PDFs.[/yellow]")
        sys.exit(0)

    # Build DataFrame
    df = pd.DataFrame(all_rows, columns=[
        "date", "description", "debit", "credit", "balance", "source_file"
    ])

    # Normalise & categorise
    df["normalised"] = df["description"].fillna("").apply(normalise)
    df["category"] = df["normalised"].apply(lambda d: categorise(d, rules))

    # Reorder columns
    df = df[["date", "description", "normalised", "debit", "credit", "balance",
             "category", "source_file"]]

    # Write CSV
    out_path = Path(args.out).expanduser()
    df.to_csv(out_path, index=False)
    console.print(f"\n[green]CSV saved:[/green] {out_path} "
                  f"([bold]{len(df)}[/bold] rows)")

    # Open in default app (Numbers / Excel on macOS)
    if args.open_after:
        if platform.system() == "Darwin":
            subprocess.run(["open", str(out_path)], check=False)
        else:
            console.print("[yellow]--open is only supported on macOS.[/yellow]")

    # Summary
    if args.summary:
        console.print()
        summarise(df)


if __name__ == "__main__":
    main()
