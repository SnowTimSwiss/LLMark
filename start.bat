@echo off
setlocal
cd /d "%~dp0"

:: Überprüfen ob Ollama installiert ist
where ollama >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Ollama ist nicht installiert. Installiere Ollama via winget...
    winget install Ollama.Ollama
    if %ERRORLEVEL% neq 0 (
        echo Installation fehlgeschlagen. Bitte installiere Ollama manuell von https://ollama.com
        pause
        exit /b 1
    )
    :: Pfad aktualisieren damit ollama sofort bekannt ist
    set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Ollama"
)

:: Überprüfen ob Ollama läuft
curl -s http://localhost:11434 >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Starte Ollama Server...
    start /b "" ollama serve
    echo Warte auf Ollama-Server...
    set count=0
    :wait_ollama
    timeout /t 2 /nobreak >nul
    set /a count+=1
    curl -s http://localhost:11434 >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        if %count% geq 20 (
            echo Ollama-Server konnte nicht gestartet werden.
            pause
            exit /b 1
        )
        goto wait_ollama
    )
)

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
