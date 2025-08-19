@echo off
echo 🚀 EmoAI 시작 스크립트
echo ========================

REM .env 파일 확인
if not exist .env (
    echo ⚠️  .env 파일이 없습니다. .env.example을 복사합니다...
    copy .env.example .env
    echo ❗ .env 파일에 OpenAI API 키를 설정해주세요!
    pause
    exit /b 1
)

REM API 키 확인
findstr "your_openai_api_key_here" .env >nul
if %errorlevel%==0 (
    echo ❗ .env 파일에 OpenAI API 키를 설정해주세요!
    pause
    exit /b 1
)

echo ✅ 환경 설정 확인 완료

REM Python 가상환경 확인 및 생성
if not exist .venv (
    echo 📦 Python 가상환경 생성 중...
    python -m venv .venv
)

REM 가상환경 활성화 및 패키지 설치
echo 📦 Python 패키지 설치 중...
call .venv\Scripts\activate
pip install -q -r server\requirements.txt

REM Node 패키지 설치
echo 📦 Node 패키지 설치 중...
cd app\electron
if not exist node_modules (
    npm install
)
cd ..\..

REM 백엔드 실행
echo 🔧 백엔드 서버 시작 (포트 8787)...
start /b cmd /c "call .venv\Scripts\activate && uvicorn server.main:app --host 127.0.0.1 --port 8787 --reload"

REM 백엔드 시작 대기
timeout /t 3 /nobreak >nul

REM 프론트엔드 실행
echo 🖥️  프론트엔드 시작...
cd app\electron
start /b npm run dev

echo ✨ EmoAI가 실행 중입니다!
echo 백엔드: http://127.0.0.1:8787
echo 프론트엔드: Electron 앱이 자동으로 열립니다
echo.
echo 종료하려면 이 창을 닫으세요
pause
