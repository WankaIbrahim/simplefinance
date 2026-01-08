@echo off
echo ========================================
echo INSTALLING DEPENDENCIES
echo ========================================

echo [1/2] Installing Backend (pip)...
cd backend
call pip install -r requirements.txt
cd ..

echo [2/2] Installing Frontend (npm)...
cd frontend
call npm install
cd ..

echo ========================================
echo STARTING SERVERS
echo ========================================

start "Backend Server" /d "backend" func start
start "Frontend Server" /d "frontend" npm start

echo.
echo Both servers are launching in separate windows.
pause