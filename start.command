#!/usr/bin/env bash
# ============================================================================
#  IHSG Personal Dashboard — double-click launcher (macOS)
#
#  HOW TO USE:  just double-click this file.
#               First time only: right-click -> Open (to clear macOS Gatekeeper).
#               To stop the dashboard: come back to this window, press Ctrl + C.
#
#  Options (advanced, run from Terminal):
#     ./start.command            normal start (refreshes data once per day)
#     ./start.command --refresh  force a fresh data pull now
#     ./start.command --no-refresh   skip the data pull entirely
#
#  ⚠️  KEEP IN SYNC: if how the app is run ever changes — the entry script
#      (APP_ENTRY), the port, new dependencies, or new startup/data steps —
#      update this launcher to match.
# ============================================================================

set -uo pipefail

# --- config (update these if the app's run setup changes) -------------------
APP_ENTRY="app/dashboard.py"   # Streamlit multipage entry point
PORT="8501"                    # local port the dashboard serves on
# ----------------------------------------------------------------------------

# Always work from the folder this script lives in.
cd "$(dirname "$0")" || exit 1

echo "=============================================="
echo "   IHSG Personal Dashboard — starting up"
echo "=============================================="
echo "Folder: $(pwd)"
echo

# 0) If it's already running, don't start a second copy — just open the browser.
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[ok] Dashboard is already running on port $PORT."
  echo "     Opening it in your browser..."
  open "http://localhost:$PORT"
  echo
  echo "(You can close this window — the dashboard keeps running.)"
  read -r
  exit 0
fi

# 1) Create the virtual environment on first run.
if [ ! -d ".venv" ]; then
  echo "[setup] First run: creating virtual environment..."
  python3 -m venv .venv || { echo "ERROR: could not create venv. Is Python 3 installed?"; read -r; exit 1; }
fi

# 2) Activate it.
# shellcheck disable=SC1091
source .venv/bin/activate

# 3) Install/update dependencies whenever requirements.txt changes.
REQ_HASH="$(shasum -a 256 requirements.txt | awk '{print $1}')"
DEPS_STAMP=".venv/.deps_installed"
if [ ! -f "$DEPS_STAMP" ] || [ "$(cat "$DEPS_STAMP" 2>/dev/null)" != "$REQ_HASH" ]; then
  echo "[setup] Installing/updating dependencies (~1-3 min if anything changed)..."
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r requirements.txt && echo "$REQ_HASH" > "$DEPS_STAMP"
fi

# 4) Refresh market data — but only once per day, so repeat launches are fast.
#    Force with --refresh, skip entirely with --no-refresh.
ARG="${1:-}"
TODAY="$(date +%Y-%m-%d)"
STAMP=".venv/.last_refresh"
need_refresh=1
[ "$ARG" = "--no-refresh" ] && need_refresh=0
if [ "$ARG" != "--refresh" ] && [ -f "$STAMP" ] && [ "$(cat "$STAMP" 2>/dev/null)" = "$TODAY" ]; then
  need_refresh=0
fi

if [ "$need_refresh" = "1" ]; then
  echo "[data] Pulling latest IHSG prices from Yahoo Finance..."
  if python3 scripts/refresh_data.py; then
    echo "$TODAY" > "$STAMP"
  else
    echo "[warn] Data refresh hit an issue; opening with existing data."
  fi
else
  echo "[data] Skipping refresh (already done today, or --no-refresh)."
fi

# 5) Launch the dashboard (opens your browser).
echo
echo "[launch] Opening dashboard at http://localhost:$PORT"
echo "         To stop it: come back here and press  Ctrl + C"
echo
python -m streamlit run "$APP_ENTRY" --server.port "$PORT"

# Keep the window open if Streamlit exits, so any message stays visible.
echo
echo "Dashboard stopped. You can close this window."
read -r
