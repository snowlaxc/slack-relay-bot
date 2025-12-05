import os
import asyncio
import threading
import uvicorn
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException, status, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

from src.database import init_db, get_user_by_key
from src.middleware import IPWhitelistMiddleware, extract_bearer_token
from src.slack_handlers import register_slack_handlers

# Load environment variables
load_dotenv()


def validate_env_vars():
    """Validate that required environment variables are set"""
    required_vars = ['SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET', 'SLACK_APP_TOKEN']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please set them in your .env file."
        )


# Validate environment variables before initializing
validate_env_vars()

# Security scheme for Swagger
security = HTTPBearer()

# Initialize FastAPI with API documentation (protected by IP whitelist)
api = FastAPI(
    title="Slack Relay Bot API",
    description="""
## 📨 Slack DM 중계 API

외부 시스템에서 간단한 HTTP 요청으로 Slack DM에 메시지와 파일을 전송할 수 있는 API입니다.

### 🔑 API Key 발급 방법

API를 사용하려면 먼저 **Slack에서 API Key를 발급**받아야 합니다:

1. Slack 워크스페이스에서 `/relay-key` 명령어 실행
2. 모달창에 표시되는 API Key 복사 (일회성 표시)
3. 복사한 API Key를 아래 **Authorize 🔓 버튼**을 클릭하여 입력

**참고:** API Key를 분실한 경우 `/relay-key` 명령어를 다시 실행하면 재발급됩니다.

### 🔐 보안

- **IP 화이트리스트**: 사설망 IP만 허용 (이 문서 포함)
- **API Key 인증**: PBKDF2-HMAC-SHA256 해싱
- **파일 크기 제한**: 100MB (기본값)
""",
    version="1.0.0",
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

# Add security scheme to OpenAPI schema
def custom_openapi():
    if api.openapi_schema:
        return api.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=api.title,
        version=api.version,
        description=api.description,
        routes=api.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "Slack에서 `/relay-key` 명령어로 발급받은 API Key를 입력하세요. (예: relay_live_abc123...)"
        }
    }
    
    api.openapi_schema = openapi_schema
    return api.openapi_schema

api.openapi = custom_openapi

# Add IP whitelist middleware to protect ALL endpoints including Swagger
@api.middleware("http")
async def ip_whitelist_middleware(request: Request, call_next):
    """Check IP whitelist for all requests"""
    ip_checker.check_ip(request)
    response = await call_next(request)
    return response

# Initialize IP whitelist checker
ip_checker = IPWhitelistMiddleware()

# Initialize Slack app
slack_app = App(
    token=os.getenv('SLACK_BOT_TOKEN'),
    signing_secret=os.getenv('SLACK_SIGNING_SECRET'),
    token_verification_enabled=False  # We're using Socket Mode
)

# Register Slack command handlers
register_slack_handlers(slack_app)


@api.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()
    print("Database initialized")


@api.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Slack Relay Bot",
        "version": "1.0.0"
    }


