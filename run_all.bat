@echo off
start "SmartPantry Backend" /D "%~dp0backend" cmd /k run_backend.bat
echo Starting the backend. The first setup may take a few minutes.
timeout /t 8 /nobreak >nul
start "SmartPantry Frontend" /D "%~dp0frontend" cmd /k run_frontend.bat
echo.
echo Frontend: http://127.0.0.1:5173
echo Backend API: http://127.0.0.1:8000/docs
echo Keep both terminal windows open while using SmartPantry.
