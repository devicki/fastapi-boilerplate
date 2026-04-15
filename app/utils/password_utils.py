"""
비밀번호 해시 유틸리티 (Argon2)
"""

import os

import argon2


class PasswordHasher:
    """비밀번호 해시 클래스 (Argon2 사용)"""

    def __init__(self):
        """Argon2 해시 설정"""
        # 기본 설정으로 Argon2id 사용 (메모리 하드 함수)
        self.hasher = argon2.PasswordHasher(
            time_cost=2,  # 시간 비용 (반복 횟수)
            memory_cost=65536,  # 메모리 비용 (64MB)
            parallelism=1,  # 병렬 처리 수
            hash_len=32,  # 해시 길이
            type=argon2.Type.ID,  # Argon2id 사용
        )

    def hash_password(self, password: str) -> str:
        """비밀번호 해시 생성

        Args:
            password: 평문 비밀번호

        Returns:
            해시된 비밀번호 (PHC 형식 문자열)
        """
        if not password:
            raise ValueError("비밀번호는 빈 문자열일 수 없습니다.")

        return self.hasher.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """비밀번호 검증

        Args:
            password: 평문 비밀번호
            hashed_password: 해시된 비밀번호 (PHC 형식)

        Returns:
            일치 여부
        """
        if not password or not hashed_password:
            return False

        try:
            self.hasher.verify(hashed_password, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
        except Exception:
            return False


# 전역 인스턴스
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """비밀번호 해시 생성 (편의 함수)"""
    return password_hasher.hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """비밀번호 검증 (편의 함수)"""
    return password_hasher.verify_password(password, hashed_password)


def get_default_password_policy() -> tuple[str, str | None]:
    """환경변수에서 초기 비밀번호 정책을 가져옵니다.

    Returns:
        (정책 타입, 고정 비밀번호 값)
        정책 타입: "user_id" 또는 "fixed_value"
    """
    policy = os.getenv("DEFAULT_PASSWORD_POLICY", "user_id")
    fixed_value = os.getenv("DEFAULT_PASSWORD_VALUE")

    if policy.lower() not in ["user_id", "fixed_value"]:
        policy = "user_id"  # 기본값

    return policy, fixed_value


def generate_initial_password(user_id: str) -> str:
    """사용자의 초기 비밀번호를 생성합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        초기 비밀번호 (평문)
    """
    policy, fixed_value = get_default_password_policy()

    if policy == "fixed_value" and fixed_value:
        return fixed_value
    else:
        # 기본 정책: 사용자 ID를 비밀번호로 사용
        return user_id
