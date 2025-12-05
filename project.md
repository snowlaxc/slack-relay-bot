# 📄 프로젝트 정의서: Slack Relay Bot

## 1. 개요 및 배경 (Background)

### 1.1 프로젝트 명
* **Relay Bot** (Personal Webhook Bridge)

### 1.2 개발 배경 (Why?)
* 개발자나 엔지니어는 서버 작업, 배치 스크립트, 머신러닝 학습 결과, 에러 로그 등을 실시간으로 확인해야 할 니즈가 빈번함.
* 기존에는 매번 Slack Incoming Webhook을 새로 생성하거나, 별도의 알림 서버를 구축해야 하는 번거로움이 존재.
* **"그냥 `curl` 한 번으로 내 슬랙 DM에 파일이나 텍스트를 쏘고 싶다"**는 단순하고 강력한 니즈를 해결하기 위함.

### 1.3 목표 (Goal)
* 복잡한 설정 없이 **API Key** 하나만 있으면 어디서든 내 슬랙 DM으로 데이터를 보낼 수 있는 **중계(Relay) 시스템** 구축.
* 사내망 보안(IP 제한)과 개인화된 인증(API Key)을 통해 안전한 사용 환경 제공.
* **보안 강화**: API 키 해싱 및 일회성 모달 전달로 키 유출 위험 최소화.

---

## 2. 핵심 기능 (Key Features)

### 2.1 메시지 및 파일 중계 (Relay)
* **기능:** 외부(서버, 로컬 스크립트 등)에서 HTTP 요청을 보내면, 봇이 해당 요청을 보낸 사용자의 **일대일 슬랙 DM**으로 내용을 전달.
* **지원 포맷:**
    * 단순 텍스트 (Markdown 지원)
    * 파일 첨부 (로그 파일, 이미지, 결과 리포트 등)
    * 파일 크기 제한: 100MB (기본값, 환경 변수로 조정 가능)

### 2.2 셀프 서비스 키 관리 (Self-Service Key Management)
* 관리자의 개입 없이 사용자가 슬랙 명령어만으로 자신의 API Key를 관리.
* **발급:** 최초 사용 시 자동으로 고유 API Key 생성 (모달창으로 일회성 전달).
* **조회:** 기존 키 보유 시 재조회 불가 (보안상 해시만 저장).
* **재발급(Rotation):** 키 유출 시 즉시 기존 키 폐기 및 신규 발급 (모달창으로 전달).

