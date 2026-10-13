#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3.12 scripts/setup.py "$@"
