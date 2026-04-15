from enum import Enum


class Error_Code(Enum):
    """커스텀 에러 코드 정의 (코드, HTTP상태, 메시지)"""

    # 공통 에러
    NOT_FOUND_EXCEPTION = ("ERR-10001", 400, "요청한 데이터가 존재하지 않습니다.")
    VALIDATION_ERROR = ("ERR-10002", 400, "요청 데이터 유효성 검사에 실패했습니다.")
    VALIDATION_EXCEPTION = ("ERR-10003", 400, "입력값이 유효하지 않습니다.")
    INVALID_REQUEST_EXCEPTION = ("ERR-10004", 400, "잘못된 요청입니다.")
    PARTIAL_FAILURE_EXCEPTION = ("ERR-10005", 207, "일부 작업이 실패했습니다.")
    GONE_EXCEPTION = ("ERR-10006", 410, "요청한 리소스가 더 이상 존재하지 않습니다.")
    FILE_NOT_FOUND = ("ERR-10007", 404, "파일을 찾을 수 없습니다.")

    # 데이터베이스 에러
    DATABASE_ERROR = ("ERR-20000", 500, "데이터베이스 처리 중 오류가 발생했습니다.")
    NO_MAPPING_DB_KEY_EXCEPTION = ("ERR-20001", 400, "컬럼 객체를 찾을 수 없습니다.")

    DATA_INTEGRITY_EXCEPTION = (
        "ERR-20002",
        400,
        "데이터베이스 무결성 제약 조건을 위반되었습니다.",
    )
    MULTI_RESULT_EXCEPTION = ("ERR-20003", 500, "여러 개의 데이터가 반환되었습니다.")
    DUPLICATE_KEY_EXCEPTION = (
        "ERR-20004",
        409,
        "데이터베이스 중복 키 제약 조건을 위반되었습니다.",
    )
    DATABASE_GENERAL_EXCEPTION = (
        "ERR-20005",
        500,
        "데이터베이스 실행 중 오류가 발생했습니다.",
    )
    INVALID_COLUMN_EXCEPTION = ("ERR-20006", 400, "컬럼의 길이 제한을 초과했습니다.")
    NO_DATETIME_COLUMN_EXCEPTION = ("ERR-20007", 400, "날짜 형식의 컬럼이 아닙니다.")

    UNAUTHORIZED_EXCEPTION = ("ERR-30001", 401, "인증이 필요합니다.")
    FORBIDDEN_EXCEPTION = ("ERR-30002", 403, "권한이 없습니다.")

    SERVER_ERROR = ("ERR-90000", 503, "서버 오류가 발생했습니다.")

    def __init__(self, code: str, http_status: int, description: str):
        self.code = code
        self.http_status = http_status
        self.description = description

    def __str__(self):
        return f"[{self.code}] {self.description}"


class Custom_Exception(Exception):
    """커스텀 예외 클래스"""

    def __init__(self, error_code: Error_Code, error_message: str = ""):
        self.code = error_code.code
        self.http_status = error_code.http_status
        self.error_msg = error_message or error_code.description

    def __str__(self):
        return self.error_msg
