@echo off
echo === Building AutoPwn Agent Sandbox ===
cd /d %~dp0..
docker build -t auto-pwn-agent -f docker\Dockerfile .
if %errorlevel% equ 0 (
    echo.
    echo Build OK. Run: docker run --rm auto-pwn-agent python /app/agents/crypto_agent.py
) else (
    echo Build FAILED.
)
pause
