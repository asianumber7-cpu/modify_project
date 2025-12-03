import logging
import os  # 👈 [필수 추가] 이 부분이 없어서 에러가 발생했습니다.
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi.staticfiles import StaticFiles
from src.config.settings import settings
from src.core.security import setup_superuser # 초기 관리자 생성 함수
from src.db.session import engine, async_session_maker # DB engine 및 session maker
from src.middleware.exception_handler import global_exception_handler
from src.api.v1 import api_router # 통합 라우터 (auth, users, products, search, admin 포함)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# 1. Lifespan 이벤트 핸들러 (Startup/Shutdown 관리)
# --------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 시 이벤트를 처리합니다."""
    
    # [Startup] Redis 및 Rate Limiter 초기화
    try:
        redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_connection)
        logger.info("✅ Rate Limiter System Ready.")
    except Exception as e:
        logger.error(f"⚠️ Redis Connection Failed. Rate Limiter will be inactive: {e}")
        # Redis 연결이 실패해도 앱은 계속 실행되도록 합니다. (rate limit 기능만 비활성화)
    
    # [Startup] 초기 관리자 계정 생성 및 DB 유효성 검사
    async with async_session_maker() as session:
        try:
            await setup_superuser(session)
            logger.info("Default superuser setup checked/completed.")
        except Exception as e:
            logger.error(f"Failed to set up superuser (DB Error likely): {e}")

    yield # 애플리케이션 실행

    # [Shutdown] 리소스 해제
    # FastAPILimiter.shutdown()은 별도로 구현되어 있지 않으므로, Redis 연결만 닫습니다.
    if 'redis_connection' in locals():
        await redis_connection.close()
    await engine.dispose() # DB 연결 풀 해제
    logger.info("Application shutdown complete.")

# --------------------------------------------------------------------------
# 2. FastAPI 애플리케이션 인스턴스 생성
# --------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan, # Lifespan 등록
    docs_url="/docs" if settings.ENVIRONMENT == "dev" else None,
    openapi_url="/openapi.json"
)

# --------------------------------------------------------------------------
# 3. CORS 미들웨어 설정
# --------------------------------------------------------------------------
origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:5173", 
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    settings.FRONTEND_URL, 
    "http://0.0.0.0:5173" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# 4. 예외 핸들러 및 라우터 포함
# --------------------------------------------------------------------------
# 전역 예외 핸들러 등록
app.add_exception_handler(Exception, global_exception_handler)

# 통합 API 라우터 연결 (prefix="/api/v1")
app.include_router(api_router, prefix=settings.API_V1_STR)

# --------------------------------------------------------------------------
# [추가된 기능] 정적 파일(이미지) 서빙 설정
# --------------------------------------------------------------------------
# static/images 폴더가 없으면 생성 (이제 import os가 있어서 에러 안 남)
try:
    os.makedirs("static/images", exist_ok=True)
    # 브라우저에서 http://localhost:8000/static/images/... 로 접근 가능하게 함
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Static file serving enabled at /static")
except Exception as e:
    logger.error(f"⚠️ Failed to setup static file serving: {e}")

# --------------------------------------------------------------------------
# 5. 루트 엔드포인트
# --------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """상태 체크 엔드포인트"""
    return {"status": "ok", "env": settings.ENVIRONMENT}

@app.get("/")
def read_root():
    """기본 루트 엔드포인트"""
    return {"message": f"Welcome to {settings.PROJECT_NAME} API Service"}