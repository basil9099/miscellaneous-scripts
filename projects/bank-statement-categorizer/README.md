# Bank Statement Categorizer

Parse Australian bank statement PDFs, normalise transaction descriptions, categorise
spending using editable regex/keyword rules, and output a CSV + terminal summary.

## macOS Setup (recommended)

Run the one-command installer — it installs Homebrew (if needed), sets up a
Python virtual environment, installs dependencies, and adds a `bank-cat` shell alias:

```bash
bash install_mac.sh
source ~/.zshrc          # or open a new terminal
```

Then use the alias from anywhere:

```bash
bank-cat statement.pdf --open   # parses PDF and opens CSV in Numbers
```

## Requirements

Python 3.11+

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Single statement
python categorize.py statement.pdf

# Multiple statements merged into one CSV (processed in parallel)
python categorize.py jan.pdf feb.pdf mar.pdf --out q1.csv

# Open the CSV in Numbers / Excel automatically after saving (macOS)
python categorize.py statement.pdf --open

# Control the number of parallel worker processes (default: CPU count)
python categorize.py *.pdf --workers 4

# Specify output file
python categorize.py statement.pdf --out my_transactions.csv

# Suppress the terminal summary table
python categorize.py statement.pdf --no-summary

# Hint the bank format (helps with ambiguous layouts)
python categorize.py statement.pdf --bank commbank
```

## Output

**CSV** (`transactions_YYYY-MM-DD.csv` by default) with columns:

| Column | Description |
|--------|-------------|
| `date` | Transaction date as parsed from the PDF |
| `description` | Original description text |
| `normalised` | Cleaned description used for matching |
| `debit` | Amount debited (spending), or blank |
| `credit` | Amount credited (income/refund), or blank |
| `balance` | Running balance, or blank |
| `category` | Matched category name |
| `source_file` | PDF filename the row came from |

**Terminal summary table** (printed by default):

```
              Spending Summary
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Category    ┃ Transactions ┃ Total Spent  ┃ % of Total ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ groceries   │           18 │   $1,234.50  │     24.1%  │
│ dining      │           12 │     $876.00  │     17.1%  │
│ ...         │          ... │         ...  │       ...  │
└─────────────┴──────────────┴──────────────┴────────────┘
```

## Customising Categories

Edit `categories.yaml` — changes take effect immediately on the next run.

Each category has a list of regex patterns matched **case-insensitively** against
the normalised transaction description. The **first matching category wins**.
`misc` at the bottom is the catch-all.

```yaml
categories:
  groceries:
    - "woolworths|coles|aldi|iga|harris farm"

  # Add your own:
  subscriptions:
    - "my_streaming_service|my_gym_app"

  misc: []  # keep this last
```

Tips:
- Use `|` to separate alternatives within a single pattern string.
- Patterns are full Python regex — you can use `(?i)`, `\b`, `.*`, etc.
- Add a new category block anywhere above `misc`.
- To rename a category, just change the key name.
- Order matters: put more specific categories above broader ones.

## Bank Format Detection

The script auto-detects the PDF structure by:

1. **Table extraction** — works for most modern bank PDFs that embed real tables
   (Commonwealth Bank, ANZ, NAB, Westpac internet banking exports).
2. **Line-by-line regex parsing** — fallback for text-based PDFs without tables.

Use `--bank commbank|anz|nab|westpac` to hint the format if auto-detection misses
transactions. Currently this hint is logged but the same two-strategy pipeline is used;
future versions may add bank-specific column mappings.

## Supported Banks (tested)

- Commonwealth Bank (CBA) — NetBank PDF statements
- ANZ — internet banking PDF exports
- NAB — internet banking PDF exports
- Westpac — internet banking PDF exports

Other Australian banks using standard columnar layouts should work with auto-detection.

## Troubleshooting

**No transactions extracted**: The PDF may be image-scanned (not text-based). Run
`pdfplumber` on it interactively to check:
```python
import pdfplumber
with pdfplumber.open("statement.pdf") as pdf:
    print(pdf.pages[0].extract_text())
```
If output is empty, you'll need OCR preprocessing (e.g. `ocrmypdf`) before using
this script.

**Wrong amounts / columns**: Use `--bank` to hint the format and open an issue with
a sanitised sample if the problem persists.

**Category not matching**: Check the normalised value in the CSV output, then add or
adjust a pattern in `categories.yaml`.
