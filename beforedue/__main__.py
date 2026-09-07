"""CLI: simulate the product loop without an LLM, or run the real Strands agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beforedue import store
from beforedue.tools import (
    file_safe_reminder,
    ingest_item,
    list_new_inbox_items,
    list_open_deadlines,
    list_pending_decisions,
    mark_item_processed,
    request_payment_approval,
    start_return,
)


def _call(fn, **kwargs):
    """Strands @tool objects are callable; fall back to the wrapped function."""
    if kwargs:
        try:
            return fn(**kwargs)
        except TypeError:
            inner = getattr(fn, "func", None) or getattr(fn, "__wrapped__", None)
            if inner:
                return inner(**kwargs)
            raise
    try:
        return fn()
    except TypeError:
        inner = getattr(fn, "func", None) or getattr(fn, "__wrapped__", None)
        if inner:
            return inner()
        raise


def _print(title: str, payload: str) -> None:
    print(f"\n=== {title} ===")
    print(payload)


def simulate() -> None:
    """Deterministic walk of the same tools the Strands agent uses. No model needed."""
    _print("inbox", _call(list_new_inbox_items))
    for path in store.list_inbox_files():
        item = store.load_inbox_item(path)
        _print(
            f"ingest {path.name}",
            _call(
                ingest_item,
                item_id=item["id"],
                kind=item["kind"],
                title=item["title"],
                due_date=item["due_date"],
                amount=float(item.get("amount") or 0),
                currency=item.get("currency", "USD"),
                source_file=path.name,
                notes=item.get("notes", ""),
            ),
        )
        kind = item["kind"]
        if kind == "bill":
            _print("ask human", _call(request_payment_approval, item_id=item["id"]))
        elif kind == "return":
            _print("start return", _call(start_return, item_id=item["id"]))
        else:
            _print(
                "reminder",
                _call(
                    file_safe_reminder,
                    item_id=item["id"],
                    message=f"Warranty/window for {item['title']} closes {item['due_date']}.",
                ),
            )
        _print("processed", _call(mark_item_processed, source_file=path.name))
    _print("open deadlines", _call(list_open_deadlines))
    _print("pending human decisions", _call(list_pending_decisions))


def run_agent() -> None:
    from beforedue.agent import SCAN_PROMPT, build_agent

    agent = build_agent()
    result = agent(SCAN_PROMPT)
    print("\n=== pending decisions ===")
    print(_call(list_pending_decisions))
    if hasattr(result, "metrics"):
        print("\n=== metrics ===")
        print(json.dumps(result.metrics.get_summary(), indent=2, default=str)[:4000])


def decide(decision_id: str, action: str) -> None:
    resolution = "approved" if action == "approve" else "rejected"
    decision = store.resolve_decision_row(decision_id, resolution)
    row = store.get_ledger_row(decision["item_id"])
    if row and resolution == "approved":
        actions = list(row.get("actions") or [])
        actions.append({"type": "paid", "decision_id": decision_id, "at": store._now()})
        store.upsert_ledger_row({**row, "status": "paid", "actions": actions})
    elif row:
        actions = list(row.get("actions") or [])
        actions.append({"type": "payment_rejected", "decision_id": decision_id, "at": store._now()})
        store.upsert_ledger_row({**row, "status": "dismissed", "actions": actions})
    print(json.dumps(decision, indent=2))


def status() -> None:
    print(_call(list_open_deadlines))
    print(_call(list_pending_decisions))


def main() -> None:
    parser = argparse.ArgumentParser(description="BeforeDue household agent")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("simulate", help="run the product loop with no LLM")
    sub.add_parser("run", help="run the Strands agent against the inbox")
    sub.add_parser("status", help="print ledger and pending decisions")
    d = sub.add_parser("decide", help="approve or reject a payment")
    d.add_argument("--id", required=True)
    d.add_argument("--action", choices=["approve", "reject"], required=True)
    args = parser.parse_args()
    if args.cmd == "simulate":
        simulate()
    elif args.cmd == "run":
        run_agent()
    elif args.cmd == "status":
        status()
    elif args.cmd == "decide":
        decide(args.id, args.action)


if __name__ == "__main__":
    main()
