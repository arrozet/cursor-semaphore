#!/usr/bin/env bash
# Thin wrapper — prefer: python3 viz/serve.py  (works on macOS + Windows)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 viz/serve.py "$@"
