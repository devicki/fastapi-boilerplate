from pydantic import BaseModel, Field, model_validator

from app.constants.filter_items import SORT_MAPPING
from app.utils.error_class import Custom_Exception, Error_Code
from app.utils.filter_utils.filter_data_recode import (
    DateRecord,
    SearchRecode,
    SelectRecode,
    SortRecode,
)


class DateParam(BaseModel):
    """## 기간 스키마 클래스

    `Args`:

        dateParam (str): 입력 받는 파라미터
        _date_data_info_list (list(dict)): 코드에서 사용할 변수

    `Return`:

        _date_data_info_list =
        [
            {'data_field_name': 'created_at',
            'start_date': datetime.datetime(2025, 2, 24, 0, 0),
            'end_date': datetime.datetime(2025, 2, 25, 0, 0)}
        ]

    """

    dateParam: str | None = Field(None, examples=["created_at:2025-02-24+2025-02-24"])
    _date_data_info_list: list[DateRecord] = []

    @model_validator(mode="after")
    def check_dates(self):
        if not self.dateParam:
            return self
        param_list = self.dateParam.split(",")
        for date_param in param_list:
            date_fields = date_param.split(":")
            if len(date_fields) != 2:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. (필드명:yyyy-mm-dd+yyyy-mm-dd)로 입력해야 합니다",
                )
            data_field_name = date_fields[0].strip()

            if not data_field_name:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. 필드명은 필수로 입력해야 합니다",
                )
            date_fields_value = date_fields[1].split("+")
            if len(date_fields_value) != 2:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. (필드명:yyyy-mm-dd+yyyy-mm-dd)로 입력해야 합니다",
                )

            start_date = date_fields_value[0].strip() if date_fields_value[0] else None
            end_date = date_fields_value[1].strip() if date_fields_value[1] else None

            self._date_data_info_list.append(
                DateRecord(
                    data_field_name=data_field_name,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        return self


class SortParam(BaseModel):
    """## 정렬 스키마 클래스

    `Args`:

        sortParam (str): 입력 받는 파라미터
        _sort_data_info_list (list(dict)): 코드에서 사용할 변수

    `Return`:

        _sort_data_info_list =
        [
            {'data_field_name': 'mdfcDttm',
            'sort_type': "DESC"}
        ]
    """

    sortParam: str | None = Field(None, examples=["mdfcDttm:DESC"])
    _sort_data_info_list: list[SortRecode] = []

    @model_validator(mode="after")
    def check_sort(self):
        if not self.sortParam:
            return self
        param_list = self.sortParam.split(",")
        for sort_param in param_list:
            sort_fields = sort_param.split(":")
            if len(sort_fields) != 2:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. (필드명:DESC)로 입력해야 합니다",
                )
            data_field_name = sort_fields[0].strip()
            sort_type = sort_fields[1].strip().upper()

            if sort_type not in SORT_MAPPING:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. (DEFAULT,ASC,DESC)로 입력해야 합니다",
                )
            if not data_field_name:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. 필드명은 필수로 입력해야 합니다",
                )
            self._sort_data_info_list.append(
                SortRecode(data_field_name=data_field_name, sort_type=sort_type)
            )
        return self


class SearchParam(BaseModel):
    """## 검색 스키마 클래스

    `Args`:

        searchParam (str): 입력 받는 파라미터
        _search_data_info (list(dict)): 코드에서 사용할 변수

    `Return`:

        _search_data_info = SearchRecode 클래스
    """

    searchParam: str | None = Field(None, examples=["mdfcId:user_0001"])

    _search_data_info: list[SearchRecode] = []

    @model_validator(mode="after")
    def check_search(self):
        if not self.searchParam:
            return self

        conditions = self.searchParam.split(",")
        for cond in conditions:
            # "필드명:검색어"
            parts = cond.split(":", 1)  # 첫 번째 ':' 기준으로 분리
            if len(parts) != 2:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. (필드명:검색어)로 입력해야 합니다",
                )
            data_field_name = parts[0].strip()
            searches = parts[1].strip()

            if not data_field_name:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. 필드명은 필수로 입력해야 합니다.",
                )
            if not searches:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. 검색어는 필수로 입력해야 합니다.",
                )

            search_recode = SearchRecode(
                data_field_name=data_field_name, searches=searches
            )

            self._search_data_info.append(search_recode)
        return self


class SelectParam(BaseModel):
    """## 선택 스키마 클래스

    `Args`:

        selectParam (str): 입력 받는 파라미터
        _select_data_info_list (list(dict)): 코드에서 사용할 변수

    `Return`:

        _search_data_info = [SelectRecode] 클래스
    """

    selectParam: str | None = Field(None, examples=["mdcd:s|A"])
    _select_data_info_list: list[SelectRecode] = []

    @model_validator(mode="after")
    def check_select(self):
        if not self.selectParam:
            return self
        param_list = self.selectParam.split(",")

        for select_param in param_list:
            select_fields = select_param.split(":", 1)
            if len(select_fields) != 2:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. (필드명:선택값)로 입력해야 합니다",
                )
            data_field_name = select_fields[0].strip()
            select_value = select_fields[1].strip()
            if not data_field_name:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. 필드명은 필수로 입력해야 합니다",
                )
            if not select_value:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. 선택값은 필수로 입력해야 합니다",
                )
            self._select_data_info_list.append(
                SelectRecode(
                    data_field_name=data_field_name,
                    select_value=select_value,
                )
            )
        return self
