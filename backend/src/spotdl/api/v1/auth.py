"""Authentication API endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from spotdl.db.database import get_db_session
from spotdl.db.models.user import User
from spotdl.db.repositories.user import UserRepository

router = APIRouter(prefix="/auth")
security = HTTPBearer(auto_error=False)


# Request/Response models
class RegisterRequest(BaseModel):
    """Request model for user registration."""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    """Request model for user login."""

    username: str
    password: str


class RefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class UserResponse(BaseModel):
    """Response model for user data."""

    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    reputation_score: int

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Dependencies
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises HTTPException if token is invalid or user not found.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_data.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    try:
        user_id = UUID(token_data.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User | None:
    """
    Get current user if authenticated, None otherwise.

    Does not raise an exception if not authenticated.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_user_id(
    user: Annotated[User, Depends(get_current_user)],
) -> UUID:
    """Get current user ID from authenticated user."""
    return user.id


async def get_current_user_id_optional(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> UUID | None:
    """Get current user ID if authenticated, None otherwise."""
    return user.id if user else None


# Endpoints
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    """
    Register a new user.

    Args:
        request: Registration data (username, email, password)
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If username or email already exists
    """
    user_repo = UserRepository(db)

    # Check if username exists
    if await user_repo.username_exists(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email exists
    if await user_repo.email_exists(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if this is the first user (make them admin)
    is_first_user = await user_repo.count() == 0

    # Create user
    created_user = await user_repo.create(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        is_admin=is_first_user,  # First user becomes admin
    )
    await db.commit()

    # Generate tokens
    access_token = create_access_token(str(created_user.id))
    refresh_token = create_refresh_token(str(created_user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=str(created_user.id),
            username=created_user.username,
            email=created_user.email,
            is_active=created_user.is_active,
            is_admin=created_user.is_admin,
            reputation_score=created_user.reputation_score,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    """
    Login with username and password.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    user_repo = UserRepository(db)

    # Find user by username
    user = await user_repo.get_by_username(request.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Generate tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            reputation_score=user.reputation_score,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    token_data = decode_token(request.refresh_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if token_data.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_repo = UserRepository(db)
    try:
        user_id = UUID(token_data.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    # Generate new tokens
    access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """
    Get current authenticated user's profile.

    Args:
        user: Current authenticated user

    Returns:
        User profile data
    """
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        reputation_score=user.reputation_score,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    _user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """
    Logout current user.

    Note: JWT tokens are stateless, so this endpoint just returns success.
    In a production system, you might want to:
    - Add tokens to a blacklist (with Redis)
    - Clear client-side storage

    Returns:
        Success message
    """
    return MessageResponse(message="Successfully logged out")
