"""JSON runtime store for needs, releases, trips, inbound ids, Schedule II rows."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aftermess.paths import data_dir, runtime_path
from aftermess import persist

EMPTY_RUNTIME: dict[str, Any] = {
    "needs": [],
    "releases": [],
    "trips": [],
    "sittings": [],
    "inbound_ids": [],
    "schedule_ii": [],
    "outbox": [],
    "events": [],
}

_LOCK = threading.Lock()
_pulled = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def load_runtime() -> dict[str, Any]:
    global _pulled
    with _LOCK:
        if not _pulled:
            persist.pull()
            _pulled = True
        path = runtime_path()
        if not path.exists():
            return json.loads(json.dumps(EMPTY_RUNTIME))
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, default in EMPTY_RUNTIME.items():
            data.setdefault(key, json.loads(json.dumps(default)))
        return data


def save_runtime(payload: dict[str, Any]) -> None:
    with _LOCK:
        path = runtime_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        persist.push()


def reset_runtime() -> None:
    save_runtime(json.loads(json.dumps(EMPTY_RUNTIME)))


def seen_inbound(message_id: str) -> bool:
    if not message_id:
        return False
    return message_id in load_runtime()["inbound_ids"]


def remember_inbound(message_id: str) -> None:
    if not message_id:
        return
    rt = load_runtime()
    if message_id not in rt["inbound_ids"]:
        rt["inbound_ids"].append(message_id)
        save_runtime(rt)


def append_event(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    rt = load_runtime()
    event = {"at": _now(), "kind": kind, **payload}
    rt["events"].append(event)
    save_runtime(rt)
    return event


def append_outbox(row: dict[str, Any]) -> dict[str, Any]:
    rt = load_runtime()
    rec = {"id": new_id("out"), "at": _now(), **row}
    rt["outbox"].append(rec)
    save_runtime(rt)
    return rec


def upsert_need(row: dict[str, Any]) -> dict[str, Any]:
    rt = load_runtime()
    key = (row["drop_id"], row["sitting_date"], row["sitting"])
    for i, existing in enumerate(rt["needs"]):
        if (existing["drop_id"], existing["sitting_date"], existing["sitting"]) == key:
            merged = {**existing, **row, "updated_at": _now()}
            rt["needs"][i] = merged
            save_runtime(rt)
            return merged
    row = {**row, "id": row.get("id") or new_id("need"), "created_at": _now(), "updated_at": _now()}
    rt["needs"].append(row)
    save_runtime(rt)
    return row


def upsert_release(row: dict[str, Any]) -> dict[str, Any]:
    rt = load_runtime()
    key = (row["mess_id"], row["sitting_date"], row["sitting"])
    for i, existing in enumerate(rt["releases"]):
        if (existing["mess_id"], existing["sitting_date"], existing["sitting"]) == key:
            merged = {**existing, **row, "updated_at": _now()}
            rt["releases"][i] = merged
            save_runtime(rt)
            return merged
    row = {**row, "id": row.get("id") or new_id("rel"), "created_at": _now(), "updated_at": _now()}
    rt["releases"].append(row)
    save_runtime(rt)
    return row


def get_need(drop_id: str, sitting_date: str, sitting: str) -> dict[str, Any] | None:
    for row in load_runtime()["needs"]:
        if row["drop_id"] == drop_id and row["sitting_date"] == sitting_date and row["sitting"] == sitting:
            return row
    return None


def get_release(mess_id: str, sitting_date: str, sitting: str) -> dict[str, Any] | None:
    for row in load_runtime()["releases"]:
        if row["mess_id"] == mess_id and row["sitting_date"] == sitting_date and row["sitting"] == sitting:
            return row
    return None


def needs_for(sitting_date: str, sitting: str) -> list[dict[str, Any]]:
    return [
        n
        for n in load_runtime()["needs"]
        if n["sitting_date"] == sitting_date and n["sitting"] == sitting
    ]


def releases_for(sitting_date: str, sitting: str) -> list[dict[str, Any]]:
    return [
        r
        for r in load_runtime()["releases"]
        if r["sitting_date"] == sitting_date and r["sitting"] == sitting
    ]


def trips_for(sitting_date: str, sitting: str) -> list[dict[str, Any]]:
    return [
        t
        for t in load_runtime()["trips"]
        if t["sitting_date"] == sitting_date and t["sitting"] == sitting
    ]


def delete_trip(trip_id: str) -> None:
    rt = load_runtime()
    rt["trips"] = [row for row in rt["trips"] if row["id"] != trip_id]
    save_runtime(rt)


def get_trip(trip_id: str) -> dict[str, Any] | None:
    for row in load_runtime()["trips"]:
        if row["id"] == trip_id:
            return row
    return None


def upsert_trip(row: dict[str, Any]) -> dict[str, Any]:
    rt = load_runtime()
    if "id" not in row:
        row["id"] = new_id("trip")
    for i, existing in enumerate(rt["trips"]):
        if existing["id"] == row["id"]:
            merged = {**existing, **row, "updated_at": _now()}
            rt["trips"][i] = merged
            save_runtime(rt)
            return merged
    row = {**row, "created_at": _now(), "updated_at": _now()}
    rt["trips"].append(row)
    save_runtime(rt)
    return row


def active_trips_for_rider(rider_id: str) -> list[dict[str, Any]]:
    terminal = {"settled", "no_rider", "no_match", "unsafe_refused"}
    return [
        t
        for t in load_runtime()["trips"]
        if t.get("rider_id") == rider_id and t.get("state") not in terminal
    ]


def open_trips_for_drop(drop_id: str) -> list[dict[str, Any]]:
    terminal = {"settled", "no_rider", "no_match", "unsafe_refused"}
    return [
        t
        for t in load_runtime()["trips"]
        if t.get("drop_id") == drop_id and t.get("state") not in terminal
    ]


def get_sitting(sitting_date: str, sitting: str) -> dict[str, Any]:
    rt = load_runtime()
    for row in rt["sittings"]:
        if row["sitting_date"] == sitting_date and row["sitting"] == sitting:
            return row
    row = {
        "id": new_id("sit"),
        "sitting_date": sitting_date,
        "sitting": sitting,
        "need_summary_sent_at": None,
        "release_ask_sent_at": None,
        "matched_at": None,
        "match_result": None,
        "created_at": _now(),
    }
    rt["sittings"].append(row)
    save_runtime(rt)
    return row


def upsert_sitting(row: dict[str, Any]) -> dict[str, Any]:
    rt = load_runtime()
    for i, existing in enumerate(rt["sittings"]):
        if existing["sitting_date"] == row["sitting_date"] and existing["sitting"] == row["sitting"]:
            merged = {**existing, **row, "updated_at": _now()}
            rt["sittings"][i] = merged
            save_runtime(rt)
            return merged
    row = {**row, "id": row.get("id") or new_id("sit"), "created_at": _now()}
    rt["sittings"].append(row)
    save_runtime(rt)
    return row


def append_schedule_ii(row: dict[str, Any]) -> dict[str, Any]:
    rt = load_runtime()
    rec = {**row, "id": row.get("id") or new_id("sii"), "written_at": _now()}
    rt["schedule_ii"].append(rec)
    save_runtime(rt)
    return rec


def schedule_ii_for_trip(trip_id: str) -> list[dict[str, Any]]:
    return [r for r in load_runtime()["schedule_ii"] if r.get("trip_id") == trip_id]


def data_dir_str() -> str:
    return str(data_dir())
