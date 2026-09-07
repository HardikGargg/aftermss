"""Local JSON store for inbox items, the household ledger, and human decisions.

This is the stand-in for email / SES / DynamoDB. Same tool surface either way.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INBOX = DATA / "inbox"
PROCESSED = DATA / "processed"
LEDGER_PATH = DATA / "ledger.json"
DECISIONS_PATH = DATA / "decisions.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> date:
    return date.today()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def days_until(iso_date: str) -> int:
    due = date.fromisoformat(iso_date[:10])
    return (due - _today()).days


def list_inbox_files() -> list[Path]:
    INBOX.mkdir(parents=True, exist_ok=True)
    return sorted(p for p in INBOX.glob("*.json") if p.is_file())


def load_inbox_item(path: Path) -> dict[str, Any]:
    item = json.loads(path.read_text(encoding="utf-8"))
    item["_source_file"] = path.name
    return item


def mark_processed(path: Path) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    target = PROCESSED / path.name
    path.replace(target)


def load_ledger() -> list[dict[str, Any]]:
    return _read_json(LEDGER_PATH, [])


def save_ledger(rows: list[dict[str, Any]]) -> None:
    _write_json(LEDGER_PATH, rows)


def upsert_ledger_row(row: dict[str, Any]) -> dict[str, Any]:
    rows = load_ledger()
    item_id = row["id"]
    for i, existing in enumerate(rows):
        if existing["id"] == item_id:
            rows[i] = {**existing, **row, "updated_at": _now()}
            save_ledger(rows)
            return rows[i]
    row = {**row, "created_at": _now(), "updated_at": _now()}
    rows.append(row)
    save_ledger(rows)
    return row


def get_ledger_row(item_id: str) -> dict[str, Any] | None:
    for row in load_ledger():
        if row["id"] == item_id:
            return row
    return None


def load_decisions() -> list[dict[str, Any]]:
    return _read_json(DECISIONS_PATH, [])


def save_decisions(rows: list[dict[str, Any]]) -> None:
    _write_json(DECISIONS_PATH, rows)


def create_decision(item_id: str, question: str, amount: float, currency: str) -> dict[str, Any]:
    rows = load_decisions()
    for existing in rows:
        if existing["item_id"] == item_id and existing["status"] == "pending":
            return existing
    decision = {
        "id": str(uuid4())[:8],
        "item_id": item_id,
        "question": question,
        "amount": amount,
        "currency": currency,
        "status": "pending",
        "created_at": _now(),
        "resolved_at": None,
        "resolution": None,
    }
    rows.append(decision)
    save_decisions(rows)
    return decision


def get_decision(decision_id: str) -> dict[str, Any] | None:
    for row in load_decisions():
        if row["id"] == decision_id:
            return row
    return None


def resolve_decision_row(decision_id: str, resolution: str) -> dict[str, Any]:
    if resolution not in {"approved", "rejected"}:
        raise ValueError("resolution must be 'approved' or 'rejected'")
    rows = load_decisions()
    for i, row in enumerate(rows):
        if row["id"] == decision_id:
            if row["status"] != "pending":
                raise ValueError(f"decision {decision_id} is already {row['status']}")
            rows[i] = {
                **row,
                "status": resolution,
                "resolution": resolution,
                "resolved_at": _now(),
            }
            save_decisions(rows)
            return rows[i]
    raise KeyError(f"unknown decision {decision_id}")
