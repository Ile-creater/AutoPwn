@echo off
chcp 65001 >nul
title AutoPwn Setup

echo.
echo   ╔════════════════════════════════╗
echo   ║     AutoPwn 安装脚本           ║
echo   ╚════════════════════════════════╝
echo.

:: ====== Python ======
echo [1/5] 检查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [×] 没装 Python，先去 https://python.org 下载
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do echo   [√] Python %%v

:: ====== Node.js ======
echo [2/5] 检查 Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [×] 没装 Node.js，先去 https://nodejs.org 下载 LTS 版
    pause & exit /b 1
)
for /f "tokens=1 delims=v" %%v in ('node --version 2^>^&1') do echo   [√] Node.js v%%v

:: ====== pip install ======
echo [3/5] 安装 Python 依赖...
cd /d "%~dp0"
pip install -r backend\requirements.txt -q 2>&1
if %errorlevel% neq 0 (
    echo   [!] pip install 有点问题，但不一定影响运行
) else (
    echo   [√] fastapi + uvicorn + websockets + requests
)

:: ====== npm install ======
echo [4/5] 安装前端依赖...
cd frontend
call npm install --silent 2>&1
if %errorlevel% neq 0 (
    echo   [!] npm install 有点问题
) else (
    echo   [√] Next.js + React + Tailwind
)
cd ..

:: ====== 目录 ======
echo [5/5] 创建工作区...
if not exist "workspace" mkdir workspace
if not exist "submitted" mkdir submitted
if not exist "knowledge" mkdir knowledge
echo   [√] workspace / submitted / knowledge

echo.
echo   ╔════════════════════════════════╗
echo   ║  安装完成！                    ║
echo   ╠════════════════════════════════╣
echo   ║  启动：双击 start.bat           ║
echo   ║  或者手动开两个终端：           ║
echo   ║                                ║
echo   ║  终端1: python -m uvicorn       ║
echo   ║          backend.main:app       ║
echo   ║          --port 8000            ║
echo   ║                                ║
echo   ║  终端2: cd frontend ^&^&         ║
echo   ║          npm run dev            ║
echo   ╚════════════════════════════════╝
echo.

:: Ollama 可选提示
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Ollama 没装，AI 推理会用不了
    echo       安装：winget install Ollama.Ollama
    echo       拉模型：ollama pull qwen2.5:3b
)

:: Docker 可选
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Docker 没装，沙箱模式不可用（不影响基本运行）
)

echo.
pause
