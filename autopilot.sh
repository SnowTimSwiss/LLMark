#!/bin/bash

# LLMark Auto-Pilot Setup & Execution (Linux Version)

echo "========================================================"
echo "       LLMark Auto-Pilot Setup & Execution"
echo "========================================================"
echo ""
echo "Um den Auto-Pilot zu nutzen, benoetigst du einen GitHub Token."
echo "Diesen kannst du hier erstellen:"
echo "https://github.com/settings/tokens/new"
echo ""
echo "WICHTIG: Der Token braucht das Recht 'public_repo'."
echo ""

read -p "Bitte gib dener GitHub Token ein: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Kein Token eingegeben. Abbruch."
    exit 1
fi

echo ""
read -p "Sollen Ollama und alle Modelle nach Abschluss wieder deinstalliert werden? (j/n): " UNINSTALL_AFTER

# Überprüfen ob Ollama installiert ist
if ! command -v ollama &> /dev/null; then
    echo "Ollama ist nicht installiert. Installiere Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "Installation fehlgeschlagen. Bitte installiere Ollama manuell von https://ollama.com"
        exit 1
    fi
fi

# Überprüfen ob Ollama läuft
if ! curl -s http://localhost:11434 > /dev/null; then
    echo "Starte Ollama Server..."
    ollama serve > /dev/null 2>&1 &
    
    echo "Warte auf Ollama-Server..."
    count=0
    until curl -s http://localhost:11434 > /dev/null; do
        sleep 2
        count=$((count + 1))
        if [ $count -ge 20 ]; then
            echo "Ollama-Server konnte nicht gestartet werden."
            exit 1
        fi
    done
fi

if [ ! -d ".venv" ]; then
    echo "Erstelle virtuelles Environment..."
    python3 -m venv .venv
fi

echo "Aktiviere Environment und installiere Requirements..."
source .venv/bin/activate
pip install -r requirements.txt

echo "Starte LLMark im Auto-Pilot Modus..."
python3 app.py --autopilot --token "$GITHUB_TOKEN"

if [ "$UNINSTALL_AFTER" = "j" ]; then
    echo ""
    echo "========================================================"
    echo "       Bereinigung (Cleanup) wird ausgefuehrt..."
    echo "========================================================"
    
    echo "Beende Ollama Prozesse..."
    pkill ollama
    
    echo "Deinstalliere Ollama..."
    # Auf Linux wird Ollama oft nach /usr/local/bin/ollama installiert
    if [ -f "/usr/local/bin/ollama" ]; then
        sudo rm /usr/local/bin/ollama
    fi
    
    # Falls es als systemd service läuft (was der installer macht)
    if systemctl is-active --quiet ollama; then
        sudo systemctl stop ollama
        sudo systemctl disable ollama
        sudo rm /etc/systemd/system/ollama.service
    fi

    echo "Loesche Ollama Daten (Modelle) in ~/.ollama ..."
    if [ -d "$HOME/.ollama" ]; then
        rm -rf "$HOME/.ollama"
    fi
    
    echo "Loesche lokales virtuelles Environment (.venv)..."
    if [ -d ".venv" ]; then
        # Deactivate first if inside venv
        deactivate 2>/dev/null || true
        rm -rf ".venv"
    fi
    
    echo "Bereinigung abgeschlossen."
fi

echo ""
echo "Auto-Pilot Durchlauf beendet."
