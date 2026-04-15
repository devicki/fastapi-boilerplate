"""
업로드 데이터 캐시 관리 유틸리티 (Redis 기반)
"""

import json
import logging
import time
from typing import Any
from uuid import uuid4

from app.databases.redis import RedisClient

# Excel upload cache key prefix
EXCEL_UPLOAD_PREFIX = "excel_upload:"


class UploadCacheManager:
    """업로드된 엑셀 데이터의 임시 캐시 관리 (Redis 기반)"""

    _instance: "UploadCacheManager | None" = None
    _use_redis: bool
    _memory_cache: dict[str, dict[str, Any]]
    ttl_seconds: int

    def __new__(cls, ttl_seconds: int = 3600):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, ttl_seconds: int = 3600):
        if hasattr(self, "_initialized"):
            return

        self.ttl_seconds = ttl_seconds

        # Redis 연결 설정 및 테스트
        try:
            RedisClient.init_redis()
            # 초기화 확인
            if RedisClient.ping():
                logging.info("UploadCacheManager: Redis 연결 테스트 성공")
                self._use_redis = True
                self._memory_cache = {}
            else:
                raise RuntimeError("Redis 연결 실패")
        except Exception as e:
            # Redis 연결 실패 시 메모리 기반 폴백 (개발용)
            logging.warning(f"Redis 연결 실패, 메모리 기반 캐시로 폴백: {e}")
            self._use_redis = False
            self._memory_cache = {}

        self._initialized = True

    def store_upload_data(
        self,
        template_name: str,
        parsed_data: list[dict[str, Any]],
        validation_result: dict[str, Any],
        original_filename: str,
        saved_file_path: str | None = None,
    ) -> str:
        """
        업로드 데이터를 캐시에 저장하고 고유 ID 반환

        Args:
            template_name: 템플릿 이름
            parsed_data: 파싱된 데이터 리스트
            validation_result: 검증 결과
            original_filename: 원본 파일명
            saved_file_path: 디스크에 저장된 파일의 상대 경로 (고위험 취약점 엑셀 등)

        Returns:
            고유 업로드 ID
        """
        upload_id = str(uuid4())

        cache_data: dict[str, Any] = {
            "template_name": template_name,
            "parsed_data": parsed_data,
            "validation_result": validation_result,
            "original_filename": original_filename,
            "created_at": time.time(),
            "status": "pending",  # pending, imported, cancelled
            "import_result": None,
        }
        if saved_file_path is not None:
            cache_data["saved_file_path"] = saved_file_path

        if self._use_redis:
            # Redis에 JSON 형태로 저장
            key = f"{EXCEL_UPLOAD_PREFIX}{upload_id}"
            RedisClient.setex(key, self.ttl_seconds, json.dumps(cache_data))
        else:
            # 메모리 기반 폴백
            self._memory_cache[upload_id] = cache_data

        return upload_id

    def get_upload_data(self, upload_id: str) -> dict[str, Any] | None:
        """
        업로드 데이터 조회

        Args:
            upload_id: 업로드 ID

        Returns:
            캐시된 데이터 또는 None (만료되었거나 존재하지 않음)
        """
        if self._use_redis:
            key = f"{EXCEL_UPLOAD_PREFIX}{upload_id}"
            data_str = RedisClient.get(key)
            if data_str and isinstance(data_str, str):
                try:
                    return json.loads(data_str)
                except json.JSONDecodeError:
                    return None
            return None
        else:
            # 메모리 기반 폴백
            return self._memory_cache.get(upload_id)

    def update_import_status(
        self, upload_id: str, status: str, import_result: dict[str, Any] | None = None
    ) -> bool:
        """
        import 상태 업데이트

        Args:
            upload_id: 업로드 ID
            status: 새로운 상태 (imported, cancelled 등)
            import_result: import 결과 데이터

        Returns:
            성공 여부
        """
        # 현재 데이터 조회
        current_data = self.get_upload_data(upload_id)
        if not current_data:
            return False

        # 상태 업데이트
        current_data["status"] = status
        if import_result:
            current_data["import_result"] = import_result

        if self._use_redis:
            key = f"{EXCEL_UPLOAD_PREFIX}{upload_id}"
            # TTL을 현재 남은 시간으로 계산 (단순화를 위해 전체 TTL 재설정)
            RedisClient.setex(key, self.ttl_seconds, json.dumps(current_data))
        else:
            self._memory_cache[upload_id] = current_data

        return True

    def cancel_upload(self, upload_id: str) -> bool:
        """
        업로드 취소

        Args:
            upload_id: 업로드 ID

        Returns:
            성공 여부
        """
        return self.update_import_status(upload_id, "cancelled")

    def get_import_status(self, upload_id: str) -> dict[str, Any] | None:
        """
        업로드 상태 조회 (외부용)

        Args:
            upload_id: 업로드 ID

        Returns:
            상태 정보
        """
        data = self.get_upload_data(upload_id)
        if not data:
            return None

        return {
            "upload_id": upload_id,
            "template_name": data["template_name"],
            "original_filename": data["original_filename"],
            "status": data["status"],
            "created_at": data["created_at"],
            "is_valid": data["validation_result"]["is_valid"],
            "total_rows": data["validation_result"]["total_rows"],
            "error_count": data["validation_result"]["error_count"],
            "errors": data["validation_result"]["errors"],
            "import_result": data["import_result"],
            "preview_data": (
                data["parsed_data"][:5] if data["parsed_data"] else []
            ),  # 최대 5개 미리보기
        }

    def _cleanup_expired(self) -> int:
        """
        만료된 캐시 정리 (Redis에서는 TTL이 자동으로 처리되므로 메모리 폴백에서만 사용)
        """
        if not self._use_redis:
            # 메모리 기반에서는 수동 정리
            current_time = time.time()
            expired_keys: list[str] = []

            for upload_id, data in self._memory_cache.items():
                if current_time - data["created_at"] > self.ttl_seconds:
                    expired_keys.append(upload_id)

            for key in expired_keys:
                del self._memory_cache[key]

            return len(expired_keys)
        return 0  # Redis에서는 자동 정리

    def get_cache_stats(self) -> dict[str, Any]:
        """
        캐시 통계 정보

        Returns:
            통계 정보
        """
        if self._use_redis:
            try:
                # Redis에서 excel_upload:* 키들을 찾아서 통계 계산
                keys = RedisClient.keys(f"{EXCEL_UPLOAD_PREFIX}*")

                if not isinstance(keys, list):
                    keys = []

                total_count: int = len(keys)

                status_counts: dict[str, int] = {}
                for key in keys:
                    data_str = RedisClient.get(key)
                    if data_str and isinstance(data_str, str):
                        try:
                            data = json.loads(data_str)
                            status = data.get("status", "unknown")
                            status_counts[status] = status_counts.get(status, 0) + 1
                        except json.JSONDecodeError:
                            pass

                return {
                    "total_uploads": total_count,
                    "status_breakdown": status_counts,
                    "ttl_seconds": self.ttl_seconds,
                    "cache_type": "redis",
                }
            except Exception as e:
                return {
                    "error": f"Redis 통계 조회 실패: {str(e)}",
                    "cache_type": "redis",
                    "ttl_seconds": self.ttl_seconds,
                }
        else:
            # 메모리 기반
            self._cleanup_expired()

            total_count: int = len(self._memory_cache)
            status_counts: dict[str, int] = {}
            for data in self._memory_cache.values():
                status = data["status"]
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total_uploads": total_count,
                "status_breakdown": status_counts,
                "ttl_seconds": self.ttl_seconds,
                "cache_type": "memory",
            }
