"""Locked lunch demo used by CLI and the public live URL."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from aftermess import store
from aftermess.export import export_files
from aftermess.loop import handle_inbound, sitting_status, tick
from aftermess.paths import data_dir

DEMO_NOW = "2026-09-08T14:30:00+05:30"
DEMO_DATE = "2026-09-08"
DEMO_SITTING = "lunch"


def _release(plates: int, dishes: str) -> str:
    return (
        f"RELEASE {plates} DISHES {dishes} VEG veg UNUSED yes "
        "PREP 2026-09-08T13:00:00+05:30 USEBY 2026-09-08T18:00:00+05:30 "
        "TEMP 65 PACKED yes INSULATED yes BATCH fresh-cooked PERISHABLE yes"
    )


def run_locked_demo() -> dict[str, Any]:
    store.reset_runtime()
    now = datetime.fromisoformat(DEMO_NOW)
    steps: list[dict[str, Any]] = []

    def inbound(party: str, text: str) -> dict[str, Any]:
        result = handle_inbound(
            party,
            text,
            message_id=store.new_id("msg"),
            sitting=DEMO_SITTING,
            sitting_date=DEMO_DATE,
            now=now,
        )
        steps.append({"party": party, "text": text, "result": result})
        return result

    inbound("drop_a", "NEED 40 LUNCH VEG")
    inbound("drop_b", "NEED 20 LUNCH EITHER")
    steps.append({"tick": "needs_cutoff", "result": tick(DEMO_SITTING, "needs_cutoff", DEMO_DATE, now)})
    steps.append({"tick": "closeout", "result": tick(DEMO_SITTING, "closeout", DEMO_DATE, now)})
    inbound("mess_a", _release(15, "dal,rice,roti"))
    inbound("mess_b", _release(20, "dal,sabzi,roti"))
    steps.append({"tick": "match", "result": tick(DEMO_SITTING, "match", DEMO_DATE, now)})
    inbound("rider_1", "CANCEL")
    inbound("rider_2", "ACCEPT")
    inbound("rider_2", "PICKED")
    inbound("rider_2", "DROPPED")
    inbound("drop_a", "RECEIVED")
    inbound("drop_a", "PAID")
    status = sitting_status(DEMO_DATE, DEMO_SITTING)
    exports = export_files(DEMO_DATE, DEMO_SITTING)
    return {
        "ok": True,
        "data_dir": str(data_dir()),
        "status": status,
        "exports": exports,
        "steps": steps,
        "outbox": store.load_runtime().get("outbox", []),
    }
