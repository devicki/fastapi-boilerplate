"""
경로/파일명 관련 공통 유틸리티
"""


def filename_only(path: str | None) -> str | None:
    """
    경로에서 파일명만 추출합니다.

    - DB/로그 등에 전체 경로가 저장되어 있어도, FE 등 외부로는 파일명만 전달해야 할 때 사용합니다.
    - Linux 경로(`/`)와 Windows 경로(`\\`) 모두 지원합니다.

    Args:
        path: 파일 경로(또는 파일명). None/빈 문자열이면 그대로 반환합니다.

    Returns:
        파일명(경로의 마지막 토큰). 입력이 None/빈 문자열이면 그대로 반환합니다.
    """
    if not path:
        return path
    normalized = path.replace("\\", "/")
    return normalized.rsplit("/", 1)[-1]
