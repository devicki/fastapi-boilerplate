from datetime import datetime, timedelta

from app.constants.filter_items import SEARCH_WORD_MAX_ITEMS, SEARCH_WORD_MIN_LENGTH
from app.utils.error_class import Custom_Exception, Error_Code


# 기간 데이터 레코드
class DateRecord:
    def __init__(
        self, data_field_name: str, start_date: str | None, end_date: str | None
    ):
        self.data_field_name = data_field_name
        self.start_date = None
        self.end_date = None

        # 시작날짜 , 종료 날짜  - __check_date_range함수에서 입력
        self.__validate_and_set_date_range(
            _start_date_obj=self.__check_date_format(start_date),
            _end_date_obj=self.__check_date_format(end_date),
        )

    def __check_date_format(self, date_string: str | None) -> datetime | None:
        """## 데이터 포멧 검사 함수

        `Args`:

            date_string (str): 입력 데이터 스트림
        `Raises`:

            Custom_Exception: VALIDATION_ERROR("유효한 데이터 포멧이 아닙니다. yyyy-mm-dd로 입력해야 합니다.")
        `Returns`:

            Optional[datetime]: 데이터 객체 또는 None 반환
        """
        try:
            if date_string:
                return datetime.strptime(date_string, "%Y-%m-%d")
            else:
                return None

        except Exception as e:
            raise Custom_Exception(
                Error_Code.VALIDATION_ERROR,
                "유효한 데이터 포멧이 아닙니다. yyyy-mm-dd로 입력해야 합니다.",
            ) from e

    def __validate_and_set_date_range(
        self, _start_date_obj: datetime | None, _end_date_obj: datetime | None
    ):
        """## 날짜 범위를 검증하고 설정하는 함수

        `Args`:

            _start_date_obj (datetime): 시작 날짜
            _end_date_obj (datetime): 종료 날짜
        `Raises`:

            Custom_Exception: VALIDATION_ERROR("시작날짜와 종료날짜 모두 설정되지 않았습니다." 또는 "시작날짜가 종료날짜보다 작거나 같아야 합니다.")
        """
        # 둘 다 None인 경우 에러
        if _start_date_obj is None and _end_date_obj is None:
            raise Custom_Exception(
                Error_Code.VALIDATION_ERROR,
                "시작날짜와 종료날짜 모두 설정되지 않았습니다. 시작날짜 또는 종료날짜 중 하나를 설정해야 합니다.",
            )

        # 시작날짜만 있는 경우
        if _start_date_obj is not None and _end_date_obj is None:
            self.start_date = _start_date_obj
            return

        # 종료날짜만 있는 경우
        if _start_date_obj is None and _end_date_obj is not None:
            self.end_date = _end_date_obj + timedelta(days=1)
            return

        # 둘 다 있는 경우: 날짜 범위 검증 후 설정
        assert (
            _start_date_obj is not None and _end_date_obj is not None
        ), "날짜 검증 로직 오류"

        if _start_date_obj > _end_date_obj:
            raise Custom_Exception(
                Error_Code.VALIDATION_ERROR,
                "시작날짜가 종료날짜보다 작거나 같아야 합니다.",
            )

        self.start_date = _start_date_obj
        self.end_date = _end_date_obj + timedelta(days=1)


# 정렬 데이터 레코드
class SortRecode:
    def __init__(self, data_field_name: str, sort_type: str):
        self.data_field_name = data_field_name
        self.sort_type = sort_type


# 검색 데이터 레코드
class SearchRecode:
    def __init__(self, data_field_name: str, searches: str):
        self.data_field_name = data_field_name
        self.word_len = SEARCH_WORD_MIN_LENGTH
        check_result = self.__check_search_keyword(word=searches)

        self.searches = check_result.get("data", [])
        self.search_type = check_result.get("logicalType", "")

    def __convert_list_keyword(self, word_list: list[str]) -> list[str]:
        """스트링 리스트 데이터에 좌우 공백 제거 후,2글자 이상씩인지 검사하고, 결과 데이터를 돌려준다.
        check_search_keyword()에서 호출하는 함수이다.
        """
        if len(word_list) > SEARCH_WORD_MAX_ITEMS:
            raise Custom_Exception(
                Error_Code.VALIDATION_ERROR,
                f"유효한 데이터 포멧이 아닙니다. 검색어는 최대 {SEARCH_WORD_MAX_ITEMS}개까지 입력할 수 있습니다.",
            )
        for i in range(len(word_list)):
            word_list[i] = word_list[i].strip()  # 좌우 공백 제거 후,
            self.__check_word_length(word=word_list[i])
            self.__check_percent_keyword(word=word_list[i])
        return word_list

    def __check_search_keyword(self, word: str):
        """## 검색어 구분자 분리 함수"""
        ret: dict[str, str | list[str]] = {
            "logicalType": "",  # 'AND', 'OR', ''
            "data": [],  # 검색어 리스트
        }

        if "|" in word and "+" in word:  # '|', '*' 혼용 에러!
            raise Custom_Exception(
                Error_Code.VALIDATION_ERROR,
                "유효한 데이터 포멧이 아닙니다. '|', '+' 혼용 하여 검색할 수 없습니다.",
            )

        if "|" in word:  # OR 조건
            data = word.split("|")
            ret["data"] = self.__convert_list_keyword(data)
            ret["logicalType"] = "OR"
        elif "+" in word:  # AND 조건
            data = word.split("+")
            ret["data"] = self.__convert_list_keyword(data)
            ret["logicalType"] = "AND"
        else:  # 단일 검색어
            word = word.strip()
            self.__check_word_length(word=word)
            self.__check_percent_keyword(word=word)
            ret["data"] = [word]

        return ret

    def __check_word_length(self, word: str):
        if len(word) < self.word_len:
            raise Custom_Exception(
                Error_Code.VALIDATION_ERROR,
                f"유효한 데이터 포멧이 아닙니다. 검색어는 {self.word_len}글자 이상 입력해야 합니다.",
            )

    def __check_percent_keyword(self, word: str):
        if "%" in word:
            raise Custom_Exception(
                Error_Code.VALIDATION_ERROR,
                "유효한 데이터 포멧이 아닙니다. 검색에 %는 사용할 수 없습니다.",
            )


# 선택 데이터 레코드
class SelectRecode:
    def __init__(self, data_field_name: str, select_value: str):
        self.data_field_name = data_field_name
        self.select_value_list: list[str] = self.__check_select_keyword(select_value)

    def __check_select_keyword(self, select_value: str) -> list[str]:
        """## 선택 키워드 검증 및 파싱 함수

        `Args`:
            select_value (str): 파이프(|)로 구분된 선택값 문자열

        `Raises`:
            Custom_Exception: VALIDATION_ERROR - 빈 값이 포함된 경우

        `Returns`:
            list[str]: 검증된 선택값 리스트
        """
        select_value_list: list[str] = []

        for value in select_value.split("|"):
            select_val = value.strip()
            if not select_val:
                raise Custom_Exception(
                    Error_Code.VALIDATION_ERROR,
                    "유효한 데이터 포멧이 아닙니다. 입력된 값이 비어있습니다.",
                )
            select_value_list.append(select_val)

        return select_value_list
