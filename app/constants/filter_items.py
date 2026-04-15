from typing import Any

from sqlalchemy import asc, desc

# 정렬 매핑 변수
SORT_MAPPING: dict[str, Any] = {
    "DESC": desc,
    "ASC": asc,
    "DEFAULT": None,
}

AGGREGATE_FUNCTION_NAMES: set[str] = {
    # 기본 ANSI
    "count",
    "sum",
    "avg",
    "min",
    "max",
    "group_concat",
    # 문자열 / 배열
    "string_agg",
    "array_agg",
    # JSON
    "json_agg",
    "jsonb_agg",
    # 논리
    "bool_and",
    "bool_or",
    "every",
}

# 검색 데이터 최소 길이 변수
SEARCH_WORD_MIN_LENGTH: int = 1
# 검색 데이터 최대 개수 변수
SEARCH_WORD_MAX_ITEMS: int = 5
