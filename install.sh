#!/usr/bin/env bash
# Install agenda: dedicated venv + ~/.local/bin symlink.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${AGENDA_VENV:-$HOME/.venv-agenda}"
BIN="${AGENDA_BIN:-$HOME/.local/bin}"

python3 -m venv "$VENV"
"$VENV/bin/pip" -q install --upgrade pip
"$VENV/bin/pip" -q install -e "$HERE"
mkdir -p "$BIN"
ln -sf "$VENV/bin/agenda" "$BIN/agenda"
echo "installed: $BIN/agenda  ->  $VENV"
