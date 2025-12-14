@echo off
echo.
echo ========================================
echo   VIDOCQ - Intelligence Autonome
echo   Demarrage du systeme...
echo ========================================
echo.

REM Check if Redis is running
echo [1/3] Verification de Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [!] Redis n'est pas demarre. Lancez Redis d'abord.
    pause
    exit /b 1
)
echo [OK] Redis connecte

REM Start Celery worker in background
echo [2/3] Demarrage du worker Celery...
start "Vidocq Worker" cmd /c "celery -A src.ingestion.tasks worker -Q celery,parse_queue --loglevel=info -P solo"
timeout /t 3 >nul
echo [OK] Worker demarre

REM Start FastAPI server
echo [3/3] Demarrage du serveur API...
echo.
echo ========================================
echo   Vidocq est pret!
echo   
echo   Interface: http://localhost:8000/ui
echo   API Docs:  http://localhost:8000/docs
echo ========================================
echo.

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
