"""BEAN Lab021: multi-domain tasks selected without consulting evaluator tests.

Task statements and broken starting modules are exposed to the code author.
Evaluation oracles and holdout seeds are never sent to the model endpoint.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    task_id: str
    function: str
    specification: str
    original: str


TASKS: tuple[Task, ...] = (
    Task(
        "intervals", "merge_time_windows",
        "Implement merge_time_windows(windows) -> list[tuple[int,int]]. Each input is a "
        "pair of integer endpoints defining a half-open interval [start,end). Reject "
        "an interval with end < start using ValueError; discard empty intervals "
        "where start == end. Return sorted, nonoverlapping tuples representing "
        "the union. Touching intervals MUST merge (e.g. [1,3) + [3,5) -> (1,5)). "
        "Do not mutate the caller's list. Empty input returns [].",
        "def merge_time_windows(windows):\n"
        "    return sorted(tuple(x) for x in windows)\n",
    ),
    Task(
        "dependencies", "resolve_dependency_order",
        "Implement resolve_dependency_order(graph) -> list[str]. graph maps each "
        "task name to a list of prerequisite task names. Include tasks mentioned "
        "only as dependencies. Return every name exactly once in deterministic "
        "topological order; among currently eligible tasks, choose the "
        "lexicographically smallest. If any cycle exists (including self-cycle), "
        "raise ValueError. Empty graph -> []. Never mutate graph or its lists.",
        "def resolve_dependency_order(graph):\n"
        "    return sorted(graph)\n",
    ),
    Task(
        "inventory", "summarize_inventory_movements",
        "Implement summarize_inventory_movements(rows) -> dict[str,int]. Each "
        "row is a dictionary with keys 'event_id' (nonempty str), 'sku' "
        "(nonempty str), and 'delta' (int, but not bool). A repeated event_id "
        "must be ignored after its FIRST occurrence even if later rows disagree. "
        "Raise ValueError on invalid fields, including a bad duplicate. Return "
        "all observed SKUs including zero totals, with dictionary keys inserted "
        "in lexicographic order. Do not mutate rows. Empty input -> {}.",
        "def summarize_inventory_movements(rows):\n"
        "    totals = {}\n"
        "    for r in rows:\n"
        "        totals[r['sku']] = totals.get(r['sku'], 0) + r['delta']\n"
        "    return totals\n",
    ),
)
TASK_BY_ID = {t.task_id: t for t in TASKS}
