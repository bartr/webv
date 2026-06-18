#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$ROOT_DIR"

echo "[bootstrap] Using Python: $PYTHON_BIN"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[bootstrap] ERROR: $PYTHON_BIN not found in PATH." >&2
  exit 1
fi

create_venv() {
  echo "[bootstrap] Creating virtual environment at .venv"
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
    cat >&2 <<'EOF'
[bootstrap] Failed to create a virtual environment.
On Debian/Ubuntu, install venv support first:
  sudo apt install python3-venv
Then rerun:
  ./bootstrap.sh
EOF
    exit 1
  fi
}

if [[ ! -d "$VENV_DIR" ]]; then
  create_venv
else
  if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    echo "[bootstrap] Existing .venv appears incomplete; recreating it"
    rm -rf "$VENV_DIR"
    create_venv
  else
    echo "[bootstrap] Reusing existing virtual environment at .venv"
  fi
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[bootstrap] Done. Activate with: source .venv/bin/activate"
