#!/usr/bin/env bash
set -e
python -m pytest -q
python -m compileall backend
echo "Verification passed."
