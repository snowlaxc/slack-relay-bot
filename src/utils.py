import secrets
import hashlib


def generate_api_key() -> str:
    """
    Generate a unique API key with 'relay_live_' prefix.
    
    Returns:
        str: Generated API key (e.g., 'relay_live_abc123...')
    """
    random_part = secrets.token_urlsafe(32)
    return f"relay_live_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key with salt using PBKDF2.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        str: Hashed key in format 'salt$hash'
    """
    # Generate a random salt (16 bytes = 128 bits)
    salt = secrets.token_bytes(16)
    
    # Hash the API key with PBKDF2-HMAC-SHA256 (100,000 iterations)
    key_hash = hashlib.pbkdf2_hmac('sha256', api_key.encode('utf-8'), salt, 100000)
    
    # Return salt and hash in hex format, separated by $
    return f"{salt.hex()}${key_hash.hex()}"


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against a stored hash.
    
    Args:
        api_key: Plain text API key to verify
        stored_hash: Stored hash in format 'salt$hash'
        
    Returns:
        bool: True if API key matches the hash
    """
    try:
        # Split salt and hash
        salt_hex, hash_hex = stored_hash.split('$')
        salt = bytes.fromhex(salt_hex)
        stored_key_hash = bytes.fromhex(hash_hex)
        
        # Hash the provided API key with the same salt
        key_hash = hashlib.pbkdf2_hmac('sha256', api_key.encode('utf-8'), salt, 100000)
        
        # Compare hashes using constant-time comparison
        return secrets.compare_digest(key_hash, stored_key_hash)
    except (ValueError, AttributeError):
        # Invalid hash format
        return False

