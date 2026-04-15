import logging
import os
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.utils.error_class import Custom_Exception, Error_Code


# SQL 로깅을 위한 이벤트 리스너
def log_sql_execution(
    conn: Connection,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """실제 실행되는 SQL문을 로깅 (파라미터 바인딩 완료)"""
    try:
        bound_sql = statement

        # 파라미터가 있는 경우 바인딩
        if parameters:
            if isinstance(parameters, dict):
                # Named parameters 바인딩
                for key, value in parameters.items():  # type: ignore
                    placeholder = f"%({key})s"
                    # 값 타입에 따라 적절히 포맷팅
                    if isinstance(value, str):
                        bound_sql = bound_sql.replace(placeholder, f"'{value}'")
                    elif value is None:
                        bound_sql = bound_sql.replace(placeholder, "NULL")
                    elif isinstance(value, bool):
                        bound_sql = bound_sql.replace(
                            placeholder, "TRUE" if value else "FALSE"
                        )
                    else:
                        bound_sql = bound_sql.replace(placeholder, str(value))

            elif isinstance(parameters, list | tuple):
                # Positional parameters (간단히 표시)
                bound_sql = f"{statement} -- params: {parameters}"
            else:
                # 기타 케이스
                bound_sql = f"{statement} -- params: {parameters}"
        else:
            # 파라미터 없는 경우 원본 SQL
            pass

        # 길이가 너무 긴 경우 축약
        # if len(bound_sql) > 500:
        #     bound_sql = bound_sql[:500] + "..."

        logging.info("----- Executed SQL -----")
        logging.info(f"[SQL] {bound_sql}")
        logging.info("------------------------\n")

    except Exception as e:
        # 로깅 실패 시 원본 SQL만 출력
        logging.debug(
            f"[SQL] {statement} -- params: {parameters} (binding failed: {e})"
        )


# .env 파일에서 환경변수를 읽어오기
# 기본적으로 현재 작업 디렉토리의 .env를 찾지만, 경로를 직접 지정도 가능
load_dotenv()
load_dotenv(".env.local", override=True)  # .env.local이 있으면 덮어쓰기

# docker 환경변수 우선 적용
DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    # 환경변수를 읽어서 DB 접속 정보 구성
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_SERVICE_NAME = os.getenv("DB_SERVICE_NAME", "app_db")

    DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_SERVICE_NAME}"
    )

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    isolation_level="READ_COMMITTED",
    echo=False,  # 기본 echo 비활성화 (커스텀 로깅 사용)
    pool_size=8,  # 커넥션 풀의 크기
    poolclass=QueuePool,
    max_overflow=10,  # 최대 10개까지 추가 대기열 허용
    pool_timeout=30,  # 커넥션 못 받을 경우 30초 대기
    pool_recycle=3600,  # 1시간마다 커넥션 재활용 (zombie 방지)
    pool_pre_ping=True,  # DB 죽었는지 확인 (유휴 연결 확인)
)

# SQL 로깅 활성화 여부 (환경변수로 제어)
enable_sql_logging = os.getenv("ENABLE_SQL_LOGGING", "true").lower() == "true"
if enable_sql_logging:
    # SQL 실행 이벤트 리스너 등록 (실제 바인딩된 SQL 로깅)
    event.listen(engine, "before_cursor_execute", log_sql_execution)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pool = engine.pool
if isinstance(pool, QueuePool):
    logging.info(
        f"DB Pool - checkedin: {pool.checkedin()}, checkedout: {pool.checkedout()}, size: {pool.size()}"
    )


# 의존성 함수
def get_db():
    """
    db 세션 반환
    Depends사용시 commit, close, rollback 내부에서 진행함

    Yields:
        db: Session
    """

    db = SessionLocal()
    try:
        yield db

    except NoResultFound as e:
        logging.error(f"get_db error > {str(e)}")
        db.rollback()
        raise Custom_Exception(Error_Code.NOT_FOUND_EXCEPTION) from e

    except MultipleResultsFound as e:
        logging.error(f"get_db error > {str(e)}")
        db.rollback()
        raise Custom_Exception(Error_Code.MULTI_RESULT_EXCEPTION) from e

    except Exception as e:
        logging.error(f"get_db error > {str(e)}")
        print(
            "in_transaction",
            db.is_active,
            db.in_transaction(),
            db.in_nested_transaction(),
        )
        db.rollback()
        raise

    finally:
        db.close()


Base = declarative_base()
