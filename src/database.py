import aiosqlite
import os
from datetime import datetime, timezone
from typing import Optional, Dict
from dotenv import load_dotenv
from .utils import hash_api_key, verify_api_key

load_dotenv()

DATABASE_PATH = os.getenv('DATABASE_PATH', './relay.db')


async def init_db():
    """Initialize database and create tables if they don't exist"""
    db_path = os.getenv('DATABASE_PATH', './relay.db')
    print(f"Database initialized at: {db_path}")
    
    async with aiosqlite.connect(db_path) as db:
        # Users and API keys table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                apikey_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Messages table for tracking sent messages
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_ts TEXT NOT NULL,
                text TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        await db.commit()


async def create_api_key(user_id: str, apikey: str) -> bool:
    """
    Create or update an API key for a user.
    Stores only the hashed version of the API key.
    
    Args:
        user_id: Slack user ID
        apikey: Plain text API key (will be hashed before storage)
        
    Returns:
        bool: True if successful
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            now = datetime.now(timezone.utc).isoformat()
            apikey_hash = hash_api_key(apikey)
            
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, apikey_hash, created_at) VALUES (?, ?, ?)",
                (user_id, apikey_hash, now)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"Database error creating API key for user {user_id}: {e}")
        raise


async def get_user_by_key(apikey: str) -> Optional[str]:
    """
    Get user ID by verifying the API key against stored hashes.
    
    Args:
        apikey: Plain text API key to verify
        
    Returns:
        Optional[str]: User ID if API key is valid, None otherwise
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Get all user_id and apikey_hash pairs
            async with db.execute("SELECT user_id, apikey_hash FROM users") as cursor:
                rows = await cursor.fetchall()
                
                # Check each hash to find a match
                for user_id, stored_hash in rows:
                    if verify_api_key(apikey, stored_hash):
                        return user_id
                
                return None
    except Exception as e:
        print(f"Database error verifying API key: {e}")
        raise


async def get_api_key_by_user(user_id: str) -> Optional[Dict[str, str]]:
    """
    Get API key information by user ID.
    Note: This returns the hash, not the actual API key (which is never stored).
    
    Args:
        user_id: Slack user ID
        
    Returns:
        Optional[Dict]: API key info if found, None otherwise
        Note: 'apikey_hash' field contains the hash, not the actual key
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT user_id, apikey_hash, created_at FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'apikey_hash': row[1],  # This is the hash, not the actual key
                    'created_at': row[2]
                }
            return None


async def delete_api_key(user_id: str) -> bool:
    """
    Delete an API key for a user.
    
    Args:
        user_id: Slack user ID
        
    Returns:
        bool: True if successful
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()
        return True


async def save_message(user_id: str, channel_id: str, message_ts: str, text: str = None):
    """
    Save a sent message to database for deletion tracking.
    
    Args:
        user_id: Slack user ID
        channel_id: Slack channel/DM ID
        message_ts: Message timestamp from Slack
        text: Optional message text
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                'INSERT INTO messages (user_id, channel_id, message_ts, text, created_at) VALUES (?, ?, ?, ?, ?)',
                (user_id, channel_id, message_ts, text, datetime.now(timezone.utc).isoformat())
            )
            await db.commit()
    except Exception as e:
        print(f"Error saving message: {e}")


async def get_recent_messages(user_id: str, limit: int = 10):
    """
    Get recent messages sent to a user.
    
    Args:
        user_id: Slack user ID
        limit: Maximum number of messages to return
        
    Returns:
        List of message records
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error getting recent messages: {e}")
        return []


async def delete_message_record(message_ts: str):
    """
    Delete a message record from database.
    
    Args:
        message_ts: Message timestamp to delete
        
    Returns:
        True if deleted, False otherwise
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'DELETE FROM messages WHERE message_ts = ?',
                (message_ts,)
            )
            await db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting message record: {e}")
        return False


async def get_message_by_ts(message_ts: str):
    """
    Get message info by timestamp.
    
    Args:
        message_ts: Message timestamp
        
    Returns:
        Message record dict or None
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM messages WHERE message_ts = ?',
                (message_ts,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    except Exception as e:
        print(f"Error getting message by ts: {e}")
        return None
