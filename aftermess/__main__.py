"""CLI: simulate WhatsApp keywords, tick sitting phases, dump ledger, optional live webhook/agent."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aftermess import store
from aftermess.config import sitting_date_str
from aftermess.export import export_files
from aftermess.loop import handle_inbound, sitting_status, tick


def _print(title: str, payload: object) -> None:
    print(f"\n=== {title} ===")
    if isinstance(payload, str):
        print(payload)
        return
    print(json.dumps(payload, indent=2, default=str))


def _now(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def _last_outbox(n: int = 12) -> list:
    return store.load_runtime().get("outbox", [])[-n:]


def cmd_reset() -> None:
    store.reset_runtime()
    print(f"runtime cleared at {store.runtime_path()}")


def cmd_inbound(args: argparse.Namespace) -> None:
    result = handle_inbound(
        args.party,
        args.text,
        message_id=args.message_id or store.new_id("msg"),
        sitting=args.sitting,
        sitting_date=args.date,
        now=_now(args.now),
    )
    _print("result", result)
    _print("outbox", _last_outbox())


def cmd_tick(args: argparse.Namespace) -> None:
    result = tick(
        args.sitting,
        phase=args.phase,
        sitting_date=args.date,
        now=_now(args.now),
    )
    _print("tick", result)
    _print("outbox", _last_outbox())


def cmd_status(args: argparse.Namespace) -> None:
    date = args.date or sitting_date_str(now=_now(args.now))
    _print("status", sitting_status(date, args.sitting))


def cmd_export(args: argparse.Namespace) -> None:
    date = args.date or sitting_date_str(now=_now(args.now))
    _print("export", export_files(date, args.sitting))


def cmd_outbox() -> None:
    _print("outbox", store.load_runtime().get("outbox", []))


def cmd_run(args: argparse.Namespace) -> None:
    from aftermess.agent import build_agent, tick_prompt

    date = args.date or sitting_date_str(now=_now(args.now))
    agent = build_agent()
    result = agent(tick_prompt(args.sitting, date, args.phase))
    _print("agent", str(result))
    _print("status", sitting_status(date, args.sitting))


def cmd_webhook(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run(
        "aftermess.server:get_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_demo() -> None:
    from aftermess.demo import run_locked_demo

    result = run_locked_demo()
    _print("status", result["status"])
    _print("export", result["exports"])
    print(f"\nData dir: {result['data_dir']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AfterMess IIITD leftover closeout")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("reset", help="clear runtime ledger")
    sub.add_parser("demo", help="run the locked lunch demo script (no LLM, no live WhatsApp)")
    sub.add_parser("outbox", help="print simulated WhatsApp outbox")

    inn = sub.add_parser("inbound", help="simulate one WhatsApp body from a party id")
    inn.add_argument("--party", required=True, help="mess_a, drop_a, rider_1, ...")
    inn.add_argument("--text", required=True)
    inn.add_argument("--sitting", choices=["lunch", "dinner"])
    inn.add_argument("--date")
    inn.add_argument("--now")
    inn.add_argument("--message-id")

    tk = sub.add_parser("tick", help="run a sitting phase")
    tk.add_argument("--sitting", required=True, choices=["lunch", "dinner"])
    tk.add_argument("--phase", choices=["needs_cutoff", "closeout", "match", "chase"])
    tk.add_argument("--date")
    tk.add_argument("--now")

    st = sub.add_parser("status", help="print sitting ledger")
    st.add_argument("--sitting", required=True, choices=["lunch", "dinner"])
    st.add_argument("--date")
    st.add_argument("--now")

    ex = sub.add_parser("export", help="write Schedule II + Eat Right files")
    ex.add_argument("--sitting", required=True, choices=["lunch", "dinner"])
    ex.add_argument("--date")
    ex.add_argument("--now")

    rn = sub.add_parser("run", help="Strands agent tick (needs a model)")
    rn.add_argument("--sitting", required=True, choices=["lunch", "dinner"])
    rn.add_argument("--phase", choices=["needs_cutoff", "closeout", "match", "chase"])
    rn.add_argument("--date")
    rn.add_argument("--now")

    wh = sub.add_parser("webhook", help="live WhatsApp webhook (FastAPI)")
    wh.add_argument("--host", default="0.0.0.0")
    wh.add_argument("--port", type=int, default=8080)
    wh.add_argument("--reload", action="store_true")

    args = parser.parse_args()
    if args.cmd == "reset":
        cmd_reset()
    elif args.cmd == "demo":
        cmd_demo()
    elif args.cmd == "outbox":
        cmd_outbox()
    elif args.cmd == "inbound":
        cmd_inbound(args)
    elif args.cmd == "tick":
        cmd_tick(args)
    elif args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "export":
        cmd_export(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "webhook":
        cmd_webhook(args)


if __name__ == "__main__":
    main()
