"""
사용자 데이터 액세스 레이어
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.schemas.common.request_filter import FilterParam
from app.databases.models import UserModel
from app.databases.session import SessionLocal
from app.utils.filter_utils.filter_class import FilterClass


class UserRepository:
    """사용자 데이터 액세스 레이어"""

    def __init__(self, db_session: Session | None = None):
        self.db = db_session or SessionLocal()

    def get_by_id(self, user_id: UUID) -> UserModel | None:
        """ID로 사용자 조회"""
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def get_all(
        self,
        offset: int | None,
        limit: int | None,
        filter_param: FilterParam | None = None,
    ) -> tuple[list[UserModel], int]:
        """모든 사용자 조회"""
        # 기본 쿼리 생성
        query = self.db.query(UserModel).filter(UserModel.is_active.is_(True))
        # 필터링 적용
        if filter_param:
            query = FilterClass(query, filter_param).build()

        # 전체 갯수 반환
        total_count = query.count()

        # offset과 limit이 None인 경우 전체 데이터 조회
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all(), total_count

    def exists_by_email(self, email: str) -> bool:
        """이메일로 사용자 존재 여부 확인"""
        return (
            self.db.query(UserModel).filter(UserModel.email == email).first()
            is not None
        )

    def create(self, user_model: UserModel) -> UserModel:
        """새 사용자 생성"""
        self.db.add(user_model)
        self.db.flush()  # commit 대신 flush 사용 (트랜잭션은 상위에서 관리)
        self.db.refresh(user_model)
        return user_model

    def update(self, user_id: UUID, **kwargs: Any) -> UserModel | None:
        """사용자 정보 업데이트"""
        user_model = self.get_by_id(user_id)
        if not user_model:
            return None

        for key, value in kwargs.items():
            if hasattr(user_model, key):
                setattr(user_model, key, value)

        self.db.flush()  # commit 대신 flush 사용 (트랜잭션은 상위에서 관리)
        self.db.refresh(user_model)
        return user_model

    def delete(self, user_id: UUID) -> bool:
        """사용자 삭제"""
        user_model = self.get_by_id(user_id)
        if not user_model:
            return False

        self.db.delete(user_model)
        self.db.flush()  # commit 대신 flush 사용 (트랜잭션은 상위에서 관리)
        return True
