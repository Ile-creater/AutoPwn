@echo off
chcp 65001 >nul
title AutoPwn

echo.
echo   ╔═══════════════════════╗
echo   ║   AutoPwn 启动中...   ║
echo   ╚═══════════════════════╝
echo.

cd /d "%~dp0"

:: 后端
start "AutoPwn Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: 等后端起来
echo   等后端起来...
timeout /t 3 /nobreak >nul

:: 前端
start "AutoPwn Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo   浏览器打开 → http://localhost:3000
echo.

timeout /t 5 /nobreak >nul
