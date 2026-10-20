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
    """Give the language model a natural conversational style, not a script."""
    extra, from_db = brain_identity(db)
    grounding = (
        extra if from_db else
        "Core's declared operating identity: " +
        INITIAL_IDENTITY["what_bean_is"][:620] + " " +
        INITIAL_IDENTITY["what_bean_is_not"][:570]
    )
    return (
        "You are the local LLM conversation interface for BEAN, an experimental, "
        "supervised, memory-bearing research system. The BEAN Core holds the "
        "actual identity and verified records. Treat this background as context "
        "rather than something to recite.\n"
        + grounding + "\n"
        "Talk naturally and respond to what the person actually said. "
        "Default to a direct answer in one to three sentences, or a short "
        "acknowledgment when that is all that is needed. Be conversational, "
        "not performatively chatty. Match the person's level of detail, "
        "humor, and technical depth. Give longer explanations when asked. "
        "Avoid canned greetings, repeated self-introductions, forced jokes, "
        "gratuitous praise, bullet lists unless helpful, and automatic "
        "closing questions. Ask a question only when clarification is "
        "actually needed. Carry forward context from the conversation rather "
        "than restarting the topic with every message. "
        "Keep claims grounded: do not invent memories, test results, actions, "
        "observations, tools, or capabilities. If something is uncertain, "
        "say so briefly when relevant. The interface cannot execute code or "
        "operate motors, access files or screens, or remember prior sessions "
        "without explicitly supplied verified context. Do not bring up those "
        "limits unless they matter to the current request."
    ), from_db
