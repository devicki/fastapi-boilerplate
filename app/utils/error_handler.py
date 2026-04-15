import logging
import logging.handlers
import os
import traceback
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.utils.error_class import Custom_Exception, Error_Code


# ==================== 에러 전용 로거 설정 ====================
def setup_error_logger() -> logging.Logger:
    """에러 전용 파일 로거 설정 (일별 로테이션)"""
    error_logger = logging.getLogger("error_logger")

    # 이미 핸들러가 설정되어 있으면 중복 설정 방지
    if error_logger.handlers:
        return error_logger

    # 로그 디렉토리 생성
    log_dir = "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    try:
        # 에러 전용 파일 핸들러 (일별 로테이션, 30일 보관)
        error_handler = logging.handlers.TimedRotatingFileHandler(
            f"{log_dir}/error.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )

        error_formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [PID:%(process)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        error_handler.setFormatter(error_formatter)
        error_handler.setLevel(logging.ERROR)

        error_logger.addHandler(error_handler)
        error_logger.setLevel(logging.ERROR)
        error_logger.propagate = False

    except Exception as e:
        logging.warning(f"Failed to setup error logger: {e}")

    return error_logger


# 전역 에러 로거 인스턴스
error_logger = setup_error_logger()


# ==================== 유틸리티 함수 ====================
def get_timestamp() -> str:
    """현재 타임스탬프 반환"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def find_last_my_code(
    tb: list[traceback.FrameSummary],
) -> traceback.FrameSummary | None:
    """내가 작성한 코드 중 가장 마지막 호출 위치 찾기"""
    for trace in reversed(tb):
        if "venv" not in trace.filename and "site-packages" not in trace.filename:
            return trace
    return tb[-1] if tb else None


def log_error(request: Request, exc: Exception):
    """에러 정보를 파일에 로깅"""
    try:
        error_msg = str(exc) if exc else "Unknown error"
    except Exception:
        error_msg = f"Error converting exception: {type(exc).__name__}"

    # 기본 에러 정보
    error_logger.error(f"Exception: {exc.__class__.__name__}: {error_msg}")
    error_logger.error(f"Request: {request.method} {request.url}")

    # 스택 트레이스
    if exc.__traceback__:
        tb = traceback.extract_tb(exc.__traceback__)
        if tb:
            last_call = find_last_my_code(tb)
            if last_call:
                error_logger.error(
                    f"Location: {last_call.filename}:{last_call.lineno} in {last_call.name}"
                )
        error_logger.error(f"Traceback:\n{traceback.format_exc()}")


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    request: Request,
    details: str | None = None,
) -> JSONResponse:
    """통일된 에러 응답 생성"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": get_timestamp(),
                "path": str(request.url.path),
                "details": details,
            },
        },
    )


# ==================== 에러 핸들러 ====================
async def custom_exception_handler(request: Request, exc: Custom_Exception):
    """커스텀 예외 핸들러"""
    log_error(request, exc)

    return create_error_response(
        status_code=exc.http_status,
        error_code=exc.code,
        message=exc.error_msg,
        request=request,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 유효성 검사 에러 핸들러"""
    log_error(request, exc)

    # 상세 에러 메시지 생성
    details: list[str] = []
    for error in exc.errors():
        param = ".".join(str(loc) for loc in error["loc"])
        details.append(f"{param}: {error['msg']}")

    return create_error_response(
        status_code=Error_Code.VALIDATION_ERROR.http_status,
        error_code=Error_Code.VALIDATION_ERROR.code,
        message=f"{Error_Code.VALIDATION_ERROR.description}",
        details=", ".join(details),
        request=request,
    )


async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러 (예상치 못한 에러)"""
    log_error(request, exc)

    return create_error_response(
        status_code=Error_Code.SERVER_ERROR.http_status,
        error_code=Error_Code.SERVER_ERROR.code,
        message=Error_Code.SERVER_ERROR.description,
        request=request,
    )


async def database_exc_error_handler(request: Request, exc: DatabaseError):
    """데이터베이스 관련 예외 핸들러"""
    log_error(request, exc)

    # 데이터베이스 에러 타입에 따른 세부 처리
    if isinstance(exc, IntegrityError):
        error_code_obj = Error_Code.DATA_INTEGRITY_EXCEPTION
    else:
        error_code_obj = Error_Code.DATABASE_GENERAL_EXCEPTION

    return create_error_response(
        status_code=error_code_obj.http_status,
        error_code=error_code_obj.code,
        message=error_code_obj.description,
        request=request,
    )


# ==================== 핸들러 등록 ====================
def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 에러 핸들러 등록"""
    app.add_exception_handler(Custom_Exception, custom_exception_handler)  # type: ignore
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(DatabaseError, database_exc_error_handler)  # type: ignore
