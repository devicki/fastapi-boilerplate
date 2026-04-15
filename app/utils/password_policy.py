"""
비밀번호 정책 상수, 조회, 검증 로직.
DB에서 정책을 조회하려면 get_password_policy()를 오버라이드하세요.
"""

import re
from typing import Any

from app.utils.error_class import Custom_Exception, Error_Code

# 기본 비밀번호 정책
DEFAULT_PASSWORD_POLICY: dict[str, Any] = {
    # 복잡도 (Complexity)
    "min_length": 8,
    "max_length": 20,
    "require_digit": True,
    "require_lowercase": True,
    "require_uppercase": False,
    "require_special": True,
    "max_consecutive_same": 3,  # 동일/연속 문자 N회 이상 금지
    "disallow_user_id": True,  # 자신의 아이디 포함 금지
    # 변경 주기 (Expiration)
    "expiration_days": 90,  # 0이면 만료 없음
}


def get_password_policy() -> dict[str, Any]:
    """
    비밀번호 정책을 반환합니다.
    DB 기반 정책이 필요하면 이 함수를 오버라이드하세요.
    """
    return dict(DEFAULT_PASSWORD_POLICY)


def validate_password(
    password: str,
    user_id: str,
    policy: dict[str, Any] | None = None,
) -> None:
    """
    비밀번호가 정책에 맞는지 검사합니다.
    policy가 None이면 DEFAULT_PASSWORD_POLICY 사용.
    위반 시 Custom_Exception(VALIDATION_EXCEPTION) 발생.
    """
    if policy is None:
        policy = dict(DEFAULT_PASSWORD_POLICY)

    min_len = int(policy.get("min_length", DEFAULT_PASSWORD_POLICY["min_length"]))
    max_len = int(policy.get("max_length", DEFAULT_PASSWORD_POLICY["max_length"]))
    require_digit = bool(
        policy.get("require_digit", DEFAULT_PASSWORD_POLICY["require_digit"])
    )
    require_lowercase = bool(
        policy.get("require_lowercase", DEFAULT_PASSWORD_POLICY["require_lowercase"])
    )
    require_uppercase = bool(
        policy.get("require_uppercase", DEFAULT_PASSWORD_POLICY["require_uppercase"])
    )
    require_special = bool(
        policy.get("require_special", DEFAULT_PASSWORD_POLICY["require_special"])
    )
    max_consecutive = int(
        policy.get(
            "max_consecutive_same", DEFAULT_PASSWORD_POLICY["max_consecutive_same"]
        )
    )
    disallow_user_id = bool(
        policy.get("disallow_user_id", DEFAULT_PASSWORD_POLICY["disallow_user_id"])
    )

    if len(password) < min_len:
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            f"비밀번호는 최소 {min_len}자 이상이어야 합니다.",
        )
    if len(password) > max_len:
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            f"비밀번호는 최대 {max_len}자 이하여야 합니다.",
        )
    if require_digit and not re.search(r"[0-9]", password):
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            "비밀번호에 숫자를 포함해야 합니다.",
        )
    if require_lowercase and not re.search(r"[a-z]", password):
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            "비밀번호에 영문 소문자를 포함해야 합니다.",
        )
    if require_uppercase and not re.search(r"[A-Z]", password):
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            "비밀번호에 영문 대문자를 포함해야 합니다.",
        )
    if require_special and not re.search(
        r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password
    ):
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            "비밀번호에 특수문자를 포함해야 합니다.",
        )

    # 동일/연속 문자 max_consecutive 회 이상 금지
    if max_consecutive >= 1 and len(password) >= max_consecutive:
        for i in range(len(password) - max_consecutive + 1):
            window = password[i : i + max_consecutive]
            if len(set(window)) == 1:  # 동일 문자 연속
                raise Custom_Exception(
                    Error_Code.VALIDATION_EXCEPTION,
                    f"동일한 문자를 {max_consecutive}회 이상 연속 사용할 수 없습니다.",
                )
            # # 연속된 문자/숫자 (예: abc, 123)
            # if window.isalpha() and len(window) == max_consecutive:
            #     ords = [ord(c) for c in window]
            #     if all(ords[j] + 1 == ords[j + 1] for j in range(len(ords) - 1)):
            #         raise Custom_Exception(
            #             Error_Code.VALIDATION_EXCEPTION,
            #             f"연속된 문자를 {max_consecutive}회 이상 사용할 수 없습니다.",
            #         )
            # if window.isdigit() and len(window) == max_consecutive:
            #     ords = [ord(c) for c in window]
            #     if all(ords[j] + 1 == ords[j + 1] for j in range(len(ords) - 1)):
            #         raise Custom_Exception(
            #             Error_Code.VALIDATION_EXCEPTION,
            #             f"연속된 숫자를 {max_consecutive}회 이상 사용할 수 없습니다.",
            #         )

    if disallow_user_id and user_id and user_id.lower() in password.lower():
        raise Custom_Exception(
            Error_Code.VALIDATION_EXCEPTION,
            "비밀번호에 사용자 ID를 포함할 수 없습니다.",
        )


def is_password_change_required(
    pwd_changed_date: Any,
    policy: dict[str, Any],
) -> bool:
    """
    비밀번호 변경일과 정책(expiration_days)을 기준으로 변경 필요 여부 판단.
    pwd_changed_date가 None이면 True.
    expiration_days가 0이면 만료 없음 → False.
    """
    if pwd_changed_date is None:
        return True
    expiration_days = int(
        policy.get("expiration_days", DEFAULT_PASSWORD_POLICY["expiration_days"])
    )
    if expiration_days <= 0:
        return False
    from datetime import date, datetime

    today = date.today()
    if isinstance(pwd_changed_date, datetime):
        changed_date = pwd_changed_date.date()
    else:
        changed_date = pwd_changed_date
    delta_days = (today - changed_date).days
    return delta_days >= expiration_days
