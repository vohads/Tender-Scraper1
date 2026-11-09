#!/usr/bin/env bash
set -euo pipefail

# Simple runner for cron / Codespaces
cd "$(dirname "$0")"

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

python -m scraper.main "$@"