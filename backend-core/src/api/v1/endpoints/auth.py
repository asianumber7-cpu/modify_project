from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from src.api.deps import get_db, get_current_user
from src.core import security
from src.crud import crud_user
from src.schemas.user import UserCreate, UserResponse, Token
from src.models.user import User
from src.config.settings import settings

router = APIRouter()

# --------------------------------------------------------------------------
# 회원가입 API
# POST /api/v1/auth/signup
# --------------------------------------------------------------------------
@router.post("/signup", response_model=UserResponse, status_code=201)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    일반 사용자 회원가입
    """
    # 이메일 중복 체크
    user = await crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # 유저 생성
    user = await crud_user.create_user(db, user=user_in)
    return user

# --------------------------------------------------------------------------
# 로그인 API
# POST /api/v1/auth/login
# --------------------------------------------------------------------------
@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 호환 토큰 로그인 (username=이메일)
    """
    user = await crud_user.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Access Token (짧은 만료)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    # Refresh Token (긴 만료: 7일)
    refresh_token_expires = timedelta(days=7)
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

# --------------------------------------------------------------------------
# 토큰 갱신 API
# POST /api/v1/auth/refresh
# --------------------------------------------------------------------------
@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh Token을 검증하여 새로운 Access Token을 발급합니다.
    """
    try:
        # 토큰 디코딩 및 검증
        payload = jwt.decode(
            refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_type = payload.get("type")
        user_id = payload.get("sub")
        
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token subject")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
        
    # 🚨 [CRITICAL FIX] 올바른 함수 호출: crud_user.get_user -> crud_user.get
    # crud_user.py 파일에 정의된 함수명(get)과 일치해야 합니다.
    user = await crud_user.get(db, user_id=int(user_id))
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # 새 Access Token 발급
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Refresh Token Rotation (보안 강화: Refresh Token도 새로 발급)
    new_refresh_token = security.create_refresh_token(
        user.id, expires_delta=timedelta(days=7)
    )
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

# --------------------------------------------------------------------------
# 내 정보 조회 API
# GET /api/v1/auth/me
# --------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 내 정보 조회
    """
    return current_user