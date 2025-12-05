#!/bin/bash

# Slack Relay Bot - systemd 배포 스크립트
set -e

echo "🚀 Slack Relay Bot을 systemd 서비스로 배포합니다..."

# 환경 변수 파일 확인
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다."
    echo "   먼저 ./install.sh를 실행하여 설치를 완료하세요."
    exit 1
fi

# 현재 디렉토리 및 사용자 정보
WORK_DIR="$(pwd)"
USER_NAME="$(whoami)"

# Python 경로 결정
if [ -d "venv" ]; then
    PYTHON_PATH="$WORK_DIR/venv/bin/python3"
else
    PYTHON_PATH="$(which python3)"
fi

# 로그 디렉토리 생성
mkdir -p logs

# systemd 서비스 파일 생성
SERVICE_NAME="slack-relay"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "📝 systemd 서비스 파일 생성 중..."
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Slack Relay Bot
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$WORK_DIR
Environment="PATH=$WORK_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PYTHON_PATH -m src.main
Restart=always
RestartSec=10
StandardOutput=append:$WORK_DIR/logs/output.log
StandardError=append:$WORK_DIR/logs/error.log

# 보안 설정
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "   ✅ 서비스 파일 생성 완료: $SERVICE_FILE"

# systemd 데몬 리로드
echo "🔄 systemd 데몬 리로드 중..."
sudo systemctl daemon-reload

# 기존 서비스 중지 (있다면)
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "⏹️  기존 서비스 중지 중..."
    sudo systemctl stop "$SERVICE_NAME"
fi

# 서비스 활성화 및 시작
echo "🚀 서비스 시작 중..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

# 잠시 대기
sleep 2

# 상태 확인
echo ""
echo "📊 서비스 상태:"
sudo systemctl status "$SERVICE_NAME" --no-pager || true

echo ""
echo "✅ 배포가 완료되었습니다!"
echo ""
echo "📖 유용한 명령어:"
echo "   sudo systemctl status $SERVICE_NAME       # 상태 확인"
echo "   sudo systemctl restart $SERVICE_NAME      # 재시작"
echo "   sudo systemctl stop $SERVICE_NAME         # 중지"
echo "   sudo systemctl start $SERVICE_NAME        # 시작"
echo "   sudo systemctl disable $SERVICE_NAME      # 자동 시작 비활성화"
echo "   sudo journalctl -u $SERVICE_NAME -f       # 실시간 로그 보기"
echo "   sudo journalctl -u $SERVICE_NAME -n 100   # 최근 100줄 로그"
echo "   sudo journalctl -u $SERVICE_NAME -p err   # 에러 로그만 보기"
echo ""
echo "📁 로그 파일 위치:"
echo "   $WORK_DIR/logs/output.log  # 표준 출력"
echo "   $WORK_DIR/logs/error.log   # 에러 로그"
echo ""
