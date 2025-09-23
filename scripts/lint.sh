#!/usr/bin/env bash
set -euo pipefail
IndyCalculator/bin/python -m ruff check .
IndyCalculator/bin/python -m black --check .

