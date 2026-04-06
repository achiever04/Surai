"""
Authentication endpoints
"""
import time
from collections import defaultdict
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserResponse, UserCreate
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.timezone import utc_now
from config.settings import settings
from app.api.deps import get_current_user

router = APIRouter()

# ── Rate Limiting ──────────────────────────────────────────────────────
# Simple in-memory rate limiter for login endpoint.
# Tracks failed attempts per IP; blocks after MAX_ATTEMPTS within WINDOW_SECONDS.
_login_attempts: dict = defaultdict(list)  # ip -> [timestamp, ...]
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5-minute window


def _check_rate_limit(client_ip: str) -> None:
    """Raise 429 if too many login attempts from this IP."""
    now = time.time()
    # Prune old attempts outside the window
    _login_attempts[client_ip] = [
        t for t in _login_attempts[client_ip] if now - t < _WINDOW_SECONDS
    ]
    if len(_login_attempts[client_ip]) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {_WINDOW_SECONDS // 60} minutes.",
        )


def _record_failed_attempt(client_ip: str) -> None:
    """Record a failed login attempt timestamp."""
    _login_attempts[client_ip].append(time.time())


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Login endpoint to get access token"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limit check
    _check_rate_limit(client_ip)
    
    # Get user
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    # Verify credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        _record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Update last login (timezone-aware)
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login=utc_now())
    )
    await db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # Clear failed attempts on successful login
    _login_attempts.pop(client_ip, None)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register new user (for testing - remove in production)"""
    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == user_in.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint (client should discard token)"""
    return {"message": "Successfully logged out"}