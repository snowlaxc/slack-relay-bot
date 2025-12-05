# Slack Relay Bot

외부 시스템에서 간단한 `curl` 명령어 하나로 당신의 Slack DM으로 메시지나 파일을 전송할 수 있는 중계 봇입니다.

## 주요 기능

- **간편한 메시지 전송**: HTTP 요청만으로 Slack DM에 메시지 전송
- **파일 업로드**: 로그 파일, 이미지, 보고서 등 모든 파일 전송 가능
- **셀프 서비스**: 슬래시 명령어로 API Key 직접 관리
- **보안**: IP 화이트리스트 + API Key 인증 이중 보안

> [!NOTE]
> **파일 저장 위치**: 업로드된 파일은 Slack의 클라우드 저장소에 저장됩니다. relay 봇 서버에는 파일이 저장되지 않으며, 단지 HTTP 요청을 Slack API로 중계할 뿐입니다. 업로드된 파일은 Slack 워크스페이스의 "파일" 섹션에서 관리할 수 있습니다.

> [!IMPORTANT]
> **삭제 권한**:
> - **메시지**: 봇이 보낸 메시지는 **봇만 삭제 가능**하며, 사용자는 직접 삭제할 수 없습니다. (Slack의 기본 동작)
> - **파일**: DM으로 전송받은 사용자 본인과 워크스페이스 관리자가 직접 삭제할 수 있습니다.

## 사전 준비

### 1. Slack 앱 생성 및 설정

