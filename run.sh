#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -x .venv/bin/python ]]; then
  terrapulse_python=.venv/bin/python
else
  terrapulse_python=python3
fi
"$terrapulse_python" -m src.api.readiness
export OFFLINE=1
exec "$terrapulse_python" -m src.api.app "$@"
