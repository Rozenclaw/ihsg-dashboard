#!/usr/bin/env bash
# Double-click this file to start the IHSG dashboard.
# (First run only: right-click -> Open, to bypass macOS Gatekeeper.)

# Always work from the folder this script lives in.
cd "$(dirname "$0")" || exit 1

echo "=============================================="
echo "   IHSG Personal Dashboard - starting up"
echo "=============================================="
echo "Folder: $(pwd)"
echo

# 1) Create the virtual environment on first run.
if [ ! -d ".venv" ]; then
  echo "[setup] First run: creating virtual environment..."
  python3 -m venv .venv || { echo "ERROR: could not create venv. Is Python 3 installed?"; read -r; exit 1; }
fi

# 2) Activate it.
# shellcheck disable=SC1091
source .venv/bin/activate

# 3) Install/update dependencies (quietly). Marker file skips this next time.
if [ ! -f ".venv/.deps_installed" ]; then
  echo "[setup] Installing dependencies (one-time, ~1-3 min)..."
  pip install --quiet --upgrade pip
  pip install --quiet -r requirements.txt && touch ".venv/.deps_installed"
fi

# 4) Refresh market data from Yahoo (skip with: ./start.command --no-refresh)
if [ "$1" != "--no-refresh" ]; then
  echo "[data] Pulling latest IHSG prices from Yahoo Finance..."
  python3 scripts/refresh_data.py || echo "[warn] Data refresh hit an issue; opening with existing data."
else
  echo "[data] Skipping refresh (--no-refresh)."
fi

# 5) Launch the dashboard (opens your browser).
echo
echo "[launch] Opening dashboard at http://localhost:8501"
echo "         To stop it: come back here and press  Ctrl + C"
echo
streamlit run app/dashboard.py

# Keep the window open if Streamlit exits, so any message stays visible.
echo
echo "Dashboard stopped. You can close this window."
read -r
