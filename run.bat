@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================
echo   斗鱼主播等级排行榜 - DouyuRank
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

:: Check dependencies
python -c "import aiohttp" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing aiohttp...
    pip install aiohttp
)

echo [1/3] Running full test suite...
python test_project.py
if %errorlevel% neq 0 (
    echo [WARN] Some tests failed, check output above
)

echo.
echo [2/3] Running scraper to fetch live data...
echo This will take 3-5 minutes for ~5500 streamers...
python scraper.py
if %errorlevel% neq 0 (
    echo [ERROR] Scraper failed
    pause
    exit /b 1
)

echo.
echo [3/3] Starting local HTTP server...
echo.
echo ========================================
echo   Open: http://localhost:8080
echo   Press Ctrl+C to stop the server
echo ========================================
echo.

start http://localhost:8080
python -m http.server 8080
pause
