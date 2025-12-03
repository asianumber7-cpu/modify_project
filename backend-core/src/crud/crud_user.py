from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.user import User
from src.schemas.user import UserCreate
from src.core.security import get_password_hash, verify_password

# --------------------------------------------------------------------------
# [NEW] ID로 유저 조회 (필수 기능 추가)
# --------------------------------------------------------------------------
async def get(db: AsyncSession, user_id: int) -> Optional[User]:
    """ID 기반 유저 조회"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

# --------------------------------------------------------------------------
# 이메일로 유저 조회
# --------------------------------------------------------------------------
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """이메일 기반 유저 조회"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

# --------------------------------------------------------------------------
# 유저 생성
# --------------------------------------------------------------------------
async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """새로운 유저 생성 (비밀번호 해싱 적용)"""
    hashed_password = get_password_hash(user.password)
    db_obj = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        provider="local"
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

# --------------------------------------------------------------------------
# 인증 확인 (로그인 용)
# --------------------------------------------------------------------------
async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """이메일과 비밀번호로 유저 검증"""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user