"""WhatsApp copy. Template ids stay null until a WABA is live. Never calls leftover a food sale."""

from __future__ import annotations

from typing import Any


def _name(party: dict[str, Any] | None, fallback: str) -> str:
    if not party:
        return fallback
    return party.get("display_name") or fallback


def need_ack(need: dict[str, Any]) -> str:
    policy = need.get("veg_policy") or "directory default"
    if int(need.get("plates") or 0) <= 0:
        return (
            f"Need recorded: 0 plates, {need['sitting']} {need['sitting_date']}. "
            "You will not receive food this sitting."
        )
    return (
        f"Need recorded: {need['plates']} plates, {policy.replace('_', ' ')}, "
        f"{need['sitting']} {need['sitting_date']}. Food stays free. You only pay the rider if a trip runs."
    )


def need_summary_for_mess(sitting: str, sitting_date: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "No drop sent a need."
    return (
        f"Today's {sitting} needs ({sitting_date}). This is leftover unused food only — do not cook extra.\n"
        f"{body}\n"
        "Do not reply yet. At sitting end reply RELEASE ... or NO."
    )


def release_ask(sitting: str, sitting_date: str) -> str:
    return (
        f"{sitting} {sitting_date} closeout. Release unused leftover that was never served, "
        "or reply NO.\n"
        "Format: RELEASE <plates> DISHES <names> VEG veg|nonveg UNUSED yes PREP <iso> "
        "USEBY <iso> TEMP <c> PACKED yes INSULATED yes BATCH fresh-cooked PERISHABLE yes"
    )


def release_incomplete(missing: list[str]) -> str:
    return "RELEASE is incomplete. Send all of: " + ", ".join(missing)


def unsafe_refused(reasons: list[str]) -> str:
    return (
        "This batch cannot go out. Unsafe leftover is refused with no workaround. "
        "Reasons: " + ", ".join(reasons)
    )


def match_none(sitting: str) -> str:
    return f"No {sitting} trip. Need and safe leftover did not both exist."


def rider_assign(trip: dict[str, Any], drop: dict[str, Any], messes: list[dict[str, Any]]) -> str:
    pickup = ", ".join(_name(m, m.get("id", "mess")) for m in messes)
    plates = trip.get("assigned_plates") or {}
    names = {m.get("id"): _name(m, m.get("id", "mess")) for m in messes}
    if trip.get("lat") is not None:
        named = ", ".join(f"{names.get(key, key)} {qty}" for key, qty in plates.items())
        return (
            f"Nearby leftover pickup. Food is free.\n"
            f"Pickup: {pickup}. Drop: {_name(drop, trip['drop_id'])}.\n"
            f"Plates: {trip.get('plates')} ({named})."
        )
    plate_txt = ", ".join(f"{k}:{v}" for k, v in plates.items())
    return (
        f"Campus leftover pickup (not a food sale). Reply ACCEPT or CANCEL.\n"
        f"Pickup: {pickup} (same campus). Drop: {_name(drop, trip['drop_id'])}.\n"
        f"Plates: {trip.get('plates')} ({plate_txt})."
    )


def no_rider(trip: dict[str, Any]) -> str:
    if trip.get("lat") is not None:
        return (
            "No free rider within 10 km. The leftover stays at the mess. "
            "No one is added from outside registered riders."
        )
    return (
        f"No rostered rider available for {_name(None, trip['drop_id'])}. "
        "Leftover will not be sent. No outside recruit."
    )


def request_replaced() -> str:
    return "That pickup request was updated and closed. Use the newest message only."


def pay_reminder(trip: dict[str, Any], rider: dict[str, Any], rupees: int | None) -> str:
    upi = rider.get("upi_id") or "(UPI OPEN — fill directory)"
    amount = f"INR {rupees}" if rupees not in (None, "") else "the agreed trip amount"
    who = _name(rider, trip.get("rider_id") or "rider")
    if trip.get("lat") is not None:
        return f"Food is free. Pay the rider {amount} on UPI {upi} ({who})."
    return (
        f"Food is free. Pay the rider {amount} on UPI {upi} "
        f"({who}). Reply PAID or NOT YET."
    )


def chase(what: str) -> str:
    return f"Still waiting for {what}. Reply with the keyword when done."


def clarify() -> str:
    return (
        "I did not parse that. Drops: NEED <plates> LUNCH|DINNER VEG|NONVEG|EITHER, "
        "or RECEIVED, PAID, NOT YET. Mess: RELEASE ... or NO. Riders: ACCEPT, CANCEL, PICKED, DROPPED."
    )
