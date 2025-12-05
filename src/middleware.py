import os
import ipaddress
from typing import Optional
from fastapi import Request, HTTPException, status
from dotenv import load_dotenv

load_dotenv()


class IPWhitelistMiddleware:
    """Middleware to check if the request IP is in the whitelist"""
    
    def __init__(self):
        allowed_ips_str = os.getenv('ALLOWED_IPS', '127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16')
        self.allowed_networks = []
        
        for ip_str in allowed_ips_str.split(','):
            ip_str = ip_str.strip()
            try:
                if '/' in ip_str:
                    self.allowed_networks.append(ipaddress.ip_network(ip_str, strict=False))
                else:
                    self.allowed_networks.append(ipaddress.ip_network(f"{ip_str}/32", strict=False))
            except ValueError as e:
                print(f"Warning: Invalid IP/network in ALLOWED_IPS: {ip_str} - {e}")
    
    def check_ip(self, request: Request) -> bool:
        """
        Check if the request IP is allowed.
        
        Args:
            request: FastAPI request object
            
        Returns:
            bool: True if allowed
            
        Raises:
            HTTPException: 403 if IP is not allowed
        """
        client_host = request.client.host if request.client else None
        
        if not client_host:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot determine client IP"
            )
        
        try:
            client_ip = ipaddress.ip_address(client_host)
            
            for network in self.allowed_networks:
                if client_ip in network:
                    return True
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied from IP: {client_host}"
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid client IP address"
            )


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """
    Extract API key from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Optional[str]: Extracted API key or None
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    
    return None
