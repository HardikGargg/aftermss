"""Open signup closeout: nearby need, safe release, nearest rider."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from aftermess import messages, store
from aftermess.accounts import as_party, list_rows, nearby_rider_ids, row_by_id
from aftermess.config import get_party, load_config, sitting_date_str
from aftermess.geo import haversine, nearby_km
from aftermess.loop import (
    assign_next_rider,
    record_dropped,
    record_mess_no,
    record_mess_release,
    record_need,
    record_paid,
    record_picked,
    record_received,
    record_rider_accept,
    record_rider_cancel,
)
from aftermess.match import plan_trips
from aftermess.notify import emit

_LOCK = threading.Lock()
UNSTARTED = {"draft_match", "awaiting_rider", "no_rider"}
QUIET = UNSTARTED | {"no_match", "unsafe_refused"}
BUSY_DONE = {"settled", "no_rider", "no_match", "unsafe_refused"}

REASONS = {
    "mess_missing_fssai": "The mess FSSAI number is missing.",
    "not_unused_unserved": "Only unused food that was never served can go out.",
    "marked_unsafe_or_spoiled": "The batch was marked unsafe or spoiled.",
    "mixed_veg_nonveg_unlabeled": "Veg and non-veg must be packed separately.",
    "veg_tag_missing": "Say whether the food is veg or non-veg.",
    "food_name_missing": "Add the dish names.",
    "prep_date_missing": "Add when the food was prepared.",
    "use_by_missing": "Add the use-by time.",
    "not_packed_covered": "The food must be packed and covered.",
    "temperature_missing": "Add the temperature.",
    "plates_not_positive": "Plate count must be at least 1.",
    "perishable_without_insulated": "Perishable food must be insulated.",
    "past_use_by": "This batch is past its use-by time.",
    "past_configured_use_by_hours": "This batch is older than the allowed hours.",
}

STATE_LABEL = {
    "draft_match": "Matching",
    "awaiting_rider": "Waiting for the rider to accept",
    "awaiting_pickup": "Rider accepted. Pickup is next.",
    "awaiting_drop": "Picked up. On the way to the NGO.",
    "awaiting_received": "Dropped. The NGO needs to confirm.",
    "awaiting_pay": "The NGO has the food. Pay the rider on UPI.",
    "settled": "Paid and closed.",
    "no_rider": "No free rider within 10 km.",
    "stuck": "This trip needs a person to step in.",
}

ACTIONS = {
    "accept": "Accept",
    "cancel": "Cancel",
    "picked": "Picked up",
    "dropped": "Dropped off",
    "received": "I received the food",
    "paid": "I paid the rider",
}

VEG_LABEL = {
    "veg_only": "veg only",
    "nonveg_ok": "veg or non-veg",
    "nonveg_only": "non-veg only",
    "veg": "veg",
    "nonveg": "non-veg",
}

LOOP_ERRORS = {
    "already_matched": "This sitting is already closed.",
    "no_awaiting_rider_trip": "There is no trip waiting for you to accept.",
    "not_your_trip": "This trip is assigned to another rider.",
    "no_cancellable_trip": "This trip can no longer be cancelled.",
    "too_late_to_cancel": "This trip can no longer be cancelled.",
    "no_awaiting_pickup_trip": "Pickup is not waiting on you.",
    "no_awaiting_drop_trip": "Drop-off is not waiting on you.",
    "no_awaiting_received_trip": "The rider has not marked this dropped yet.",
    "no_awaiting_pay_trip": "Payment is not waiting on this trip.",
    "unknown_trip": "That trip does not exist.",
}


def _flag(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _with_tz(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.endswith("Z") or "+" in text[10:] or (len(text) > 19 and text.count("-") > 2):
        return text
    if len(text) == 16:
        text += ":00"
    return text + "+05:30"


def _sitting(value: str) -> str:
    sitting = str(value or "").strip().lower()
    if sitting not in {"lunch", "dinner"}:
        raise ValueError("Choose lunch or dinner.")
    return sitting


def _plates(value: Any) -> int:
    try:
        plates = int(value)
    except (TypeError, ValueError):
        raise ValueError("Enter a plate count.") from None
    if plates < 1 or plates > 500:
        raise ValueError("Plate count must be from 1 to 500.")
    return plates


def _clock(now: datetime | None) -> tuple[dict[str, Any], datetime, str]:
    cfg = load_config()
    from aftermess.config import now_local

    current = now_local(cfg, now)
    return cfg, current, sitting_date_str(cfg, current)


def _directory() -> dict[str, Any]:
    messes, drops, riders = [], [], []
    index: dict[str, dict[str, Any]] = {}
    for row in list_rows():
        party = as_party(row)
        index[party["id"]] = party
        if row["role"] == "mess":
            messes.append(party)
        elif row["role"] == "ngo":
            drops.append(party)
        else:
            riders.append(party)
    return {
        "messes": messes,
        "drops": drops,
        "riders": riders,
        "rider_ids_in_order": [rider["id"] for rider in riders],
        "index": index,
    }


def _signature(obj: dict[str, Any]) -> tuple:
    assigned = tuple(
        sorted((str(key), int(qty)) for key, qty in (obj.get("assigned_plates") or {}).items())
    )
    return (obj.get("drop_id"), int(obj.get("plates") or 0), assigned)


def _busy(except_trip_id: str) -> set[str]:
    busy: set[str] = set()
    for other in store.load_runtime()["trips"]:
        if other["id"] == except_trip_id:
            continue
        if other.get("rider_id") and other.get("state") not in BUSY_DONE:
            busy.add(other["rider_id"])
    return busy


def _name(party_id: str, index: dict[str, dict[str, Any]]) -> str:
    party = index.get(party_id)
    if party:
        return party.get("display_name") or party_id
    try:
        return get_party(party_id).get("display_name") or party_id
    except KeyError:
        return party_id


def _retire(trip: dict[str, Any]) -> None:
    rider_id = trip.get("rider_id")
    if rider_id and trip.get("state") == "awaiting_rider":
        emit(rider_id, messages.request_replaced())
    store.delete_trip(trip["id"])


def _announce(trip: dict[str, Any], directory: dict[str, Any]) -> None:
    index = directory["index"]
    drop = index.get(trip["drop_id"]) or {}
    plate_txt = ", ".join(
        f"{_name(mess_id, index)} {qty}" for mess_id, qty in (trip.get("assigned_plates") or {}).items()
    )
    emit(
        trip["drop_id"],
        f"Match: {trip.get('plates')} free plates from {plate_txt}. "
        "A nearby rider has been asked. You pay only the rider, on UPI, after the food arrives.",
    )
    for mess_id, qty in (trip.get("assigned_plates") or {}).items():
        emit(
            mess_id,
            f"Pack {qty} unused plates for {drop.get('display_name') or trip['drop_id']}. "
            "Hand them only to the assigned rider.",
        )


def _open_trip(
    draft: dict[str, Any],
    sitting: str,
    sitting_date: str,
    directory: dict[str, Any],
) -> dict[str, Any]:
    assigned = draft.get("assigned_plates") or {}
    anchor_id = max(assigned, key=lambda mess_id: (int(assigned[mess_id]), str(mess_id)))
    anchor = directory["index"].get(anchor_id) or {}
    trip = store.upsert_trip(
        {
            **draft,
            "sitting": sitting,
            "sitting_date": sitting_date,
            "lat": anchor.get("lat"),
            "lng": anchor.get("lng"),
            "chases": {},
            "pay_reminders": 0,
            "state": "draft_match",
        }
    )
    result = assign_next_rider(trip["id"])
    saved = result.get("trip") or store.get_trip(trip["id"]) or trip
    if not result.get("no_rider"):
        _announce(saved, directory)
    return saved


def _retry(trip: dict[str, Any]) -> dict[str, Any] | None:
    if trip.get("lat") is None or trip.get("lng") is None:
        return None
    order = nearby_rider_ids(float(trip["lat"]), float(trip["lng"]))
    tried = set(trip.get("rider_attempts") or [])
    busy = _busy(trip["id"])
    if not any(rider_id not in tried and rider_id not in busy for rider_id in order):
        return None
    store.upsert_trip({**trip, "state": "draft_match", "rider_id": None})
    result = assign_next_rider(trip["id"])
    return result.get("trip")


def _match_unlocked(sitting: str, sitting_date: str) -> dict[str, Any]:
    directory = _directory()
    drop_ids = {drop["id"] for drop in directory["drops"]}
    mess_ids = {mess["id"] for mess in directory["messes"]}
    if not drop_ids or not mess_ids:
        return {"ok": True, "opened": [], "kept": 0, "match_result": "waiting"}

    needs = [row for row in store.needs_for(sitting_date, sitting) if row.get("drop_id") in drop_ids]
    releases = []
    for row in store.releases_for(sitting_date, sitting):
        if row.get("mess_id") not in mess_ids or row.get("status") != "offered":
            continue
        mess = directory["index"][row["mess_id"]]
        releases.append({**row, "lat": mess.get("lat"), "lng": mess.get("lng")})

    trips = [row for row in store.trips_for(sitting_date, sitting) if row.get("drop_id") in drop_ids]
    committed = [row for row in trips if row.get("state") not in QUIET]
    used: dict[str, int] = {}
    covered: dict[str, int] = {}
    for trip in committed:
        covered[trip["drop_id"]] = covered.get(trip["drop_id"], 0) + int(trip.get("plates") or 0)
        for mess_id, qty in (trip.get("assigned_plates") or {}).items():
            used[mess_id] = used.get(mess_id, 0) + int(qty)

    pool_releases = []
    for rel in releases:
        left = int(rel.get("plates") or 0) - used.get(rel["mess_id"], 0)
        if left <= 0:
            continue
        pool_releases.append({**rel, "plates": left, "plates_remaining": left, "status": "offered"})
    pool_needs = []
    for need in needs:
        left = int(need.get("plates") or 0) - covered.get(need["drop_id"], 0)
        if left <= 0:
            continue
        pool_needs.append({**need, "plates": left})

    planned = plan_trips(pool_needs, pool_releases, directory)
    planned_left = {_signature(draft): draft for draft in planned}
    unstarted = [row for row in trips if row.get("state") in UNSTARTED]
    unstarted.sort(key=lambda row: (row.get("state") == "no_rider", row.get("created_at") or ""))

    kept: list[dict[str, Any]] = []
    for trip in unstarted:
        key = _signature(trip)
        if key in planned_left:
            kept.append(trip)
            del planned_left[key]
        else:
            _retire(trip)

    opened = [
        _open_trip(draft, sitting, sitting_date, directory) for draft in planned_left.values()
    ]
    for trip in kept:
        fresh = store.get_trip(trip["id"])
        if fresh and fresh.get("state") == "no_rider":
            _retry(fresh)
    return {
        "ok": True,
        "opened": opened,
        "kept": len(kept),
        "match_result": "matched" if opened or kept else "no_match",
    }


def match_posted(sitting: str, sitting_date: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    _, _, today = _clock(now)
    with _LOCK:
        return _match_unlocked(sitting, sitting_date or today)


def _mess_committed(mess_id: str, sitting: str, sitting_date: str) -> bool:
    for trip in store.trips_for(sitting_date, sitting):
        if trip.get("state") in QUIET:
            continue
        if int((trip.get("assigned_plates") or {}).get(mess_id) or 0) > 0:
            return True
    return False


def _human_reasons(codes: list[str]) -> list[str]:
    return [REASONS.get(code, code) for code in codes]


def _result_or_raise(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("ok"):
        return result
    code = str(result.get("error") or "could_not_save")
    raise ValueError(LOOP_ERRORS.get(code, "That step could not be saved."))


def post_need(
    row: dict[str, Any],
    *,
    plates: Any,
    sitting: str,
    veg_policy: str | None = None,
    now: datetime | None = None,
    sitting_date: str | None = None,
) -> dict[str, Any]:
    if row.get("role") != "ngo":
        raise PermissionError("Only an NGO can ask for plates.")
    sitting = _sitting(sitting)
    count = _plates(plates)
    _, current, today = _clock(now)
    date = sitting_date or today
    policy = veg_policy or row.get("veg_policy") or "veg_only"
    if policy not in {"veg_only", "nonveg_ok", "nonveg_only"}:
        raise ValueError("Choose veg only, non-veg only, or either.")
    with _LOCK:
        existing = store.get_need(row["id"], date, sitting)
        if existing and int(existing.get("plates") or 0) > 0:
            raise ValueError("You already asked for plates this sitting.")
        saved = record_need(
            row["id"],
            count,
            sitting,
            sitting_date=date,
            veg_policy=policy,
            now=current,
        )
        _result_or_raise(saved)
        need = saved["need"]
        store.upsert_need({**need, "lat": row.get("lat"), "lng": row.get("lng")})
        match = _match_unlocked(sitting, date)
    if not match["opened"] and not match["kept"]:
        message = "Request saved. No nearby mess has released safe leftover yet."
    else:
        message = _joined("Request saved.", match)
    return {"ok": True, "message": message}


def post_release(
    row: dict[str, Any],
    payload: dict[str, Any],
    *,
    sitting: str,
    now: datetime | None = None,
    sitting_date: str | None = None,
) -> dict[str, Any]:
    if row.get("role") != "mess":
        raise PermissionError("Only a mess can release leftover.")
    sitting = _sitting(sitting)
    _, current, today = _clock(now)
    date = sitting_date or today
    body = {
        "plates": _plates(payload.get("plates")),
        "dishes": str(payload.get("dishes") or "").strip(),
        "veg": str(payload.get("veg") or row.get("veg_policy") or "").strip().lower(),
        "unused_not_served": _flag(payload.get("unused_not_served")),
        "prep_at": _with_tz(payload.get("prep_at")),
        "use_by": _with_tz(payload.get("use_by")),
        "temp_c": payload.get("temp_c"),
        "packed_covered": _flag(payload.get("packed_covered")),
        "insulated": _flag(payload.get("insulated")),
        "perishable": _flag(payload.get("perishable"), default=True),
        "batch": str(payload.get("batch") or "fresh-cooked"),
        "unsafe": _flag(payload.get("unsafe")),
        "spoiled": _flag(payload.get("spoiled")),
    }
    with _LOCK:
        if _mess_committed(row["id"], sitting, date):
            raise ValueError("A rider already accepted these plates. This sitting cannot be changed.")
        saved = record_mess_release(row["id"], body, sitting, sitting_date=date, now=current)
        _result_or_raise(saved)
        release = saved.get("release") or {}
        if release:
            store.upsert_release({**release, "lat": row.get("lat"), "lng": row.get("lng")})
        refused = bool(saved.get("refused"))
        match = _match_unlocked(sitting, date)
    if refused:
        text = " ".join(_human_reasons(release.get("refuse_reasons") or []))
        return {"ok": False, "message": f"This food cannot go out. {text}".strip()}
    if not match["opened"] and not match["kept"]:
        message = "Leftover recorded. No nearby NGO has asked for plates yet."
    else:
        message = _joined("Leftover recorded.", match)
    return {"ok": True, "message": message}


def post_no(
    row: dict[str, Any],
    *,
    sitting: str,
    now: datetime | None = None,
    sitting_date: str | None = None,
) -> dict[str, Any]:
    if row.get("role") != "mess":
        raise PermissionError("Only a mess can say there is no leftover.")
    sitting = _sitting(sitting)
    _, current, today = _clock(now)
    date = sitting_date or today
    with _LOCK:
        if _mess_committed(row["id"], sitting, date):
            raise ValueError("A rider already accepted these plates. This sitting cannot be changed.")
        saved = record_mess_no(row["id"], sitting, sitting_date=date, now=current)
        _result_or_raise(saved)
        _match_unlocked(sitting, date)
    return {"ok": True, "message": "Recorded: no leftover this sitting."}


def _joined(prefix: str, match: dict[str, Any]) -> str:
    parts = []
    for trip in match.get("opened") or []:
        count = trip.get("plates")
        if trip.get("state") == "no_rider":
            parts.append(
                f"{count} plates are ready, but no rider is free within {int(nearby_km())} km."
            )
        else:
            parts.append(f"{count} plates matched. The nearest rider has been asked.")
    if not parts and match.get("kept"):
        return f"{prefix} The nearby trip is unchanged."
    if not parts:
        return prefix
    return f"{prefix} {' '.join(parts)}"


def retry_unassigned() -> None:
    with _LOCK:
        for trip in store.load_runtime()["trips"]:
            if trip.get("state") == "no_rider" and trip.get("lat") is not None:
                _retry(trip)


def act(row: dict[str, Any], trip_id: str, action: str) -> dict[str, Any]:
    action = str(action or "").strip().lower()
    if action not in ACTIONS:
        raise ValueError("That action is not available.")
    trip = store.get_trip(trip_id)
    if not trip:
        raise ValueError("That trip does not exist.")
    role = row.get("role")
    if action in {"accept", "cancel", "picked", "dropped"}:
        if role != "rider" or trip.get("rider_id") != row.get("id"):
            raise PermissionError("Only the assigned rider can do that.")
        fn = {
            "accept": record_rider_accept,
            "cancel": record_rider_cancel,
            "picked": record_picked,
            "dropped": record_dropped,
        }[action]
        result = fn(row["id"], trip_id)
    else:
        if role != "ngo" or trip.get("drop_id") != row.get("id"):
            raise PermissionError("Only the NGO on this trip can do that.")
        fn = {"received": record_received, "paid": record_paid}[action]
        result = fn(row["id"], trip_id)
    _result_or_raise(result)
    fresh = store.get_trip(trip_id) or result.get("trip") or {}
    return {"ok": True, "message": STATE_LABEL.get(fresh.get("state"), "Saved."), "state": fresh.get("state")}


def _actions(row: dict[str, Any], trip: dict[str, Any]) -> list[dict[str, str]]:
    role = row.get("role")
    state = trip.get("state")
    ids: list[str] = []
    if role == "rider" and trip.get("rider_id") == row.get("id"):
        if state == "awaiting_rider":
            ids = ["accept", "cancel"]
        elif state == "awaiting_pickup":
            ids = ["picked", "cancel"]
        elif state == "awaiting_drop":
            ids = ["dropped"]
    if role == "ngo" and trip.get("drop_id") == row.get("id"):
        if state == "awaiting_received":
            ids = ["received"]
        elif state == "awaiting_pay":
            ids = ["paid"]
    return [{"id": action, "label": ACTIONS[action]} for action in ids]


def _trip_card(row: dict[str, Any], trip: dict[str, Any], index: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    assigned = trip.get("assigned_plates") or {}
    drop_name = _name(trip.get("drop_id") or "", index)
    rider_row = row_by_id(trip.get("rider_id") or "")
    rider_name = (rider_row or {}).get("display_name") or ""
    from_line = ", ".join(
        f"{_name(mess_id, index)} · {qty} plates" for mess_id, qty in assigned.items()
    )
    state = trip.get("state") or ""
    pack = ""
    pay = ""
    qty = int(assigned.get(row["id"]) or 0)
    if row.get("role") == "mess" and qty and state not in {"no_rider", "no_match"}:
        pack = f"Pack {qty} unused plates. Hand them only to the rider."
    upi = (rider_row or {}).get("upi_id") or ""
    rupees = cfg.get("trip_rupees")
    if state == "awaiting_pay" and row.get("role") == "ngo" and upi:
        fare = f"INR {rupees} " if rupees not in (None, "") else ""
        pay = (
            f"Pay {rider_name or 'the rider'} {fare}on UPI {upi}. "
            "This is the trip fare, not a price for the food."
        )
    elif state == "awaiting_pay" and row.get("role") == "rider":
        pay = "Waiting for the NGO to mark paid."
    return {
        "id": trip["id"],
        "state": state,
        "state_label": STATE_LABEL.get(state, state),
        "plates": trip.get("plates"),
        "title": f"{trip.get('plates')} plates for {drop_name}",
        "from": from_line,
        "rider": rider_name or ("No rider yet" if state == "no_rider" else "Rider not assigned"),
        "pack": pack,
        "pay": pay,
        "actions": _actions(row, trip),
    }


def _mess_record(row: dict[str, Any]) -> dict[str, Any]:
    """Plates the NGO actually received, plus the Schedule II rows for this mess."""
    fssai = str(row.get("fssai") or "").strip()
    matched = []
    for rec in store.load_runtime().get("schedule_ii") or []:
        if rec.get("mess_id") == row["id"] or (fssai and rec.get("donor_fssai") == fssai):
            matched.append(rec)
    plates = sum(int(rec.get("quantity_donated_plates") or 0) for rec in matched)
    public = []
    for rec in reversed(matched):
        when = str(rec.get("distribution_date") or rec.get("sitting_date") or "")
        public.append(
            {
                "date": when[:10],
                "sitting": rec.get("sitting") or "",
                "kitchen": rec.get("sfdo_name") or "",
                "food": rec.get("food_name") or "",
                "plates": int(rec.get("quantity_donated_plates") or 0),
                "temp_c": rec.get("temperature_c") if rec.get("temperature_c") is not None else rec.get("temp_c"),
            }
        )
    return {
        "plates_handed_over": plates,
        "row_count": len(public),
        "item_7": plates > 0,
        "rows": public[:20],
    }


def _note(other: dict[str, Any], sitting: str, sitting_date: str) -> str:
    if other["role"] == "rider":
        return "Rider"
    if other["role"] == "ngo":
        need = store.get_need(other["id"], sitting_date, sitting)
        if need and int(need.get("plates") or 0) > 0:
            return f"Asked for {need['plates']} {sitting} plates"
        return "No request yet"
    release = store.get_release(other["id"], sitting_date, sitting)
    if not release:
        return "No release yet"
    if release.get("status") == "offered":
        return f"Offered {release.get('plates')} plates"
    if release.get("status") == "none":
        return "No leftover today"
    if release.get("status") == "refused_unsafe":
        return "Release refused"
    return "No release yet"


def board(row: dict[str, Any], sitting: str, now: datetime | None = None) -> dict[str, Any]:
    sitting = _sitting(sitting)
    cfg, _, today = _clock(now)
    directory = _directory()
    index = directory["index"]
    limit = nearby_km()
    nearby = []
    for other in list_rows():
        if other["id"] == row["id"]:
            continue
        if other["role"] == row["role"]:
            continue
        try:
            distance = haversine(float(row["lat"]), float(row["lng"]), float(other["lat"]), float(other["lng"]))
        except (TypeError, ValueError):
            continue
        if distance > limit:
            continue
        nearby.append(
            {
                "id": other["id"],
                "role": other["role"],
                "display_name": other["display_name"],
                "area": other.get("area") or "",
                "distance_km": round(distance, 1),
                "veg_policy": VEG_LABEL.get(other.get("veg_policy") or "", ""),
                "note": _note(other, sitting, today),
            }
        )
    nearby.sort(key=lambda item: (item["distance_km"], item["display_name"]))

    need = store.get_need(row["id"], today, sitting) if row["role"] == "ngo" else None
    release = store.get_release(row["id"], today, sitting) if row["role"] == "mess" else None
    need_text = ""
    if need and int(need.get("plates") or 0) > 0:
        policy = VEG_LABEL.get(need.get("veg_policy") or "", "plates")
        need_text = f"You asked for {need['plates']} plates, {policy}, {sitting}."
    release_text = ""
    release_open = True
    if release:
        status = release.get("status")
        if status == "offered":
            release_text = (
                f"You offered {release.get('plates')} {release.get('veg') or ''} plates "
                f"({release.get('dishes') or 'food'})."
            ).replace("  ", " ")
            release_open = False
        elif status == "none":
            release_text = "You said there is no leftover this sitting."
            release_open = False
        elif status == "refused_unsafe":
            release_text = "This food cannot go out. " + " ".join(
                _human_reasons(release.get("refuse_reasons") or [])
            )

    trips = []
    for trip in store.trips_for(today, sitting):
        involved = False
        if row["role"] == "ngo" and trip.get("drop_id") == row["id"]:
            involved = True
        elif row["role"] == "rider" and trip.get("rider_id") == row["id"]:
            involved = True
        elif row["role"] == "mess" and int((trip.get("assigned_plates") or {}).get(row["id"]) or 0) > 0:
            involved = True
        if involved:
            trips.append(_trip_card(row, trip, index, cfg))

    updates = [
        item.get("body") or ""
        for item in store.load_runtime().get("outbox", [])
        if item.get("party_id") == row["id"]
    ]
    updates = [text for text in updates if text][-8:]
    updates.reverse()
    me = {
        "id": row["id"],
        "role": row["role"],
        "display_name": row["display_name"],
        "phone": row.get("phone") or "",
        "area": row.get("area") or "",
        "veg_policy": row.get("veg_policy") or "",
        "fssai": row.get("fssai") or "",
    }
    if row["role"] == "rider":
        me["upi_id"] = row.get("upi_id") or ""
    return {
        "ok": True,
        "me": me,
        "sitting": sitting,
        "sitting_date": today,
        "nearby_km": limit,
        "nearby": nearby,
        "need_text": need_text,
        "need_open": not need_text,
        "release_text": release_text,
        "release_open": release_open,
        "trips": trips,
        "updates": updates,
        "record": _mess_record(row) if row["role"] == "mess" else None,
    }
