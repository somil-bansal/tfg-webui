#!/bin/bash

# Activate the virtual environment relative to the script's location
source "$(dirname "$0")/../.venv/bin/activate"

PORT="${PORT:-8080}"
uvicorn main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload