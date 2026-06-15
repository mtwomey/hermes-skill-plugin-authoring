#!/usr/bin/env bash
# setup.sh — thin launcher for setup.py under the Hermes venv Python.
# Usage: ./setup.sh [install|uninstall|status]
set -euo pipefail
exec "$HOME/.hermes/hermes-agent/venv/bin/python3" "$(dirname "${BASH_SOURCE[0]}")/setup.py" "$@"
