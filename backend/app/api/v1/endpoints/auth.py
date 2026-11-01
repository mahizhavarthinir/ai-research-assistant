"""
AI Research Assistant — Authentication Endpoints
"""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import DBSession, CurrentUser
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_username,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DBSession):
    """Register a new user account."""
    # Check for existing email
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Check for existing username
    existing = await get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    user = await create_user(db, data)

    return TokenResponse(
        access_token=create_access_token(data={"sub": user.id}),
        refresh_token=create_refresh_token(data={"sub": user.id}),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DBSession):
    """Authenticate and receive access tokens."""
    user = await authenticate_user(db, data.email, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenResponse(
        access_token=create_access_token(data={"sub": user.id}),
        refresh_token=create_refresh_token(data={"sub": user.id}),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: CurrentUser):
    """Log out the current user (client should discard the token)."""
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: CurrentUser):
    """Get the currently authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at.isoformat(),
    )
