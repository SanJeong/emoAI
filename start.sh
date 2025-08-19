#!/bin/bash

echo "🚀 EmoAI 시작 스크립트"
echo "========================"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# .env 파일 확인
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다. .env.example을 복사합니다...${NC}"
    cp .env.example .env
    echo -e "${RED}❗ .env 파일에 OpenAI API 키를 설정해주세요!${NC}"
    exit 1
fi

# API 키 확인
if grep -q "your_openai_api_key_here" .env; then
    echo -e "${RED}❗ .env 파일에 OpenAI API 키를 설정해주세요!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 환경 설정 확인 완료${NC}"

# Python 가상환경 확인 및 생성
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📦 Python 가상환경 생성 중...${NC}"
    python3 -m venv .venv
fi

# 가상환경 활성화 및 패키지 설치
echo -e "${YELLOW}📦 Python 패키지 설치 중...${NC}"
source .venv/bin/activate
pip install -q -r server/requirements.txt

# Node 패키지 설치
echo -e "${YELLOW}📦 Node 패키지 설치 중...${NC}"
cd app/electron
if [ ! -d "node_modules" ]; then
    npm install
fi
cd ../..

# 백엔드 실행
echo -e "${GREEN}🔧 백엔드 서버 시작 (포트 8787)...${NC}"
source .venv/bin/activate
uvicorn server.main:app --host 127.0.0.1 --port 8787 --reload &
BACKEND_PID=$!

# 백엔드 시작 대기
sleep 3

# 프론트엔드 실행
echo -e "${GREEN}🖥️  프론트엔드 시작...${NC}"
cd app/electron
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}✨ EmoAI가 실행 중입니다!${NC}"
echo "백엔드: http://127.0.0.1:8787"
echo "프론트엔드: Electron 앱이 자동으로 열립니다"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"

# 종료 시그널 처리
trap "echo '종료 중...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# 프로세스 대기
wait
