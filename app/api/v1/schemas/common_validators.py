"""
공통 밸리데이션 함수들
"""

import re


def validate_email_field(v: str | None) -> str | None:
    """이메일 검증 함수"""
    if v == "" or v is None:
        return None

    # 기본적인 이메일 형식 검증
    if "@" not in v or "." not in v.split("@")[1]:
        raise ValueError("올바른 이메일 형식이 아닙니다")

    # 이메일 주소 분리
    local_part, domain_part = v.split("@", 1)

    # 로컬 파트와 도메인 파트 검증
    if not local_part or not domain_part:
        raise ValueError("올바른 이메일 형식이 아닙니다")

    # 로컬 파트가 점으로 시작하거나 끝나지 않아야 함
    if local_part.startswith(".") or local_part.endswith("."):
        raise ValueError("올바른 이메일 형식이 아닙니다")

    # 도메인 파트가 점으로 시작하거나 끝나지 않아야 함
    if domain_part.startswith(".") or domain_part.endswith("."):
        raise ValueError("올바른 이메일 형식이 아닙니다")

    # 연속된 점(.)이 있는지 검증
    if ".." in local_part or ".." in domain_part:
        raise ValueError("올바른 이메일 형식이 아닙니다")

    # 더 엄격한 검증을 위한 정규식
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, v):
        raise ValueError("올바른 이메일 형식이 아닙니다")

    return v
