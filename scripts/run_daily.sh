#!/usr/bin/env bash
# Wrapper for cron: activates the venv and runs the daily job, logging output.
# Edit PROJECT_DIR if you move the folder.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Activate venv if present.
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p logs
TS="$(date +%Y-%m-%d_%H%M%S)"
echo "=== daily_job $TS ===" >> "logs/daily_${TS}.log"
python scripts/daily_job.py "$@" >> "logs/daily_${TS}.log" 2>&1
echo "Done. Log: logs/daily_${TS}.log"
