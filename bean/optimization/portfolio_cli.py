"""Small portable JSON/stdin interface for independent portfolio applications.

Example:
  python -m bean.optimization.portfolio_cli record --db bean.sqlite < event.json
  python -m bean.optimization.portfolio_cli context --db bean.sqlite --app FUN/EmperorGauntlet --query night
No network, no autonomous execution and no credentials required.
"""
import argparse
import json
import sys

from .portfolio_ledger import PortfolioLedger


def main(argv=None):
    parser = argparse.ArgumentParser(description="BEAN experimental portfolio learning I/O")
    parser.add_argument("command", choices=("record","context","portfolio","event","verify"))
    parser.add_argument("--db", required=True, help="Local shared SQLite research store")
    parser.add_argument("--app")
    parser.add_argument("--event-id")
    parser.add_argument("--query", default="")
    parser.add_argument("--max-bytes", type=int, default=2048)
    args = parser.parse_args(argv)
    with_store = PortfolioLedger(args.db)
    try:
        if args.command == "record":
            payload = json.load(sys.stdin)
            if not isinstance(payload,dict):
                parser.error("record input must be a JSON object")
            result = with_store.observe(**payload)
        elif args.command == "context":
            if not args.app:
                parser.error("context requires --app")
            result = with_store.state_context(
                app=args.app,query=args.query,max_bytes=args.max_bytes)
        elif args.command == "portfolio":
            result = with_store.portfolio_context(max_bytes=args.max_bytes)
        elif args.command == "event":
            if not args.app or not args.event_id:
                parser.error("event requires --app and --event-id")
            result = with_store.event(args.app,args.event_id)
        else:
            result = with_store.verify()
        print(json.dumps(result,sort_keys=True,separators=(",",":")))
    finally:
        with_store.close()


if __name__ == "__main__":
    main()
