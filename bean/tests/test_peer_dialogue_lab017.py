"""Lab017 regression: peer messages are durable, pinned and never auto-approved."""
from __future__ import annotations

import copy
import json

import pytest

from bean.optimization.peer_dialogue import PeerDialogue, PeerMessage
from bean.optimization.code_candidate import CodeCandidate, draft_candidate, digest

COMMIT = "a772c41db9b38580c1532565086a071f82dc02a0"
RUN = "https://github.com/danieloculus0-bot/BEAN/actions/runs/38102911597"


def candidate():
    source = "def answer():\n    return 0\n"
    proposal = draft_candidate(
        source=source, base_commit=COMMIT, path="bean/evaluation/fix_probe.py",
        problem="Correct the seeded test failure from the verified unit test",
        proposer=lambda _, original: original.replace("return 0", "return 1"),
    )
    return source, proposal


def dialogue():
    source, code = candidate()
    assert "+    return 1" in code.preview(source)
    ledger = PeerDialogue().next(
        role="selector", kind="proposal",
        branch="feat/agentic-improvement-selection-20261010",
        commit_sha=COMMIT, subject="Fix a reproducibly failing fixture",
        evidence_refs=("bean/tests/test_fixture.py:12",),
        candidate_sha256=code.candidate_digest,
    )
    ledger = ledger.next(
        role="validator", kind="challenge",
        branch="experiment/bean-peer-development-lab017-20261010",
        commit_sha=COMMIT, subject="Challenge existing expected behavior",
        evidence_refs=("bean/tests/test_peer_dialogue.py:15",),
        candidate_sha256=code.candidate_digest,
    )
    ledger = ledger.next(
        role="validator", kind="result",
        branch="experiment/bean-peer-development-lab017-20261010",
        commit_sha=COMMIT, subject="Reported external CI only; not an approval",
        evidence_refs=("github:actions:38102911597",),
        candidate_sha256=code.candidate_digest,
        test_state="reported_pass", test_run_url=RUN,
    )
    return ledger


def test_replay_roundtrip_and_no_approval_assertion(tmp_path):
    journal = dialogue()
    saved = tmp_path / "peer.json"
    journal.save(saved)
    loaded = PeerDialogue.load(saved)
    assert loaded.export() == journal.export()
    assert loaded.tip == journal.entries[-1].digest
    assert not hasattr(journal, "merge")
    assert not hasattr(journal, "execute")


def test_modifying_past_fails_even_with_recomputed_outer_digest(tmp_path):
    data = dialogue().export()
    broken = copy.deepcopy(data)
    broken["messages"][0]["subject"] = "A false historical assertion"
    from bean.optimization.peer_dialogue import fingerprint
    broken["sha256"] = fingerprint({k: v for k, v in broken.items() if k != "sha256"})
    with pytest.raises(ValueError, match="integrity mismatch"):
        PeerDialogue.restore(broken)
    broken = copy.deepcopy(data)
    broken["messages"].reverse()
    broken["sha256"] = fingerprint({k: v for k, v in broken.items() if k != "sha256"})
    with pytest.raises(ValueError, match="missing, reordered|tip mismatch"):
        PeerDialogue.restore(broken)


def test_cannot_overwrite_ledger_with_shorter_history(tmp_path):
    path = tmp_path / "journal.json"
    full = dialogue()
    full.save(path)
    with pytest.raises(ValueError, match="cannot rewrite"):
        PeerDialogue(full.entries[:1]).save(path)
    assert len(PeerDialogue.load(path).entries) == 3


def test_duplicate_or_orphan_peer_results_rejected():
    _, code = candidate()
    with pytest.raises(ValueError, match="unknown candidate"):
        PeerDialogue().next(
            role="validator", kind="result", branch="peer/dev",
            commit_sha=COMMIT, subject="Do not accept a free-floating test verdict",
            evidence_refs=("sample:test",), candidate_sha256=code.candidate_digest,
            test_state="reported_fail", test_run_url=RUN,
        )
    with pytest.raises(ValueError, match="requires a run URL"):
        PeerMessage(role="validator", kind="result", branch="peer/dev",
                    commit_sha=COMMIT, subject="Reported without run evidence",
                    evidence_refs=("sample:test",), candidate_sha256=code.candidate_digest,
                    test_state="reported_pass")


def test_path_and_origin_digest_safety(tmp_path):
    source, patch = candidate()
    root = tmp_path / "new-sandbox"
    path = patch.write_disposable(source, root)
    assert path.read_text() == "def answer():\n    return 1\n"
    assert (root / "candidate.diff").exists()
    assert source == "def answer():\n    return 0\n"
    with pytest.raises(ValueError, match="must be new"):
        patch.write_disposable(source, root)
    with pytest.raises(ValueError, match="original has changed"):
        patch.preview("def answer():\n    return 2\n")
    with pytest.raises(ValueError, match="relative"):
        CodeCandidate(COMMIT, "../outside.py", digest(source), "x=1\n",
                      "Correct a seeded finding")
    with pytest.raises(SyntaxError):
        CodeCandidate(COMMIT, "bean/test.py", digest(source), "def bad(:\n",
                      "Correct a seeded finding")


def test_deterministic_candidate_identity_and_data_only_generation():
    source, first = candidate()
    _, second = candidate()
    assert first.candidate_digest == second.candidate_digest
    assert digest(first.replacement) != first.source_digest
    assert "return 0" in source
    assert "return 1" in first.replacement
    assert "return 1" not in source


def test_peer_status_is_reported_not_authenticated():
    data = dialogue()
    assert data.entries[-1].test_state == "reported_pass"
    assert not hasattr(data.entries[-1], "verified")
    assert data.entries[-1].test_run_url == RUN
