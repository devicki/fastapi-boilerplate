"""
JWT 토큰 생성 및 검증 유틸리티
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWTError

from app.databases.redis import RedisClient

# Token key prefixes
REFRESH_TOKEN_PREFIX = "refresh_token:"
ACCESS_TOKEN_BLACKLIST_PREFIX = "access_token_blacklist:"


class JWTManager:
    """JWT 토큰 관리 클래스"""

    _instance: "JWTManager | None" = None
    _use_redis: bool
    _memory_cache: dict[str, dict[str, Any]]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        # 환경변수에서 설정 로드
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY 환경변수가 설정되지 않았습니다.")

        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        # 토큰 유효기간 설정
        self.access_token_expire_minutes: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
        )
        self.refresh_token_expire_days: int = int(
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 14)
        )

        # RedisClient 초기화 시도
        try:
            RedisClient.init_redis()
            # 초기화 확인
            if RedisClient.ping():
                logging.info("JWTManager: Redis 연결 테스트 성공")
                self._use_redis = True
                self._memory_cache = {}
            else:
                raise RuntimeError("Redis 연결 실패")
        except Exception as e:
            # Redis 연결 실패 시 메모리 기반 폴백 (개발용)
            logging.warning(f"Redis 연결 실패, 메모리 기반 캐시로 폴백: {e}")
            self._use_redis = False
            self._memory_cache = {}  # 메모리 기반 저장소

        self._initialized = True

    def create_access_token(self, data: dict[str, Any]) -> str:
        """Access Token 생성"""
        to_encode = data.copy()

        # 토큰 만료 시간 설정

        expire = datetime.now(UTC) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "access"})

        # JWT 토큰 생성
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)  # type: ignore
        return encoded_jwt

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        """Refresh Token 생성"""
        to_encode = data.copy()

        # 토큰 만료 시간 설정
        expire = datetime.now(UTC) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "refresh"})

        # JWT 토큰 생성
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)  # type: ignore
        return encoded_jwt

    def verify_token(
        self, token: str, token_type: str = "access"
    ) -> dict[str, Any] | None:
        """토큰 검증"""
        try:
            # 토큰 디코딩 및 검증
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])  # type: ignore

            # 토큰 타입 확인
            if payload.get("type") != token_type:
                return None

            # 액세스 토큰의 경우 블랙리스트 확인
            if token_type == "access" and self.is_access_token_blacklisted(token):
                return None

            # 민감 정보 제외하고 필요한 정보만 반환
            user_data = {
                key: value
                for key, value in payload.items()
                if key not in ["exp", "iat", "type"]
            }

            return user_data

        except ExpiredSignatureError:
            # 토큰 만료
            return None
        except (PyJWTError, InvalidTokenError):
            # 토큰 위조 또는 기타 오류
            return None

    def store_refresh_token(self, user_id: str, refresh_token: str) -> bool:
        """Refresh Token을 저장 (Redis 또는 메모리)"""
        try:
            if self._use_redis:
                # RedisClient를 사용하여 저장 (키: user_id, 값: refresh_token, 만료시간: {refresh_token_expire_days}일)
                expire_seconds = self.refresh_token_expire_days * 24 * 60 * 60
                RedisClient.setex(
                    f"{REFRESH_TOKEN_PREFIX}{user_id}",
                    expire_seconds,
                    refresh_token,
                )
            else:
                # 메모리에 저장 (개발용)
                expire_time = datetime.now(UTC) + timedelta(
                    days=self.refresh_token_expire_days
                )
                self._memory_cache[f"{REFRESH_TOKEN_PREFIX}{user_id}"] = {
                    "token": refresh_token,
                    "expire_time": expire_time,
                }
            return True
        except Exception:
            return False

    def get_stored_refresh_token(self, user_id: str) -> str | None:
        """저장된 Refresh Token 조회"""
        try:
            if self._use_redis:
                # RedisClient를 사용하여 조회
                token = RedisClient.get(f"{REFRESH_TOKEN_PREFIX}{user_id}")
                return token
            else:
                # 메모리에서 조회 (개발용)
                data = self._memory_cache.get(f"{REFRESH_TOKEN_PREFIX}{user_id}")
                if data and data["expire_time"] > datetime.now(UTC):
                    return data["token"]
                elif data:
                    # 만료된 토큰 제거
                    del self._memory_cache[f"{REFRESH_TOKEN_PREFIX}{user_id}"]
                return None
        except Exception:
            return None

    def revoke_refresh_token(self, user_id: str) -> bool:
        """Refresh Token 폐기 (로그아웃 시 사용)"""
        try:
            if self._use_redis:
                # RedisClient를 사용하여 삭제
                RedisClient.delete(f"{REFRESH_TOKEN_PREFIX}{user_id}")
            else:
                # 메모리에서 제거 (개발용)
                key = f"{REFRESH_TOKEN_PREFIX}{user_id}"
                if key in self._memory_cache:
                    del self._memory_cache[key]
            return True
        except Exception:
            return False

    def rotate_refresh_token(
        self, user_id: str, old_token: str, new_token: str
    ) -> bool:
        """Refresh Token 회전 (1회 사용 후 새로운 토큰 발급)"""
        try:
            # 저장된 토큰과 비교
            stored_token = self.get_stored_refresh_token(user_id)
            if stored_token != old_token:
                return False

            # 새로운 토큰으로 교체
            return self.store_refresh_token(user_id, new_token)
        except Exception:
            return False

    def add_access_token_to_blacklist(self, access_token: str) -> bool:
        """Access Token을 블랙리스트에 추가 (로그아웃 시 사용)"""
        try:
            # 토큰에서 만료 시간 추출 (검증하지 않고 디코드만)
            payload = jwt.decode(access_token, options={"verify_signature": False})  # type: ignore
            exp_timestamp = payload.get("exp")

            if not exp_timestamp:
                return False

            # 현재 시간부터 만료까지 남은 시간 계산
            current_time = datetime.now(UTC).timestamp()
            ttl_seconds = max(0, int(exp_timestamp - current_time))

            if ttl_seconds <= 0:
                # 이미 만료된 토큰
                return True

            if self._use_redis:
                # Redis에 블랙리스트 추가 (TTL 적용)
                RedisClient.setex(
                    f"{ACCESS_TOKEN_BLACKLIST_PREFIX}{access_token}",
                    ttl_seconds,
                    "blacklisted",
                )
            else:
                # 메모리에 블랙리스트 추가
                expire_time = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
                self._memory_cache[f"{ACCESS_TOKEN_BLACKLIST_PREFIX}{access_token}"] = {
                    "status": "blacklisted",
                    "expire_time": expire_time,
                }

            return True
        except Exception:
            return False

    def is_access_token_blacklisted(self, access_token: str) -> bool:
        """Access Token이 블랙리스트에 있는지 확인"""
        try:
            if self._use_redis:
                # Redis에서 확인
                result = RedisClient.get(
                    f"{ACCESS_TOKEN_BLACKLIST_PREFIX}{access_token}"
                )
                return result is not None
            else:
                # 메모리에서 확인
                key = f"{ACCESS_TOKEN_BLACKLIST_PREFIX}{access_token}"
                data = self._memory_cache.get(key)

                if data:
                    if data["expire_time"] > datetime.now(UTC):
                        return True
                    else:
                        # 만료된 블랙리스트 항목 제거
                        del self._memory_cache[key]
                        return False
                return False
        except Exception:
            return False


def create_token_pair(user_data: dict[str, Any]) -> tuple[str, str]:
    """Access Token과 Refresh Token 쌍 생성"""
    jwt_manager = JWTManager()
    access_token = jwt_manager.create_access_token(user_data)
    refresh_token = jwt_manager.create_refresh_token(user_data)

    # Refresh Token을 Redis에 저장
    user_id: str | list[str] | None = user_data.get("sub")
    if user_id and isinstance(user_id, str):
        jwt_manager.store_refresh_token(user_id, refresh_token)

    return access_token, refresh_token


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Access Token 검증"""
    jwt_manager = JWTManager()

    return jwt_manager.verify_token(token, "access")


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """Refresh Token 검증"""
    jwt_manager = JWTManager()

    return jwt_manager.verify_token(token, "refresh")


