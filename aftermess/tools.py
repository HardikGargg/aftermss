"""Strands tools. Matching, safety, roster, and Schedule II stay in Python."""

from __future__ import annotations

import json
from typing import Any

from strands import tool

from aftermess import loop, store
from aftermess.export import export_files, write_schedule_ii_for_trip
from aftermess.notify import emit
from aftermess.parse import parse_inbound


def _dump(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


@tool
def record_need(
    drop_id: str,
    plates: int,
    sitting: str,
    sitting_date: str = "",
    veg_policy: str = "",
    dishes: str = "",
) -> str:
    """Record a drop's plate need for lunch or dinner. Does not send food."""
    result = loop.record_need(
        drop_id,
        int(plates),
        sitting,
        sitting_date=sitting_date or None,
        veg_policy=veg_policy or None,
        dishes=dishes or None,
    )
    return _dump(result)


@tool
def record_mess_release(
    mess_id: str,
    sitting: str,
    plates: int,
    dishes: str,
    veg: str,
    unused_not_served: bool,
    prep_at: str,
    use_by: str,
    temp_c: float,
    packed_covered: bool,
    insulated: bool,
    sitting_date: str = "",
    batch: str = "fresh-cooked",
    perishable: bool = True,
    kg: float = -1.0,
) -> str:
    """Record a mess RELEASE. The safety gate may refuse the batch. Never override a refuse."""
    payload = {
        "plates": int(plates),
        "dishes": dishes,
        "veg": veg,
        "unused_not_served": unused_not_served,
        "prep_at": prep_at,
        "use_by": use_by,
        "temp_c": temp_c,
        "packed_covered": packed_covered,
        "insulated": insulated,
        "batch": batch,
        "perishable": perishable,
        "kg": None if kg < 0 else kg,
    }
    result = loop.record_mess_release(mess_id, payload, sitting, sitting_date=sitting_date or None)
    return _dump(result)


@tool
def record_mess_no(mess_id: str, sitting: str, sitting_date: str = "") -> str:
    """Record that a mess has no leftover this sitting."""
    return _dump(loop.record_mess_no(mess_id, sitting, sitting_date=sitting_date or None))


@tool
def run_safety_and_match(sitting: str, sitting_date: str = "") -> str:
    """Run the hard safety gate and fill-one-drop match. Python math only. Then assign a rostered rider."""
    return _dump(loop.run_safety_and_match(sitting, sitting_date=sitting_date or None))


@tool
def assign_next_rider(trip_id: str) -> str:
    """Walk the named rider roster. No gig recruit."""
    return _dump(loop.assign_next_rider(trip_id))


@tool
def record_rider_accept(rider_id: str, trip_id: str = "") -> str:
    """Rider accepted the assigned trip."""
    return _dump(loop.record_rider_accept(rider_id, trip_id or None))


@tool
def record_rider_cancel(rider_id: str, trip_id: str = "") -> str:
    """Rider cancelled. Assign the next rostered rider."""
    return _dump(loop.record_rider_cancel(rider_id, trip_id or None))


@tool
def record_picked(rider_id: str, trip_id: str = "") -> str:
    """Rider picked up at campus (one stop even if two messes)."""
    return _dump(loop.record_picked(rider_id, trip_id or None))


@tool
def record_dropped(rider_id: str, trip_id: str = "") -> str:
    """Rider dropped containers at the kitchen."""
    return _dump(loop.record_dropped(rider_id, trip_id or None))


@tool
def record_received(drop_id: str, trip_id: str = "") -> str:
    """Kitchen received the batch. Writes Schedule II, then reminds rider pay. Never skip this before pay."""
    return _dump(loop.record_received(drop_id, trip_id or None))


@tool
def remind_rider_pay(trip_id: str) -> str:
    """UPI reminder to the drop. Only after RECEIVED. Agent does not collect money."""
    return _dump(loop.remind_rider_pay(trip_id))


@tool
def record_paid(drop_id: str, trip_id: str = "") -> str:
    """Drop confirmed the rider was paid on UPI."""
    return _dump(loop.record_paid(drop_id, trip_id or None))


@tool
def export_schedule_ii(sitting: str, sitting_date: str) -> str:
    """Write Schedule II JSON/sheet and Eat Right evidence for one sitting."""
    trips = store.trips_for(sitting_date, sitting)
    for trip in trips:
        if trip.get("received_at"):
            write_schedule_ii_for_trip(trip["id"])
    paths = export_files(sitting_date, sitting)
    return _dump({"ok": True, **paths})


@tool
def sitting_status(sitting: str, sitting_date: str = "") -> str:
    """Plates needed, released, moved, unmatched, plus trip states."""
    from aftermess.config import sitting_date_str

    date = sitting_date or sitting_date_str()
    return _dump(loop.sitting_status(date, sitting))


@tool
def send_whatsapp(party_id: str, body: str, template_key: str = "") -> str:
    """Send a WhatsApp (or simulator outbox) message. Do not describe leftover as a paid food order."""
    rec = emit(party_id, body, template_key=template_key or None)
    return _dump({"ok": True, "outbox": rec})


@tool
def parse_party_text(text: str) -> str:
    """Parse a WhatsApp body into a structured intent. If ambiguous, ask a closed follow-up. Do not guess plates."""
    parsed = parse_inbound(text)
    return _dump(parsed)
