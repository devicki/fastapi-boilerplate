"""
인증 데이터 액세스 레이어
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.databases.models import UserModel
from app.databases.session import SessionLocal


class AuthRepository:
    """인증 관련 데이터 액세스"""

    def __init__(self, db_session: Session | None = None):
        self.db = db_session or SessionLocal()

    def get_by_email(self, email: str) -> UserModel | None:
        """이메일로 사용자 조회"""
        return self.db.query(UserModel).filter(UserModel.email == email).first()

    def get_by_id(self, user_id: UUID) -> UserModel | None:
        """ID로 사용자 조회"""
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def create_user(self, user_model: UserModel) -> UserModel:
        """새 사용자 생성"""
        self.db.add(user_model)
        self.db.flush()
        self.db.refresh(user_model)
        return user_model

    def update_password(self, user_id: UUID, hashed_password: str) -> bool:
        """비밀번호 업데이트"""
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.hashed_password = hashed_password
        self.db.flush()
        return True

    def exists_by_email(self, email: str) -> bool:
        """이메일 존재 여부 확인"""
        return (
            self.db.query(UserModel).filter(UserModel.email == email).first()
            is not None
        )
