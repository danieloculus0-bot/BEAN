"""Lab 017: evidence-bearing messages between independent BEAN development branches.

The message ledger is *not a chat transport*. GitHub branch files and PR comments
carry the messages. This module validates immutable handoffs and catches omitted,
reordered or changed test receipts. Digests provide integrity, not identity/authenticity.
No code is executed and no main branch or approval status is changed here.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SCHEMA = "bean.peer-development.v1"
KINDS = frozenset({"proposal", "challenge", "result", "revision", "acknowledgement"})
ROLES = frozenset({"selector", "builder", "validator"})
SHA = re.compile(r"^[a-f0-9]{40}$")
REF = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/:#-]{0,150}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
# A human-readable label only, not a verified assertion about external CI status.
STATES = frozenset({"not_run", "reported_pass", "reported_fail", "unavailable"})


def _json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def fingerprint(data: dict) -> str:
    return hashlib.sha256(_json(data)).hexdigest()


@dataclass(frozen=True)
class PeerMessage:
    """Strict, immutable, branch-pinned exchange item.

    Consumers MUST resolve commit_sha from the remote repository independently;
    no string supplied in an envelope constitutes GitHub authentication.
    """
    role: str
    kind: str
    branch: str
    commit_sha: str
    subject: str
    evidence_refs: tuple[str, ...]
    parent_digest: Optional[str] = None
    candidate_sha256: Optional[str] = None
    test_state: str = "not_run"
    test_run_url: Optional[str] = None

    def __post_init__(self):
        if self.role not in ROLES or self.kind not in KINDS:
            raise ValueError("unknown role or message kind")
        if not isinstance(self.branch, str) or not REF.fullmatch(self.branch):
            raise ValueError("invalid branch reference")
        if type(self.commit_sha) is not str or not SHA.fullmatch(self.commit_sha):
            raise ValueError("commit must be a pinned 40-character SHA")
        if not isinstance(self.subject, str) or not 4 <= len(self.subject) <= 300:
            raise ValueError("subject required and bounded")
        if (type(self.evidence_refs) is not tuple or not self.evidence_refs
                or len(self.evidence_refs) > 40
                or any(type(ref) is not str or not REF.fullmatch(ref)
                       for ref in self.evidence_refs)):
            raise ValueError("at least one bounded evidence reference required")
        if self.parent_digest is not None and (
            type(self.parent_digest) is not str or not DIGEST.fullmatch(self.parent_digest)):
            raise ValueError("invalid parent digest")
        if self.candidate_sha256 is not None and (
            type(self.candidate_sha256) is not str or not DIGEST.fullmatch(self.candidate_sha256)):
            raise ValueError("invalid candidate digest")
        if self.test_state not in STATES:
            raise ValueError("invalid reported test state")
        if self.kind == "result":
            if self.test_state == "not_run" or not self.candidate_sha256:
                raise ValueError("result must refer to candidate and a test outcome")
        elif self.test_state != "not_run":
            raise ValueError("non-result messages cannot report test outcomes")
        if self.test_run_url is not None:
            if (not isinstance(self.test_run_url, str)
                    or not re.fullmatch(
                        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+",
                        self.test_run_url)):
                raise ValueError("test URL must identify a GitHub Actions run")
        if self.test_state.startswith("reported_") and self.test_run_url is None:
            raise ValueError("a reported CI outcome requires a run URL")

    def canonical(self) -> dict:
        payload = asdict(self)
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["schema"] = SCHEMA
        return payload

    @property
    def digest(self) -> str:
        return fingerprint(self.canonical())

    @classmethod
    def parse(cls, record: dict) -> "PeerMessage":
        if not isinstance(record, dict) or record.get("schema") != SCHEMA:
            raise ValueError("unsupported peer message schema")
        allowed = set(cls.__dataclass_fields__) | {"schema", "digest"}
        if set(record) != allowed:
            raise ValueError("peer envelope has extra or missing fields")
        data = {k: record[k] for k in cls.__dataclass_fields__}
        if not isinstance(data["evidence_refs"], list):
            raise ValueError("serialized evidence_refs must be a list")
        data["evidence_refs"] = tuple(data["evidence_refs"])
        msg = cls(**data)
        if record["digest"] != msg.digest:
            raise ValueError("peer message integrity mismatch")
        return msg

    def serialize(self) -> dict:
        return {**self.canonical(), "digest": self.digest}


class PeerDialogue:
    """Linear review conversation; each message binds the prior digest."""

    def __init__(self, entries: tuple[PeerMessage, ...] = ()):
        self.entries = tuple(entries)
        self.verify()

    def verify(self):
        for index, message in enumerate(self.entries):
            expected = self.entries[index - 1].digest if index else None
            if message.parent_digest != expected:
                raise ValueError("missing, reordered or substituted peer message")
            if index and message.digest in {m.digest for m in self.entries[:index]}:
                raise ValueError("duplicate peer message")
            if message.kind == "result":
                previous = self.entries[:index]
                matching = [entry for entry in previous
                            if entry.candidate_sha256 == message.candidate_sha256
                            and entry.kind in ("proposal", "challenge", "revision")]
                if not matching:
                    raise ValueError("peer result refers to an unknown candidate")

    def append(self, message: PeerMessage) -> "PeerDialogue":
        return PeerDialogue((*self.entries, message))

    @property
    def tip(self) -> Optional[str]:
        return self.entries[-1].digest if self.entries else None

    def next(self, **fields) -> "PeerDialogue":
        if "parent_digest" in fields:
            raise ValueError("parent is assigned by the ledger")
        return self.append(PeerMessage(parent_digest=self.tip, **fields))

    def export(self) -> dict:
        body = {"schema": SCHEMA, "messages": [m.serialize() for m in self.entries],
                "tip": self.tip}
        return {**body, "sha256": fingerprint(body)}

    @classmethod
    def restore(cls, record: dict) -> "PeerDialogue":
        if not isinstance(record, dict) or set(record) != {
            "schema", "messages", "tip", "sha256"
        } or record.get("schema") != SCHEMA:
            raise ValueError("invalid peer ledger schema")
        unsigned = {k: v for k, v in record.items() if k != "sha256"}
        if fingerprint(unsigned) != record["sha256"]:
            raise ValueError("peer ledger integrity mismatch")
        if not isinstance(record["messages"], list) or len(record["messages"]) > 10000:
            raise ValueError("invalid peer history size")
        result = cls(tuple(PeerMessage.parse(item) for item in record["messages"]))
        if record["tip"] != result.tip:
            raise ValueError("tip mismatch")
        return result

    def save(self, path: Path) -> None:
        """Save to a caller-owned path; no GitHub side effects.

        Two simultaneous writers must be serialized by the host (e.g. a PR
        review queue); this file operation is not a distributed lock.
        """
        path = Path(path)
        if path.exists():
            old = self.restore(json.loads(path.read_text(encoding="utf-8")))
            if len(self.entries) < len(old.entries) or self.entries[:len(old.entries)] != old.entries:
                raise ValueError("cannot rewrite existing peer history")
        tmp = path.with_name(path.name + ".tmp")
        if tmp.exists():
            raise ValueError("peer temp journal already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp.write_text(json.dumps(self.export(), indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)

    @classmethod
    def load(cls, path: Path) -> "PeerDialogue":
        return cls.restore(json.loads(Path(path).read_text(encoding="utf-8")))
