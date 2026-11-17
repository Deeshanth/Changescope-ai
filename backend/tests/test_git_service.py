from pathlib import Path
import subprocess
import pytest

from app.core.exceptions import GitOperationError
from app.services.git_service import GitService


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture()
def real_git_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "real_repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")

    (repo / "pkg").mkdir()
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pkg" / "math_ops.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial commit")
    c1 = _git(repo, "rev-parse", "HEAD")

    (repo / "pkg" / "math_ops.py").write_text(
        "def add(a, b):\n    return a + b + 0\n\ndef mul(a, b):\n    return a * b\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "modify add")
    c2 = _git(repo, "rev-parse", "HEAD")

    return repo, c1, c2


def test_git_service_commits_and_files(real_git_repo: tuple[Path, str, str]) -> None:
    repo, _, c2 = real_git_repo
    git = GitService()

    assert git.get_head_commit(repo) == c2
    commits = git.list_commits(repo)
    assert len(commits) == 2
    assert commits[0].subject == "modify add"

    tracked = git.list_tracked_files(repo)
    assert tracked == ["pkg/__init__.py", "pkg/math_ops.py"]


def test_git_service_diff_hunks(real_git_repo: tuple[Path, str, str]) -> None:
    repo, c1, c2 = real_git_repo
    git = GitService()

    diffs = git.get_diff_hunks(repo, c1, c2)
    assert len(diffs) == 1
    assert diffs[0].primary_path == "pkg/math_ops.py"
    assert diffs[0].hunks[0].new_line_range == (2, 2)


def test_git_service_rejects_flag_injection(real_git_repo: tuple[Path, str, str]) -> None:
    repo, c1, _ = real_git_repo
    git = GitService()

    with pytest.raises(GitOperationError):
        git.get_diff_hunks(repo, "--output=/tmp/pwn", c1)
