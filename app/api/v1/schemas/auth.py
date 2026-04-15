"""
인증 관련 API 스키마
"""

from pydantic import BaseModel, Field, field_validator, model_validator

from .common_validators import validate_email_field


class UserSignupRequest(BaseModel):
    """사용자 회원가입 요청 스키마"""

    email: str = Field(..., description="이메일", min_length=1, max_length=255)
    password: str = Field(..., description="비밀번호", min_length=1)
    name: str = Field(..., description="이름", min_length=1, max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        return validate_email_field(v)


class UserLoginRequest(BaseModel):
    """사용자 로그인 요청 스키마"""

    email: str = Field(..., description="이메일", min_length=1, max_length=255)
    password: str = Field(..., description="비밀번호", min_length=1)


class TokenRefreshRequest(BaseModel):
    """토큰 갱신 요청 스키마"""

    refresh_token: str = Field(..., description="Refresh Token")


class UserPasswordChangeRequest(BaseModel):
    """사용자 비밀번호 변경 요청 스키마"""

    email: str = Field(..., description="사용자 이메일", min_length=1, max_length=255)
    current_password: str = Field(..., description="현재 비밀번호", min_length=1)
    new_password: str = Field(..., description="새 비밀번호", min_length=8)
    confirm_password: str = Field(..., description="새 비밀번호 확인", min_length=8)

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserPasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("새 비밀번호와 확인 비밀번호가 일치하지 않습니다.")
        return self
