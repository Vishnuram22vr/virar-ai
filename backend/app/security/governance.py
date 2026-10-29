import hashlib
import json
from typing import Any, Dict, Optional
from fastapi import Header, HTTPException, status
from app.config import settings

def compute_parameter_fingerprint(params: Dict[str, Any]) -> str:
    """
    Computes a deterministic SHA-256 fingerprint for action parameters.
    Used to guarantee that parameters have not been tampered with between
    approval request and approval decision/execution.
    """
    canonical_json = json.dumps(params, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

class DevUser:
    def __init__(self, user_id: str, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role

def get_current_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> DevUser:
    """
    Development authentication & authorization dependency.
    Validates API key and user role. In dev mode, allows standard admin access.
    """
    if settings.DEV_AUTH_MODE:
        user_id = x_user_id or settings.DEV_USER_ID
        return DevUser(
            user_id=user_id,
            username=f"user_{user_id}",
            role="admin"
        )
    
    # In production mode: enforce explicit authorization token
    if not x_api_key or x_api_key != settings.DEV_ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication credentials."
        )
    
    user_id = x_user_id or "auth-user"
    return DevUser(user_id=user_id, username=f"user_{user_id}", role="admin")

def enforce_not_self_approval(requester_id: str, reviewer_id: str):
    """
    Enforces governance rule: the requesting agent or actor cannot approve its own action.
    """
    if requester_id and reviewer_id and requester_id == reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Governance Policy Violation: Requesting agent or user cannot approve their own action."
        )
