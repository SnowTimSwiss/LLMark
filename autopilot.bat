@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo        LLMark Auto-Pilot Setup ^& Execution
echo ========================================================
echo.
echo Um den Auto-Pilot zu nutzen, benoetigst du einen GitHub Token.
echo Diesen kannst du hier erstellen:
echo https://github.com/settings/tokens/new
echo.
echo WICHTIG: Der Token braucht das Recht 'public_repo'.
echo.

set /p GITHUB_TOKEN="Bitte gib deinen GitHub Token ein: "

if "%GITHUB_TOKEN%"=="" (
    echo Kein Token eingegeben. Abbruch.
    pause
    exit /b 1
)

echo.
set /p UNINSTALL_AFTER="Sollen Ollama und alle Modelle nach Abschluss wieder deinstalliert werden? (j/n): "

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

echo Starte LLMark im Auto-Pilot Modus...
python app.py --autopilot --token "%GITHUB_TOKEN%"

if /i "%UNINSTALL_AFTER%"=="j" (
    echo.
    echo ========================================================
    echo        Bereinigung (Cleanup) wird ausgefuehrt...
    echo ========================================================
    
    echo Beende Ollama Prozesse...
    taskkill /F /IM ollama.exe >nul 2>nul
    
    echo Deinstalliere Ollama via winget...
    winget uninstall Ollama.Ollama
    
    echo Loesche Ollama Daten (Modelle) in %USERPROFILE%\.ollama ...
    if exist "%USERPROFILE%\.ollama" (
        rd /s /q "%USERPROFILE%\.ollama"
    )
    
    echo Loesche lokales virtuelles Environment (.venv)...
    if exist ".venv" (
        :: Wir muessen das venv verlassen, um es zu loeschen (da wir in der shell sind)
        :: Aber da python beendet ist, ist der Lock meist weg.
        rd /s /q ".venv"
    )
    
    echo Bereinigung abgeschlossen.
)

echo.
echo Auto-Pilot Durchlauf beendet.
pause
