@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo        LLMark Auto-Pilot Setup ^& Execution
echo ========================================================
echo.
echo To use the Auto-Pilot, you need a GitHub Token.
echo You can create it here:
echo https://github.com/settings/tokens/new
echo.
echo IMPORTANT: The token needs the 'public_repo' scope.
echo.

set /p GITHUB_TOKEN="Please enter your GitHub Token: "

if "%GITHUB_TOKEN%"=="" (
    echo No token entered. Aborting.
    pause
    exit /b 1
)

echo.
set /p UNINSTALL_AFTER="Should Ollama and all models be uninstalled after completion? (y/n): "

:: Überprüfen ob Ollama installiert ist
where ollama >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Ollama is not installed. Installing Ollama via winget...
    winget install Ollama.Ollama
    if %ERRORLEVEL% neq 0 (
        echo Installation failed. Please install Ollama manually from https://ollama.com
        pause
        exit /b 1
    )
    :: Update path so ollama is recognized immediately
    set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Ollama"
)

:: Überprüfen ob Ollama läuft
curl -s http://localhost:11434 >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Starting Ollama Server...
    start /b "" ollama serve
    echo Waiting for Ollama server...
    set count=0
    :wait_ollama
    timeout /t 2 /nobreak >nul
    set /a count+=1
    curl -s http://localhost:11434 >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        if %count% geq 20 (
            echo Ollama server could not be started.
            pause
            exit /b 1
        )
        goto wait_ollama
    )
)

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating environment and installing requirements...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo Starting LLMark in Auto-Pilot mode...
python app.py --autopilot --token "%GITHUB_TOKEN%"

if /i "%UNINSTALL_AFTER%"=="y" (
    echo.
    echo ========================================================
    echo        Cleanup is being performed...
    echo ========================================================
    
    echo Terminating Ollama processes...
    taskkill /F /IM ollama.exe >nul 2>nul
    
    echo Uninstalling Ollama via winget...
    winget uninstall Ollama.Ollama
    
    echo Deleting Ollama data (models) in %USERPROFILE%\.ollama ...
    if exist "%USERPROFILE%\.ollama" (
        rd /s /q "%USERPROFILE%\.ollama"
    )
    
    echo Deleting local virtual environment (.venv)...
    if exist ".venv" (
        :: We must leave the venv to delete it (since we are in the shell)
        :: But since python has terminated, the lock is usually gone.
        rd /s /q ".venv"
    )
    
    echo Cleanup completed.
)

echo.
echo Auto-Pilot run finished.
pause
