@echo off
echo ========================================
echo Starting AI Surveillance Platform
echo ========================================

echo [1/6] Starting Docker containers...
docker-compose up -d
timeout /t 10

echo [2/6] Waiting for services to be ready...
timeout /t 20

echo [3/6] Starting Fabric network...
cd blockchain\fabric-network\scripts
call start_network.bat
cd ..\..\..

echo [4/6] Starting backend API...
start cmd /k "cd backend && ..\venv\Scripts\activate && python -m app.main"
timeout /t 5

echo [5/6] Starting frontend...
start cmd /k "cd frontend && npm run dev"
timeout /t 5

echo [6/6] Starting FL server (optional)...
REM start cmd /k "cd federated_learning && python fl_server.py"

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/api/v1/docs
echo.
pause