@api.delete("/delete")
async def delete_message_endpoint(
    request: Request,
    authorization: Optional[str] = Header(None, include_in_schema=False),
    message_ts: str = Form(..., description="삭제할 메시지의 타임스탬프")
):
    """
    Delete a previously sent message.
    
    ## 사용 방법
    ```bash
    curl -X DELETE http://server:8000/delete \
      -H "Authorization: Bearer YOUR_API_KEY" \
      -F "message_ts=1234567890.123456"
    ```
    
    ## 필수 사항
    - Authorization header with Bearer token
    - message_ts: Message timestamp returned from /send
    
    ## 반환값
    - 200: 삭제 성공
    - 401: 인증 실패
    - 404: 메시지를 찾을 수 없음
    """
    # Extract and validate API key
    api_key = extract_bearer_token(authorization)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    
    # Get user ID from API key
    user_id = await get_user_by_key(api_key)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    try:
        from src.database import get_message_by_ts, delete_message_record
        
        # Get message info
        msg_info = await get_message_by_ts(message_ts)
        if not msg_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Verify message belongs to this user
        if msg_info['user_id'] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own messages"
            )
        
        # Delete from Slack
        slack_app.client.chat_delete(
            channel=msg_info['channel_id'],
            ts=message_ts
        )
        
        # Delete from database
        await delete_message_record(message_ts)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Message deleted successfully"
        })
        
    except SlackApiError as e:
        error_message = e.response.get('error', 'Unknown error')
        print(f"Slack API error deleting message: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete message from Slack: {error_message}"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@api.post(
    "/send",
    responses={
        200: {"description": "메시지 전송 성공"},
        401: {"description": "인증 실패"},
        403: {"description": "권한 없음"},
        413: {"description": "파일 크기 초과"},
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def send_message(
    request: Request,
    authorization: Optional[str] = Header(None, include_in_schema=False),
    text: Optional[str] = Form(default=None, description="전송할 텍스트 메시지"),
    file: UploadFile = File(default=None, description="전송할 파일 (최대 100MB)")
):
    """
    Send a message or file to user's Slack DM.
    
    ## 사용 방법 (Swagger UI)
    1. 우측 상단의 **Authorize 🔓** 버튼 클릭
    2. Value에 API Key만 입력 (예: relay_live_abc123...)
    3. **Authorize** 클릭
    4. 아래 **Try it out** 버튼으로 테스트
    
    ## 사용 방법 (curl)
    ```bash
    # 텍스트 메시지만 전송
    curl -X POST http://your-server:8000/send \
      -H "Authorization: Bearer relay_live_YOUR_API_KEY" \
      -F "text=테스트 메시지입니다"
    
    # 파일과 함께 전송
    curl -X POST http://your-server:8000/send \
      -H "Authorization: Bearer relay_live_YOUR_API_KEY" \
      -F "text=로그 파일입니다" \
      -F "file=@./error.log"
    
    # 파일만 전송
    curl -X POST http://your-server:8000/send \
      -H "Authorization: Bearer relay_live_YOUR_API_KEY" \
      -F "file=@./screenshot.png"
    ```
    
    ## 제한 사항
    - **파일 크기 제한**: 100MB (기본값, 환경 변수 MAX_FILE_SIZE로 조정 가능)
    - **필수 입력**: text 또는 file 중 최소 1개 필수
    
    ## 필수 사항
    - Authorization header with Bearer token (API key from Slack /relay-key command)
    - At least one of: text or file
    
    ## 반환값
    - 200: 전송 성공
    - 401: 인증 실패 (API Key 누락 또는 잘못됨)
    - 403: 권한 없음 (유효하지 않은 API Key 또는 IP 차단)
    - 413: 파일 크기 초과 (MAX_FILE_SIZE 초과)
    """
    # Extract and validate API key (IP already checked by middleware)
    api_key = extract_bearer_token(authorization)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Use 'Authorization: Bearer YOUR_API_KEY'"
        )
    
    # Get user ID from API key
    user_id = await get_user_by_key(api_key)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    # Validate request - at least text or file must be provided
    if not text and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'text' or 'file' must be provided"
        )
    
    # Check file size limit if file is provided
    file_content = None
    if file:
        max_file_size = int(os.getenv('MAX_FILE_SIZE', 104857600))  # Default 100MB
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({max_file_size} bytes)"
            )
    
    # Send message or file to Slack
    try:
        # Open DM channel
        dm_response = slack_app.client.conversations_open(users=[user_id])
        channel_id = dm_response['channel']['id']
        
        from src.database import save_message
        
        if file:
            # Upload file
            upload_result = slack_app.client.files_upload_v2(
                channels=[channel_id],  # Must be a list
                file=file_content,
                filename=file.filename,
                initial_comment=text if text else None
            )
            
            file_id = upload_result.get('file', {}).get('id')
            
            # Send a separate message with delete button for the file
            button_message = slack_app.client.chat_postMessage(
                channel=channel_id,
                text=f"📎 파일: {file.filename}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📎 *파일 업로드됨*\n`{file.filename}`"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🗑️ 파일 삭제"
                                },
                                "action_id": "delete_file",
                                "value": file_id,  # Store file_id for deletion
                                "style": "danger",
                                "confirm": {
                                    "title": {
                                        "type": "plain_text",
                                        "text": "파일 삭제"
                                    },
                                    "text": {
                                        "type": "plain_text",
                                        "text": "업로드한 파일을 삭제하시겠습니까?"
                                    },
                                    "confirm": {
                                        "type": "plain_text",
                                        "text": "삭제"
                                    },
                                    "deny": {
                                        "type": "plain_text",
                                        "text": "취소"
                                    }
                                }
                            }
                        ]
                    }
                ]
            )
            
            message_ts = button_message['ts']
            
            # Save to database with file_id
            await save_message(user_id, channel_id, message_ts, f"FILE:{file_id}:{file.filename}")
            
            return JSONResponse(content={
                "status": "success",
                "message": "File uploaded successfully",
                "file_id": file_id,
                "message_ts": message_ts
            })
        else:
            # Send text message with delete button
            result = slack_app.client.chat_postMessage(
                channel=channel_id,
                text=text,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": text
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🗑️ 삭제"
                                },
                                "action_id": "delete_message",
                                "style": "danger",
                                "value": "delete",
                                "confirm": {
                                    "title": {
                                        "type": "plain_text",
                                        "text": "메시지 삭제"
                                    },
                                    "text": {
                                        "type": "plain_text",
                                        "text": "이 메시지를 삭제하시겠습니까?"
                                    },
                                    "confirm": {
                                        "type": "plain_text",
                                        "text": "삭제"
                                    },
                                    "deny": {
                                        "type": "plain_text",
                                        "text": "취소"
                                    }
                                }
                            }
                        ]
                    }
                ]
            )
            
            message_ts = result['ts']
            
            # Save to database
            await save_message(user_id, channel_id, message_ts, text)
            
            return JSONResponse(content={
                "status": "success",
                "message": "Message sent successfully",
                "message_ts": message_ts
            })
            
    except SlackApiError as e:
        error_message = e.response.get('error', 'Unknown error')
        print(f"Slack API error for user {user_id}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack API error: {error_message}"
        )
    except KeyError as e:
        print(f"Unexpected response format from Slack API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error communicating with Slack"
        )
    except Exception as e:
        print(f"Internal error sending message to user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


def run_slack_bot():
    """Run Slack bot in Socket Mode"""
    handler = SocketModeHandler(slack_app, os.getenv('SLACK_APP_TOKEN'))
    handler.start()


def run_fastapi():
    """Run FastAPI server"""
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(api, host="0.0.0.0", port=port)


def main():
    """Main entry point - runs both FastAPI and Slack bot"""
    print("Starting Slack Relay Bot...")
    
    # Run Slack bot in a separate thread
    slack_thread = threading.Thread(target=run_slack_bot, daemon=True)
    slack_thread.start()
    print("Slack bot started in Socket Mode")
    
    # Run FastAPI in the main thread
    print(f"Starting FastAPI server on port {os.getenv('PORT', 8000)}...")
    run_fastapi()


if __name__ == "__main__":
    main()
