from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
from typing import List, Optional

from app.core.exceptions import GitOperationError

_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9._/\-~^]+$")
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)


@dataclass(frozen=True)
class CommitInfo:
    commit_hash: str
    short_hash: str
    author_name: str
    committed_at: str
    subject: str


@dataclass(frozen=True)
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int

    @property
    def new_line_range(self) -> tuple[int, int]:
        if self.new_count == 0:
            return (self.new_start, self.new_start)
        return (self.new_start, self.new_start + self.new_count - 1)

    @property
    def old_line_range(self) -> tuple[int, int]:
        if self.old_count == 0:
            return (self.old_start, self.old_start)
        return (self.old_start, self.old_start + self.old_count - 1)


@dataclass
class FileDiff:
    old_path: Optional[str]
    new_path: Optional[str]
    change_type: str
    hunks: List[DiffHunk] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0

    @property
    def primary_path(self) -> str:
        return self.new_path or self.old_path or ""


class GitService:
    """Safe, read-only Git CLI wrapper. Never uses shell=True or modifies working trees."""

    def _validate_ref(self, ref: str) -> str:
        if not ref or ref.startswith("-") or not _SAFE_REF_RE.match(ref):
            raise GitOperationError(f"Invalid Git reference: '{ref}'")
        return ref

    def _run_git(self, repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise GitOperationError(f"Git execution failed: {exc}") from exc

        if proc.returncode != 0:
            stderr = proc.stderr.strip() or "Unknown git error"
            raise GitOperationError(f"git {' '.join(args)} failed: {stderr}")
        return proc

    def get_default_branch(self, repo_root: Path) -> Optional[str]:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            branch = proc.stdout.strip()
            return branch if branch and branch != "HEAD" else None
        return None

    def get_head_commit(self, repo_root: Path) -> Optional[str]:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
        return None

    def list_commits(self, repo_root: Path, limit: int = 50) -> List[CommitInfo]:
        safe_limit = max(1, min(limit, 200))
        fmt = "%H%x1f%h%x1f%an%x1f%aI%x1f%s"
        proc = subprocess.run(
            ["git", "log", f"-n{safe_limit}", f"--pretty=format:{fmt}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            return []

        commits: List[CommitInfo] = []
        for line in proc.stdout.splitlines():
            parts = line.split("\x1f", 4)
            if len(parts) == 5:
                commits.append(
                    CommitInfo(
                        commit_hash=parts[0],
                        short_hash=parts[1],
                        author_name=parts[2],
                        committed_at=parts[3],
                        subject=parts[4],
                    )
                )
        return commits

    def list_tracked_files(
        self, repo_root: Path, extensions: tuple[str, ...] = (".py",)
    ) -> List[str]:
        proc = self._run_git(repo_root, ["ls-files", "-z"])
        raw_entries = [entry for entry in proc.stdout.split("\x00") if entry]
        if not extensions:
            return sorted(raw_entries)
        return sorted(
            entry for entry in raw_entries if entry.lower().endswith(extensions)
        )

    def read_file_at_commit(
        self, repo_root: Path, commit: str, file_path: str
    ) -> Optional[str]:
        safe_commit = self._validate_ref(commit)
        clean_path = file_path.lstrip("/")
        if "\x00" in clean_path or ".." in Path(clean_path).parts:
            raise GitOperationError(f"Unsafe file path in commit lookup: '{file_path}'")

        proc = subprocess.run(
            ["git", "show", f"{safe_commit}:{clean_path}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout

    def get_diff_hunks(
        self, repo_root: Path, base_commit: str, head_commit: str
    ) -> List[FileDiff]:
        safe_base = self._validate_ref(base_commit)
        safe_head = self._validate_ref(head_commit)

        proc = self._run_git(
            repo_root,
            [
                "diff",
                "--unified=0",
                "--no-color",
                "--find-renames",
                safe_base,
                safe_head,
                "--",
            ],
        )
        return self._parse_unified_diff(proc.stdout)

    def _parse_unified_diff(self, diff_text: str) -> List[FileDiff]:
        files: List[FileDiff] = []
        current: Optional[FileDiff] = None

        for line in diff_text.splitlines():
            if line.startswith("diff --git "):
                if current is not None:
                    files.append(current)
                parts = line.split(" ")
                a_path = parts[2][2:] if len(parts) >= 4 and parts[2].startswith("a/") else None
                b_path = parts[3][2:] if len(parts) >= 4 and parts[3].startswith("b/") else None
                current = FileDiff(
                    old_path=a_path,
                    new_path=b_path,
                    change_type="modified",
                )
                continue

            if current is None:
                continue

            if line.startswith("new file mode "):
                current.change_type = "added"
                current.old_path = None
            elif line.startswith("deleted file mode "):
                current.change_type = "deleted"
                current.new_path = None
            elif line.startswith("rename from "):
                current.change_type = "renamed"
                current.old_path = line[len("rename from "):].strip()
            elif line.startswith("rename to "):
                current.change_type = "renamed"
                current.new_path = line[len("rename to "):].strip()
            elif line.startswith("--- "):
                raw = line[4:].strip()
                if raw == "/dev/null":
                    current.old_path = None
                elif raw.startswith("a/"):
                    current.old_path = raw[2:]
            elif line.startswith("+++ "):
                raw = line[4:].strip()
                if raw == "/dev/null":
                    current.new_path = None
                elif raw.startswith("b/"):
                    current.new_path = raw[2:]
            elif line.startswith("@@ "):
                match = _HUNK_HEADER_RE.match(line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) is not None else 1
                    new_start = int(match.group(3))
                    new_count = int(match.group(4)) if match.group(4) is not None else 1
                    current.hunks.append(
                        DiffHunk(
                            old_start=old_start,
                            old_count=old_count,
                            new_start=new_start,
                            new_count=new_count,
                        )
                    )
            elif line.startswith("+") and not line.startswith("+++"):
                current.added_lines += 1
            elif line.startswith("-") and not line.startswith("---"):
                current.removed_lines += 1

        if current is not None:
            files.append(current)

        return files
