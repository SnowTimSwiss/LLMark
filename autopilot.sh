#!/bin/bash

# LLMark Auto-Pilot Setup & Execution (Linux Version)

echo "========================================================"
echo "       LLMark Auto-Pilot Setup & Execution"
echo "========================================================"
echo ""
echo "To use the Auto-Pilot, you need a GitHub Token."
echo "You can create it here:"
echo "https://github.com/settings/tokens/new"
echo ""
echo "IMPORTANT: The token needs the 'public_repo' scope."
echo ""

read -p "Please enter your GitHub Token: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "No token entered. Aborting."
    exit 1
fi

echo ""
read -p "Should Ollama and all models be uninstalled after completion? (y/n): " UNINSTALL_AFTER

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed. Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "Installation failed. Please install Ollama manually from https://ollama.com"
        exit 1
    fi
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434 > /dev/null; then
    echo "Starting Ollama Server..."
    ollama serve > /dev/null 2>&1 &
    
    echo "Waiting for Ollama server..."
    count=0
    until curl -s http://localhost:11434 > /dev/null; do
        sleep 2
        count=$((count + 1))
        if [ $count -ge 20 ]; then
            echo "Ollama server could not be started."
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

echo "Starting LLMark in Auto-Pilot mode..."
python3 app.py --autopilot --token "$GITHUB_TOKEN"

if [ "$UNINSTALL_AFTER" = "y" ]; then
    echo ""
    echo "========================================================"
    echo "       Cleanup is being performed..."
    echo "========================================================"
    
    echo "Terminating Ollama processes..."
    pkill ollama
    
    echo "Uninstalling Ollama..."
    # On Linux, Ollama is often installed to /usr/local/bin/ollama
    if [ -f "/usr/local/bin/ollama" ]; then
        sudo rm /usr/local/bin/ollama
    fi
    
    # If it runs as a systemd service (as the installer does)
    if systemctl is-active --quiet ollama; then
        sudo systemctl stop ollama
        sudo systemctl disable ollama
        sudo rm /etc/systemd/system/ollama.service
    fi

    echo "Deleting Ollama data (models) in ~/.ollama ..."
    if [ -d "$HOME/.ollama" ]; then
        rm -rf "$HOME/.ollama"
    fi
    
    echo "Deleting local virtual environment (.venv)..."
    if [ -d ".venv" ]; then
        # Deactivate first if inside venv
        deactivate 2>/dev/null || true
        rm -rf ".venv"
    fi
    
    echo "Cleanup completed."
fi

echo ""
echo "Auto-Pilot run finished."
