@echo off
echo Stopping all services...

echo [1/3] Stopping Docker containers...
docker-compose down

echo [2/3] Stopping Fabric network...
cd blockchain\fabric-network\scripts
call stop_network.bat
cd ..\..\..

echo [3/3] Killing Python and Node processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul

echo.
echo All services stopped!
pause