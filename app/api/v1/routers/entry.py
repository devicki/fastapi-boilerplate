from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router

# v1 API 라우터
router = APIRouter(prefix="/api/v1")

# ==================== 인증 ====================
router.include_router(auth_router)

# ==================== 샘플 CRUD ====================
router.include_router(users_router)
