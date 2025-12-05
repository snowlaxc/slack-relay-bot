#!/bin/bash

# Slack Relay Bot - 설치 스크립트
set -e

echo "🚀 Slack Relay Bot 설치를 시작합니다..."

# Python 버전 확인
echo "📌 Python 버전 확인 중..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3가 설치되어 있지 않습니다."
    echo "   Python 3.9 이상을 설치해주세요."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "   ✅ Python $PYTHON_VERSION 감지됨"

# pip 명령어 결정 (가상환경 우선)
PIP_CMD="pip3"

# 가상환경 생성 (선택사항)
if [ ! -d "venv" ]; then
    echo ""
    read -p "🤔 가상환경(venv)을 생성하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 가상환경 생성 중..."
        python3 -m venv venv
        echo "   ✅ 가상환경 생성 완료"
        # 가상환경 pip 사용
        PIP_CMD="venv/bin/pip"
        echo ""
        echo "✅ 가상환경을 자동으로 사용합니다."
    fi
else
    echo "ℹ️  가상환경이 이미 존재합니다."
    # 기존 가상환경 pip 사용
    PIP_CMD="venv/bin/pip"
fi

# 의존성 설치
echo ""
echo "📦 Python 패키지 설치 중..."
$PIP_CMD install -r requirements.txt
echo "   ✅ 패키지 설치 완료"

# 환경 변수 파일 생성
echo ""
if [ ! -f ".env" ]; then
    echo "📝 환경 변수 파일 생성 중..."
    cp .env.example .env
    echo "   ✅ .env 파일이 생성되었습니다"
    echo ""
    echo "⚠️  중요: .env 파일을 편집하여 Slack 토큰을 입력하세요:"
    echo "   - SLACK_BOT_TOKEN"
    echo "   - SLACK_SIGNING_SECRET"
    echo "   - SLACK_APP_TOKEN"
    echo ""
    read -p "지금 편집하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
else
    echo "⚠️  .env 파일이 이미 존재합니다. 건너뜁니다."
fi

echo ""
echo "✅ 설치가 완료되었습니다!"
echo ""
echo "📖 다음 단계:"
echo "   1. README.md의 'Slack 앱 설정' 섹션을 따라 Slack 앱을 생성하세요"
echo "   2. .env 파일에 Slack 토큰을 입력하세요"
echo "   3. ./run.sh 명령어로 봇을 실행하세요"
echo ""
