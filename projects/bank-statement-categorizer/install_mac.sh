#!/usr/bin/env bash
# install_mac.sh — one-command setup for bank-statement-categorizer on macOS
# Requires macOS 12+ (Monterey or later) with Xcode Command Line Tools.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── 1. Homebrew ──────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "==> Installing Homebrew…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon (/opt/homebrew) or Intel (/usr/local)
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

echo "==> Homebrew $(brew --version | head -1)"

# ── 2. Python 3.11+ ──────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3.13 python3.12 python3.11; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "==> Installing Python 3.12 via Homebrew…"
    brew install python@3.12
    PYTHON="python3.12"
fi

echo "==> Using $($PYTHON --version)"

# ── 3. Virtual environment ───────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    echo "==> Creating virtual environment at .venv …"
    "$PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip

# ── 4. Dependencies ──────────────────────────────────────────────────────────
echo "==> Installing Python dependencies…"
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# ── 5. Make script executable ────────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/categorize.py"

# ── 6. Optional: shell alias ─────────────────────────────────────────────────
ALIAS_LINE="alias bank-cat='source \"$VENV_DIR/bin/activate\" && python \"$SCRIPT_DIR/categorize.py\"'"
SHELL_RC=""
if [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == */bash ]]; then
    SHELL_RC="$HOME/.bash_profile"
fi

if [[ -n "$SHELL_RC" ]]; then
    if ! grep -q "bank-cat" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# bank-statement-categorizer" >> "$SHELL_RC"
        echo "$ALIAS_LINE" >> "$SHELL_RC"
        echo "==> Added 'bank-cat' alias to $SHELL_RC"
        echo "    Run: source $SHELL_RC   (or open a new terminal)"
    else
        echo "==> 'bank-cat' alias already present in $SHELL_RC"
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Setup complete."
echo ""
echo "To use:"
echo "  source .venv/bin/activate"
echo "  python categorize.py statement.pdf --open"
echo ""
echo "Or if you added the alias (new terminal / after sourcing your shell rc):"
echo "  bank-cat statement.pdf --open"
