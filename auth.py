"""
Authentication module for the DevOps Agent
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.exceptions import InvalidSignature

from models import AuthMethod, AuthRequest, AuthResponse
from logger import logger
from config import AUTH_TOKEN_SECRET, AUTHORIZED_KEYS_FILE

class AuthManager:
    """Handles user authentication via SSH keys or API tokens"""
    
    def __init__(self):
        self.active_sessions: Dict[str, dict] = {}
        self.api_tokens = self._load_api_tokens()
        self.ssh_keys = self._load_ssh_keys()
    
    def _load_api_tokens(self) -> Dict[str, str]:
        """Load valid API tokens (in production, this would be from a database)"""
        # For demo purposes, generate some default tokens
        return {
            "admin": hashlib.sha256(f"admin-{AUTH_TOKEN_SECRET}".encode()).hexdigest()[:32],
            "devops": hashlib.sha256(f"devops-{AUTH_TOKEN_SECRET}".encode()).hexdigest()[:32],
            "user": hashlib.sha256(f"user-{AUTH_TOKEN_SECRET}".encode()).hexdigest()[:32]
        }
    
    def _load_ssh_keys(self) -> Dict[str, str]:
        """Load authorized SSH public keys"""
        ssh_keys = {}
        
        if AUTHORIZED_KEYS_FILE.exists():
            try:
                with open(AUTHORIZED_KEYS_FILE, 'r') as f:
                    for line_num, line in enumerate(f):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) >= 2:
                                key_type, key_data = parts[0], parts[1]
                                # Use line number as username if not specified
                                username = parts[2] if len(parts) > 2 else f"user_{line_num}"
                                ssh_keys[username] = f"{key_type} {key_data}"
            except Exception as e:
                logger.error("Failed to load SSH keys", error=str(e))
        
        # Add a default key for testing
        if not ssh_keys:
            ssh_keys["demo"] = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... demo@localhost"
        
        return ssh_keys
    
    def _validate_ssh_key(self, provided_key: str) -> Optional[str]:
        """Validate SSH public key and return username if valid"""
        provided_key = provided_key.strip()
        
        for username, stored_key in self.ssh_keys.items():
            if provided_key == stored_key or provided_key in stored_key:
                return username
        
        return None
    
    def _validate_api_token(self, token: str) -> Optional[str]:
        """Validate API token and return username if valid"""
        for username, stored_token in self.api_tokens.items():
            if secrets.compare_digest(token, stored_token):
                return username
        
        return None
    
    def authenticate(self, auth_request: AuthRequest) -> AuthResponse:
        """Authenticate user and create session"""
        username = None
        
        if auth_request.method == AuthMethod.SSH_KEY:
            username = self._validate_ssh_key(auth_request.credentials)
        elif auth_request.method == AuthMethod.API_TOKEN:
            username = self._validate_api_token(auth_request.credentials)
        
        if not username:
            logger.audit(
                "authentication_failed",
                session_id="none",
                method=auth_request.method,
                username=auth_request.username
            )
            return AuthResponse(
                success=False,
                message="Invalid credentials"
            )
        
        # Create session
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        self.active_sessions[session_id] = {
            "username": username,
            "auth_method": auth_request.method,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_activity": datetime.utcnow()
        }
        
        logger.audit(
            "authentication_success",
            session_id=session_id,
            method=auth_request.method,
            username=username
        )
        
        return AuthResponse(
            success=True,
            session_id=session_id,
            message=f"Authenticated as {username}",
            expires_at=expires_at
        )
    
    def validate_session(self, session_id: str) -> Optional[dict]:
        """Validate session and return session info if valid"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        # Check expiration
        if datetime.utcnow() > session["expires_at"]:
            del self.active_sessions[session_id]
            logger.audit("session_expired", session_id=session_id)
            return None
        
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        
        return session
    
    def logout(self, session_id: str) -> bool:
        """Logout user and invalidate session"""
        if session_id in self.active_sessions:
            username = self.active_sessions[session_id]["username"]
            del self.active_sessions[session_id]
            logger.audit("logout", session_id=session_id, username=username)
            return True
        return False
    
    def get_active_sessions(self) -> Dict[str, dict]:
        """Get all active sessions (for admin purposes)"""
        # Clean expired sessions
        now = datetime.utcnow()
        expired_sessions = [
            sid for sid, session in self.active_sessions.items()
            if now > session["expires_at"]
        ]
        for sid in expired_sessions:
            del self.active_sessions[sid]
        
        return self.active_sessions.copy()

# Global auth manager instance
auth_manager = AuthManager()
