#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Create the local environment first; see m2_guardian/README.md.'
  exit 1
fi
exec .venv/bin/python -m streamlit run app_m2.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
