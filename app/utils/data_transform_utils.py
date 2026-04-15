"""
데이터 변환 유틸리티 함수들
"""

from app.utils.filter_utils.filter_param_utils import FIELD_MAPPINGS
from app.utils.types import ApiResponseDataType


def add_id_to_data_list(
    data_list: ApiResponseDataType, entity_type: str
) -> ApiResponseDataType:
    """데이터 리스트에 id 필드 일괄 추가

    FIELD_MAPPINGS를 사용하여 각 엔티티의 id 필드를 매핑하여 추가합니다.

    Args:
        data_list: 변환할 데이터 리스트
        entity_type: 엔티티 타입 ("member", "auth_group", "member_group" 등)

    Returns:
        id 필드가 추가된 데이터 리스트
    """
    if not data_list:
        return data_list

    # FIELD_MAPPINGS에서 해당 엔티티의 id 매핑 정보 가져오기
    entity_mappings = FIELD_MAPPINGS.get(entity_type, {})
    id_mapping = entity_mappings.get("id")

    if not id_mapping:
        # 매핑 정보가 없는 경우 그대로 반환
        return data_list

    # data_list가 리스트가 아닌 경우 그대로 반환
    if not isinstance(data_list, list):
        return data_list

    # 각 데이터 항목에 id 필드 추가
    for item in data_list:
        # 복합키 처리: 리스트/튜플인 경우 모든 필드 값을 "@"로 연결
        if isinstance(id_mapping, list):
            # 복합키의 모든 필드 값을 "@"로 연결
            id_values: list[str] = []
            for field in id_mapping:  # type: ignore
                value = item.get(field)
                if value is not None:
                    id_values.append(str(value))
                else:
                    id_values.append("")  # None인 경우 빈 문자열
            item["id"] = "@".join(id_values)
        else:
            item["id"] = item.get(id_mapping)

    return data_list
