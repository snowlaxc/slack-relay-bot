import os
import asyncio
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .database import create_api_key, get_api_key_by_user, delete_api_key
from .utils import generate_api_key


def register_slack_handlers(app: App):
    """Register all Slack command handlers"""
    
    @app.command("/relay-help")
    def handle_help(ack, command, client):
        ack()
        
        trigger_id = command['trigger_id']
        port = os.getenv('PORT', '8000')
        server_url = os.getenv('SERVER_URL', f'http://localhost:{port}')
        max_file_size = int(os.getenv('MAX_FILE_SIZE', 104857600))
        max_file_mb = max_file_size // (1024 * 1024)
        allowed_ips = os.getenv('ALLOWED_IPS', '127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16')
        
        # Format allowed IPs for display
        ip_list = allowed_ips.split(',')
        ip_display = '\n• '.join(ip_list)
        
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "title": {
                    "type": "plain_text",
                    "text": "Relay Bot 가이드"
                },
                "close": {
                    "type": "plain_text",
                    "text": "닫기"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*:wave: Relay Bot 사용 방법*\n\n외부 시스템에서 HTTP API로 Slack DM에 메시지를 전송할 수 있습니다."
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*:key: 1단계: API Key 발급*\n\n`/relay-key` 명령어를 실행하여 API Key를 발급받으세요.\n• 모달창에 한 번만 표시되므로 즉시 복사하세요\n• 재발급 시 기존 키는 무효화됩니다"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*:globe_with_meridians: 서버 주소*\n`{server_url}`"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*:package: 사용 제한*\n• 파일 크기: 최대 {max_file_mb}MB\n• 허용된 IP:\n• {ip_display}"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*:rocket: 2단계: 메시지 전송*\n\n```curl -X POST " + server_url + """/send \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "text=메시지 내용"```\n\n파일과 함께 전송:\n```curl -X POST """ + server_url + """/send \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "text=파일 설명" \\
  -F "file=@/path/to/file.pdf"```"""
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*:wastebasket: 메시지 삭제 방법*\n\n*1. 삭제 버튼 (가장 간편)*\n• 텍스트: \"🗑️ 삭제\" 버튼 클릭\n• 파일: \"🗑️ 파일 삭제\" 버튼 클릭\n\n*2. 명령어로 일괄 삭제*\n• `/relay-delete 10` - 최근 10개 확인\n• `/relay-delete all` - 전체 삭제\n\n*3. API로 삭제*\n자동화/스크립트용"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*:books: 사용 가능한 명령어*\n\n• `/relay-help` - 이 도움말 표시\n• `/relay-key` - API Key 발급/재발급\n• `/relay-delete [N]` - 최근 N개 메시지 삭제\n• `/relay-delete all` - 전체 메시지 삭제\n• `/relay-stop` - API Key 삭제 및 서비스 중단"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*:page_facing_up: API 문서*\n\nSwagger UI: `{server_url}/docs`"
                        }
                    }
                ]
            }
        )
    
    @app.command("/relay-key")
    def handle_key(ack, command, client):
        ack()
        
        user_id = command['user_id']
        trigger_id = command['trigger_id']
        
        try:
            # Check if user already has a key
            existing_key = asyncio.run(get_api_key_by_user(user_id))
            
            # Delete old key if exists
            if existing_key:
                asyncio.run(delete_api_key(user_id))
            
            # Generate and save new key
            new_key = generate_api_key()
            asyncio.run(create_api_key(user_id, new_key))
            
            # Prepare modal message
            server_url = os.getenv('SERVER_URL', f'http://localhost:{os.getenv("PORT", "8000")}')
            max_file_size = int(os.getenv('MAX_FILE_SIZE', 104857600))
            max_file_mb = max_file_size // (1024 * 1024)
            
            if existing_key:
                title_text = "API Key 재발급"
                header_text = ":recycle: *API Key가 재발급되었습니다*"
                warning_text = f":warning: *중요:*\n\n• 기존 키는 즉시 무효화되었습니다.\n• 외부 시스템에서 사용 중인 키를 새 키로 업데이트하세요.\n• 이 키는 이 창에서만 확인 가능합니다. 지금 바로 복사하세요!\n\n*서버 주소:* `{server_url}`\n*파일 크기 제한:* {max_file_mb}MB\n\n*사용 예시:*\n```curl -X POST {server_url}/send \\\n  -H \"Authorization: Bearer YOUR_API_KEY\" \\\n  -F \"text=메시지\"```"
            else:
                title_text = "새 API Key 발급"
                header_text = ":sparkles: *새로운 API Key가 발급되었습니다!*"
                warning_text = f":warning: *이 키는 이 창에서만 확인 가능합니다!*\n\n보안상의 이유로 서버에는 해시값만 저장되므로, 지금 바로 안전한 곳에 복사하여 보관하세요.\n\n키를 분실한 경우 `/relay-key` 명령어로 재발급할 수 있습니다.\n\n*서버 주소:* `{server_url}`\n*파일 크기 제한:* {max_file_mb}MB\n\n*사용 예시:*\n```curl -X POST {server_url}/send \\\n  -H \"Authorization: Bearer YOUR_API_KEY\" \\\n  -F \"text=테스트 메시지\"```\n\n자세한 사용법은 `/relay-help` 명령어를 실행해보세요!"
            
            # Show key in modal
            client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "title": {
                        "type": "plain_text",
                        "text": title_text
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "닫기"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": header_text
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"```{new_key}```"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": warning_text
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            print(f"Error in /relay-key command: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f":x: API Key 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            )
    
    @app.command("/relay-stop")
    def handle_stop(ack, command, client):
        ack()
        
        user_id = command['user_id']
        trigger_id = command['trigger_id']
        
        try:
            import asyncio
            from src.database import get_api_key_by_user
            
            # Check if API key exists
            existing_key = asyncio.run(get_api_key_by_user(user_id))
            
            if not existing_key:
                client.views_open(
                    trigger_id=trigger_id,
                    view={
                        "type": "modal",
                        "title": {
                            "type": "plain_text",
                            "text": "서비스 중단"
                        },
                        "close": {
                            "type": "plain_text",
                            "text": "닫기"
                        },
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":information_source: *발급된 API Key가 없습니다*\n\n현재 Relay Bot 서비스를 사용하고 있지 않습니다."
                                }
                            }
                        ]
                    }
                )
                return
            
            # Show confirmation modal BEFORE deleting
            client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "callback_id": "confirm_stop_service",
                    "title": {
                        "type": "plain_text",
                        "text": "서비스 중단 확인"
                    },
                    "submit": {
                        "type": "plain_text",
                        "text": "중단"
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "취소"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": ":warning: *Relay Bot 서비스를 중단하시겠습니까?*"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "다음 작업이 수행됩니다:\n\n• API Key가 삭제됩니다\n• 외부 시스템에서 더 이상 메시지를 보낼 수 없습니다\n• 기존에 받은 메시지는 그대로 유지됩니다"
                            }
                        },
                        {
                            "type": "divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "_서비스를 다시 사용하려면 `/relay-key` 명령어로 새 API Key를 발급받으시면 됩니다._"
                            }
                        }
                    ]
                }
            )
            
        except Exception as e:
            print(f"Error in /relay-stop: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f":x: 서비스 중단 처리 중 오류가 발생했습니다."
            )
    
    # Delete button interaction handler
    @app.action("delete_message")
    def handle_delete_button(ack, body, client):
        ack()
        
        user_id = body['user']['id']
        message_ts = body['message']['ts']
        channel_id = body['channel']['id']
        
        try:
            # Delete the message from Slack
            client.chat_delete(
                channel=channel_id,
                ts=message_ts
            )
            
            # Delete from database
            import asyncio
            from src.database import delete_message_record
            asyncio.run(delete_message_record(message_ts))
            
        except Exception as e:
            print(f"Error deleting message: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f":x: 메시지 삭제 중 오류가 발생했습니다."
            )
    
    # Delete file button interaction handler
    @app.action("delete_file")
    def handle_delete_file_button(ack, body, client):
        ack()
        
        user_id = body['user']['id']
        message_ts = body['message']['ts']
        channel_id = body['channel']['id']
        file_id = body['actions'][0]['value']
        
        try:
            # Get recent messages to find file-related messages
            history = client.conversations_history(
                channel=channel_id,
                limit=20  # Check last 20 messages
            )
            
            # Find and delete all messages related to this file
            deleted_count = 0
            for msg in history.get('messages', []):
                # Check if message contains this file
                if 'files' in msg:
                    for file_obj in msg['files']:
                        if file_obj.get('id') == file_id:
                            try:
                                client.chat_delete(
                                    channel=channel_id,
                                    ts=msg['ts']
                                )
                                deleted_count += 1
                            except Exception as e:
                                print(f"Error deleting file message {msg['ts']}: {e}")
            
            # Delete the file from Slack
            client.files_delete(file=file_id)
            
            # Delete the button message
            client.chat_delete(
                channel=channel_id,
                ts=message_ts
            )
            
            # Delete from database
            import asyncio
            from src.database import delete_message_record
            asyncio.run(delete_message_record(message_ts))
            
            print(f"Deleted file {file_id} and {deleted_count} related messages")
            
        except Exception as e:
            print(f"Error deleting file: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f":x: 파일 삭제 중 오류가 발생했습니다."
            )
    
    # /relay-delete command handler
    @app.command("/relay-delete")
    def handle_delete_command(ack, command, client):
        ack()
        
        user_id = command['user_id']
        text = command.get('text', '').strip()
        trigger_id = command['trigger_id']
        
        # Handle 'all' keyword to delete all messages
        if text.lower() == 'all':
            # For 'all', get messages directly from Slack instead of DB
            try:
                # Open DM channel
                dm_response = client.conversations_open(users=[user_id])
                channel_id = dm_response['channel']['id']
                
                # Get all messages from Slack
                all_messages = []
                cursor = None
                while True:
                    if cursor:
                        history = client.conversations_history(channel=channel_id, cursor=cursor, limit=200)
                    else:
                        history = client.conversations_history(channel=channel_id, limit=200)
                    
                    # Filter bot messages only
                    bot_messages = [msg for msg in history.get('messages', []) if msg.get('bot_id') or msg.get('subtype') == 'bot_message' or 'blocks' in msg]
                    all_messages.extend(bot_messages)
                    
                    # Check if there are more messages
                    if not history.get('has_more'):
                        break
                    cursor = history.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        break
                
                if not all_messages:
                    client.chat_postEphemeral(
                        channel=user_id,
                        user=user_id,
                        text=":information_source: 삭제할 메시지가 없습니다."
                    )
                    return
                
                # Build preview
                message_count = len(all_messages)
                message_list = []
                for i, msg in enumerate(all_messages[:10], 1):
                    text_preview = msg.get('text', '[파일]')[:50] if msg.get('text') else '[파일]'
                    ts_date = datetime.fromtimestamp(float(msg['ts'])).strftime('%m-%d %H:%M')
                    message_list.append(f"{i}. `{ts_date}` - {text_preview}")
                
                if message_count > 10:
                    message_list.append(f"... 외 {message_count - 10}개 더")
                
                # Store message_ts list
                message_ts_list = [msg['ts'] for msg in all_messages]
                
                confirmation_text = f":warning: *Slack DM의 전체 {message_count}개 봇 메시지를 모두 삭제하시겠습니까?*\n\n_DB 기록과 관계없이 실제 Slack 메시지를 삭제합니다_"
                
                client.views_open(
                    trigger_id=trigger_id,
                    view={
                        "type": "modal",
                        "callback_id": "confirm_delete_all_slack",
                        "title": {
                            "type": "plain_text",
                            "text": "전체 메시지 삭제"
                        },
                        "submit": {
                            "type": "plain_text",
                            "text": "삭제"
                        },
                        "close": {
                            "type": "plain_text",
                            "text": "취소"
                        },
                        "private_metadata": f"{channel_id}|{','.join(message_ts_list)}",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": confirmation_text
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "\n".join(message_list)
                                }
                            }
                        ]
                    }
                )
                return
                
            except Exception as e:
                print(f"Error getting all messages from Slack: {e}")
                client.chat_postEphemeral(
                    channel=user_id,
                    user=user_id,
                    text=f":x: 메시지 조회 중 오류가 발생했습니다."
                )
                return
        else:
            # Default to 10 recent messages if no number specified
            try:
                limit = int(text) if text else 10
                limit = min(limit, 50)  # Max 50 messages for numbered delete
            except ValueError:
                client.chat_postEphemeral(
                    channel=user_id,
                    user=user_id,
                    text=":x: 올바른 숫자를 입력하세요. 예: `/relay-delete 5` 또는 `/relay-delete all`"
                )
                return
        
        try:
            # Get recent messages
            import asyncio
            from src.database import get_recent_messages
            messages = asyncio.run(get_recent_messages(user_id, limit))
            
            if not messages:
                client.chat_postEphemeral(
                    channel=user_id,
                    user=user_id,
                    text=":information_source: 삭제할 메시지가 없습니다."
                )
                return
            
            # Build message preview list
            message_count = len(messages)
            message_list = []
            for i, msg in enumerate(messages[:10], 1):  # Show max 10 in preview
                preview = msg.get('text', '[파일]')[:50] if msg.get('text') else '[파일]'
                created_at = msg['created_at'][:16].replace('T', ' ')
                message_list.append(f"{i}. `{created_at}` - {preview}")
            
            if message_count > 10:
                message_list.append(f"... 외 {message_count - 10}개 더")
            
            # Prepare message_ts list for deletion
            message_ts_list = [msg['message_ts'] for msg in messages]
            
            # Show confirmation modal
            confirmation_text = f":warning: *전체 {message_count}개의 메시지를 모두 삭제하시겠습니까?*" if text.lower() == 'all' else f":warning: *최근 {message_count}개의 메시지를 삭제하시겠습니까?*"
            
            client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "callback_id": "confirm_delete_messages",
                    "title": {
                        "type": "plain_text",
                        "text": "메시지 삭제"
                    },
                    "submit": {
                        "type": "plain_text",
                        "text": "삭제"
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "취소"
                    },
                    "private_metadata": ",".join(message_ts_list),  # Store message_ts list
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": confirmation_text
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "\n".join(message_list)
                            }
                        }
                    ]
                }
            )
            
        except Exception as e:
            print(f"Error in /relay-delete command: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f":x: 메시지 조회 중 오류가 발생했습니다."
            )
    
    # Handle delete confirmation modal submission
    @app.view("confirm_delete_messages")
    def handle_delete_confirmation(ack, body, client, view):
        ack()
        
        user_id = body['user']['id']
        message_ts_list = view['private_metadata'].split(',')
        
        try:
            import asyncio
            import time
            from src.database import delete_message_record, get_message_by_ts
            
            deleted_count = 0
            deleted_files = 0
            
            for message_ts in message_ts_list:
                try:
                    # Get message info
                    msg_info = asyncio.run(get_message_by_ts(message_ts))
                    if msg_info:
                        channel_id = msg_info['channel_id']
                        
                        # Check if it's a file message
                        text = msg_info.get('text', '')
                        if text.startswith('FILE:'):
                            # Extract file_id from text (format: FILE:file_id:filename)
                            parts = text.split(':', 2)
                            if len(parts) >= 2:
                                file_id = parts[1]
                                
                                # Find and delete all messages related to this file BEFORE deleting the file
                                try:
                                    history = client.conversations_history(
                                        channel=channel_id,
                                        limit=100  # Increased to 100 to find older messages
                                    )
                                    
                                    for msg in history.get('messages', []):
                                        # Check if message contains this file
                                        if 'files' in msg:
                                            for file_obj in msg['files']:
                                                if file_obj.get('id') == file_id:
                                                    try:
                                                        client.chat_delete(
                                                            channel=channel_id,
                                                            ts=msg['ts']
                                                        )
                                                        print(f"Deleted file message: {msg['ts']}")
                                                        time.sleep(0.5)  # Rate limit protection
                                                    except Exception as e:
                                                        print(f"Error deleting file message {msg['ts']}: {e}")
                                                        time.sleep(0.5)  # Rate limit protection on error too
                                except Exception as e:
                                    print(f"Error finding file messages: {e}")
                                
                                # Now delete the file from Slack
                                try:
                                    client.files_delete(file=file_id)
                                    deleted_files += 1
                                    time.sleep(0.5)  # Rate limit protection
                                except Exception as e:
                                    # Ignore 'file_deleted' error (file already deleted when message was deleted)
                                    if 'file_deleted' not in str(e):
                                        print(f"Error deleting file {file_id}: {e}")
                                    time.sleep(0.5)  # Rate limit protection on error too
                        
                        # Delete the button message from Slack
                        client.chat_delete(
                            channel=msg_info['channel_id'],
                            ts=message_ts
                        )
                        # Delete from database
                        asyncio.run(delete_message_record(message_ts))
                        deleted_count += 1
                        
                        # Rate limit protection: 0.5초 대기
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"Error deleting message {message_ts}: {e}")
                    time.sleep(0.5)  # Rate limit protection on error too
                    continue
            
            # Send confirmation
            result_msg = f":white_check_mark: {deleted_count}개의 메시지가 삭제되었습니다."
            if deleted_files > 0:
                result_msg += f"\n📎 {deleted_files}개의 파일도 함께 삭제되었습니다."
            
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=result_msg
            )
            
        except Exception as e:
            print(f"Error in delete confirmation: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=":x: 메시지 삭제 중 오류가 발생했습니다."
            )
    
    # Handle delete all Slack messages confirmation
    @app.view("confirm_delete_all_slack")
    def handle_delete_all_slack(ack, body, client, view):
        ack()
        
        user_id = body['user']['id']
        metadata = view['private_metadata'].split('|', 1)
        channel_id = metadata[0]
        message_ts_list = metadata[1].split(',')
        
        try:
            from datetime import datetime
            import time
            deleted_count = 0
            deleted_files = 0
            
            for message_ts in message_ts_list:
                try:
                    # Get message to check for files
                    history = client.conversations_history(
                        channel=channel_id,
                        inclusive=True,
                        oldest=message_ts,
                        latest=message_ts,
                        limit=1
                    )
                    
                    if history.get('messages'):
                        msg = history['messages'][0]
                        
                        # Delete files if any
                        if 'files' in msg:
                            for file_obj in msg['files']:
                                try:
                                    client.files_delete(file=file_obj['id'])
                                    deleted_files += 1
                                    time.sleep(0.5)  # Rate limit protection
                                except Exception as e:
                                    print(f"Error deleting file {file_obj['id']}: {e}")
                                    time.sleep(0.5)  # Rate limit protection on error too
                   
                    # Delete message
                    client.chat_delete(
                        channel=channel_id,
                        ts=message_ts
                    )
                    deleted_count += 1
                    
                    # Also delete from DB if exists
                    import asyncio
                    from src.database import delete_message_record
                    asyncio.run(delete_message_record(message_ts))
                    
                    # Rate limit protection: 0.5초 대기
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Error deleting message {message_ts}: {e}")
                    time.sleep(0.5)  # Rate limit protection on error too
                    continue
            
            # Send confirmation
            result_msg = f":white_check_mark: {deleted_count}개의 메시지가 삭제되었습니다."
            if deleted_files > 0:
                result_msg += f"\n📎 {deleted_files}개의 파일도 함께 삭제되었습니다."
            
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=result_msg
            )
            
        except Exception as e:
            print(f"Error in delete all confirmation: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=":x: 메시지 삭제 중 오류가 발생했습니다."
            )
    
    # Handle delete by index button clicks (legacy - can be removed)
    @app.action({"action_id": "delete_by_index_*"})
    def handle_delete_by_index(ack, body, client):
        ack()
        
        user_id = body['user']['id']
        message_ts = body['actions'][0]['value']
        channel_id = body['channel']['id']
        
        try:
            import asyncio
            from src.database import delete_message_record, get_message_by_ts
            
            # Get message info
            msg_info = asyncio.run(get_message_by_ts(message_ts))
            if not msg_info:
                client.chat_postEphemeral(
                    channel=user_id,
                    user=user_id,
                    text=":x: 메시지를 찾을 수 없습니다."
                )
                return
            
            # Delete from Slack
            client.chat_delete(
                channel=msg_info['channel_id'],
                ts=message_ts
            )
            
            # Delete from database
            asyncio.run(delete_message_record(message_ts))
            
            # Update the ephemeral message
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=":white_check_mark: 메시지가 삭제되었습니다."
            )
            
        except Exception as e:
            print(f"Error deleting message by index: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f":x: 메시지 삭제 중 오류가 발생했습니다."
            )
    
    # Handle stop service confirmation modal submission
    @app.view("confirm_stop_service")
    def handle_stop_confirmation(ack, body, client, view):
        ack()
        
        user_id = body['user']['id']
        
        try:
            import asyncio
            from src.database import delete_api_key
            
            # Delete API key
            asyncio.run(delete_api_key(user_id))
            
            # Send confirmation
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=":white_check_mark: *Relay Bot 서비스가 중단되었습니다*\n\n• API Key가 삭제되었습니다\n• 외부 시스템에서 더 이상 메시지를 보낼 수 없습니다\n• 기존에 받은 메시지는 그대로 유지됩니다\n\n_서비스를 다시 사용하려면 `/relay-key` 명령어로 새 API Key를 발급받으세요._"
            )
            
        except Exception as e:
            print(f"Error in stop confirmation: {e}")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=":x: 서비스 중단 처리 중 오류가 발생했습니다."
            )

