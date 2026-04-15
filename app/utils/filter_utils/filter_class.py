# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: © 2025 Coontec.,ltd
# SPDX-License-Identifier: Coontec-AEZIZ-v0.1
# AEZIZ v0.1 (Cyber Battle-field Management System)
# Copyright : © 2025 COONTEC Co.,Ltd. All rights reserved.
# Except for open sources, packages, and binary files where the copyright
# belongs to third-party, the copyrights of the remaining source codes,
# packages, and binary files are owned by Coontec.,ltd.
# ------------------------------------------------------------------------------
# 작성자 : 전윤호
# 수정일 : 25-02-20
# 설명 : 필터링 클래스 관리 파일
# 변경내용 :
# ------------------------------------------------------------------------------
import logging
from typing import Any

from sqlalchemy import (
    Column,
    FunctionElement,
    Label,
    WithinGroup,
    and_,
    cast,
    func,
    or_,
)
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.sqltypes import DateTime, Text

from app.constants.filter_items import AGGREGATE_FUNCTION_NAMES, SORT_MAPPING
from app.utils.error_class import Custom_Exception, Error_Code

# Note: FilterClass는 내부 모듈이므로 filter_base_schema에서 직접 import 허용
# 외부 API에서는 request_filter를 통해 import하세요
from app.utils.filter_utils.filter_base_schema import (
    DateParam,
    SearchParam,
    SelectParam,
    SortParam,
)
from app.utils.filter_utils.filter_data_recode import (
    DateRecord,
    SearchRecode,
    SelectRecode,
    SortRecode,
)