### 2.3 보안 (Security)
* **네트워크 레벨:** 
    * 허용된 사내 IP 대역(Whitelist) 외의 접근 차단
    * 기본값: 사설망 IP (127.0.0.1, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
* **애플리케이션 레벨:** 
    * `Authorization: Bearer` 헤더를 통한 철저한 사용자 인증
    * **API 키 해싱**: PBKDF2-HMAC-SHA256 (100,000 iterations) 사용
    * DB에는 해시값만 저장, 평문 키는 서버에 절대 저장 안 됨
* **UI 레벨:**
    * 모달창(Modal)으로 키 전달: 일회성, DM 히스토리에 남지 않음
    * 워크스페이스 관리자도 모달 내용 확인 불가

### 2.4 에러 처리 및 안정성
* 모든 Slack 명령어에 try-except 블록 적용
* 데이터베이스 에러 로깅 및 사용자 친화적 에러 메시지
* FastAPI에서 Slack API 에러, 파일 크기 초과, 인증 실패 등 명확히 처리
* 환경 변수 검증: 필수 토큰 누락 시 명확한 에러 메시지

---

## 3. 시스템 아키텍처 (Architecture)

### 3.1 기술 스택 (Tech Stack)

| 구분 | 기술 | 선정 이유 |
| :--- | :--- | :--- |
| **Language** | Python 3.9+ | 빠른 개발 속도, 풍부한 라이브러리 지원 |
| **Framework** | FastAPI | 비동기 처리, 파일 업로드 용이, 자동 API 문서 |
| **Database** | SQLite (aiosqlite) | 별도 서버 불필요, 파일 기반의 간편한 관리 및 백업 |
| **Interface** | Slack Bolt | 슬랙 API 및 Socket Mode와의 안정적인 통신 |
| **Security** | PBKDF2-HMAC-SHA256 | 업계 표준 password 해싱, 무차별 대입 공격 방어 |
| **Deployment** | PM2 (선택) | 프로세스 관리, 자동 재시작, 로그 관리 |

### 3.2 데이터 흐름 (Data Flow)
1.  **User (Slack):** `/relay-key` 명령어로 API Key 발급 받음 → **모달창**에서 일회성 확인.
2.  **External Client:** `curl` 등을 통해 봇 서버로 `POST /send` 요청 (Header에 API Key 포함).
3.  **Bot Server:**
    * IP 허용 여부 체크 (Middleware).
    * API Key 해싱 후 DB의 해시값과 비교하여 검증.
    * 검증 성공 시 매핑된 User ID 조회.
4.  **Slack API:** 
    * `conversations.open`으로 DM 채널 ID 확보 (일대일 DM 보장).
    * 조회된 User ID로 메시지/파일 전송 (`chat.postMessage`, `files_upload_v2`).
5.  **User (Slack):** 봇으로부터 DM 수신.

### 3.3 프로젝트 구조

```
slack-relay/
├── src/
│   ├── __init__.py          # 패키지 초기화
│   ├── main.py              # FastAPI + Slack Bolt 통합, 환경 변수 검증
│   ├── database.py          # SQLite 관리 (해싱 적용)
│   ├── models.py            # Pydantic 데이터 모델
│   ├── middleware.py        # IP 화이트리스트, Bearer 토큰 추출
│   ├── slack_handlers.py    # Slack 명령어 핸들러 (모달 사용)
│   └── utils.py             # API Key 생성, 해싱, 검증
├── install.sh               # 자동 설치 스크립트
├── run.sh                   # 실행 스크립트
├── deploy.sh                # PM2 배포 스크립트
├── .env.example             # 환경 변수 템플릿
├── .gitignore               # Git 제외 파일
├── requirements.txt         # Python 의존성
├── README.md                # 사용 설명서
└── project.md               # 이 파일
```

---

## 4. 상세 스펙 (Specifications)

### 4.1 슬랙 명령어 (Slash Commands)
봇과의 모든 상호작용은 슬랙 명령어로 이루어집니다.

| 명령어 | 설명 | 전달 방식 |
| :--- | :--- | :--- |
| `/relay-help` | 사용 가이드 및 `curl` 예시 코드 출력 | Ephemeral (나에게만 보임) |
| `/relay-key` | API Key 발급 또는 재발급 | **모달창** (일회성) |

**보안 개선:**
- API 키는 모달창으로만 표시 (DM 히스토리에 남지 않음)
- 관리자도 모달 내용 확인 불가
- 기존 키 재조회 불가 (해시만 저장되므로 복원 불가능)
- `/relay-key` 재실행 시 기존 키 자동 무효화 및 새 키 발급

### 4.2 API 엔드포인트
외부 시스템이 호출할 유일한 창구입니다.

* **URL:** `POST /send`
* **Headers:**
    * `Authorization`: `Bearer relay_live_xxxx...` (필수)
* **Body (Multipart/Form-data):**
    * `text`: 전송할 메시지 내용 (선택)
    * `file`: 전송할 파일 바이너리 (선택, 최대 100MB)
    * 최소 하나 이상 필수
* **Response:**
    * `200 OK`: 전송 성공
    * `400 Bad Request`: text와 file 모두 누락
    * `401 Unauthorized`: Authorization 헤더 누락/잘못됨
    * `403 Forbidden`: 유효하지 않은 API Key 또는 IP 차단
    * `413 Request Entity Too Large`: 파일 크기 초과
    * `500 Internal Server Error`: Slack API 에러 또는 서버 내부 에러

### 4.3 데이터베이스 스키마 (SQLite)
단 하나의 테이블로 심플하게 관리합니다.

**Table: `api_keys`**

| Column Name | Type | Key | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | TEXT | PK | 슬랙 유저 ID (예: U123456) |
| `apikey_hash` | TEXT | UNIQUE | API Key의 해시값 (salt$hash 형식) |
| `created_at` | TIMESTAMP | | 생성 일시 (UTC) |

**보안 특징:**
- 평문 API 키는 절대 저장하지 않음
- PBKDF2-HMAC-SHA256으로 해싱 (100,000 iterations)
- Salt는 각 키마다 랜덤 생성 (16 bytes)

### 4.4 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `SLACK_BOT_TOKEN` | ✅ | - | Slack Bot Token (xoxb-...) |
| `SLACK_SIGNING_SECRET` | ✅ | - | Slack Signing Secret |
| `SLACK_APP_TOKEN` | ✅ | - | Slack App Token (xapp-...) |
| `PORT` | ❌ | 8000 | FastAPI 서버 포트 |
| `ALLOWED_IPS` | ❌ | 사설망 IP | IP 화이트리스트 (CIDR 표기법) |
| `MAX_FILE_SIZE` | ❌ | 104857600 | 최대 파일 크기 (바이트, 100MB) |
| `DATABASE_PATH` | ❌ | ./relay.db | SQLite 데이터베이스 경로 |

---

## 5. 배포 및 운영 (Deployment)

### 5.1 빠른 시작

```bash
# 1. 설치
./install.sh

# 2. .env 파일에 Slack 토큰 입력

# 3-A. 개발 환경 실행
./run.sh

# 3-B. 프로덕션 배포 (PM2)
./deploy.sh
```

### 5.2 프로덕션 권장 사항
* **PM2 사용**: `deploy.sh` 스크립트로 자동 재시작 및 로그 관리
* **리버스 프록시**: Nginx/Apache 사용 권장 (HTTPS, 추가 IP 제한 등)
* **DB 백업**: `relay.db` 파일 정기 백업
* **로그 모니터링**: PM2 로그 또는 별도 로깅 시스템 연동

---

## 6. 기대 효과 (Benefits)

1.  **생산성 향상:** 개발자가 모니터링 시스템을 구축하는 시간을 획기적으로 단축 (단 1줄의 curl 명령어로 해결).
2.  **보안성 강화:** 
    * 공유된 Webhook URL을 사용하는 방식보다, 사용자별 고유 Key와 IP 제한을 적용하여 훨씬 안전함.
    * API 키 해싱으로 DB 유출 시에도 실제 키는 안전.
    * 모달창 전달로 DM 히스토리에 평문 키 노출 방지.
3.  **관리 용이성:** 
    * 별도의 Admin 페이지 없이 슬랙 내부에서 모든 키 관리가 가능.
    * SQLite 사용으로 인프라 유지보수 비용 최소화.
    * 자동화 스크립트(`install.sh`, `deploy.sh`)로 배포 간소화.
4.  **안정성:** 
    * 포괄적인 에러 처리로 장애 최소화.
    * PM2를 통한 자동 재시작으로 고가용성 확보.

---

## 7. 제약 사항 및 향후 개선안

### 7.1 현재 제약 사항
* 봇이 보낸 메시지는 사용자가 직접 삭제할 수 없음 (Slack의 기본 정책)
* 파일은 사용자가 삭제 가능
* Slack 무료 플랜: 워크스페이스 전체 5GB 저장소 제한

### 7.2 향후 개선안
* API Key 사용 통계 및 모니터링 기능
* 웹 대시보드 (키 사용 이력, 통계)
* 여러 채널로 전송 지원 (현재는 DM 전용)
* Rate limiting (요청 횟수 제한)
* 메시지 템플릿 기능