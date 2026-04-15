"""
날짜/시간 공통 유틸
"""

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "UTC"))


def get_today() -> date:
    """앱 타임존 기준 현재 날짜 반환. 비즈니스 날짜 기준용."""
    return datetime.now(APP_TIMEZONE).date()


def get_year_date_range(year: int) -> tuple[date, date]:
    """주어진 연도의 시작일과 종료일을 반환."""
    return date(year, 1, 1), date(year, 12, 31)
