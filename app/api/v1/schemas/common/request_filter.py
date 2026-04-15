from app.utils.filter_utils.filter_base_schema import (
    DateParam,
    SearchParam,
    SelectParam,
    SortParam,
)

__all__ = [
    "DateParam",
    "SearchParam",
    "SelectParam",
    "SortParam",
    "FilterParam",
]


##### 선택 필터 파람
class FilterParam(DateParam, SearchParam, SortParam, SelectParam):
    """기본 필터 파라미터 (DateParam 포함)"""

    pass


class SearchDateSortParam(DateParam, SortParam, SearchParam):
    pass


class SelectSearchParam(SelectParam, SearchParam):
    pass


class SelectSortSearchParam(SelectParam, SortParam, SearchParam):
    pass


class SortSearchParam(SortParam, SearchParam):
    pass
