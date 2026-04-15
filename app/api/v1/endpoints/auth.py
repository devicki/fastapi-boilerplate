"""
인증 API 엔드포인트
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.schemas.auth import (
    UserLoginRequest,
    UserPasswordChangeRequest,
    UserSignupRequest,
)
from app.databases.session import get_db
from app.services.auth.auth_service import AuthService
from app.utils.response_utils import create_response
from app.utils.types import CurrentUserInfoDict

router = APIRouter(prefix="/auth", tags=["auth (인증)"])


# JWT 쿠키 기반 토큰 인증
async def get_current_user(
    request: Request,
) -> CurrentUserInfoDict:
    """현재 사용자 정보 조회 (의존성 주입용)"""
    return AuthService.get_current_user(request)


def check_permission(
    required_permission: str | None = None, sub_permission: str = "read"
):
    """권한 체크 함수"""

    def permission_checker(
        current_user: CurrentUserInfoDict | None = Depends(get_current_user),
    ):
        """특정 권한이 있는지 확인"""
        return AuthService.check_permission(
            current_user, required_permission, sub_permission
        )

    return permission_checker


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup_user(
    user_data: UserSignupRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """사용자 회원가입"""
    auth_service = AuthService(db)

    signup_payload = user_data.model_dump()

    # base64로 인코딩된 비밀번호 디코딩
    decoded_password = AuthService.decode_password(user_data.password)
    signup_payload["password"] = decoded_password

    with auth_service.transaction():
        user = auth_service.signup_user(signup_payload)

    return create_response(
        data=user,
        message="회원가입이 성공적으로 완료되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login")
def login_user(
    login_data: UserLoginRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """사용자 로그인"""
    auth_service = AuthService(db)

    # base64로 인코딩된 비밀번호 디코딩
    decoded_password = AuthService.decode_password(login_data.password)

    login_payload = login_data.model_dump()
    login_payload["password"] = decoded_password

    with auth_service.transaction():
        access_token, refresh_token = auth_service.login_user(login_payload)

    response_data: dict[str, Any] = {
        "token_type": "bearer",
        "expires_in": AuthService._get_access_token_expire_seconds(),
    }

    response = create_response(
        data=response_data,
        message="로그인이 성공적으로 완료되었습니다.",
    )

    AuthService.set_token_cookies(response, access_token, refresh_token)

    return response


@router.post("/refresh")
def refresh_token(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Access Token 갱신"""
    auth_service = AuthService(db)

    refresh_token = AuthService.get_refresh_token_from_cookies(request)
    current_access_token = AuthService.get_access_token_from_cookies(request)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 쿠키에 없습니다.",
        )

    with auth_service.transaction():
        new_access_token, new_refresh_token = auth_service.refresh_user_token(
            refresh_token, current_access_token
        )

    response_data: dict[str, Any] = {
        "token_type": "bearer",
        "expires_in": AuthService._get_access_token_expire_seconds(),
    }

    response = create_response(
        data=response_data,
        message="토큰이 성공적으로 갱신되었습니다.",
    )

    AuthService.set_token_cookies(response, new_access_token, new_refresh_token)

    return response


@router.post("/logout")
def logout_user(
    request: Request,
    current_user: CurrentUserInfoDict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """사용자 로그아웃"""
    auth_service = AuthService(db)

    access_token = AuthService.get_access_token_from_cookies(request)

    with auth_service.transaction():
        success = auth_service.logout_user(current_user["id"], access_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 처리 중 오류가 발생했습니다.",
        )

    response = create_response(
        data=None,
        message="로그아웃이 성공적으로 완료되었습니다.",
    )

    AuthService.delete_token_cookies(response)

    return response


@router.get("/me")
def get_current_user_info(
    current_user: CurrentUserInfoDict = Depends(get_current_user),
) -> JSONResponse:
    """현재 로그인된 사용자 정보 조회"""
    return create_response(
        data=dict(current_user),
        message="현재 사용자 정보 조회에 성공했습니다.",
    )


@router.put("/password")
def change_password(
    password_data: UserPasswordChangeRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """비밀번호 변경"""
    auth_service = AuthService(db)

    # base64로 인코딩된 비밀번호 디코딩
    decoded_current_password = AuthService.decode_password(
        password_data.current_password
    )
    decoded_new_password = AuthService.decode_password(password_data.new_password)

    with auth_service.transaction():
        auth_service.change_user_password(
            email=password_data.email,
            current_password=decoded_current_password,
            new_password=decoded_new_password,
        )

    return create_response(
        message="비밀번호가 성공적으로 변경되었습니다.",
    )
