import logging
import os
from contextlib import contextmanager, suppress
from typing import Any, cast

import redis
from dotenv import load_dotenv

# .env 파일에서 환경변수를 읽어오기
load_dotenv()
load_dotenv(".env.local", override=True)  # .env.local이 있으면 덮어쓰기


class RedisClient:
    _redis_instance: redis.StrictRedis | None = (
        None  # Redis 클라이언트 인스턴스 (싱글톤)
    )

    @classmethod
    def _ensure_initialized(cls) -> redis.StrictRedis:
        """Redis 인스턴스가 초기화되었는지 확인하고 반환"""
        if cls._redis_instance is None:
            raise RuntimeError(
                "Redis client is not initialized. Call init_redis() first."
            )
        return cls._redis_instance

    @classmethod
    def init_redis(cls):
        """
        Redis 클라이언트 초기화 및 설정 (동기 방식)
        """
        if cls._redis_instance is None:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_password = os.getenv("REDIS_PASSWORD")
            # 빈 문자열인 경우 None으로 처리 (비밀번호가 설정되지 않은 경우)
            if redis_password == "":
                redis_password = None

            cls._redis_instance = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
            )
            logging.info("Redis client successfully initialized")

    @classmethod
    def get_instance(cls):
        """
        싱글톤 인스턴스 반환
        """
        if cls._redis_instance is None:
            raise RuntimeError("Redis client is not initialized")
        return cls

    @classmethod
    def set(cls, key: str, value: str, lock_timeout: int = 10) -> None:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"  # 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            redis_client.set(key, value)
            # logging.info(f"Set key={key}, value={value} with lock {lock_name}")

    @classmethod
    def get(cls, key: str) -> str | None:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"  # 고유한 락 이름 설정
        with redis_client.lock(lock_name):
            value = redis_client.get(key)
            # logging.info(f"Get key={key}, value={value} with lock {lock_name}")
            return cast(str | None, value)

    @classmethod
    def setex(cls, key: str, ttl: int, value: str, lock_timeout: int = 10) -> None:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"  # 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            redis_client.setex(key, ttl, value)
            # logging.info(f"Setex key={key}, value={value}, ttl={ttl} with lock {lock_name}")

    @classmethod
    def delete(cls, key: str, lock_timeout: int = 10) -> None:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"  # 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            redis_client.delete(key)
            # logging.info(f"Deleted key={key} with lock {lock_name}")

    @classmethod
    def keys(cls, pattern: str = "*", lock_timeout: int = 10) -> list[str]:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_pattern_{pattern}"  # 패턴별로 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            keys_list = redis_client.keys(pattern)  # type: ignore[assignment]
            # logging.info(f"Keys for pattern={pattern}: {keys_list} with lock {lock_name}")
            return cast(list[str], keys_list)

    @classmethod
    def expire(cls, key: str, ttl: int, lock_timeout: int = 10) -> bool:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"  # 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            result = redis_client.expire(key, ttl)
            # if result:
            #     logging.info(f"Expire set for key={key} with ttl={ttl} seconds with lock {lock_name}")
            # else:
            #     logging.warning(f"Failed to set expire for key={key} with lock {lock_name}")
            return cast(bool, result)

    @classmethod
    def sadd(cls, key: str, *members: str, lock_timeout: int = 10) -> int:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"  # 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            added_count = redis_client.sadd(key, *members)
            # logging.info(f"SADD key={key}, members={members} - {added_count} new members added with lock {lock_name}")
            return cast(int, added_count)

    @classmethod
    def scan(
        cls, cursor: int = 0, match: str = "*", count: int = 10, lock_timeout: int = 10
    ) -> tuple[int, list[str]]:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_scan_{match}"  # SCAN 명령어에 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            scan_result = redis_client.scan(cursor=cursor, match=match, count=count)  # type: ignore[assignment]
            # scan_result는 튜플이므로 타입 캐스팅
            if isinstance(scan_result, tuple) and len(scan_result) == 2:
                next_cursor: Any
                keys: Any
                next_cursor, keys = scan_result  # type: ignore[assignment]
                return cast(int, next_cursor), cast(list[str], keys)
            else:
                # 타입 체커를 위한 폴백
                return (0, [])

    @classmethod
    def getbit(cls, key: str, offset: int, lock_timeout: int = 10) -> int:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}_bit_{offset}"  # GETBIT 명령어에 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            bit_value = redis_client.getbit(key, offset)
            # logging.info(f"GETBIT key={key}, offset={offset} - bit_value={bit_value} with lock {lock_name}")
            return cast(int, bit_value)

    @classmethod
    def setbit(cls, key: str, offset: int, value: int, lock_timeout: int = 10) -> int:
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}_bit_{offset}"  # SETBIT 명령어에 고유한 락 이름 설정
        with redis_client.lock(lock_name, timeout=lock_timeout):
            prev_bit_value = redis_client.setbit(key, offset, value)
            # logging.info(f"SETBIT key={key}, offset={offset}, value={value} - prev_bit_value={prev_bit_value} with lock {lock_name}")
            return cast(int, prev_bit_value)

    @classmethod
    def exists(cls, *keys: str, lock_timeout: int = 10) -> int:
        redis_client = cls._ensure_initialized()
        lock_name = (
            f"lock_exists_{'_'.join(keys)}"  # EXISTS 명령어에 고유한 락 이름 설정
        )
        with redis_client.lock(lock_name, timeout=lock_timeout):
            count = redis_client.exists(*keys)
            # logging.info(f"EXISTS keys={keys} - count={count} keys exist with lock {lock_name}")
            return cast(int, count)

    @classmethod
    def lrange(
        cls, key: str, start: int, end: int, lock_timeout: int = 10
    ) -> list[str]:
        """리스트 범위 조회"""
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"
        with redis_client.lock(lock_name, timeout=lock_timeout):
            result = redis_client.lrange(key, start, end)  # type: ignore[assignment]
            return cast(list[str], result)

    @classmethod
    def rpush(cls, key: str, *values: str, lock_timeout: int = 10) -> int:
        """리스트 오른쪽에 추가"""
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"
        with redis_client.lock(lock_name, timeout=lock_timeout):
            result = redis_client.rpush(key, *values)
            return cast(int, result)

    @classmethod
    def lpush(cls, key: str, *values: str, lock_timeout: int = 10) -> int:
        """리스트 왼쪽에 추가"""
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_{key}"
        with redis_client.lock(lock_name, timeout=lock_timeout):
            result = redis_client.lpush(key, *values)
            return cast(int, result)

    @classmethod
    def publish(cls, channel: str, message: str, lock_timeout: int = 10) -> int:
        """채널에 메시지 발행"""
        redis_client = cls._ensure_initialized()
        lock_name = f"lock_pub_{channel}"
        with redis_client.lock(lock_name, timeout=lock_timeout):
            result = redis_client.publish(channel, message)  # type: ignore[assignment]
            return cast(int, result)

    @classmethod
    @contextmanager
    def multi_key_lock(cls, *keys: str, lock_timeout: int = 30):
        """
        여러 키에 대한 통합 lock 컨텍스트 매니저
        모든 키를 순차적으로 lock하여 데드락 방지

        Args:
            *keys: lock할 Redis 키들
            lock_timeout: lock 획득 대기 시간 (초)

        Yields:
            Redis 인스턴스
        """
        redis_client = cls._ensure_initialized()
        locks: list[Any] = []
        try:
            # 키를 정렬하여 데드락 방지
            sorted_keys = sorted(keys)
            for key in sorted_keys:
                lock_name = f"lock_{key}"
                lock = redis_client.lock(lock_name, timeout=lock_timeout)
                lock.acquire()
                locks.append(lock)
            yield redis_client
        finally:
            # 역순으로 해제
            for lock in reversed(locks):
                with suppress(Exception):
                    lock.release()

    @classmethod
    def close(cls):
        if cls._redis_instance:
            cls._redis_instance.close()
            logging.info("Redis client closed")

    @classmethod
    def ping(cls) -> bool:
        """Redis 서버에 ping 보내기"""
        redis_client = cls._ensure_initialized()
        try:
            response = redis_client.ping()  # type: ignore
            return response is True
        except Exception as e:
            logging.error(f"Redis ping failed: {e}")
            return False
