#!/usr/bin/env bash
export PYTHONPATH="$PYTHONPATH:src"
exec python -m con-espressione "$@"
