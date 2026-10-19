"""Audit regressions: independent memory instances and explicit provider identity.

The tests are about correctness of learning state, not behavioral permissions.
"""
from __future__ import annotations

import sqlite3

import pytest

from bean.memory.store import MemoryStore, get_store, init_store
from bean.reasoning.reasoning_engine import adapter_from_name, ReasoningEngine


def test_parallel_memory_stores_do_not_mix_database_paths(tmp_path):
    first = MemoryStore(str(tmp_path / "one.sqlite"))
    second = MemoryStore(str(tmp_path / "two.sqlite"))
    try:
        first.execute("CREATE TABLE local_probe (answer TEXT)")
        first.execute("INSERT INTO local_probe VALUES ('first')")
        first.commit()
        second.execute("CREATE TABLE local_probe (answer TEXT)")
        second.execute("INSERT INTO local_probe VALUES ('second')")
        second.commit()
        assert first.fetchone("SELECT answer FROM local_probe")["answer"] == "first"
        assert second.fetchone("SELECT answer FROM local_probe")["answer"] == "second"
        assert first.fetchone("PRAGMA database_list")[2] != second.fetchone("PRAGMA database_list")[2]
    finally:
        first.close()
        second.close()


def test_standalone_memory_store_does_not_overwrite_initialized_core(tmp_path):
    init_store(str(tmp_path / "core.sqlite"))
    core = get_store()
    other = MemoryStore(str(tmp_path / "experimental.sqlite"))
    try:
        core.execute("CREATE TABLE core_only (v INTEGER)")
        core.execute("INSERT INTO core_only VALUES (101)")
        core.commit()
        other.execute("CREATE TABLE experiment_only (v INTEGER)")
        other.execute("INSERT INTO experiment_only VALUES (202)")
        other.commit()
        assert core.fetchone("SELECT v FROM core_only")["v"] == 101
        assert other.fetchone("SELECT v FROM experiment_only")["v"] == 202
        assert get_store() is core
    finally:
        other.close()
        core.close()


def test_unrecognized_provider_does_not_become_mock():
    assert adapter_from_name("mock").adapter_name == "mock"
    with pytest.raises(ValueError, match="Unknown BEAN reasoning provider"):
        adapter_from_name("olama")  # simulate an Ollama spelling mistake
    with pytest.raises(ValueError, match="Unknown BEAN reasoning provider"):
        adapter_from_name("not_registered_yet")


def test_invalid_provider_does_not_generate_a_fake_reasoning_proposal(tmp_path):
    from bean.memory.identity import bootstrap_identity
    from bean.memory.session import begin_session

    init_store(str(tmp_path / "reasoning.sqlite"))
    try:
        bootstrap_identity()
        session = begin_session()
        with pytest.raises(ValueError, match="Unknown BEAN reasoning provider"):
            ReasoningEngine().run(session, adapter_name="provider_typo")
        row = get_store().fetchone("SELECT COUNT(*) FROM reasoning_proposals")
        assert row[0] == 0
    finally:
        get_store().close()
