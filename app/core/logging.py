import logging
import os
from logging.handlers import TimedRotatingFileHandler

from concurrent_log_handler import ConcurrentRotatingFileHandler


def setup_logging(is_scheduler: bool = False) -> logging.Logger:
    """
    Gunicorn / Uvicorn 멀티 프로세스 환경에서
    안전한 파일 로깅을 설정합니다.

    Args:
        is_scheduler: 스케줄러 프로세스용 로그 설정 여부
    """
    # 경로 설정 (Project Root/logs/app.log)
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    # 로그 파일 경로 설정 (스케줄러용 분리)
    if is_scheduler:
        app_log_path = os.path.join(log_dir, "scheduler.log")
        error_log_path = os.path.join(log_dir, "scheduler_error.log")
        log_prefix = "SCHEDULER"
    else:
        app_log_path = os.path.join(log_dir, "app.log")
        error_log_path = os.path.join(log_dir, "error.log")
        log_prefix = "APP"

    log_format = (
        f"%(asctime)s | %(levelname)-8s | {log_prefix} | PID:%(process)d | "
        "%(name)s:%(lineno)d | %(message)s"
    )
    formatter = logging.Formatter(log_format)

    # --------------------
    # Root Logger
    # --------------------
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # preload_app / reload / lifespan 중복 방지
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 콘솔 핸들러 (Gunicorn stdout 수집용)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 멀티프로세스 안전 파일 핸들러 (전체 로그)
    file_handler = ConcurrentRotatingFileHandler(
        filename=app_log_path,
        mode="a",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
        use_gzip=True,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    error_handler = TimedRotatingFileHandler(
        filename=error_log_path,
        when="midnight",  # 매일 자정에 새 파일 생성
        interval=1,  # 1일 간격
        backupCount=30,  # 30일치 보관
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)  # ERROR 레벨 이상만 기록
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # --------------------
    # Uvicorn / FastAPI Logger 통합
    # --------------------
    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
    ):
        _logger = logging.getLogger(logger_name)
        _logger.handlers.clear()  # uvicorn 기본 핸들러 제거
        _logger.propagate = True  # root_logger로 전달
        _logger.setLevel(logging.INFO)

    return root_logger
