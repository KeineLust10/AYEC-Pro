# -*- coding: utf-8 -*-


import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..utils.config import config

class AuthHandler:
    security = HTTPBearer()
    SECRET_KEY = config.secret_key
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS = 30
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=AuthHandler.ACCESS_TOKEN_EXPIRE_DAYS)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, AuthHandler.SECRET_KEY, algorithm=AuthHandler.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, AuthHandler.SECRET_KEY, algorithms=[AuthHandler.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Oturum süresi doldu")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Geçersiz oturum")
            
    @staticmethod
    def get_current_user(token_data: Dict[str, Any] = Depends(verify_token)):
        # This function acts as a dependency that returns the user data
        return token_data
