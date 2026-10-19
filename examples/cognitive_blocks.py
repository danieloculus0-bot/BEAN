"""Offline-first composition example; registered Bridge plugin loads on demand.

Run from Core checkout:
    python -m examples.cognitive_blocks --bridge /path/to/BEAN-AI-Bridge-
To pull the public Bridge branch when it is not already local, omit --bridge.
No actual exchange, remote data or motor hardware is used.
"""
from __future__ import annotations
import argparse
import json
import tempfile
from pathlib import Path

from bean.memory.store import init_store
from bean.modules import BlockRuntime
from bean.modules.builtin import register_builtin


def example(bridge_root: str | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="bean_blocks_") as tmp:
        directory = Path(tmp)
        init_store(str(directory / "memory.sqlite"))
        runner = BlockRuntime(cache_dir=directory / "git-cache")
        register_builtin(runner)
        bridge = {
            "name": "bridge.strategy_policy",
            "entrypoint": "ezbean.bean_blocks:run",
            "capabilities": ["strategy_selection", "policy_feedback"],
            "description": "Bridge reward-updated contextual strategy policy",
            "source": {
                "module_file": "src/ezbean/bean_blocks.py",
                "python_root": "src",
            },
        }
        if bridge_root:
            bridge["source"]["local_root"] = bridge_root
        else:
            bridge["source"].update({
                "git_url": "https://github.com/danieloculus0-bot/BEAN-AI-Bridge-.git",
                "ref": "feature/cognitive-blocks-20261019",
            })
        runner.register(bridge)
        history = [.01, .02, -.01, .03] * 4
        chain = [
            {"id": "analysis", "capability": "numeric_context",
             "payload": {"history": {"$from": "input.history"}}},
            {"id": "strategy", "capability": "strategy_selection",
             "payload": {"history": {"$from": "analysis.history"},
                         "seed": 7}},
        ]
        return runner.chain(chain, inputs={"history": history},
                            context={"data_dir": str(directory)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge", help="Optional existing local Bridge checkout")
    args = parser.parse_args()
    print(json.dumps(example(args.bridge), indent=2))