class FilterClass:
    def __init__(
        self,
        query: Query[Any],
        filter_param: DateParam | SearchParam | SortParam | SelectParam,
    ):
        self._query = query
        self._columns = self._query.statement.column_descriptions
        self._filter_param = filter_param
        self._filters: list[ColumnElement[bool]] = []
        self._select_filters: list[ColumnElement[bool]] = []
        self._order_bys: list[ColumnElement[Any]] = []
        self._search_filters: list[ColumnElement[bool]] = []
        # having 조건을 저장할 리스트 추가
        self._search_having_filters: list[ColumnElement[bool]] = []
        self._select_having_filters: list[ColumnElement[bool]] = []

    def _set_datetime(self, date_param: DateParam):
        """## 날자 필터링 추가 함수

        `Args`:

            date_param (DateParam): 날짜 객체
        """

        if not date_param._date_data_info_list:
            return self

        for _data_info in date_param._date_data_info_list:
            model_columns = self._get_col_obj(_data_info.data_field_name)

            self._check_type_is_datetime(model_columns)
            self._filters.append(model_columns.isnot(None))
            if _data_info.start_date and _data_info.end_date:
                self._filters.append(
                    model_columns.between(_data_info.start_date, _data_info.end_date)
                )
            elif _data_info.start_date:
                self._filters.append(model_columns >= _data_info.start_date)
            elif _data_info.end_date:
                self._filters.append(model_columns <= _data_info.end_date)
        self._query = self._query.filter(*self._filters)
        return self

    def _set_sort(self, sort_param: SortParam):
        """## 정렬 필터링 추가

        `Args`:

            sort_param (SortParam): 정렬 객체
        """
        if not sort_param._sort_data_info_list:
            return self

        for _data_info in sort_param._sort_data_info_list:
            sort_function = SORT_MAPPING.get(_data_info.sort_type)
            if sort_function is None:
                continue

            model_columns = self._check_col_type(
                self._get_col_obj(_data_info.data_field_name)
            )
            # 케이스에 따른 order 순서 정의
            # match _data_info.data_field_name:
            #     case "cveRisk":
            #         # model_columns = QueryConstantCase.get_query_case("cve_risk_order")
            #     case _:
            #         pass
            self._order_bys.append(sort_function(model_columns).nullslast())
        self._query = self._query.order_by(*self._order_bys)
        return self

    def _set_search(self, search_param: SearchParam):
        """## 여러 검색 조건 추가 (여러 필드 지원)
        각 SearchRecode 객체에 대해 검색 필터를 구성하고,
        모든 필터를 AND 조건으로 결합합니다.

        """
        if not search_param._search_data_info:
            return self

        for search_obj in search_param._search_data_info:
            model_columns = self._get_col_obj(search_obj.data_field_name)
            field_filters: list[ColumnElement[bool]] = []
            for search_word in search_obj.searches:
                temp = search_word.replace(" ", "%").lower()
                field_filters.append(
                    func.lower(cast(model_columns, Text)).like(f"%{temp}%")
                )  # text 타입으로 cast

            # SearchRecode 내부에서 logicalType은 OR 또는 AND로 처리됨
            logical_operator = or_ if search_obj.search_type == "OR" else and_
            if self._is_group_column(model_columns):
                self._search_having_filters.append(logical_operator(*field_filters))
            else:
                self._search_filters.append(logical_operator(*field_filters))
        # 여러 필드의 조건은 모두 만족 => AND 조건
        # 조건 자체를 return
        self._query = self._query.having(and_(*self._search_having_filters))
        self._query = self._query.filter(and_(*self._search_filters))
        return self

    def _set_select(self, select_param: SelectParam):
        """## 선택 필터링  추가

        `Args`:

            select_param (SelectParam): 선택 객체
        """
        if not select_param._select_data_info_list:
            return self

        for _data_info in select_param._select_data_info_list:
            model_columns = self._get_col_obj(_data_info.data_field_name)
            model_columns = self._check_col_type(model_columns)

            if self._is_group_column(model_columns):
                self._select_having_filters.append(
                    model_columns.in_(_data_info.select_value_list)
                )
            else:
                self._select_filters.append(
                    model_columns.in_(_data_info.select_value_list)
                )

        self._query = self._query.filter(*self._select_filters)
        self._query = self._query.having(*self._select_having_filters)
        return self

    def build(self):
        """## 필터링 시작

        `Returns`:

            _query: 필터링된 쿼리
        """

        if hasattr(self._filter_param, "dateParam") and isinstance(
            self._filter_param, DateParam
        ):
            self._set_datetime(self._filter_param)
        if hasattr(self._filter_param, "selectParam") and isinstance(
            self._filter_param, SelectParam
        ):
            self._set_select(self._filter_param)
        if hasattr(self._filter_param, "searchParam") and isinstance(
            self._filter_param, SearchParam
        ):
            self._set_search(self._filter_param)
        if hasattr(self._filter_param, "sortParam") and isinstance(
            self._filter_param, SortParam
        ):
            self._set_sort(self._filter_param)

        return self._query

    def remove_filter(
        self,
        removed_filters: dict[
            type[DateParam | SearchParam | SortParam | SelectParam], set[str]
        ],
    ):
        # 필터 타입별 내부 리스트 속성명 매핑
        filter_list_map: dict[
            type[DateParam | SearchParam | SortParam | SelectParam], str
        ] = {
            DateParam: "_date_data_info_list",
            SearchParam: "_search_data_info",
            SortParam: "_sort_data_info_list",
            SelectParam: "_select_data_info_list",
        }

        # # 각 필터 타입별로 필드명 제거
        for filter_type, field_name_list in removed_filters.items():
            list_attr = filter_list_map.get(filter_type, "")
            recode_data_list = getattr(self._filter_param, list_attr, [])
            if not recode_data_list:
                continue

            filtered_recode_data_list: list[
                DateRecord | SearchRecode | SelectRecode | SortRecode
            ] = []
            for record_data in recode_data_list:
                # data_field_name 값은 필수
                if not hasattr(record_data, "data_field_name"):
                    logging.warning(
                        f"data_field_name값이 없습니다 : {record_data.__dict__}"
                    )
                    continue

                if record_data.data_field_name not in field_name_list:
                    filtered_recode_data_list.append(record_data)
                else:
                    logging.info(
                        f"필터링에서 제거 ({filter_type.__name__}: {record_data.data_field_name})"
                    )
            setattr(self._filter_param, list_attr, filtered_recode_data_list)

        return self

    def _get_col_obj(self, col: str) -> ColumnElement[Any]:
        """## 컬럼 객체 획득 함수

        `Args`:

            col (_type_): 컬럼명
        `Raises`:

            Custom_Exception: NO_MAPPING_DB_KEY_EXCEPTION
        `Returns`:

            컬럼 객체: i["expr"]
        """
        for i in self._columns:
            # 컬럼이 모델 객체일경우 속성 가져옴
            if isinstance(i["type"], DeclarativeAttributeIntercept) and hasattr(
                i["expr"], col
            ):
                return getattr(i["expr"], col)

            if i["name"] == col:
                return i["expr"]  # type: ignore

        raise Custom_Exception(Error_Code.NO_MAPPING_DB_KEY_EXCEPTION)

    def _check_col_type(self, col_obj: ColumnElement[Any]) -> ColumnElement[Any]:
        """## 컬럼 타입 체크 하여 변환  함수

        `Args`:

            col_obj (_type_): 컬럼 오브젝트
        `Returns`:

            col_obj: 변환된 타입
        """

        # 라벨일경우 패스
        if isinstance(col_obj, Label):
            return col_obj

        if isinstance(col_obj, Column):
            if col_obj.type == Text:
                return func.to_char(col_obj)
            return col_obj

        return col_obj

    def _is_group_column(self, col_obj: ColumnElement[Any]) -> bool:
        """## 컬럼이 그룹 함수인지 확인하는 함수

        `Args`:

            col_obj (_type_): 컬럼 오브젝트
        `Returns`:

            bool: 그룹 함수 여부
        """
        # 그룹 함수 이름 리스트

        if isinstance(col_obj, Label):
            col_obj = col_obj.element
        if isinstance(col_obj, WithinGroup):
            col_obj = col_obj.element

        return (
            isinstance(col_obj, FunctionElement)
            and col_obj.name in AGGREGATE_FUNCTION_NAMES
        )

    def _check_type_is_datetime(self, col_obj: ColumnElement[Any]):
        """## 컬럼의 타입이 datetime이 아니면 에러 발생 함수

        `Args`:

            col_obj (_type_): 컬럼 오브젝트
        `Raises`:

            Custom_Exception: NO_DATETIME_COLUMN_EXCEPTION("날짜 형식의 컬럼이 아니어서 날짜 범위로 검색할 수 없습니다")
        """
        if isinstance(col_obj, Label):
            col_obj = col_obj.element

        check_property = getattr(col_obj, "property", None)

        if check_property is None:
            # 컬럼 값에 none이 있어도 확인 가능하도록 추가
            column_type = col_obj.type
        else:
            column_type = check_property.columns[0].type

        # 컬럼 타입이 datetime이 아니면 에러 발생
        if not isinstance(column_type, DateTime):
            raise Custom_Exception(Error_Code.NO_DATETIME_COLUMN_EXCEPTION)
