#!/bin/bash

# Slack Relay Bot - 실행 스크립트
set -e

echo "🤖 Slack Relay Bot을 시작합니다..."

# 환경 변수 파일 확인
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다."
    echo "   먼저 ./install.sh를 실행하여 설치를 완료하세요."
    exit 1
fi

# .env 파일에서 환경 변수 로드
set -a
source .env
set +a

# Python 경로 결정 (가상환경 우선)
if [ -d "venv" ]; then
    PYTHON="venv/bin/python3"
    echo "📦 가상환경 사용 중"
else
    PYTHON="python3"
fi

# 봇 실행
echo "🚀 봇 실행 중..."
echo "   종료하려면 Ctrl+C를 누르세요"
echo ""

$PYTHON -m src.main

