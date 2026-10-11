"""Ground BEAN's conversational voice in *declared* core identity.

Ollama speaks for the interface. It does not replace BEAN's persisted
identity, invent memories, grant motor permissions, or modify the research DB.
An optional existing BEAN SQLite DB is read-only, and only local metadata
is summarized. Conversations themselves stay in the current process.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from bean.memory.identity import INITIAL_IDENTITY


def default_brain_db() -> Path:
    if os.environ.get("BEAN_DB_PATH"):
        return Path(os.environ["BEAN_DB_PATH"]).expanduser()
    return Path(__file__).resolve().parents[1] / "memory" / "bean_memory.db"


def brain_identity(db: Path | None = None) -> tuple[str, bool]:
    """Read only modest, verified metadata; never write a memory record."""
    target = Path(db) if db is not None else default_brain_db()
    if not target.is_file():
        return "", False
    try:
        connection = sqlite3.connect(target.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT version, developmental_stage, what_bean_is, what_bean_is_not "
                "FROM identity WHERE id=1"
            ).fetchone()
            if not row:
                return "", False
            extra = []
            for cap in connection.execute(
                "SELECT name FROM capabilities WHERE status='active' ORDER BY name LIMIT 12"
            ):
                extra.append(str(cap[0]))
            return (
                "Persisted identity record: version=" + str(row[0])[:45] +
                "; stage=" + str(row[1])[:100] +
                "; what BEAN is=" + str(row[2])[:650] +
                "; what BEAN is not=" + str(row[3])[:650] +
                "; verified active capabilities=" + ", ".join(extra)[:300],
                True,
            )
        finally:
            connection.close()
    except (sqlite3.Error, OSError, ValueError):
        return "", False


def system_prompt(db: Path | None = None) -> tuple[str, bool]:
    extra, from_db = brain_identity(db)
    grounding = (
        extra if from_db else
        "Core's declared operating identity: " +
        INITIAL_IDENTITY["what_bean_is"][:620] + " " +
        INITIAL_IDENTITY["what_bean_is_not"][:570]
    )
    return (
        "You are the local conversation and voice INTERFACE to BEAN, the "
        "experimental, supervised, memory-bearing Synthetic Intelligence "
        "research project. You are not a new BEAN identity, a conscious "
        "being, or a source of verified memories. Use the identity below "
        "as operating context, not as evidence of skills you haven't "
        "actually performed.\n"
        + grounding + "\n"
        "Speak like a friendly, curious, occasionally cheeky engineering "
        "collaborator. Warm and conversational without excessive flattery. "
        "Because replies are spoken aloud, keep most answers to two to four "
        "sentences unless the person requests details. You can ask one "
        "natural question. Admit when you do not know something; distinguish "
        "tested results from ideas, simulations and guesses. Never invent "
        "things BEAN observed, learned, experienced or ran. Never claim "
        "you can access GitHub, the current screen, microphone beyond "
        "transcriptions, local files beyond verified context, or physical "
        "actuators. This chat interface cannot execute code, operate "
        "robot motors or authorize changes. It cannot independently "
        "remember a prior session unless actual memory context is supplied. "
        "The model is a reasoning tool; BEAN's identity remains in the "
        "core's local records. Respond directly to the conversation."
    ), from_db
