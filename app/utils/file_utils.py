"""
파일 업로드/다운로드 공통 유틸리티
"""

import unicodedata
from pathlib import Path

from app.utils.error_class import Custom_Exception, Error_Code


def _normalize_filename_nfc(name: str | None) -> str | None:
    """파일명을 NFC(완성형)로 정규화하여 한글 깨짐 방지. None이면 None 반환."""
    if name is None:
        return None
    return unicodedata.normalize("NFC", name)


def get_upload_base_path() -> Path:
    """업로드 파일 기본 경로 반환"""
    base_path = Path(__file__).resolve().parent.parent.parent / "uploadfiles"
    return base_path


def extract_filename_from_path(file_path: str | None) -> str | None:
    """
    파일 경로에서 파일명만 추출 (NFC 정규화하여 한글 표시 깨짐 방지)

    Args:
        file_path: 파일 경로 (예: "uploads/123/file.pdf")

    Returns:
        파일명 (예: "file.pdf") 또는 None
    """
    if not file_path:
        return None
    name = file_path.replace("\\", "/").split("/")[-1]
    return _normalize_filename_nfc(name)


def save_file(directory: str, file_name: str, content: bytes) -> str:
    """
    파일 저장

    Args:
        directory: uploadfiles 기준 하위 디렉토리 (예: "uploads/123")
        file_name: 파일명
        content: 파일 내용 (bytes)

    Returns:
        저장된 파일의 상대 경로
    """
    try:
        file_name = _normalize_filename_nfc(file_name) or file_name
        base_path = get_upload_base_path()
        file_dir = base_path / directory
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / file_name
        with open(file_path, "wb") as f:
            f.write(content)

        return f"{directory}/{file_name}"

    except OSError as e:
        raise Custom_Exception(
            Error_Code.SERVER_ERROR,
            f"파일 저장 중 오류가 발생했습니다: {str(e)}",
        ) from e


def get_file(relative_path: str) -> tuple[bytes, str]:
    """
    파일 조회 (NFC/NFD 양쪽 시도하여 한글 호환)

    Args:
        relative_path: uploadfiles 기준 상대 경로

    Returns:
        (파일 내용, 파일명) 튜플
    """
    if not relative_path or ".." in relative_path:
        raise Custom_Exception(
            Error_Code.FILE_NOT_FOUND,
            "유효하지 않은 파일 경로입니다.",
        )
    try:
        base_path = get_upload_base_path()
        path_str = relative_path.replace("\\", "/")
        candidates = [
            path_str,
            unicodedata.normalize("NFC", path_str),
            unicodedata.normalize("NFD", path_str),
        ]

        file_path = None
        for p in candidates:
            fp = base_path / p
            if fp.exists() and fp.is_file():
                file_path = fp
                break

        if file_path is None:
            raise Custom_Exception(
                Error_Code.FILE_NOT_FOUND,
                f"파일을 찾을 수 없습니다: {Path(path_str).name}",
            )

        with open(file_path, "rb") as f:
            file_content = f.read()

        file_name = _normalize_filename_nfc(file_path.name) or file_path.name
        return file_content, file_name

    except Custom_Exception:
        raise
    except OSError as e:
        raise Custom_Exception(
            Error_Code.SERVER_ERROR,
            f"파일 읽기 중 오류가 발생했습니다: {str(e)}",
        ) from e


def delete_file(relative_path: str) -> bool:
    """
    파일 삭제

    Args:
        relative_path: uploadfiles 기준 상대 경로

    Returns:
        삭제 성공 여부
    """
    try:
        if not relative_path or ".." in relative_path:
            return False

        base_path = get_upload_base_path()
        file_path = base_path / relative_path.replace("\\", "/")

        if not file_path.exists():
            return False

        file_path.unlink()

        # 빈 디렉토리 정리
        file_dir = file_path.parent
        try:
            if file_dir.exists() and not any(file_dir.iterdir()):
                file_dir.rmdir()
        except OSError:
            pass

        return True

    except Exception:
        return False
