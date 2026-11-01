"""
AI Research Assistant — Security Utilities

Password hashing and JWT token management.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

# Workaround for passlib + bcrypt >= 4.1.0 compatibility
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        class _BcryptAbout:
            __version__ = getattr(bcrypt, "__version__", "4.0.1")
        bcrypt.__about__ = _BcryptAbout()
except Exception:
    pass

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password Hashing ────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ───────────────────────────────
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a signed JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns None on failure."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
