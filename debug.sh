#!/bin/bash

# Exit on error
set -e

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project root directory
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Virtual environment not found. Please create one first."
    exit 1
fi

# Sync dependencies
echo "Syncing dependencies..."
uv sync

# Start backend in debug mode
echo "Starting backend in debug mode..."
cd backend
PYTHONPATH=$PYTHONPATH:. uvicorn the_finance_genie.main:app --host "0.0.0.0" --port "8080" --reload --log-level debug &

# Wait a moment for backend to start
sleep 2

# Start frontend in debug mode
echo "Starting frontend in debug mode..."
cd ..
npm run dev

# Trap SIGINT to kill background processes
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT 