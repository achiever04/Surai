@echo off
echo ========================================
echo AI Surveillance Platform Setup
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo [1/10] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/10] Upgrading pip...
python -m pip install --upgrade pip

echo [3/10] Installing PyTorch (CPU version)...
pip install torch==2.1.1+cpu torchvision==0.16.1+cpu --index-url https://download.pytorch.org/whl/cpu

echo [4/10] Installing core dependencies...
pip install -r requirements.txt

echo [5/10] Installing Node.js dependencies (Frontend)...
cd frontend
call npm install
cd ..

echo [6/10] Checking Docker installation...
docker --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Docker not found. Please install Docker Desktop
    echo Download from: https://www.docker.com/products/docker-desktop/
    pause
)

echo [7/10] Creating necessary directories...
mkdir storage\local\evidence
mkdir storage\models\pretrained
mkdir storage\models\checkpoints
mkdir logs\backend
mkdir logs\ai_engine
mkdir logs\blockchain
mkdir data\watchlist
mkdir data\embeddings
mkdir data\temp

echo [8/10] Copying environment template...
copy .env.example .env

echo [9/10] Downloading pretrained models...
python scripts\download_models.py

echo [10/10] Initializing database schema...
REM Will be run after Docker containers start

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start Docker Desktop
echo 2. Run: docker-compose up -d
echo 3. Run: python scripts\init_database.py
echo 4. Run: python scripts\create_admin_user.py
echo 5. Start backend: cd backend ^&^& python -m app.main
echo 6. Start frontend: cd frontend ^&^& npm run dev
echo 7. Access dashboard: http://localhost:5173
echo.
pause