#!/usr/bin/env bash
# Foreground run (used by start.sh). Paper only, stdlib python.
cd "$(dirname "$0")"
exec python3 -u funding_carry.py >> logs/stdout.log 2>&1
