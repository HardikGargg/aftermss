"""Sitting loop: inbound keywords, tick phases, timeouts. Safety and match stay in Python."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from aftermess import messages, store
from aftermess.config import (
    get_party,
    load_config,
    load_directory,
    now_local,
    roster_ids,
    sitting_date_str,
)
from aftermess.match import plan_trips
from aftermess.notify import emit
from aftermess.parse import parse_inbound
from aftermess.safety import apply_gate

SITTINGS = {"lunch", "dinner"}


def _campus_locked(party_id: str, sitting_row: dict[str, Any]) -> bool:
    """The closed campus demo locks a sitting after match. Registered messes stay open."""
    if not sitting_row.get("matched_at"):
        return False
    from aftermess.accounts import is_registered

    return not is_registered(party_id)
PROOF_STATES = {
    "awaiting_pickup": ("picked", "PICKED"),
    "awaiting_drop": ("dropped", "DROPPED"),
    "awaiting_received": ("received", "RECEIVED"),
    "awaiting_pay": ("paid", "PAID"),
    "awaiting_rider": ("rider_accept", "ACCEPT"),
}


def _cfg_now(now: datetime | None) -> tuple[dict[str, Any], datetime]:
    cfg = load_config()
    return cfg, now_local(cfg, now)


def _require_sitting(sitting: str | None, parsed_sitting: str | None) -> str | None:
    value = (parsed_sitting or sitting or "").lower()
    if value in SITTINGS:
        return value
    return None


def sitting_status(sitting_date: str, sitting: str) -> dict[str, Any]:
    needs = store.needs_for(sitting_date, sitting)
    releases = store.releases_for(sitting_date, sitting)
    trips = store.trips_for(sitting_date, sitting)
    needed = sum(int(n.get("plates") or 0) for n in needs)
    released = sum(int(r.get("plates") or 0) for r in releases if r.get("status") == "offered")
    refused = [r for r in releases if r.get("status") == "refused_unsafe"]
    none = [r for r in releases if r.get("status") == "none"]
    moved = sum(int(t.get("plates") or 0) for t in trips if t.get("state") not in {"no_match", "no_rider"})
    unmatched = max(released - moved, 0)
    return {
        "sitting_date": sitting_date,
        "sitting": sitting,
        "sitting_row": store.get_sitting(sitting_date, sitting),
        "plates_needed": needed,
        "plates_released": released,
        "plates_moved": moved,
        "plates_unmatched": unmatched,
        "needs": needs,
        "releases": releases,
        "trips": trips,
        "unsafe_refused": refused,
        "mess_no": none,
        "schedule_ii": [
            row
            for trip in trips
            for row in store.schedule_ii_for_trip(trip["id"])
        ],
    }


def record_need(
    drop_id: str,
    plates: int,
    sitting: str,
    sitting_date: str | None = None,
    veg_policy: str | None = None,
    dishes: str | None = None,
    raw_message_id: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    row = store.upsert_need(
        {
            "drop_id": drop_id,
            "sitting_date": sitting_date,
            "sitting": sitting,
            "plates": int(plates),
            "veg_policy": veg_policy,
            "dishes": dishes,
            "raw_message_id": raw_message_id,
        }
    )
    emit(drop_id, messages.need_ack(row))
    return {"ok": True, "need": row}


def record_mess_no(
    mess_id: str,
    sitting: str,
    sitting_date: str | None = None,
    now: datetime | None = None,
    raw_message_id: str = "",
) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    sit = store.get_sitting(sitting_date, sitting)
    if _campus_locked(mess_id, sit):
        return {"ok": False, "error": "already_matched"}
    row = store.upsert_release(
        {
            "mess_id": mess_id,
            "sitting_date": sitting_date,
            "sitting": sitting,
            "plates": 0,
            "status": "none",
            "raw_message_id": raw_message_id,
        }
    )
    emit(mess_id, "Recorded NO leftover this sitting.")
    return {"ok": True, "release": row}


def record_mess_release(
    mess_id: str,
    payload: dict[str, Any],
    sitting: str,
    sitting_date: str | None = None,
    now: datetime | None = None,
    raw_message_id: str = "",
) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    directory = load_directory()
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    sit = store.get_sitting(sitting_date, sitting)
    if _campus_locked(mess_id, sit):
        return {"ok": False, "error": "already_matched"}
    mess = get_party(mess_id, directory)
    row = {
        "mess_id": mess_id,
        "sitting_date": sitting_date,
        "sitting": sitting,
        "plates": payload.get("plates"),
        "dishes": payload.get("dishes"),
        "veg": payload.get("veg"),
        "unused_not_served": payload.get("unused_not_served"),
        "prep_at": payload.get("prep_at"),
        "use_by": payload.get("use_by"),
        "temp_c": payload.get("temp_c"),
        "packed_covered": payload.get("packed_covered"),
        "insulated": payload.get("insulated"),
        "batch": payload.get("batch") or "fresh-cooked",
        "perishable": True if payload.get("perishable") is None else payload.get("perishable"),
        "kg": payload.get("kg"),
        "unsafe": payload.get("unsafe"),
        "spoiled": payload.get("spoiled"),
        "packed_separate": payload.get("packed_separate"),
        "source": mess.get("display_name"),
        "raw_message_id": raw_message_id,
    }
    gated = apply_gate(row, mess, cfg, current)
    saved = store.upsert_release(gated)
    if saved.get("status") == "refused_unsafe":
        emit(mess_id, messages.unsafe_refused(saved.get("refuse_reasons") or []))
        return {"ok": True, "release": saved, "refused": True}
    emit(
        mess_id,
        f"RELEASE recorded: {saved.get('plates')} plates, {saved.get('veg')}, "
        f"{saved.get('dishes')}. Waiting for match at closeout.",
    )
    return {"ok": True, "release": saved, "refused": False}


def _timeout_as_no(sitting_date: str, sitting: str, now: datetime) -> None:
    cfg = load_config()
    minutes = (cfg.get("timeouts_minutes") or {}).get("mess_release")
    sit = store.get_sitting(sitting_date, sitting)
    asked = sit.get("release_ask_sent_at")
    if minutes in (None, "") or not asked:
        return
    asked_dt = datetime.fromisoformat(asked)
    if now_local(cfg, now) < asked_dt + timedelta(minutes=int(minutes)):
        return
    directory = load_directory()
    for mess in directory.get("messes") or []:
        existing = store.get_release(mess["id"], sitting_date, sitting)
        if existing:
            continue
        store.upsert_release(
            {
                "mess_id": mess["id"],
                "sitting_date": sitting_date,
                "sitting": sitting,
                "plates": 0,
                "status": "none",
                "timeout": True,
            }
        )


def assign_next_rider(trip_id: str) -> dict[str, Any]:
    directory = load_directory()
    trip = store.get_trip(trip_id)
    if not trip:
        return {"ok": False, "error": "unknown_trip"}
    if trip.get("state") not in {"draft_match", "awaiting_rider"}:
        return {"ok": False, "error": f"bad_state_{trip.get('state')}"}
    tried = list(trip.get("rider_attempts") or [])
    busy = set()
    for other in store.load_runtime()["trips"]:
        if other["id"] == trip_id:
            continue
        if other.get("rider_id") and other.get("state") not in {
            "settled",
            "no_rider",
            "no_match",
            "unsafe_refused",
        }:
            busy.add(other["rider_id"])
    chosen = None
    if trip.get("lat") is not None and trip.get("lng") is not None:
        from aftermess.accounts import nearby_rider_ids

        rider_order = nearby_rider_ids(float(trip["lat"]), float(trip["lng"]))
    else:
        rider_order = roster_ids(directory)
    for rider_id in rider_order:
        rider = get_party(rider_id, directory)
        if not rider.get("active", True):
            continue
        if rider_id in tried or rider_id in busy:
            continue
        chosen = rider_id
        break
    if not chosen:
        trip = store.upsert_trip(
            {
                **trip,
                "state": "no_rider",
                "rider_id": None,
            }
        )
        drop_id = trip["drop_id"]
        emit(drop_id, messages.no_rider(trip))
        for mess_id in trip.get("mess_ids") or []:
            emit(mess_id, messages.no_rider(trip))
        return {"ok": True, "trip": trip, "no_rider": True}

    tried.append(chosen)
    trip = store.upsert_trip(
        {
            **trip,
            "state": "awaiting_rider",
            "rider_id": chosen,
            "rider_attempts": tried,
            "assigned_at": store._now(),
        }
    )
    drop = get_party(trip["drop_id"], directory)
    messes = [get_party(mid, directory) for mid in trip.get("mess_ids") or []]
    emit(
        chosen,
        messages.rider_assign(trip, drop, messes),
        template_key="rider_assign",
    )
    return {"ok": True, "trip": trip}


def run_safety_and_match(
    sitting: str,
    sitting_date: str | None = None,
    now: datetime | None = None,
    force: bool = False,
) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    directory = load_directory()
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    sit = store.get_sitting(sitting_date, sitting)
    if sit.get("matched_at"):
        return {"ok": True, "already_matched": True, "trips": store.trips_for(sitting_date, sitting)}

    _timeout_as_no(sitting_date, sitting, current)
    pending = [
        mess["id"]
        for mess in directory.get("messes") or []
        if store.get_release(mess["id"], sitting_date, sitting) is None
    ]
    if pending and not force:
        return {"ok": False, "error": "waiting_for_mess", "pending": pending}

    for rel in store.releases_for(sitting_date, sitting):
        if rel.get("status") in {"none", "refused_unsafe", "offered"}:
            continue
        mess = get_party(rel["mess_id"], directory)
        gated = apply_gate(rel, mess, cfg, current)
        store.upsert_release(gated)
        if gated.get("status") == "refused_unsafe":
            emit(rel["mess_id"], messages.unsafe_refused(gated.get("refuse_reasons") or []))

    needs = store.needs_for(sitting_date, sitting)
    releases = store.releases_for(sitting_date, sitting)
    planned = plan_trips(needs, releases, directory)
    if not planned:
        store.upsert_sitting({**sit, "matched_at": store._now(), "match_result": "no_match"})
        for need in needs:
            if int(need.get("plates") or 0) > 0:
                emit(need["drop_id"], messages.match_none(sitting))
        return {"ok": True, "trips": [], "match_result": "no_match"}

    trips = []
    for draft in planned:
        trip = store.upsert_trip(
            {
                **draft,
                "sitting_date": sitting_date,
                "sitting": sitting,
                "chases": {},
                "pay_reminders": 0,
            }
        )
        result = assign_next_rider(trip["id"])
        trips.append(result.get("trip") or trip)
        drop = get_party(draft["drop_id"], directory)
        plate_txt = ", ".join(f"{k}:{v}" for k, v in (draft.get("assigned_plates") or {}).items())
        emit(
            draft["drop_id"],
            f"Match: {draft['plates']} plates to {drop.get('display_name')} from {plate_txt}. "
            "Food is free. Wait for pickup.",
        )
        for mess_id, qty in (draft.get("assigned_plates") or {}).items():
            emit(
                mess_id,
                f"Pack {qty} unused plates for {drop.get('display_name')}. Hand to the assigned rider only.",
            )
    store.upsert_sitting({**sit, "matched_at": store._now(), "match_result": "matched"})
    return {"ok": True, "trips": trips, "match_result": "matched"}


def record_rider_accept(rider_id: str, trip_id: str | None = None) -> dict[str, Any]:
    trip = _rider_trip(rider_id, trip_id, "awaiting_rider")
    if not trip:
        return {"ok": False, "error": "no_awaiting_rider_trip"}
    if trip.get("rider_id") != rider_id:
        return {"ok": False, "error": "not_your_trip"}
    trip = store.upsert_trip({**trip, "state": "awaiting_pickup", "accepted_at": store._now()})
    if trip.get("lat") is not None:
        emit(rider_id, "Accepted. Mark picked up when you have the covered containers.")
    else:
        emit(rider_id, "Accepted. Reply PICKED when you have the covered containers at campus.")
    return {"ok": True, "trip": trip}


def record_rider_cancel(rider_id: str, trip_id: str | None = None) -> dict[str, Any]:
    trip = _rider_trip(rider_id, trip_id, "awaiting_rider")
    if not trip:
        trip = _rider_trip(rider_id, trip_id, "awaiting_pickup")
    if not trip:
        return {"ok": False, "error": "no_cancellable_trip"}
    if trip.get("state") not in {"awaiting_rider", "awaiting_pickup"}:
        return {"ok": False, "error": "too_late_to_cancel"}
    trip = store.upsert_trip(
        {**trip, "state": "awaiting_rider", "rider_id": None, "cancelled_by": rider_id}
    )
    emit(rider_id, "Cancelled. Another rostered rider will be asked.")
    return assign_next_rider(trip["id"])


def record_picked(rider_id: str, trip_id: str | None = None) -> dict[str, Any]:
    trip = _rider_trip(rider_id, trip_id, "awaiting_pickup")
    if not trip:
        return {"ok": False, "error": "no_awaiting_pickup_trip"}
    trip = store.upsert_trip({**trip, "state": "awaiting_drop", "picked_at": store._now()})
    if trip.get("lat") is not None:
        emit(rider_id, "Pickup recorded. Mark dropped off at the NGO.")
    else:
        emit(rider_id, "Pickup recorded (one campus stop). Reply DROPPED at the kitchen.")
    return {"ok": True, "trip": trip}


def record_dropped(rider_id: str, trip_id: str | None = None) -> dict[str, Any]:
    trip = _rider_trip(rider_id, trip_id, "awaiting_drop")
    if not trip:
        return {"ok": False, "error": "no_awaiting_drop_trip"}
    trip = store.upsert_trip({**trip, "state": "awaiting_received", "dropped_at": store._now()})
    if trip.get("lat") is not None:
        emit(rider_id, "Drop recorded. Waiting for the NGO to confirm.")
        emit(trip["drop_id"], "Rider reports dropped. Confirm when the covered containers are with you.")
    else:
        emit(rider_id, "Drop recorded. Waiting for the kitchen to reply RECEIVED.")
        emit(trip["drop_id"], "Rider reports dropped. Reply RECEIVED if the covered containers are with you.")
    return {"ok": True, "trip": trip}


def record_received(drop_id: str, trip_id: str | None = None) -> dict[str, Any]:
    trip = _drop_trip(drop_id, trip_id, "awaiting_received")
    if not trip:
        return {"ok": False, "error": "no_awaiting_received_trip"}
    trip = store.upsert_trip({**trip, "state": "awaiting_pay", "received_at": store._now()})
    from aftermess.export import write_schedule_ii_for_trip

    rows = write_schedule_ii_for_trip(trip["id"])
    remind_rider_pay(trip["id"])
    return {"ok": True, "trip": store.get_trip(trip["id"]), "schedule_ii": rows}


def remind_rider_pay(trip_id: str) -> dict[str, Any]:
    cfg = load_config()
    directory = load_directory()
    trip = store.get_trip(trip_id)
    if not trip:
        return {"ok": False, "error": "unknown_trip"}
    if trip.get("state") != "awaiting_pay":
        return {"ok": False, "error": "pay_only_after_received"}
    max_n = int(cfg.get("pay_reminder_max") or 2)
    count = int(trip.get("pay_reminders") or 0)
    if count >= max_n:
        trip = store.upsert_trip({**trip, "state": "stuck", "stuck_reason": "pay_unconfirmed"})
        return {"ok": True, "trip": trip, "stuck": True}
    rider = get_party(trip["rider_id"], directory)
    emit(
        trip["drop_id"],
        messages.pay_reminder(trip, rider, cfg.get("trip_rupees")),
        template_key="pay_reminder",
    )
    trip = store.upsert_trip(
        {**trip, "pay_reminders": count + 1, "pay_reminded_at": store._now()}
    )
    return {"ok": True, "trip": trip}


def record_paid(drop_id: str, trip_id: str | None = None) -> dict[str, Any]:
    trip = _drop_trip(drop_id, trip_id, "awaiting_pay")
    if not trip:
        return {"ok": False, "error": "no_awaiting_pay_trip"}
    trip = store.upsert_trip({**trip, "state": "settled", "paid_at": store._now()})
    emit(drop_id, "Payment marked. Trip settled. Thank you.")
    if trip.get("rider_id"):
        emit(trip["rider_id"], "Drop marked PAID.")
    return {"ok": True, "trip": trip}


def record_not_yet(drop_id: str, trip_id: str | None = None) -> dict[str, Any]:
    trip = _drop_trip(drop_id, trip_id, "awaiting_pay")
    if not trip:
        return {"ok": False, "error": "no_awaiting_pay_trip"}
    return remind_rider_pay(trip["id"])


def tick_needs_cutoff(sitting: str, sitting_date: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    directory = load_directory()
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    sit = store.get_sitting(sitting_date, sitting)
    needs = store.needs_for(sitting_date, sitting)
    lines = []
    for need in needs:
        drop = get_party(need["drop_id"], directory)
        lines.append(
            f"- {drop.get('display_name')}: {need.get('plates')} plates "
            f"({need.get('veg_policy') or drop.get('veg_policy')})"
        )
    body = messages.need_summary_for_mess(sitting, sitting_date, lines)
    sent = []
    for mess in directory.get("messes") or []:
        sent.append(emit(mess["id"], body, template_key="need_reminder"))
    store.upsert_sitting({**sit, "need_summary_sent_at": store._now()})
    return {"ok": True, "sent": len(sent), "needs": needs}


def tick_closeout(sitting: str, sitting_date: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    directory = load_directory()
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    sit = store.get_sitting(sitting_date, sitting)
    body = messages.release_ask(sitting, sitting_date)
    for mess in directory.get("messes") or []:
        emit(mess["id"], body, template_key="mess_release_ask")
    store.upsert_sitting({**sit, "release_ask_sent_at": store._now()})
    return {"ok": True, "asked": [m["id"] for m in directory.get("messes") or []]}


def _minutes(cfg: dict[str, Any], key: str) -> int | None:
    val = (cfg.get("timeouts_minutes") or {}).get(key)
    if val in (None, ""):
        return None
    return int(val)


def _elapsed(start: str | None, minutes: int | None, now: datetime, cfg: dict[str, Any]) -> bool:
    if not start or minutes is None:
        return False
    started = datetime.fromisoformat(start)
    if started.tzinfo is None:
        started = started.replace(tzinfo=now.tzinfo)
    return now_local(cfg, now) >= started + timedelta(minutes=minutes)


def tick_chase(sitting: str, sitting_date: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    acted = []
    for trip in store.trips_for(sitting_date, sitting):
        state = trip.get("state")
        if state not in PROOF_STATES:
            continue
        timeout_key, keyword = PROOF_STATES[state]
        minutes = _minutes(cfg, timeout_key)
        start = {
            "awaiting_rider": trip.get("assigned_at"),
            "awaiting_pickup": trip.get("accepted_at"),
            "awaiting_drop": trip.get("picked_at"),
            "awaiting_received": trip.get("dropped_at"),
            "awaiting_pay": trip.get("pay_reminded_at") or trip.get("received_at"),
        }.get(state)
        if not _elapsed(start, minutes, current, cfg):
            continue
        chases = dict(trip.get("chases") or {})
        bucket = dict(chases.get(state) or {})
        if not bucket.get("sent_at"):
            target = trip.get("rider_id") if state in {"awaiting_rider", "awaiting_pickup", "awaiting_drop"} else trip.get("drop_id")
            if target:
                emit(target, messages.chase(keyword), template_key="proof_chase")
            if state == "awaiting_pay":
                remind_rider_pay(trip["id"])
            bucket["sent_at"] = store._now()
            bucket["count"] = int(bucket.get("count") or 0) + 1
            chases[state] = bucket
            store.upsert_trip({**trip, "chases": chases})
            acted.append({"trip_id": trip["id"], "chase": state})
        else:
            store.upsert_trip({**trip, "state": "stuck", "stuck_reason": f"timeout_{state}"})
            acted.append({"trip_id": trip["id"], "stuck": state})
    return {"ok": True, "acted": acted}


def infer_phase(sitting: str, sitting_date: str | None, now: datetime | None) -> str | None:
    cfg, current = _cfg_now(now)
    clocks = cfg.get("clocks") or {}
    cutoff = clocks.get(f"{sitting}_need_cutoff")
    end = clocks.get(f"{sitting}_end")
    if not cutoff and not end:
        return None
    hhmm = current.strftime("%H:%M")
    sit = store.get_sitting(sitting_date or sitting_date_str(cfg, current), sitting)
    if cutoff and hhmm >= cutoff[:5] and not sit.get("need_summary_sent_at"):
        return "needs_cutoff"
    if end and hhmm >= end[:5] and not sit.get("release_ask_sent_at"):
        return "closeout"
    if sit.get("release_ask_sent_at") and not sit.get("matched_at"):
        releases = store.releases_for(sit["sitting_date"], sitting)
        mess_n = len(load_directory().get("messes") or [])
        if len(releases) >= mess_n:
            return "match"
        minutes = _minutes(cfg, "mess_release")
        if minutes is not None and _elapsed(sit.get("release_ask_sent_at"), minutes, current, cfg):
            return "match"
    return "chase"


def tick(
    sitting: str,
    phase: str | None = None,
    sitting_date: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    cfg, current = _cfg_now(now)
    sitting_date = sitting_date or sitting_date_str(cfg, current)
    phase = phase or infer_phase(sitting, sitting_date, current)
    if not phase:
        return {
            "ok": False,
            "error": "phase_required",
            "detail": "Clocks are OPEN/null. Pass --phase needs_cutoff|closeout|match|chase.",
        }
    if phase == "needs_cutoff":
        return {"phase": phase, **tick_needs_cutoff(sitting, sitting_date, current)}
    if phase == "closeout":
        return {"phase": phase, **tick_closeout(sitting, sitting_date, current)}
    if phase == "match":
        return {"phase": phase, **run_safety_and_match(sitting, sitting_date, current)}
    if phase == "chase":
        return {"phase": phase, **tick_chase(sitting, sitting_date, current)}
    return {"ok": False, "error": f"unknown_phase_{phase}"}


def _rider_trip(rider_id: str, trip_id: str | None, state: str) -> dict[str, Any] | None:
    if trip_id:
        trip = store.get_trip(trip_id)
        if trip and trip.get("state") == state:
            return trip
        return None
    found = [
        t
        for t in store.load_runtime()["trips"]
        if t.get("rider_id") == rider_id and t.get("state") == state
    ]
    return found[-1] if found else None


def open_closeout_sitting() -> tuple[str, str] | None:
    rows = [
        s
        for s in store.load_runtime()["sittings"]
        if s.get("release_ask_sent_at") and not s.get("matched_at")
    ]
    rows.sort(key=lambda s: s.get("release_ask_sent_at") or "")
    if not rows:
        return None
    last = rows[-1]
    return last["sitting_date"], last["sitting"]


def _drop_trip(drop_id: str, trip_id: str | None, state: str) -> dict[str, Any] | None:
    if trip_id:
        trip = store.get_trip(trip_id)
        if trip and trip.get("drop_id") == drop_id and trip.get("state") == state:
            return trip
        return None
    found = [
        t
        for t in store.load_runtime()["trips"]
        if t.get("drop_id") == drop_id and t.get("state") == state
    ]
    return found[-1] if found else None


def handle_inbound(
    party_id: str,
    text: str,
    message_id: str = "",
    sitting: str | None = None,
    sitting_date: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if message_id and store.seen_inbound(message_id):
        return {"ok": True, "duplicate": True, "message_id": message_id}
    if message_id:
        store.remember_inbound(message_id)

    directory = load_directory()
    party = get_party(party_id, directory)
    parsed = parse_inbound(text)
    intent = parsed.get("intent")
    role = party["role"]
    cfg, current = _cfg_now(now)
    sitting_date = sitting_date or sitting_date_str(cfg, current)

    if intent == "ambiguous":
        emit(party_id, messages.clarify())
        return {"ok": True, "ambiguous": True, "parse": parsed}

    if role == "drop" and intent == "need":
        sit = _require_sitting(sitting, parsed.get("sitting"))
        if not sit:
            emit(party_id, "Which sitting? Send NEED <plates> LUNCH|DINNER VEG|NONVEG|EITHER")
            return {"ok": False, "error": "sitting_required", "parse": parsed}
        return record_need(
            party_id,
            int(parsed["plates"]),
            sit,
            sitting_date=sitting_date,
            veg_policy=parsed.get("veg_policy"),
            dishes=parsed.get("dishes"),
            raw_message_id=message_id,
            now=current,
        )
    if role == "drop" and intent == "received":
        return record_received(party_id)
    if role == "drop" and intent == "paid":
        return record_paid(party_id)
    if role == "drop" and intent == "not_yet":
        return record_not_yet(party_id)

    if role == "mess" and intent in {"mess_no", "release", "release_incomplete"}:
        inferred = open_closeout_sitting()
        sit = _require_sitting(sitting, None)
        date_for = sitting_date
        if not sit and inferred:
            date_for, sit = inferred
        if intent == "release_incomplete":
            emit(party_id, messages.release_incomplete(parsed.get("missing") or []))
            return {"ok": True, "incomplete": True, "missing": parsed.get("missing")}
        if not sit:
            emit(party_id, "No open closeout. Wait for the RELEASE ask, or the operator must tick --phase closeout.")
            return {"ok": False, "error": "sitting_required"}
        if intent == "mess_no":
            return record_mess_no(
                party_id, sit, sitting_date=date_for, now=current, raw_message_id=message_id
            )
        return record_mess_release(
            party_id,
            parsed,
            sit,
            sitting_date=date_for,
            now=current,
            raw_message_id=message_id,
        )

    if role == "rider" and intent == "accept":
        return record_rider_accept(party_id)
    if role == "rider" and intent == "cancel":
        return record_rider_cancel(party_id)
    if role == "rider" and intent == "picked":
        return record_picked(party_id)
    if role == "rider" and intent == "dropped":
        return record_dropped(party_id)

    emit(party_id, messages.clarify())
    return {"ok": False, "error": "wrong_role_for_intent", "role": role, "intent": intent}
