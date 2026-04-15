"""
페이지네이션 유틸리티
"""

import math
from typing import TypedDict

from app.utils.error_class import Custom_Exception, Error_Code


class PaginationInfo(TypedDict):
    """페이지네이션 정보를 담는 TypedDict"""

    page: int
    total: int
    total_page: int
    rows: int


def validate_pagination_params(page: int | None, rows: int | None) -> tuple[int, int]:
    """
    페이지네이션 파라미터 검증 및 기본값 처리

    Args:
        page: 페이지 번호 (1부터 시작). None이면 기본값 1 사용
        rows: 페이지당 항목 수. None이면 기본값 10 사용
        page=0이고 rows=0인 경우 전체 데이터를 반환 (특별 케이스)

    Returns:
        검증된 (page, rows) 튜플

    Raises:
        Custom_Exception: page나 rows가 유효하지 않은 경우 (단, page=0, rows=0은 허용)

    Examples:
        >>> validate_pagination_params(1, 10)
        (1, 10)
        >>> validate_pagination_params(None, None)
        (1, 10)
        >>> validate_pagination_params(2, 20)
        (2, 20)
        >>> validate_pagination_params(0, 0)
        (0, 0)
    """
    # page=0이고 rows=0인 경우는 전체 데이터 조회를 위한 특별 케이스로 허용
    if page == 0 and rows == 0:
        return 0, 0

    # 기본값 설정
    validated_page = page if page is not None else 1
    validated_rows = rows if rows is not None else 10

    # 엄격한 검증
    if validated_page <= 0:
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            f"페이지 번호는 1 이상이어야 합니다. (입력값: {page})",
        )

    if validated_rows <= 0:
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            f"페이지당 항목 수는 1 이상이어야 합니다. (입력값: {rows})",
        )

    return validated_page, validated_rows


def calculate_offset(page: int, rows: int) -> int | None:
    """
    SQL 쿼리용 OFFSET 값 계산

    Args:
        page: 페이지 번호 (1부터 시작)
        rows: 페이지당 항목 수
        page=0이고 rows=0인 경우 None 반환 (전체 데이터 조회)

    Returns:
        계산된 OFFSET 값. page=0이고 rows=0인 경우 None 반환

    Examples:
        >>> calculate_offset(1, 10)
        0
        >>> calculate_offset(2, 10)
        10
        >>> calculate_offset(3, 20)
        40
        >>> calculate_offset(0, 0)
        None
    """
    # page=0이고 rows=0인 경우는 전체 데이터 조회를 의미하므로 None 반환
    if page == 0 and rows == 0:
        return None
    return (page - 1) * rows


def calculate_limit(rows: int, page: int | None = None) -> int | None:
    """
    SQL 쿼리용 LIMIT 값 계산

    Args:
        rows: 페이지당 항목 수
        page: 페이지 번호 (선택적). page=0이고 rows=0인 경우 None 반환 (전체 데이터 조회)

    Returns:
        계산된 LIMIT 값. page=0이고 rows=0인 경우 None 반환

    Examples:
        >>> calculate_limit(10)
        10
        >>> calculate_limit(20)
        20
        >>> calculate_limit(0, 0)  # page=0이고 rows=0인 경우 전체 데이터 조회
        None
    """
    # page=0이고 rows=0인 경우는 전체 데이터 조회를 의미하므로 None 반환
    if page == 0 and rows == 0:
        return None
    return rows


def create_pagination_info(
    page: int | None, rows: int | None, total_count: int
) -> PaginationInfo:
    """
    페이지네이션 정보 생성

    페이지네이션에 필요한 모든 정보를 계산하여 반환합니다.
    항상 일관된 구조를 반환하며, 모든 필드를 포함합니다.

    Args:
        page: 페이지 번호 (1부터 시작). None이면 기본값 1 사용
        rows: 페이지당 항목 수. None이면 기본값 10 사용
        total_count: 전체 항목 수
        page=0이고 rows=0인 경우 전체 데이터 조회를 의미

    Returns:
        페이지네이션 정보를 담은 PaginationInfo 딕셔너리:
        - page: 현재 페이지 번호 (전체 조회 시 1)
        - total: 전체 항목 수
        - total_page: 전체 페이지 수 (전체 조회 시 1)
        - rows: 페이지당 항목 수 (전체 조회 시 실제 반환된 데이터 개수)

    Raises:
        Custom_Exception:
            - page나 rows가 유효하지 않은 경우 (단, page=0, rows=0은 허용)
            - total_count가 음수인 경우

    Examples:
        >>> create_pagination_info(1, 10, 95)
        {'page': 1, 'total': 95, 'total_page': 10, 'rows': 10}
        >>> create_pagination_info(2, 20, 50)
        {'page': 2, 'total': 50, 'total_page': 3, 'rows': 20}
        >>> create_pagination_info(None, None, 0)
        {'page': 1, 'total': 0, 'total_page': 0, 'rows': 10}
        >>> create_pagination_info(1, 10, 100)
        {'page': 1, 'total': 100, 'total_page': 10, 'rows': 10}
        >>> create_pagination_info(0, 0, 100)
        {'page': 1, 'total': 100, 'total_page': 1, 'rows': 100}
    """
    # total_count 검증
    if total_count < 0:
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            f"전체 항목 수는 0 이상이어야 합니다. (입력값: {total_count})",
        )

    # 페이지네이션 파라미터 검증 및 기본값 처리
    validated_page, validated_rows = validate_pagination_params(page, rows)

    # page=0이고 rows=0인 경우 전체 데이터 조회를 의미
    if validated_page == 0 and validated_rows == 0:
        return PaginationInfo(
            page=1,  # 전체 조회 시에도 page는 1로 표시
            total=total_count,
            total_page=1,  # 전체 데이터를 한 페이지로 간주
            rows=total_count,  # 실제 반환된 데이터 개수로 표시
        )

    # 전체 페이지 수 계산 (math.ceil 사용)
    total_page = math.ceil(total_count / validated_rows) if total_count > 0 else 0

    return PaginationInfo(
        page=validated_page,
        total=total_count,
        total_page=total_page,
        rows=validated_rows,
    )
