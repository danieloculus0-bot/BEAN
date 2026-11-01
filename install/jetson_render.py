"""Render existing BEAN Jetson env and service templates for a real Linux user.

Does not install, start, or modify a service. No external dependencies.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKENS = (
    "BEAN_USER", "BEAN_GROUP", "BEAN_HOME", "BEAN_DATA_DIR",
    "BEAN_LOG_DIR", "BEAN_ENV_FILE",
)
TOKEN_PATTERN = re.compile(r"@[A-Z][A-Z0-9_]*@")


def render_template(kind: str, values: dict[str, str]) -> str:
    if kind not in ("env", "service"):
        raise ValueError("Template must be env or service")
    if any(k not in values for k in TOKENS):
        raise ValueError("Missing required template value")
    for name in ("BEAN_USER", "BEAN_GROUP"):
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", values[name]):
            raise ValueError(f"Invalid {name}")
    for name in ("BEAN_HOME", "BEAN_DATA_DIR", "BEAN_LOG_DIR", "BEAN_ENV_FILE"):
        value = values[name]
        # Reject characters with special meaning in environment and unit files.
        if (not value.startswith("/") or not Path(value).is_absolute()
                or ".." in Path(value).parts
                or not re.fullmatch(r"/[A-Za-z0-9_./-]+", value)):
            raise ValueError(f"Unsafe or nonabsolute {name}")
    filename = "bean.env.example" if kind == "env" else "bean.service"
    template = (ROOT / filename).read_text(encoding="utf-8")
    for name, value in values.items():
        template = template.replace("@" + name + "@", value)
    remaining = TOKEN_PATTERN.findall(template)
    if remaining:
        raise ValueError(f"Unresolved placeholders: {remaining}")
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description="Render BEAN Jetson install templates")
    parser.add_argument("kind", choices=("env", "service"))
    parser.add_argument("--user", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    vals = {
        "BEAN_USER": args.user,
        "BEAN_GROUP": args.group,
        "BEAN_HOME": args.home,
        "BEAN_DATA_DIR": args.data_dir,
        "BEAN_LOG_DIR": args.log_dir,
        "BEAN_ENV_FILE": args.env_file,
    }
    print(render_template(args.kind, vals), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
