import os
from typing import Literal, Any, Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, EmailStr, Field

class Settings(BaseSettings):
    """
    애플리케이션 전역 설정 관리
    Pydantic V2 패턴 및 환경변수 안전성 검증 적용
    """
    
    # Project Info
    PROJECT_NAME: str = Field("MODIFY AI Shopping Mall", description="프로젝트 이름")
    
    # API Prefix
    API_V1_STR: str = "/api/v1"
    
    ENVIRONMENT: Literal["dev", "prod", "test"] = "dev"
    DEBUG: bool = True
    
    # Security
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256" # 토큰 알고리즘은 상수로 유지
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENCRYPTION_KEY: str = Field(..., description="민감 데이터 암호화 키")

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret_length(cls, v: Any) -> str:
        if isinstance(v, str) and len(v) < 32:
            raise ValueError("⚠️ JWT_SECRET_KEY must be at least 32 characters long for security.")
        return v
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    DB_POOL_SIZE: int = 30
    DB_MAX_OVERFLOW: int = 20

    # Redis & Celery
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    CELERY_TASK_TIME_LIMIT: int = 600
    
    # AI & Vector DB
    EMBEDDING_DIMENSION: int = 768 # 벡터 차원 (768D)
    
    # 🚨 [FIX] AI Service Connection URL 추가 (Docker Network Internal URL)
    # 기본값: http://ai-service-api:8000/api/v1 (docker-compose 서비스명 기준)
    AI_SERVICE_API_URL: str = Field(
        "http://ai-service-api:8000/api/v1", 
        description="AI 서비스 내부 통신 URL"
    )
    
    @field_validator("EMBEDDING_DIMENSION", mode="before")
    @classmethod
    def validate_embedding_dim(cls, v: Any) -> int:
        if int(v) != 768:
            raise ValueError("⚠️ EMBEDDING_DIMENSION must be 768 to match the chosen Embedding model.")
        return int(v)

    # Superuser Setup
    SUPERUSER_EMAIL: EmailStr = Field(..., description="초기 관리자 이메일")
    SUPERUSER_PASSWORD: str = Field(..., description="초기 관리자 비밀번호")
    
    # External APIs (필요 시)
    GOOGLE_API_KEY: str | None = None
    GOOGLE_SEARCH_ENGINE_ID: str | None = None
    
    # Storage
    STORAGE_TYPE: Literal["local", "s3"] = "local"
    
    #Frontend URL 환경 변수 추가
    FRONTEND_URL: str = Field(
    "http://localhost:5173", # 기본값: Vite 개발 서버 주소
    description="Frontend 서비스 URL (CORS Origin에 사용)"
)
    
    # Email Settings
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int = 587
    MAIL_SERVER: str
    MAIL_FROM_NAME: str = "MODIFY Service"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # --- Computed Properties ---
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # --- Pydantic V2 Configuration ---
    model_config = SettingsConfigDict(
        env_file=".env.dev", 
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()