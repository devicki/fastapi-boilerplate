"""
사용자 관련 비즈니스 로직 구현 (Sample)
"""

from contextlib import contextmanager
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.schemas.common.request_filter import FilterParam
from app.databases.models import UserModel
from app.repositories.users.user_repository import UserRepository
from app.utils.error_class import Custom_Exception, Error_Code
from app.utils.types import ApiResponseDataType, CurrentUserInfoDict


class UserService:
    """사용자 도메인 서비스"""

    def __init__(
        self,
        user_repository: UserRepository,
    ):
        self.user_repository = user_repository
        # 같은 DB 세션 사용 (같은 트랜잭션 보장)
        self.db_session: Session = user_repository.db

    @contextmanager
    def transaction(self):
        """트랜잭션 컨텍스트 매니저"""
        try:
            yield self
            self.db_session.commit()  # 성공 시 commit
        except Exception:
            self.db_session.rollback()  # 실패 시 rollback
            raise

    def get_user_by_id(self, user_id: UUID) -> ApiResponseDataType:
        """ID로 사용자 조회"""
        user_model = self.user_repository.get_by_id(user_id)
        if not user_model:
            raise Custom_Exception(Error_Code.NOT_FOUND_EXCEPTION)

        return {
            "id": user_model.id,
            "email": user_model.email,
            "name": user_model.name,
            "is_active": user_model.is_active,
            "created_at": user_model.created_at,
            "updated_at": user_model.updated_at,
        }

    def get_all_users(
        self, page: int, rows: int, filter_param: FilterParam
    ) -> tuple[ApiResponseDataType, int]:
        """모든 사용자 조회"""
        from app.utils.pagination import calculate_limit, calculate_offset

        offset = calculate_offset(page, rows)
        limit = calculate_limit(rows, page)

        user_models, total_count = self.user_repository.get_all(
            offset=offset, limit=limit, filter_param=filter_param
        )

        return [
            {
                "id": user_model.id,
                "email": user_model.email,
                "name": user_model.name,
                "is_active": user_model.is_active,
                "created_at": user_model.created_at,
                "updated_at": user_model.updated_at,
            }
            for user_model in user_models
        ], total_count

    def create_user(
        self, email: str, name: str, current_user: CurrentUserInfoDict
    ) -> ApiResponseDataType:
        """새 사용자 생성"""
        if self.user_repository.exists_by_email(email):
            raise Custom_Exception(Error_Code.DUPLICATE_KEY_EXCEPTION)

        user_model = UserModel(
            email=email,
            name=name,
            is_active=True,
        )

        saved_model = self.user_repository.create(user_model)

        return {
            "id": saved_model.id,
            "email": saved_model.email,
            "name": saved_model.name,
            "is_active": saved_model.is_active,
            "created_at": saved_model.created_at,
            "updated_at": saved_model.updated_at,
        }

    def update_user(
        self, current_user: CurrentUserInfoDict, **kwargs: Any
    ) -> ApiResponseDataType:
        """사용자 정보 업데이트"""
        user_id: UUID = kwargs.pop("user_id")

        existing_user: ApiResponseDataType = self.get_user_by_id(user_id)

        if (
            "email" in kwargs
            and isinstance(existing_user, dict)
            and kwargs["email"] != existing_user.get("email")
            and self.user_repository.exists_by_email(kwargs["email"])
        ):
            raise Custom_Exception(Error_Code.DUPLICATE_KEY_EXCEPTION)

        updated_model = self.user_repository.update(user_id, **kwargs)
        if not updated_model:
            raise Custom_Exception(Error_Code.NOT_FOUND_EXCEPTION)

        return {
            "id": updated_model.id,
            "email": updated_model.email,
            "name": updated_model.name,
            "is_active": updated_model.is_active,
            "created_at": updated_model.created_at,
            "updated_at": updated_model.updated_at,
        }

    def delete_user(self, user_id: UUID, current_user: CurrentUserInfoDict) -> None:
        """사용자 삭제"""
        self.get_user_by_id(user_id)

        deleted = self.user_repository.delete(user_id)
        if not deleted:
            raise Custom_Exception(Error_Code.NOT_FOUND_EXCEPTION)
