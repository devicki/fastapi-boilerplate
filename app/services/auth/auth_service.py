"""
인증 관련 비즈니스 로직 구현
"""

import base64
import os
from contextlib import contextmanager
from typing import Any, Literal, cast

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.databases.models import UserModel
from app.repositories.auth.auth_repository import AuthRepository
from app.utils.error_class import Custom_Exception, Error_Code
from app.utils.jwt_utils import (
    create_token_pair,
    logout_user,
    refresh_access_token,
    verify_access_token,
)
from app.utils.password_utils import hash_password, verify_password
from app.utils.types import CurrentUserInfoDict


class AuthService:
    """인증 도메인 서비스"""

    # 쿠키 보안 설정
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", None)
    COOKIE_PATH = os.getenv("COOKIE_PATH", "/")
    USE_HOST_PREFIX = os.getenv("USE_HOST_PREFIX", "false").lower() == "true"

    def __init__(
        self,
        db_session: Session,
    ):
        self.db_session = db_session
        self.auth_repository = AuthRepository(db_session)

    # ==================== 쿠키 헬퍼 ====================

    @classmethod
    def get_cookie_samesite(cls) -> Literal["lax", "strict", "none"]:
        """쿠키 SameSite 값 검증 및 설정"""
        samesite = os.getenv("COOKIE_SAMESITE", "lax")
        if samesite in ["lax", "strict", "none"]:
            return cast(Literal["lax", "strict", "none"], samesite)
        return "lax"

    @classmethod
    def get_cookie_key(cls, base_name: str) -> str:
        """쿠키 키 이름 생성 (환경에 따라 __Host- prefix 적용)"""
        if cls.USE_HOST_PREFIX:
            return f"__Host-{base_name}"
        return base_name

    @classmethod
    def get_access_token_from_cookies(cls, request: Request) -> str | None:
        """쿠키에서 액세스 토큰 추출"""
        return request.cookies.get(cls.get_cookie_key("access_token"))

    @classmethod
    def get_refresh_token_from_cookies(cls, request: Request) -> str | None:
        """쿠키에서 리프레시 토큰 추출"""
        return request.cookies.get(cls.get_cookie_key("refresh_token"))

    @classmethod
    def set_cookie_safe(
        cls, response: JSONResponse, key: str, value: str, max_age: int
    ) -> None:
        """안전한 쿠키 설정 함수 - 기본 보안 설정 자동 적용"""
        samesite = cls.get_cookie_samesite()
        cookie_kwargs: dict[str, Any] = {
            "key": key,
            "value": value,
            "httponly": True,
            "secure": cls.COOKIE_SECURE,
            "samesite": samesite,
            "max_age": max_age,
            "path": cls.COOKIE_PATH,
        }
        if cls.COOKIE_DOMAIN:
            cookie_kwargs["domain"] = cls.COOKIE_DOMAIN
        response.set_cookie(**cookie_kwargs)

    @classmethod
    def delete_cookie_safe(cls, response: JSONResponse, key: str) -> None:
        """안전한 쿠키 삭제 함수 - 기본 보안 설정 자동 적용"""
        samesite = cls.get_cookie_samesite()
        cookie_kwargs: dict[str, Any] = {
            "key": key,
            "httponly": True,
            "secure": cls.COOKIE_SECURE,
            "samesite": samesite,
            "path": cls.COOKIE_PATH,
        }
        if cls.COOKIE_DOMAIN:
            cookie_kwargs["domain"] = cls.COOKIE_DOMAIN
        response.delete_cookie(**cookie_kwargs)

    @classmethod
    def set_token_cookies(
        cls, response: JSONResponse, access_token: str, refresh_token: str
    ) -> None:
        """Access Token과 Refresh Token 쿠키를 한 번에 설정"""
        cls.set_cookie_safe(
            response,
            key=cls.get_cookie_key("access_token"),
            value=access_token,
            max_age=cls._get_access_token_expire_seconds(),
        )
        cls.set_cookie_safe(
            response,
            key=cls.get_cookie_key("refresh_token"),
            value=refresh_token,
            max_age=cls._get_refresh_token_expire_seconds(),
        )

    @classmethod
    def delete_token_cookies(cls, response: JSONResponse) -> None:
        """Access Token과 Refresh Token 쿠키를 한 번에 삭제"""
        cls.delete_cookie_safe(response, key=cls.get_cookie_key("access_token"))
        cls.delete_cookie_safe(response, key=cls.get_cookie_key("refresh_token"))

    @classmethod
    def _get_access_token_expire_seconds(cls) -> int:
        """Access Token 만료 시간 (초)"""
        from app.utils.jwt_utils import get_access_token_expire_seconds

        return get_access_token_expire_seconds()

    @classmethod
    def _get_refresh_token_expire_seconds(cls) -> int:
        """Refresh Token 만료 시간 (초)"""
        from app.utils.jwt_utils import get_refresh_token_expire_seconds

        return get_refresh_token_expire_seconds()

    # ==================== 인증 로직 ====================

    @classmethod
    def get_current_user(cls, request: Request) -> CurrentUserInfoDict:
        """현재 사용자 정보 조회 (의존성 주입용)"""
        user_data = None

        # 개발환경 자동 로그인 확인
        enable_auto_login = (
            os.getenv("LOCAL_ENABLE_AUTO_LOGIN", "false").lower() == "true"
        )

        # 쿠키에서 access_token 가져오기
        access_token = cls.get_access_token_from_cookies(request)

        if not access_token and enable_auto_login:
            # 개발용 자동 로그인 사용자
            user_data: dict[str, Any] | None = {
                "sub": "00000000-0000-0000-0000-000000000000",
                "name": "Dev Admin",
                "email": "admin@example.com",
                "role": "admin",
            }
        else:
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="인증 토큰이 필요합니다.",
                )

            # 토큰 검증
            user_data = verify_access_token(access_token)
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="유효하지 않은 액세스 토큰입니다.",
                )

            user_id = user_data.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="토큰에 사용자 정보가 없습니다.",
                )

        return {
            "id": user_data.get("sub", ""),
            "name": user_data.get("name", ""),
            "email": user_data.get("email", ""),
            "role": user_data.get("role", "user"),
        }

    @classmethod
    def check_permission(
        cls,
        current_user: CurrentUserInfoDict | None,
        required_permission: str | None = None,
        sub_permission: str = "read",
    ) -> CurrentUserInfoDict:
        """역할 기반 권한 체크"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증이 필요합니다.",
            )

        if not required_permission:
            return current_user

        # 역할 기반 권한 체크
        # admin: 모든 권한 허용
        # user: read 권한만 허용
        user_role = current_user.get("role", "user")

        if user_role == "admin":
            return current_user

        # user 역할은 read만 허용
        if sub_permission == "read":
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"'{required_permission}.{sub_permission}' 권한이 필요합니다.",
        )

    @classmethod
    def decode_password(cls, encoded_password: str) -> str:
        """base64로 인코딩된 비밀번호 디코딩"""
        try:
            return base64.b64decode(encoded_password).decode("utf-8")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비밀번호 형식이 올바르지 않습니다.",
            ) from None

    @contextmanager
    def transaction(self):
        """트랜잭션 관리"""
        try:
            yield
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            raise e

    def signup_user(
        self,
        signup_data: dict[str, Any],
    ) -> dict[str, Any]:
        """사용자 회원가입"""
        email = signup_data["email"]
        name = signup_data["name"]
        password = signup_data["password"]

        # 이메일 중복 확인
        if self.auth_repository.exists_by_email(email):
            raise Custom_Exception(
                Error_Code.DUPLICATE_KEY_EXCEPTION,
                "이미 등록된 이메일입니다.",
            )

        # 비밀번호 해싱
        hashed = hash_password(password)

        # 사용자 생성
        user_model = UserModel(
            email=email,
            name=name,
            hashed_password=hashed,
            role="user",
            is_active=True,
        )

        saved = self.auth_repository.create_user(user_model)

        return {
            "id": str(saved.id),
            "email": saved.email,
            "name": saved.name,
            "role": saved.role,
            "is_active": saved.is_active,
            "created_at": saved.created_at,
        }

    def login_user(
        self,
        login_data: dict[str, str],
    ) -> tuple[str, str]:
        """사용자 로그인. (access_token, refresh_token) 반환."""
        email = login_data["email"]
        password = login_data["password"]

        # 사용자 조회
        user_model = self.auth_repository.get_by_email(email)
        if not user_model or not user_model.is_active:
            raise Custom_Exception(
                Error_Code.NOT_FOUND_EXCEPTION,
                "사용자 정보를 찾을 수 없습니다.",
            )

        # 비밀번호 검증
        if not user_model.hashed_password or not verify_password(
            password, user_model.hashed_password
        ):
            raise Custom_Exception(
                Error_Code.NOT_FOUND_EXCEPTION,
                "비밀번호가 올바르지 않습니다.",
            )

        # 토큰 데이터 생성
        token_data = {
            "sub": str(user_model.id),
            "email": user_model.email,
            "name": user_model.name,
            "role": user_model.role,
        }

        # 토큰 쌍 생성
        access_token, refresh_token = create_token_pair(token_data)

        return access_token, refresh_token

    def refresh_user_token(
        self,
        refresh_token: str,
        current_access_token: str | None = None,
    ) -> tuple[str, str]:
        """사용자 토큰 갱신"""
        result = refresh_access_token(refresh_token, current_access_token)
        if not result:
            raise Custom_Exception(
                Error_Code.UNAUTHORIZED_EXCEPTION, "유효하지 않은 리프레시 토큰입니다."
            )

        new_access_token, new_refresh_token = result

        token_data = verify_access_token(new_access_token)
        if not token_data:
            raise Custom_Exception(
                Error_Code.UNAUTHORIZED_EXCEPTION, "토큰 생성에 실패했습니다."
            )

        return new_access_token, new_refresh_token

    def logout_user(
        self,
        user_id: str,
        access_token: str | None = None,
    ) -> bool:
        """사용자 로그아웃"""
        success, _ = logout_user(user_id, access_token)
        return success

    def change_user_password(
        self,
        email: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """사용자 비밀번호 변경"""
        # 사용자 조회
        user_model = self.auth_repository.get_by_email(email)
        if not user_model or not user_model.is_active:
            raise Custom_Exception(
                Error_Code.NOT_FOUND_EXCEPTION,
                "사용자 정보를 찾을 수 없습니다.",
            )

        # 현재 비밀번호 검증
        if not user_model.hashed_password or not verify_password(
            current_password, user_model.hashed_password
        ):
            raise Custom_Exception(
                Error_Code.UNAUTHORIZED_EXCEPTION,
                "현재 비밀번호가 올바르지 않습니다.",
            )

        # 새 비밀번호가 현재 비밀번호와 같은지 확인
        if verify_password(new_password, user_model.hashed_password):
            raise Custom_Exception(
                Error_Code.VALIDATION_EXCEPTION,
                "새 비밀번호는 현재 비밀번호와 달라야 합니다.",
            )

        # 비밀번호 변경
        hashed = hash_password(new_password)
        success = self.auth_repository.update_password(user_model.id, hashed)
        if not success:
            raise Custom_Exception(
                Error_Code.SERVER_ERROR,
                "비밀번호 변경에 실패했습니다.",
            )

        return True
