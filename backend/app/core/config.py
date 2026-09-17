"""
Configuration Management
AYEC Pro Backend
"""
import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")
    
    # App
    APP_NAME: str = "AYEC Pro API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "sqlite:///./ayecpro.db"
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS -- override with comma-separated list in .env
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://85.117.239.60"
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI
    GEMINI_API_KEY: str = ""
    
    # SMS
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # Email
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@bulutteknoloji.com"
    
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
