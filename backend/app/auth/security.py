import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import UserInDB, UserResponse, UserRole


import os

# Secret key for JWT HS256 signing - strictly loaded from environment variable
_jwt_secret_env = os.getenv("JWT_SECRET_KEY")
if not _jwt_secret_env or not _jwt_secret_env.strip():
    raise RuntimeError(
        "CRITICAL SECURITY CONFIGURATION ERROR: 'JWT_SECRET_KEY' environment variable is missing or empty. "
        "A valid secret key must be configured via the 'JWT_SECRET_KEY' environment variable before starting the service."
    )

JWT_SECRET_KEY = _jwt_secret_env.strip()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 86400 * 7  # 7 days for development/demo convenience

# HTTP Bearer authentication scheme
security_bearer = HTTPBearer(auto_error=False)


def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding as per RFC 7519."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    """Base64url decode with padding restoration as per RFC 7519."""
    pad_len = 4 - (len(s) % 4)
    if pad_len != 4:
        s += "=" * pad_len
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256 with 600,000 iterations.
    Returns (hashed_hex, salt_hex).
    """
    if not salt:
        salt = secrets.token_hex(16)
    hashed_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        600_000,
    )
    return hashed_bytes.hex(), salt


def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    expected_hash, _ = hash_password(plain_password, salt)
    return hmac.compare_digest(expected_hash, hashed_password)


def create_access_token(
    user: UserInDB,
    expires_delta_seconds: int = ACCESS_TOKEN_EXPIRE_SECONDS,
) -> str:
    """
    Create a standard RFC 7519 compliant HS256 JWT string.
    """
    now = int(time.time())
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "assigned_district": user.assigned_district,
        "assigned_state": user.assigned_state,
        "iat": now,
        "exp": now + expires_delta_seconds,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Validate and decode a standard HS256 JWT.
    Raises HTTPException if signature is invalid or token has expired.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT token structure.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    header_b64, payload_b64, signature_b64 = parts

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT signature validation failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed JWT payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate expiration
    exp = payload.get("exp")
    if exp and int(time.time()) > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT access token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_optional_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Optional[UserResponse]:
    """
    Extracts user from Bearer token if provided. Returns None if unauthenticated.
    """
    if not auth or not auth.credentials:
        return None
    try:
        payload = decode_access_token(auth.credentials)
        from .store import get_user_store

        user = get_user_store().get_by_id(payload["sub"])
        if not user or not user.is_active:
            return None
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            assigned_district=user.assigned_district,
            assigned_state=user.assigned_state,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    except Exception:
        return None


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> UserResponse:
    """
    Enforces authentication. Raises HTTP 401 if missing or invalid.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    from .store import get_user_store

    user = get_user_store().get_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        assigned_district=user.assigned_district,
        assigned_state=user.assigned_state,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency factory to enforce RBAC permissions.
    """
    def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {[r.value for r in allowed_roles]} roles.",
            )
        return current_user

    return role_checker


def check_district_access(user: Optional[UserResponse], target_district: Optional[str]) -> None:
    """
    Backend Authorization Enforcer:
    If user is a DISTRICT_AUTHORITY, strictly prohibits accessing data outside their assigned district.
    Raises HTTP 403 Forbidden on violation.
    """
    if not user:
        return
    if user.role == UserRole.DISTRICT_AUTHORITY:
        if not user.assigned_district:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="District Authority account is misconfigured: no assigned district bound.",
            )
        if target_district and target_district.strip().lower() != user.assigned_district.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You are only authorized to access records for district '{user.assigned_district}'. Requested: '{target_district}'.",
            )
