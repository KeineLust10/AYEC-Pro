"""
JWT Authentication & Security
Premium Bulut Backend
"""
import bcrypt
# --- BCRYPT/PASSLIB BUG FIX ---
# Fix for "AttributeError: module 'bcrypt' has no attribute '__about__'" with passlib
if not hasattr(bcrypt, '__about__'):
    try:
        from bcrypt import __version__ as version
        class About:
            __version__ = version
        bcrypt.__about__ = About()
    except ImportError:
        pass
# ------------------------------

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password (bcrypt 72 byte limit safe)"""
    truncated = password[:72]  # bcrypt 72 byte limit
    try:
        return pwd_context.hash(truncated)
    except Exception:
        # Fallback: direct bcrypt if passlib fails on Python 3.14
        hashed = bcrypt.hashpw(truncated.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("token_type")
        # Backward compatible: older access tokens may not have token_type.
        if token_type and token_type != "access":
            raise credentials_exception
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        
        if username is None or user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Return user data from token (you can also query DB here if needed)
    return {
        "id": user_id,
        "username": username,
        "role": payload.get("role", "user")
    }


def check_permission(user_role: str, required_action: str) -> bool:
    """
    Role-Based Access Control
    
    Roles:
    - Admin: All actions
    - Teknisyen: View dashboard, add service, update status, view stock
    - Muhasebe: View dashboard, accounting, add transaction, export
    - Stajyer: View dashboard, view stock
    """
    permissions = {
        "Admin": ["*"],  # All actions
        "Teknisyen": [
            "view_dashboard",
            "add_service",
            "update_service",
            "view_stock",
            "use_part",
            "add_customer",
            "view_customer"
        ],
        "Muhasebe": [
            "view_dashboard",
            "view_accounting",
            "add_transaction",
            "export_data",
            "view_reports",
            "view_customer"
        ],
        "Stajyer": [
            "view_dashboard",
            "view_stock"
        ]
    }
    
    user_permissions = permissions.get(user_role, [])
    
    # Admin has all permissions
    if "*" in user_permissions:
        return True
    
    return required_action in user_permissions
