@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
    echo Erstelle virtuelles Environment...
    python -m venv .venv
)

echo Aktiviere Environment und installiere Requirements...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo Starte LLMark...
python app.py

pause
