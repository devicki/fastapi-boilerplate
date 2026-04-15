import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers.entry import router as v1_router
from app.core.logging import setup_logging
from app.utils.error_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 앱의 라이프사이클 이벤트를 관리하는 컨텍스트 매니저입니다.
    """
    # 앱 시작시 실행되는 로직을 여기에 추가할 수 있습니다.

    # 로깅 초기화
    setup_logging()

    yield
    # 앱 종료시 실행되는 로직을 여기에 추가할 수 있습니다.


app = FastAPI(
    title="FastAPI Boilerplate",
    description="A reusable FastAPI boilerplate with JWT auth, Redis caching, and PostgreSQL",
    version="1.0.0",
    redoc_url=None,
    lifespan=lifespan,
)


# ==================== 미들웨어 설정 ====================

# CORS 미들웨어 (크로스 오리진 요청 허용)
cors_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
allow_origins = (
    [origin.strip() for origin in cors_origins.split(",")]
    if cors_origins != "*"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(v1_router)

# 에러 핸들러 등록
register_exception_handlers(app)
