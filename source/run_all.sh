#!/usr/bin/env bash
set -eo pipefail

# This script sequentially runs all four stages with -a (automatic) mode.

PY=python3.11   # adjust if your container uses a different python command

#echo "=== Running MIP stage ==="
#$PY MILP/mip_model.py -a

echo "=== Running SAT stage ==="
$PY SAT/STS_SAT_satisf.py -a

echo "=== Running SMT stage ==="
$PY SMT/smt_model.py -a

echo "=== Running CP stage ==="
$PY CP/CP_STS.py -a
