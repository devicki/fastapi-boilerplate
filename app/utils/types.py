"""
공통 타입 정의
"""

from typing import Any, NotRequired, TypedDict


class CurrentUserInfoDict(TypedDict):
    """현재 사용자 정보"""

    id: str
    name: str
    email: NotRequired[str]
    role: NotRequired[str]


# API 응답의 data 타입
type ApiResponseDataType = (
    dict[str, Any]  # 단일 객체
    | list[dict[str, Any]]  # 목록
    | str  # 메시지
    | int  # 숫자
    | bool  # 불린
    | None  # 빈 응답
)