1. [Slack API Apps](https://api.slack.com/apps) 접속 후 **Create New App** 클릭 → **From scratch** 선택
2. 앱 이름(예: `Relay Bot`)과 워크스페이스 선택

#### Socket Mode 활성화
3. **Socket Mode** 메뉴 클릭:
   - **Enable Socket Mode** 활성화
   - 토큰 이름 입력 후 생성 → **`SLACK_APP_TOKEN`** (xapp-...) 복사

#### 권한 설정
4. **OAuth & Permissions** 메뉴 클릭:
   - **Bot Token Scopes**에 다음 권한 추가:
     - `chat:write` - 메시지 보내기
     - `im:write` - 다이렉트 메시지 (DM) 보내기 (필수)
     - `files:write` - 파일 업로드
     - `commands` - 슬래시 커맨드 사용
   - **Install to Workspace** 클릭 → **`SLACK_BOT_TOKEN`** (xoxb-...) 복사

#### 기본 정보
5. **Basic Information** 메뉴 클릭:
   - **Signing Secret** → **`SLACK_SIGNING_SECRET`** 복사

#### 슬래시 명령어 등록
6. **Slash Commands** 메뉴 클릭:
   3. **Slash Commands** 섹션에서 다음 명령어를 추가:
      - `/relay-help` - Request URL: 공란 (Socket Mode 사용)
      - `/relay-key` - Request URL: 공란 (Socket Mode 사용)
      - `/relay-delete` - Request URL: 공란 (Socket Mode 사용)
      - `/relay-stop` - Request URL: 공란 (Socket Mode 사용)

#### Interactivity 활성화
7. **Interactivity & Shortcuts** 메뉴 클릭:
   - **Interactivity** 활성화 (ON으로 전환)
   - Request URL: 공란 (Socket Mode 사용)
   - 이 설정은 메시지 삭제 버튼을 활성화하는 데 필요합니다


### 2. 설치 및 설정

터미널에서 프로젝트 폴더(`slack-relay`)로 이동한 후 진행해주세요.

### 방법 1: 간편 설치 (권장)

**한 번에 설치:**
```bash
./install.sh
```

이 스크립트는 자동으로:
- Python 버전 확인
- 가상환경 생성 (선택)
- 필수 패키지 설치
- `.env` 파일 생성

**실행:**
```bash
./run.sh
```

**프로덕션 배포 (PM2):**
```bash
./deploy.sh
```

### 방법 2: 수동 설치

```bash
# 저장소 이동
cd slack-relay

# Python 가상환경 생성 (선택사항)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### 1) 패키지 설치

```bash
pip3 install -r requirements.txt
```

#### 2) 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 Slack 토큰을 입력하세요:

```bash
cp .env.example .env
```

`.env` 파일 수정:
```bash
# Slack 설정 (위에서 복사한 값 입력)
SLACK_BOT_TOKEN=xoxb-1234567890...
SLACK_SIGNING_SECRET=abc123...
SLACK_APP_TOKEN=xapp-1-ABC123...

# FastAPI 설정
PORT=8000
SERVER_URL=http://your-server-ip:8000  # 외부에서 접근 가능한 서버 주소 (예: http://192.168.1.100:8000)

# 보안 설정 (기본값: 사설망 IP만 허용)
ALLOWED_IPS=127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16

# 파일 업로드 설정 (바이트 단위)
MAX_FILE_SIZE=104857600  # 100MB (기본값, 필요시 조정 가능)

# 데이터베이스
DATABASE_PATH=./relay.db
```

> [!IMPORTANT]
> **DM 전용**: 이 봇은 API Key 소유자의 **일대일 다이렉트 메시지(DM)**로만 메시지를 전송합니다. 채널이나 그룹 DM으로는 전송되지 않습니다.

## 실행

### 방법 1: 스크립트 사용 (권장)

```bash
./run.sh
```

### 방법 2: 직접 실행

```bash
python3 -m src.main
```

실행 성공 시:
```
Starting Slack Relay Bot...
Slack bot started in Socket Mode
Starting FastAPI server on port 8000...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
Database initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 사용 방법

### 1. API Key 발급

Slack 워크스페이스에서:

```
/relay-key
```

발급된 API Key를 안전한 곳에 보관하세요.

### 2. API 문서 확인 (선택)

봇 실행 후, 사설망 내에서 API 문서에 접근할 수 있습니다:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

> [!IMPORTANT]
> API 문서는 **IP 화이트리스트로 보호**됩니다. 사설망 IP에서만 접근 가능합니다.

### 3. 메시지 전송

외부 시스템(서버, 로컬 스크립트 등)에서:

#### 텍스트 메시지만 전송
```bash
curl -X POST http://your-server:8000/send \
  -H "Authorization: Bearer relay_live_YOUR_API_KEY" \
  -F "text=배치 작업이 완료되었습니다!"
```

#### 파일과 메시지 함께 전송
```bash
curl -X POST http://your-server:8000/send \
  -H "Authorization: Bearer relay_live_YOUR_API_KEY" \
  -F "text=에러 로그입니다" \
  -F "file=@./error.log"
```

#### 파일만 전송
```bash
curl -X POST http://your-server:8000/send \
  -H "Authorization: Bearer relay_live_YOUR_API_KEY" \
  -F "file=@./result.png"
```

## 슬랙 명령어

- **사용 가이드**: `/relay-help` - 모달로 전체 가이드 확인 (API 사용법, 명령어 목록, 삭제 방법 등)
- **API Key 발급/재발급**: `/relay-key` - 새 키 발급 (기존 키가 있으면 자동으로 무효화하고 재발급)
- **서비스 중단**: `/relay-stop` - API Key 삭제 및 서비스 중단 (재사용 시 `/relay-key`로 재발급)
- **메시지 삭제**: 
  - `/relay-delete [N]` - 최근 N개 메시지 확인 후 삭제 (기본 10개)
  - `/relay-delete all` - 전체 메시지 일괄 삭제

### 메시지 삭제 방법

1. **삭제 버튼 사용 (가장 간편)**
   - 텍스트 메시지: "🗑️ 삭제" 버튼 클릭
   - 파일 메시지: "🗑️ 파일 삭제" 버튼 클릭 (파일과 함께 업로드한 텍스트도 함께 삭제됨)

2. **명령어로 일괄 삭제**
   - `/relay-delete 10` - 최근 10개 확인 후 삭제
   - `/relay-delete all` - 전체 메시지 확인 후 삭제
   - 파일도 함께 삭제됨

3. **HTTP API로 삭제 (자동화용)**
   ```bash
   curl -X DELETE http://server:8000/delete \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -F "message_ts=1234567890.123456"
   ```
   > 참고: `/send` 응답의 `message_ts` 값을 저장해두었다가 사용

## 보안 설정

### IP 화이트리스트

`.env` 파일의 `ALLOWED_IPS`에서 허용할 IP 대역을 설정하세요:

```bash
# 예시 1: 사설망만 허용 (기본값)
ALLOWED_IPS=127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16

# 예시 2: 특정 IP만 허용
ALLOWED_IPS=127.0.0.1,203.0.113.0/24

# 예시 3: 모든 IP 허용 (주의: 프로덕션 환경에서는 권장하지 않음)
ALLOWED_IPS=0.0.0.0/0
```

### 파일 업로드 크기 제한

`.env` 파일의 `MAX_FILE_SIZE`에서 최대 파일 크기를 설정하세요 (바이트 단위):

```bash
# 예시 1: 100MB (기본값)
MAX_FILE_SIZE=104857600

# 예시 2: 10MB (더 엄격한 제한)
MAX_FILE_SIZE=10485760

# 예시 3: 500MB
MAX_FILE_SIZE=524288000
```

> [!WARNING]
> **단일 파일 크기 제한**: Slack의 단일 파일 업로드 제한은 1GB입니다. `MAX_FILE_SIZE`를 1GB보다 크게 설정해도 Slack에서 거부됩니다.

> [!NOTE]
> **Slack 워크스페이스 저장소 용량**:
> - 무료 플랜: 전체 워크스페이스에서 5GB (오래된 파일부터 자동 삭제)
> - Standard 플랜: 멤버당 10GB
> - Plus 플랜: 멤버당 20GB
> - Enterprise 플랜: 멤버당 1TB

### API Key 보안

- API Key는 절대 공개 저장소에 커밋하지 마세요
- 유출 시 즉시 `/relay-key`를 다시 실행하여 재발급하세요
- 환경 변수나 비밀 관리 도구(Vault, AWS Secrets Manager 등)에 저장하세요

## 프로덕션 배포

### systemd 서비스로 배포 (권장)

**자동 배포 스크립트 사용:**
```bash
./deploy.sh
```

이 스크립트는 자동으로:
- systemd 서비스 파일 생성
- 서비스 활성화 (시스템 재부팅 시 자동 시작)
- 서비스 시작 및 상태 확인

**유용한 명령어:**
```bash
sudo systemctl status slack-relay     # 상태 확인
sudo systemctl restart slack-relay    # 재시작
sudo systemctl stop slack-relay       # 중지
sudo systemctl start slack-relay      # 시작
sudo journalctl -u slack-relay -f     # 실시간 로그 보기
sudo journalctl -u slack-relay -n 100 # 최근 100줄 로그
```

**로그 파일 위치:**
- 표준 출력: `./logs/output.log`
- 에러 로그: `./logs/error.log`

### 수동으로 systemd 서비스 등록

`/etc/systemd/system/slack-relay.service`:

```ini
[Unit]
Description=Slack Relay Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/slack-relay
Environment="PATH=/path/to/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/path/to/venv/bin/python3 -m src.main
Restart=always
RestartSec=10
StandardOutput=append:/path/to/slack-relay/logs/output.log
StandardError=append:/path/to/slack-relay/logs/error.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable slack-relay
sudo systemctl start slack-relay
sudo systemctl status slack-relay
```

## 문제 해결

### 봇이 응답하지 않아요
- Slack 앱의 Socket Mode가 활성화되어 있는지 확인
- `SLACK_APP_TOKEN`이 올바르게 설정되었는지 확인

### API 요청이 403 에러를 반환해요
- `ALLOWED_IPS`에 요청 서버의 IP가 포함되어 있는지 확인
- API Key가 올바른지 확인 (`/relay-key`로 재확인)

### 파일 업로드가 실패해요
- Slack 앱에 `files:write` 권한이 있는지 확인
- 파일 크기가 `MAX_FILE_SIZE` 설정값을 초과하지 않는지 확인
- 파일 크기가 Slack 제한(1GB)을 초과하지 않는지 확인

### 파일이 너무 크다는 에러가 나와요 (413 오류)
- `.env` 파일의 `MAX_FILE_SIZE` 값을 늘려보세요
- 기본값은 100MB(104857600 바이트)입니다

## 라이선스

ISC

## 참고

- [프로젝트 정의서](./project.md)
- [Slack Bolt for Python 문서](https://slack.dev/bolt-python/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
