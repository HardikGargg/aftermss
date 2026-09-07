"""Inbound WhatsApp keyword parser. Ambiguous text is not guessed."""

from __future__ import annotations

import re
from typing import Any

_SITTING = r"(LUNCH|DINNER)"
_VEG = r"(VEG|NONVEG|EITHER)"

NEED_ZERO = re.compile(rf"^NEED\s+0(?:\s+{_SITTING})?$", re.IGNORECASE)
NEED = re.compile(
    rf"^NEED\s+(\d+)\s+{_SITTING}(?:\s+{_VEG})?(?:\s+(.*))?$",
    re.IGNORECASE,
)
RELEASE_HEAD = re.compile(r"^RELEASE(?:\s+NO)?(?:\s+(\d+))?(?:\s+(.*))?$", re.IGNORECASE)

YES_WORDS = {"yes", "y", "true", "1"}
NO_WORDS = {"no", "n", "false", "0"}

VEG_MAP = {
    "veg": "veg_only",
    "nonveg": "nonveg_only",
    "either": "nonveg_ok",
}

SIMPLE = {
    "RECEIVED": {"intent": "received"},
    "PAID": {"intent": "paid"},
    "NOT YET": {"intent": "not_yet"},
    "NOTYET": {"intent": "not_yet"},
    "ACCEPT": {"intent": "accept"},
    "CANCEL": {"intent": "cancel"},
    "PICKED": {"intent": "picked"},
    "DROPPED": {"intent": "dropped"},
    "NO": {"intent": "mess_no"},
}


def _norm(text: str) -> str:
    return " ".join(text.strip().split())


def _yesno(raw: str | None) -> bool | None:
    if raw is None:
        return None
    token = str(raw).strip().lower()
    if token in YES_WORDS:
        return True
    if token in NO_WORDS:
        return False
    return None


def parse_kv(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not blob:
        return out
    keys = (
        "PLATES|DISHES|VEG|UNUSED|PREP|USEBY|TEMP|PACKED|INSULATED|"
        "BATCH|PERISHABLE|KG|UNSAFE|SPOILED|SEPARATE"
    )
    for match in re.finditer(
        rf"({keys})\s*[:=]?\s*(.+?)(?=\s+(?:{keys})\b|$)",
        blob,
        re.IGNORECASE,
    ):
        out[match.group(1).upper()] = match.group(2).strip()
    leftover = blob
    for key, val in out.items():
        leftover = re.sub(rf"{key}\s*[:=]?\s*{re.escape(val)}", " ", leftover, flags=re.IGNORECASE)
    leftover = leftover.strip()
    leftover = re.sub(r"^\d+\s*", "", leftover).strip()
    if leftover and "DISHES" not in out:
        out["DISHES"] = leftover.replace(",", " ").strip()
    return out


def _release_from_kv(plates: int | None, kv: dict[str, str]) -> dict[str, Any]:
    veg_raw = (kv.get("VEG") or "").lower()
    veg = None
    if veg_raw in {"veg", "vegetarian"}:
        veg = "veg"
    elif veg_raw in {"nonveg", "non-veg", "nv"}:
        veg = "nonveg"
    elif veg_raw in {"mixed", "both"}:
        veg = "mixed"

    payload: dict[str, Any] = {
        "intent": "release",
        "plates": plates,
        "dishes": kv.get("DISHES"),
        "veg": veg,
        "unused_not_served": _yesno(kv.get("UNUSED")),
        "prep_at": kv.get("PREP"),
        "use_by": kv.get("USEBY"),
        "temp_c": kv.get("TEMP"),
        "packed_covered": _yesno(kv.get("PACKED")),
        "insulated": _yesno(kv.get("INSULATED")),
        "batch": kv.get("BATCH"),
        "perishable": _yesno(kv.get("PERISHABLE")),
        "kg": kv.get("KG"),
        "unsafe": _yesno(kv.get("UNSAFE")),
        "spoiled": _yesno(kv.get("SPOILED")),
        "packed_separate": _yesno(kv.get("SEPARATE")),
    }
    if payload["temp_c"] not in (None, ""):
        try:
            payload["temp_c"] = float(payload["temp_c"])
        except ValueError:
            payload["temp_c"] = payload["temp_c"]
    if payload["kg"] not in (None, ""):
        try:
            payload["kg"] = float(payload["kg"])
        except ValueError:
            payload["kg"] = None
    return payload


RELEASE_REQUIRED = [
    "plates",
    "dishes",
    "veg",
    "unused_not_served",
    "prep_at",
    "use_by",
    "temp_c",
    "packed_covered",
    "insulated",
]


def missing_release_fields(payload: dict[str, Any]) -> list[str]:
    missing = []
    for key in RELEASE_REQUIRED:
        val = payload.get(key)
        if val is None or val == "":
            missing.append(key)
    try:
        if int(payload.get("plates") or 0) <= 0:
            if "plates" not in missing:
                missing.append("plates")
    except (TypeError, ValueError):
        if "plates" not in missing:
            missing.append("plates")
    return missing


def parse_inbound(text: str) -> dict[str, Any]:
    raw = _norm(text)
    if not raw:
        return {"intent": "ambiguous", "reason": "empty"}

    upper = raw.upper()
    if upper in SIMPLE:
        return dict(SIMPLE[upper])
    if upper == "RELEASE NO":
        return {"intent": "mess_no"}

    m_zero = NEED_ZERO.match(raw)
    if m_zero:
        sitting = (m_zero.group(1) or "").lower() or None
        return {"intent": "need", "plates": 0, "sitting": sitting, "veg_policy": None}

    m_need = NEED.match(raw)
    if m_need:
        veg_token = (m_need.group(3) or "").lower()
        sitting = m_need.group(2).lower()
        dishes = (m_need.group(4) or "").strip() or None
        return {
            "intent": "need",
            "plates": int(m_need.group(1)),
            "sitting": sitting,
            "veg_policy": VEG_MAP.get(veg_token) if veg_token else None,
            "dishes": dishes,
        }

    if upper.startswith("RELEASE"):
        m_rel = RELEASE_HEAD.match(raw)
        if not m_rel:
            return {"intent": "ambiguous", "reason": "unparsed_release"}
        rest = m_rel.group(2) or ""
        plates = int(m_rel.group(1)) if m_rel.group(1) else None
        if plates is None:
            kv_try = parse_kv(rest)
            if "PLATES" in kv_try:
                try:
                    plates = int(kv_try["PLATES"])
                except ValueError:
                    plates = None
        kv = parse_kv(raw[len("RELEASE") :])
        payload = _release_from_kv(plates, kv)
        missing = missing_release_fields(payload)
        if missing:
            payload["intent"] = "release_incomplete"
            payload["missing"] = missing
        return payload

    return {"intent": "ambiguous", "reason": "unknown_text"}
