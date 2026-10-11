"""Lab 017: code change *candidate*, not a deployed self-rewriting agent.

A model or deterministic proposer may return replacement Python source.
The proposed change is pinned to an exact original digest and Git commit.
It is written ONLY to a caller-created disposable workspace for peer review.
No shell execution, repository writes, GitHub merge or deployment is included.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
ALLOWED = re.compile(r"^bean/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.py$")


def digest(source: str) -> str:
    if not isinstance(source, str):
        raise ValueError("source must be text")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CodeCandidate:
    base_commit: str
    path: str
    source_digest: str
    replacement: str
    explanation: str

    def __post_init__(self):
        if not isinstance(self.base_commit, str) or not HEX40.fullmatch(self.base_commit):
            raise ValueError("base_commit must pin a full commit")
        if not isinstance(self.path, str) or not ALLOWED.fullmatch(self.path):
            raise ValueError("path must be a relative BEAN Python module")
        if not isinstance(self.source_digest, str) or not HEX64.fullmatch(self.source_digest):
            raise ValueError("original source digest required")
        if not isinstance(self.replacement, str) or not 0 < len(self.replacement) <= 40000:
            raise ValueError("replacement must be bounded source text")
        if not isinstance(self.explanation, str) or not 8 <= len(self.explanation) <= 4000:
            raise ValueError("a falsifiable change explanation is required")
        # Static syntax check does not mean code is safe or correct.
        compile(self.replacement, self.path, "exec")

    @property
    def candidate_digest(self) -> str:
        data = "\n".join((self.base_commit, self.path, self.source_digest,
                          digest(self.replacement), self.explanation))
        return digest(data)

    def preview(self, source: str) -> str:
        if digest(source) != self.source_digest:
            raise ValueError("the pinned original has changed")
        if source == self.replacement:
            raise ValueError("no change proposed")
        return "".join(difflib.unified_diff(
            source.splitlines(keepends=True),
            self.replacement.splitlines(keepends=True),
            fromfile=f"a/{self.path}", tofile=f"b/{self.path}",
        ))

    def write_disposable(self, source: str, workspace: Path) -> Path:
        """Write a preview only inside a newly empty scratch directory.

        It cannot be directed at a caller's existing repository checkout. No
        patch execution, secret filtering or OS sandboxing is claimed.
        """
        patch = self.preview(source)
        if not patch:
            raise ValueError("empty diff")
        workspace = Path(workspace)
        if workspace.is_symlink() or workspace.exists():
            raise ValueError("workspace must be new, not a repository or symlink")
        # Prevent an attacker using an existing symlinked ancestor to escape.
        for parent in (workspace, *workspace.parents):
            if parent.is_symlink():
                raise ValueError("symlinked workspace ancestor")
        workspace.mkdir(mode=0o700)
        target = workspace / self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or target.exists():
            raise ValueError("workspace path already exists")
        target.write_text(self.replacement, encoding="utf-8")
        os.chmod(target, 0o600)
        (workspace / "candidate.diff").write_text(patch, encoding="utf-8")
        return target


def draft_candidate(*, source: str, base_commit: str, path: str,
                    problem: str, proposer: Callable[[str, str], str]) -> CodeCandidate:
    """Pass observed problem + original code to a replaceable draft provider.

    A proposer can be a local model, remote model, or deterministic test stub.
    This function NEVER executes the returned code or trusts its claims.
    """
    if not isinstance(problem, str) or not 8 <= len(problem) <= 4000:
        raise ValueError("problem statement required")
    if not callable(proposer):
        raise ValueError("missing proposer")
    replacement = proposer(problem, source)
    return CodeCandidate(base_commit=base_commit, path=path,
                         source_digest=digest(source), replacement=replacement,
                         explanation=problem)
