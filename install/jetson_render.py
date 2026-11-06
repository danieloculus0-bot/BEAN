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
LLM_TOKENS = ("BEAN_LLAMACPP_DIR", "BEAN_GGUF_PATH", "BEAN_LLM_PORT")
TOKEN_PATTERN = re.compile(r"@[A-Z][A-Z0-9_]*@")


def render_template(kind: str, values: dict[str, str]) -> str:
    if kind not in ("env", "service", "llm_service"):
        raise ValueError("Template must be env, service or llm_service")
    required = TOKENS + (LLM_TOKENS if kind == "llm_service" else ())
    if any(k not in values for k in required):
        raise ValueError("Missing required template value")
    for name in ("BEAN_USER", "BEAN_GROUP"):
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", values[name]):
            raise ValueError(f"Invalid {name}")
    for name in ("BEAN_HOME", "BEAN_DATA_DIR", "BEAN_LOG_DIR", "BEAN_ENV_FILE") + (("BEAN_LLAMACPP_DIR", "BEAN_GGUF_PATH") if kind == "llm_service" else ()):
        value = values[name]
        # Reject characters with special meaning in environment and unit files.
        if (not value.startswith("/") or not Path(value).is_absolute()
                or ".." in Path(value).parts
                or not re.fullmatch(r"/[A-Za-z0-9_./-]+", value)):
            raise ValueError(f"Unsafe or nonabsolute {name}")
    if kind == "llm_service":
        port = values["BEAN_LLM_PORT"]
        if not port.isdigit() or not (1024 <= int(port) <= 65535):
            raise ValueError("Invalid BEAN_LLM_PORT")
    filename = {"env": "bean.env.example", "service": "bean.service",
                "llm_service": "bean-llamacpp.service"}[kind]
    template = (ROOT / filename).read_text(encoding="utf-8")
    for name, value in values.items():
        template = template.replace("@" + name + "@", value)
    remaining = TOKEN_PATTERN.findall(template)
    if remaining:
        raise ValueError(f"Unresolved placeholders: {remaining}")
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description="Render BEAN Jetson install templates")
    parser.add_argument("kind", choices=("env", "service", "llm_service"))
    parser.add_argument("--user", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--llama-dir")
    parser.add_argument("--model-path")
    parser.add_argument("--llm-port")
    args = parser.parse_args()
    vals = {
        "BEAN_USER": args.user,
        "BEAN_GROUP": args.group,
        "BEAN_HOME": args.home,
        "BEAN_DATA_DIR": args.data_dir,
        "BEAN_LOG_DIR": args.log_dir,
        "BEAN_ENV_FILE": args.env_file,
    }
    if args.kind == "llm_service":
        vals.update({"BEAN_LLAMACPP_DIR": args.llama_dir,
                     "BEAN_GGUF_PATH": args.model_path,
                     "BEAN_LLM_PORT": args.llm_port})
    print(render_template(args.kind, vals), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
