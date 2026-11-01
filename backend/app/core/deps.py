"""
AI Research Assistant — FastAPI Dependencies

Reusable dependency injection for routes.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.user import User

security_scheme = HTTPBearer()

# Type alias for DB session dependency
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    db: DBSession,
) -> User:
    """
    Extract and validate the current user from the Authorization header.
    Raises 401 if the token is invalid or the user does not exist.
    """
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    from app.services.user_service import get_user_by_id

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


# Type alias for authenticated user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(current_user: CurrentUser) -> User:
    """Require the current user to have admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
