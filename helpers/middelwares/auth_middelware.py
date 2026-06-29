import os
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

_bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Password helpers (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt and return the hash string."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(payload: dict) -> str:
    """Create a signed JWT from the given payload dict."""

    expiry_minutes = int(os.getenv("JWT_EXPIRY_MINUTES", "1440"))
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# FastAPI dependency — injects the authenticated user_id into routes
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> int:
    """
    Dependency that extracts the Bearer token, decodes the JWT,
    and returns the user_id.  Raises 401 on any failure.
    """
    try:
        payload = decode_access_token(credentials.credentials)

        user_id: Optional[int] = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
            
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )