#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv sync --extra sf --extra dev
uv run --no-sync pytest -q
printf '\nInstalled and tested. Try:\n  uv run cordon-annealing demo --phases 2 --steps-unpenalized 10 --steps-penalized 10\n'
