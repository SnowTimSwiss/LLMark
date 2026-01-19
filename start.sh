#!/bin/bash

# Ensure script is run from its directory
cd "$(dirname "$0")"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Check if ollama is running
if ! curl -s http://localhost:11434 &> /dev/null; then
    echo "Starting Ollama server..."
    ollama serve &
    # Wait for it to start
    echo "Waiting for Ollama to be ready..."
    max_retries=30
    count=0
    while ! curl -s http://localhost:11434 &> /dev/null; do
        sleep 1
        count=$((count + 1))
        if [ $count -ge $max_retries ]; then
            echo "Failed to start Ollama server."
            exit 1
        fi
    done
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating environment and installing requirements..."
source .venv/bin/activate

pip install -r requirements.txt

echo "Starting LLMark..."
python app.py
