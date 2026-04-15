"""
필터 파라미터 전처리 유틸리티
"""

from app.api.v1.schemas.common.request_filter import FilterParam

# 엔티티별 필드 매핑 정의
# 새 엔티티를 추가할 때 여기에 매핑을 등록하세요.
FIELD_MAPPINGS: dict[str, dict[str, str | list[str]]] = {
    "users": {
        "id": "id",
    },
    # 복합키 예시
    # "sample": {
    #     "id": ["sample_id", "sample_sub_id"],
    # },
}


def map_filter_fields(filter_param: FilterParam, entity_type: str) -> FilterParam:
    """필터 파라미터의 필드명을 실제 데이터베이스 필드명으로 매핑

    Args:
        filter_param: 필터 파라미터 객체
        entity_type: 엔티티 타입 ("member", "auth_group", "member_group" 등)

    Returns:
        필드명이 매핑된 FilterParam 객체
    """
    if not filter_param:
        return filter_param

    mapping = FIELD_MAPPINGS.get(entity_type, {})
    if not mapping:
        return filter_param

    # 정렬 필드 매핑
    if hasattr(filter_param, "_sort_data_info_list"):
        for sort_record in filter_param._sort_data_info_list:
            if sort_record.data_field_name in mapping:
                mapped_value = mapping[sort_record.data_field_name]
                # 복합키 처리: 리스트/튜플인 경우 첫 번째 필드 사용
                if isinstance(mapped_value, list):
                    sort_record.data_field_name = mapped_value[0]
                else:
                    sort_record.data_field_name = mapped_value

    # 검색 필드 매핑 (필요한 경우)
    if hasattr(filter_param, "_search_data_info"):
        for search_record in filter_param._search_data_info:
            if search_record.data_field_name in mapping:
                mapped_value = mapping[search_record.data_field_name]
                # 복합키 처리: 리스트/튜플인 경우 첫 번째 필드 사용
                if isinstance(mapped_value, list):
                    search_record.data_field_name = mapped_value[0]
                else:
                    search_record.data_field_name = mapped_value

    # 선택 필드 매핑 (필요한 경우)
    if hasattr(filter_param, "_select_data_info_list"):
        for select_record in filter_param._select_data_info_list:
            if select_record.data_field_name in mapping:
                mapped_value = mapping[select_record.data_field_name]
                # 복합키 처리: 리스트/튜플인 경우 첫 번째 필드 사용
                if isinstance(mapped_value, list):
                    select_record.data_field_name = mapped_value[0]
                else:
                    select_record.data_field_name = mapped_value

    return filter_param
