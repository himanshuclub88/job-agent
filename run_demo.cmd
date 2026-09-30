@echo off
setlocal

rem ============================================================
rem Project Configuration
rem ============================================================

set "PROJECT_NAME=AI JOB Assistant"
set "PROJECT=G:\Other computers\My Laptop\Study\AI\job-agent"
set "VENV=c:\venvs\job-agent\.venv"

rem ============================================================
rem Validation
rem ============================================================

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

rem ============================================================
rem Start Project
rem ============================================================

echo.
echo ============================================================
echo        %PROJECT_NAME%
echo ============================================================
echo.
echo Starting %PROJECT_NAME%...
echo.

wt ^
  --title "%PROJECT_NAME% - Backend" ^
  cmd /k "call ""%VENV%\Scripts\activate.bat"" && cd /d ""%PROJECT%"" && echo [%PROJECT_NAME% - Backend] && echo http://127.0.0.1:8000 && uvicorn server:app --reload" ^
  ; split-pane -V ^
  --title "%PROJECT_NAME% - Frontend" ^
  cmd /k "call ""%VENV%\Scripts\activate.bat"" && cd /d ""%PROJECT%\frontend"" && echo [%PROJECT_NAME% - Frontend] && echo http://127.0.0.1:5500 && python -m http.server 5500"

rem ============================================================
rem Open Frontend
rem ============================================================

timeout /t 3 /nobreak >nul

start "" "http://127.0.0.1:5500"

echo.
echo ============================================================
echo        %PROJECT_NAME% Started
echo ============================================================
echo.
echo Backend  : http://127.0.0.1:8000
echo Frontend : http://127.0.0.1:5500
echo.
echo Backend and Frontend are running side-by-side.
echo.

endlocal