"""
API 응답 유틸리티
"""

from typing import Any, NotRequired, TypedDict

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.utils.pagination import PaginationInfo
from app.utils.types import ApiResponseDataType


class StatusInfoDict(TypedDict):
    status: int
    message: str


class ResponseDict(TypedDict):
    result: str
    statusInfo: StatusInfoDict
    data: Any
    pagination: NotRequired[PaginationInfo | None]


def create_response(
    data: ApiResponseDataType = "",
    status_code: int = 200,
    pagination: PaginationInfo | None = None,
    message: str | None = None,
) -> JSONResponse:
    """표준화된 API 응답 생성"""

    result = "SUCCESS" if status_code < 400 else "FAILURE"
    message = message or ("OK" if status_code < 400 else "ERROR")

    response: ResponseDict = {
        "result": result,
        "statusInfo": {"status": status_code, "message": message},
        "data": data,
    }

    if pagination:
        response["pagination"] = pagination

    # JSONResponse에 Decimal, datetime, set은 직렬화 불가능 하여 jsonable_encoder 사용
    return JSONResponse(status_code=status_code, content=jsonable_encoder(response))
