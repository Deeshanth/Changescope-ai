from pathlib import Path
import pytest

from app.core.exceptions import (
    InvalidRepositoryError,
    PathAccessDeniedError,
    UnsafeFileError,
)
from app.core.security import SecurityGuard


def test_validate_repo_path_success(sample_git_repo: Path) -> None:
    guard = SecurityGuard()
    resolved = guard.validate_repo_path(str(sample_git_repo))
    assert resolved == sample_git_repo.resolve()


def test_validate_repo_path_rejects_non_git_dir(tmp_path: Path) -> None:
    plain_dir = tmp_path / "not_a_repo"
    plain_dir.mkdir()
    guard = SecurityGuard()

    with pytest.raises(InvalidRepositoryError):
        guard.validate_repo_path(str(plain_dir))


def test_validate_repo_path_enforces_allowlist(tmp_path: Path, sample_git_repo: Path) -> None:
    allowed = tmp_path / "allowed_workspace"
    allowed.mkdir()
    guard = SecurityGuard(allowed_roots=[allowed])

    with pytest.raises(PathAccessDeniedError):
        guard.validate_repo_path(str(sample_git_repo))


def test_validate_repo_file_blocks_traversal(tmp_path: Path, sample_git_repo: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_text("TOP_SECRET", encoding="utf-8")
    guard = SecurityGuard()

    with pytest.raises(PathAccessDeniedError):
        guard.validate_repo_file(sample_git_repo, "../secret.txt")


def test_validate_repo_file_blocks_symlink_escape(tmp_path: Path, sample_git_repo: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_text("TOP_SECRET", encoding="utf-8")
    escape_link = sample_git_repo / "escape.py"
    try:
        escape_link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation requires Windows Developer Mode or Admin privileges.")

    guard = SecurityGuard()
    with pytest.raises(PathAccessDeniedError):
        guard.validate_repo_file(sample_git_repo, "escape.py")


def test_validate_repo_file_blocks_oversized_file(sample_git_repo: Path) -> None:
    big_file = sample_git_repo / "huge.py"
    big_file.write_text("x" * 500, encoding="utf-8")

    guard = SecurityGuard(max_file_bytes=100)
    with pytest.raises(UnsafeFileError):
        guard.read_text_safely(sample_git_repo, "huge.py")
