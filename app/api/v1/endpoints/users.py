"""
사용자 API 엔드포인트
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import check_permission
from app.api.v1.schemas.common.request_filter import FilterParam
from app.api.v1.schemas.user import UserCreate, UserUpdate
from app.databases.session import get_db
from app.repositories.users.user_repository import UserRepository
from app.services.users.user_service import UserService
from app.utils.pagination import create_pagination_info
from app.utils.response_utils import create_response
from app.utils.types import CurrentUserInfoDict

router = APIRouter(prefix="/users", tags=["users (sample)"])
PERMISSION_PREFIX = "users"


@router.get("/list")
def get_users(
    page: int = Query(1, ge=0, description="페이지 번호 (0이면 전체 데이터 조회)"),
    rows: int = Query(
        10, ge=0, le=100, description="페이지당 항목 수 (0이면 전체 데이터 조회)"
    ),
    filter_param: FilterParam = Depends(),
    current_user: CurrentUserInfoDict = Depends(check_permission(PERMISSION_PREFIX)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """모든 사용자 조회"""
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)

    users, total_count = user_service.get_all_users(page, rows, filter_param)

    # 페이지 정보 생성
    pagination = create_pagination_info(page, rows, total_count)

    return create_response(data=users, pagination=pagination)


@router.get("/by-id")
def get_user(
    user_id: UUID = Query(..., description="조회할 사용자 ID"),
    current_user: CurrentUserInfoDict = Depends(check_permission(PERMISSION_PREFIX)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """특정 사용자 조회"""
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)

    user = user_service.get_user_by_id(user_id)

    return create_response(data=user)


@router.post("/create", status_code=201)
def create_user(
    user_data: UserCreate,
    current_user: CurrentUserInfoDict = Depends(
        check_permission(PERMISSION_PREFIX, "create")
    ),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """새 사용자 생성"""
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)

    with user_service.transaction():
        user = user_service.create_user(
            email=user_data.email, name=user_data.name, current_user=current_user
        )

    return create_response(data=user, status_code=201)


@router.put("/update")
def update_user(
    user_data: UserUpdate,
    current_user: CurrentUserInfoDict = Depends(
        check_permission(PERMISSION_PREFIX, "update")
    ),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """사용자 정보 업데이트"""
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)

    # 업데이트할 필드만 추출
    update_data = user_data.model_dump(exclude_unset=True)

    with user_service.transaction():
        user = user_service.update_user(current_user=current_user, **update_data)

    return create_response(data=user)


@router.delete("/delete")
def delete_user(
    user_id: UUID = Query(..., description="삭제할 사용자 ID"),
    current_user: CurrentUserInfoDict = Depends(
        check_permission(PERMISSION_PREFIX, "delete")
    ),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """사용자 삭제"""
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)

    with user_service.transaction():
        user_service.delete_user(user_id, current_user=current_user)

    return create_response(data=None, message="사용자가 삭제되었습니다.")
