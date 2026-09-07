"""Strands tools. Safe household busywork is automatic. Money waits for a human."""

from __future__ import annotations

from typing import Any

from strands import tool

from beforedue import store


def _dump(payload: Any) -> str:
    import json

    return json.dumps(payload, indent=2)


@tool
def list_new_inbox_items() -> str:
    """List unprocessed household items sitting in the inbox (bills, returns, warranties).

    Returns:
        JSON list of new inbox items with file names and payload fields.
    """
    items = [store.load_inbox_item(path) for path in store.list_inbox_files()]
    return _dump({"count": len(items), "items": items})


@tool
def ingest_item(
    item_id: str,
    kind: str,
    title: str,
    due_date: str,
    amount: float = 0.0,
    currency: str = "USD",
    source_file: str = "",
    notes: str = "",
) -> str:
    """Record an inbox item on the household ledger if it is not already there.

    Args:
        item_id: Stable id from the inbox file.
        kind: One of bill, return, warranty.
        title: Short human label.
        due_date: ISO date when the window closes or payment is due.
        amount: Money involved. Zero for non-payment items.
        currency: Currency code.
        source_file: Original inbox filename.
        notes: Extra context from the source item.
    """
    existing = store.get_ledger_row(item_id)
    if existing:
        return _dump({"ok": True, "already_on_ledger": True, "row": existing})
    row = store.upsert_ledger_row(
        {
            "id": item_id,
            "kind": kind,
            "title": title,
            "due_date": due_date,
            "amount": amount,
            "currency": currency,
            "source_file": source_file,
            "notes": notes,
            "status": "open",
            "days_left": store.days_until(due_date),
            "actions": [],
        }
    )
    return _dump({"ok": True, "already_on_ledger": False, "row": row})


@tool
def list_open_deadlines() -> str:
    """List open ledger items with how many days remain.

    Returns:
        JSON list of open deadlines sorted by soonest due date.
    """
    rows = []
    for row in store.load_ledger():
        if row.get("status") in {"paid", "returned", "expired", "dismissed"}:
            continue
        live = {**row, "days_left": store.days_until(row["due_date"])}
        rows.append(live)
    rows.sort(key=lambda r: r["due_date"])
    return _dump({"count": len(rows), "items": rows})


@tool
def file_safe_reminder(item_id: str, message: str) -> str:
    """File a reminder for an item. Safe. Does not spend money or start a return.

    Args:
        item_id: Ledger item id.
        message: Reminder text the household would see.
    """
    row = store.get_ledger_row(item_id)
    if not row:
        return _dump({"ok": False, "error": f"unknown item {item_id}"})
    actions = list(row.get("actions") or [])
    actions.append({"type": "reminder", "message": message, "at": store._now()})
    updated = store.upsert_ledger_row({**row, "status": "watching", "actions": actions})
    return _dump({"ok": True, "row": updated})


@tool
def start_return(item_id: str) -> str:
    """Start a product return before the window closes. No money leaves the account.

    Args:
        item_id: Ledger item id of kind 'return'.
    """
    row = store.get_ledger_row(item_id)
    if not row:
        return _dump({"ok": False, "error": f"unknown item {item_id}"})
    if row.get("kind") != "return":
        return _dump({"ok": False, "error": "start_return is only for kind=return"})
    actions = list(row.get("actions") or [])
    actions.append({"type": "return_started", "at": store._now()})
    updated = store.upsert_ledger_row({**row, "status": "returned", "actions": actions})
    return _dump({"ok": True, "row": updated})


@tool
def request_payment_approval(item_id: str) -> str:
    """Ask the human whether to pay a bill. Never pay without this decision being approved.

    Args:
        item_id: Ledger item id of kind 'bill'.
    """
    row = store.get_ledger_row(item_id)
    if not row:
        return _dump({"ok": False, "error": f"unknown item {item_id}"})
    if row.get("kind") != "bill":
        return _dump({"ok": False, "error": "payments are only for kind=bill"})
    amount = float(row.get("amount") or 0)
    question = (
        f"Pay {row.get('currency', 'USD')} {amount:.2f} for '{row['title']}' "
        f"by {row['due_date']}?"
    )
    decision = store.create_decision(item_id, question, amount, row.get("currency", "USD"))
    actions = list(row.get("actions") or [])
    actions.append({"type": "payment_asked", "decision_id": decision["id"], "at": store._now()})
    store.upsert_ledger_row({**row, "status": "needs_decision", "actions": actions})
    return _dump({"ok": True, "needs_human": True, "decision": decision})


@tool
def list_pending_decisions() -> str:
    """List payment questions waiting on a human yes/no.

    Returns:
        JSON list of pending decisions.
    """
    pending = [d for d in store.load_decisions() if d.get("status") == "pending"]
    return _dump({"count": len(pending), "decisions": pending})


@tool
def mark_item_processed(source_file: str) -> str:
    """Move an inbox file to processed after it has been ingested.

    Args:
        source_file: Filename in data/inbox, for example bill-electric.json.
    """
    path = store.INBOX / source_file
    if not path.exists():
        return _dump({"ok": False, "error": f"inbox file not found: {source_file}"})
    store.mark_processed(path)
    return _dump({"ok": True, "moved": source_file})
