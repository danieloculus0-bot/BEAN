#!/usr/bin/env python3
"""Owner-scoped GitHub Issues request transport for actual Python BEAN Core."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

OWNER = "danieloculus0-bot"
SCHEMA = "bean.github.request.v1"
COMMANDS = {"reasoning_status", "reasoning_local", "reasoning_recall"}


def _bounded_text(value, field, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValueError(field + " needs bounded nonempty text")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        raise ValueError(field + " contains control characters")
    return value.strip()


def parse_public_request(body: str) -> dict:
    if not isinstance(body, str) or len(body.encode("utf-8")) > 3000:
        raise ValueError("Public request must be 3 KB or less")
    body = body.strip()
    fence = chr(96) * 3
    if body.startswith(fence + "json\n") and body.endswith("\n" + fence):
        body = body[len(fence + "json\n"):-len(fence)-1]
    request = json.loads(body)
    if (not isinstance(request, dict)
            or set(request) != {"schema", "command", "args"}
            or request["schema"] != SCHEMA
            or request["command"] not in COMMANDS
            or not isinstance(request["args"], dict)):
        raise ValueError("Expected exact BEAN v1 command envelope")
    command, args = request["command"], request["args"]
    if command == "reasoning_status":
        if args:
            raise ValueError("reasoning_status takes no arguments")
    elif command == "reasoning_recall":
        if set(args) != {"domain", "query", "limit"}:
            raise ValueError("reasoning_recall needs domain, query, limit")
        _bounded_text(args["domain"], "domain", 100)
        _bounded_text(args["query"], "query", 500)
        if type(args["limit"]) is not int or not 1 <= args["limit"] <= 3:
            raise ValueError("Recall limit must be 1..3")
    else:
        if set(args) != {"domain", "task_ref", "query"}:
            raise ValueError("reasoning_local needs domain, task_ref, query")
        _bounded_text(args["domain"], "domain", 100)
        _bounded_text(args["task_ref"], "task_ref", 120)
        _bounded_text(args["query"], "query", 500)
    return request


def from_github_event(event: dict, event_name: str) -> dict:
    issue = event.get("issue", {})
    sender = event.get("sender", {})
    if not isinstance(issue, dict) or not isinstance(sender, dict):
        raise ValueError("Missing issue identity")
    if issue.get("pull_request") or not str(issue.get("title", "")).startswith("[BEAN]"):
        raise ValueError("Not a BEAN request issue")
    if issue.get("user", {}).get("login") != OWNER or sender.get("login") != OWNER:
        raise ValueError("Only the repository owner may invoke public BEAN")
    number = issue.get("number")
    if type(number) is not int or number < 1:
        raise ValueError("Invalid issue number")
    if event_name == "issues":
        if event.get("action") != "opened":
            raise ValueError("Unsupported issue event")
        body = issue.get("body")
        request_id = f"issue-{number}"
    elif event_name == "issue_comment":
        comment = event.get("comment", {})
        if event.get("action") != "created" or not isinstance(comment, dict):
            raise ValueError("Unsupported comment event")
        if comment.get("user", {}).get("login") != OWNER:
            raise ValueError("Only the repository owner may post public BEAN requests")
        comment_id = comment.get("id")
        if type(comment_id) is not int or comment_id < 1:
            raise ValueError("Invalid comment ID")
        request_id = f"comment-{comment_id}"
        body = comment.get("body")
    else:
        raise ValueError("Unsupported GitHub event")
    return {
        "request_id": request_id,
        "issue_number": number,
        "request": parse_public_request(body),
    }


def render_public_reply(request_id: str, reply: dict) -> str:
    if (not isinstance(reply, dict)
            or reply.get("schema") != "bean.github.reply.v1"
            or not isinstance(reply.get("generation"), int)
            or not isinstance(reply.get("receipt_sha256"), str)):
        raise ValueError("Invalid BEAN Core reply")
    body = json.dumps(reply["response"], indent=2, ensure_ascii=False, sort_keys=True)
    if len(body) > 14000:
        raise ValueError("Oversized BEAN Core reply")
    return (
        f"<!-- BEAN_REPLY:{request_id} -->\n"
        "**BEAN Core answered** via the actual Python Core on GitHub Actions. "
        "This is not a streamed chat or a hosted LLM response.\n\n"
        f"**Command:** <code>{html.escape(reply['command'])}</code> · "
        f"**Generation:** {reply['generation']} · "
        f"**Receipt:** <code>{html.escape(reply['receipt_sha256'][:16])}</code>…\n\n"
        "<details open><summary>Native Core result (JSON)</summary>\n\n"
        "<pre>" + html.escape(body, quote=True) + "</pre>\n\n"
        "</details>\n\n"
        "The GitHub checkpoint is synthetic-only. Public input is visible "
        "in this issue. No Jetson connection, paid inference, or independent "
        "consciousness claim is implied.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path)
    parser.add_argument("--event-name")
    parser.add_argument("--request-out", type=Path)
    parser.add_argument("--metadata-out", type=Path)
    parser.add_argument("--reply", type=Path)
    parser.add_argument("--render-out", type=Path)
    parser.add_argument("--request-id")
    args = parser.parse_args()
    if args.event:
        if not (args.event_name and args.request_out and args.metadata_out):
            parser.error("event mode requires --event-name --request-out --metadata-out")
        payload = from_github_event(
            json.loads(args.event.read_text(encoding="utf-8")), args.event_name)
        args.request_out.write_text(json.dumps(payload["request"], sort_keys=True), encoding="utf-8")
        args.metadata_out.write_text(json.dumps({
            "request_id": payload["request_id"],
            "issue_number": payload["issue_number"],
        }), encoding="utf-8")
    elif args.reply:
        if not args.render_out or not args.request_id:
            parser.error("reply mode requires --render-out and --request-id")
        args.render_out.write_text(
            render_public_reply(args.request_id,
                                json.loads(args.reply.read_text(encoding="utf-8"))),
            encoding="utf-8")
    else:
        parser.error("select event mode or reply mode")


if __name__ == "__main__":
    main()