def refresh_access_token(
    refresh_token: str, current_access_token: str | None = None
) -> tuple[str, str] | None:
    """Refresh Token으로 새로운 Access Token 발급 (토큰 회전 적용)"""
    jwt_manager = JWTManager()

    # Refresh Token 검증
    user_data = verify_refresh_token(refresh_token)
    if not user_data:
        return None

    user_id = user_data.get("sub")
    if not user_id:
        return None

    # Redis에 저장된 토큰과 비교
    stored_token = jwt_manager.get_stored_refresh_token(user_id)
    if stored_token != refresh_token:
        return None

    # 새로운 토큰 쌍 생성
    new_access_token, new_refresh_token = create_token_pair(user_data)

    # 이전 Access Token을 블랙리스트에 추가 (보안 강화)
    if current_access_token:
        jwt_manager.add_access_token_to_blacklist(current_access_token)

    # Refresh Token 회전 (기존 토큰 폐기, 새 토큰 저장)
    jwt_manager.rotate_refresh_token(user_id, refresh_token, new_refresh_token)

    return new_access_token, new_refresh_token


def logout_user(user_id: str, access_token: str | None = None) -> tuple[bool, Any]:
    """사용자 로그아웃 (Refresh Token 폐기 + Access Token 블랙리스트)"""
    jwt_manager = JWTManager()

    # 토큰에서 사용자 데이터 추출
    user_data = {}
    payload = (
        jwt.decode(access_token, options={"verify_signature": False})  # type: ignore
        if access_token
        else None
    )
    if payload:
        # 민감 정보 제외하고 필요한 정보만 반환
        user_data = {
            key: value
            for key, value in payload.items()
            if key not in ["exp", "iat", "type"]
        }

    # Refresh Token 폐기
    refresh_success = jwt_manager.revoke_refresh_token(user_id)

    # Access Token 블랙리스트 추가 (제공된 경우)
    access_success = True
    if access_token:
        access_success = jwt_manager.add_access_token_to_blacklist(access_token)

    return refresh_success and access_success, user_data


def get_access_token_expire_seconds() -> int:
    """Access Token 만료 시간(초) 반환"""
    jwt_manager = JWTManager()

    return jwt_manager.access_token_expire_minutes * 60


def get_new_access_token_by_user_data_update(
    user_data: dict[str, Any],
) -> str:
    """사용자 데이터 변경 시 새로운 Access Token 발급"""
    jwt_manager = JWTManager()

    new_access_token = jwt_manager.create_access_token(user_data)
    return new_access_token


def get_refresh_token_expire_seconds() -> int:
    """Refresh Token 만료 시간(초) 반환"""
    jwt_manager = JWTManager()

    return jwt_manager.refresh_token_expire_days * 24 * 60 * 60
