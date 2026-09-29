@echo off
setlocal

rem ============================================================
rem AI Data Engineering Copilot - Offline Demo Launcher
rem Starts Backend and Frontend in separate CMD windows.
rem ============================================================

set "PROJECT=G:\Other computers\My Laptop\Study\AI\job-agent"
set "VENV=c:\venvs\job-agent\.venv"

if not exist "%VENV%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found:
    echo %VENV%\Scripts\activate.bat
    pause
    exit /b 1
)

if not exist "%PROJECT%\server.py" (
    echo [ERROR] server.py not found:
    echo %PROJECT%\server.py
    pause
    exit /b 1
)

if not exist "%PROJECT%\frontend\index.html" (
    echo [ERROR] frontend\index.html not found:
    echo %PROJECT%\frontend\index.html
    pause
    exit /b 1
)

echo.
echo Starting AI Data Engineering Copilot...
echo.

start "AI Copilot - Backend" cmd /k "call ""%VENV%\Scripts\activate.bat"" && cd /d ""%PROJECT%"" && echo [Backend] http://127.0.0.1:8000 && uvicorn server:app --reload"

rem Wait 5 seconds
timeout /t 5 /nobreak >nul

start "AI Copilot - Frontend" cmd /k "call ""%VENV%\Scripts\activate.bat"" && cd /d ""%PROJECT%\frontend"" && echo [Frontend] http://127.0.0.1:5500 && python -m http.server 5500"

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5500"

echo.
echo Backend:  http://127.0.0.1:8080
echo Frontend: http://127.0.0.1:5500
echo.
echo Two CMD windows were opened.
echo Close those windows to stop the demo.
echo.