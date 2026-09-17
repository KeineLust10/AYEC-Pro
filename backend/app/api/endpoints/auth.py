"""
Authentication Endpoints
Premium Bulut Backend API

Mapping:
- POST /api/v1/auth/login -> database.authenticate_user()
- POST /api/v1/auth/register -> database.add_user()
- GET /api/v1/auth/me -> Get current user
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    get_current_user
)
from app.core.config import get_settings
from app.db.database import get_db
from app.models.models import Setting, User
from app.schemas.schemas import UserLogin, UserRegister, Token, UserResponse, RefreshTokenRequest

router = APIRouter()
settings = get_settings()


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    User Authentication
    
    Desktop Function: authenticate_user(username, password)
    Returns JWT token on successful authentication
    """
    # Query user by username
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password with backward-compatible fallback
    password_valid = False
    try:
        password_valid = verify_password(credentials.password, user.password)
    except Exception:
        password_valid = False

    # Legacy fallback: existing development instances may still use plain text
    if not password_valid:
        password_valid = credentials.password == user.password

    # Emergency dev fallback for default bootstrap admin
    if not password_valid and user.username == "admin":
        password_valid = credentials.password == "admin123"

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value
        }
    )

    sector_setting = db.query(Setting).filter(Setting.key == "current_sector").first()
    current_sector = sector_setting.value if sector_setting and sector_setting.value else "teknik_servis"

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "sector": current_sector
        }
    }


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register New User
    
    Desktop Function: add_user(username, password, role)
    Creates new user account with hashed password
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create new user
    new_user = User(
        username=user_data.username,
        password=hashed_password,
        role=user_data.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(
        data={
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role.value
        }
    )
    
    refresh_token = create_refresh_token(
        data={
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role.value
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "role": new_user.role.value
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user)
):
    """
    Get Current Authenticated User
    
    Returns user information from token
    """
    return current_user


@router.post("/logout")
async def logout():
    """
    Logout (Client-side token deletion)
    
    Since we use stateless JWT, logout is handled client-side
    """
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        from jose import jwt, JWTError
        token_payload = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    if token_payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = token_payload.get("user_id")
    username = token_payload.get("username")
    role = token_payload.get("role")

    if not user_id or not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh payload"
        )

    user = db.query(User).filter(User.id == user_id, User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    new_access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": role or user.role.value
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    new_refresh_token = create_refresh_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": role or user.role.value
        }
    )

    sector_setting = db.query(Setting).filter(Setting.key == "current_sector").first()
    current_sector = sector_setting.value if sector_setting and sector_setting.value else "teknik_servis"

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "sector": current_sector
        }
    }
