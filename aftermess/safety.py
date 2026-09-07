"""Hard safety gate. Python only. Never overridden by the model or a human plea."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from aftermess.config import now_local


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"yes", "y", "true", "1"}


def _parse_dt(value: Any, tz) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt


def check_release(
    release: dict[str, Any],
    mess: dict[str, Any],
    cfg: dict[str, Any],
    now: datetime | None = None,
) -> list[str]:
    """Return refuse reasons. Empty list means the batch may enter matching."""
    reasons: list[str] = []
    current = now_local(cfg, now)

    if not (mess.get("fssai_fbo") or "").strip():
        reasons.append("mess_missing_fssai")
    if not _truthy(release.get("unused_not_served")):
        reasons.append("not_unused_unserved")
    if _truthy(release.get("unsafe")) or _truthy(release.get("spoiled")):
        reasons.append("marked_unsafe_or_spoiled")

    veg = str(release.get("veg") or "").strip().lower()
    if veg in {"mixed", "veg+nonveg", "both"}:
        if not _truthy(release.get("packed_separate")):
            reasons.append("mixed_veg_nonveg_unlabeled")
    elif veg not in {"veg", "nonveg"}:
        reasons.append("veg_tag_missing")

    dishes = str(release.get("dishes") or "").strip()
    if not dishes:
        reasons.append("food_name_missing")
    if not str(release.get("prep_at") or "").strip():
        reasons.append("prep_date_missing")
    if not str(release.get("use_by") or "").strip():
        reasons.append("use_by_missing")
    if not _truthy(release.get("packed_covered")):
        reasons.append("not_packed_covered")

    temp = release.get("temp_c")
    if temp is None or temp == "":
        reasons.append("temperature_missing")
    else:
        try:
            float(temp)
        except (TypeError, ValueError):
            reasons.append("temperature_missing")

    plates = release.get("plates")
    try:
        if int(plates) <= 0:
            reasons.append("plates_not_positive")
    except (TypeError, ValueError):
        reasons.append("plates_not_positive")

    perishable = release.get("perishable")
    if perishable is None:
        perishable = True
    else:
        perishable = _truthy(perishable)
    if perishable and cfg.get("perishable_requires_insulated", True) and not _truthy(
        release.get("insulated")
    ):
        reasons.append("perishable_without_insulated")

    use_by = _parse_dt(release.get("use_by"), current.tzinfo)
    if use_by is not None and current > use_by:
        reasons.append("past_use_by")

    prep_at = _parse_dt(release.get("prep_at"), current.tzinfo)
    hours = cfg.get("use_by_hours")
    if hours not in (None, "") and prep_at is not None:
        if current > prep_at + timedelta(hours=float(hours)):
            reasons.append("past_configured_use_by_hours")

    return reasons


def apply_gate(
    release: dict[str, Any],
    mess: dict[str, Any],
    cfg: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    reasons = check_release(release, mess, cfg, now)
    if reasons:
        return {**release, "status": "refused_unsafe", "refuse_reasons": reasons}
    return {**release, "status": "offered", "refuse_reasons": []}
