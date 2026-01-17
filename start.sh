#!/bin/bash

# Ensure script is run from its directory
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating environment and installing requirements..."
source .venv/bin/activate

pip install -r requirements.txt

echo "Starting LLMark..."
python app.py
