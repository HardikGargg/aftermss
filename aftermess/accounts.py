"""Phone + PIN accounts for messes, NGOs, and riders."""

from __future__ import annotations

import hashlib
import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from aftermess.geo import haversine, nearby_km
from aftermess.paths import accounts_path

_LOCK = threading.Lock()
_SECRET_KEYS = {"pin_hash", "pin_salt"}


class AccountError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read() -> dict[str, Any]:
    path = accounts_path()
    if not path.exists():
        return {"parties": [], "sessions": []}
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("parties", [])
    data.setdefault("sessions", [])
    return data


def _write(data: dict[str, Any]) -> None:
    import json

    path = accounts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def normalize_phone(raw: str) -> str:
    digits = _digits(raw)
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) < 10 or len(digits) > 15:
        raise AccountError("Enter a real phone number.")
    return digits


def _phones_match(stored: str, incoming: str) -> bool:
    have = _digits(stored)
    want = _digits(incoming)
    if len(want) == 12 and want.startswith("91"):
        want = want[2:]
    if len(want) == 11 and want.startswith("0"):
        want = want[1:]
    if not have or not want:
        return False
    return have == want or have.endswith(want) or want.endswith(have)


def _hash_pin(pin: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 120_000).hex()


def _check_pin(pin: str) -> str:
    text = str(pin or "").strip()
    if not text.isdigit() or not 4 <= len(text) <= 6:
        raise AccountError("PIN must be 4 to 6 digits.")
    return text


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _public(row: dict[str, Any]) -> dict[str, Any]:
    data = {
        "id": row["id"],
        "role": row["role"],
        "display_name": row["display_name"],
        "phone": row.get("phone") or "",
        "area": row.get("area") or "",
        "lat": row.get("lat"),
        "lng": row.get("lng"),
        "veg_policy": row.get("veg_policy") or "",
        "fssai": row.get("fssai") or "",
    }
    if row.get("role") == "rider":
        data["upi_id"] = row.get("upi_id") or ""
    return data


def _strip(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in _SECRET_KEYS}


def as_party(row: dict[str, Any]) -> dict[str, Any]:
    """Directory shape used by the safety gate, matcher, and outbox."""
    role = row["role"]
    party: dict[str, Any] = {
        "id": row["id"],
        "display_name": row.get("display_name") or row["id"],
        "whatsapp": row.get("phone") or "",
        "address": row.get("area") or "",
        "area": row.get("area") or "",
        "lat": row.get("lat"),
        "lng": row.get("lng"),
        "active": True,
    }
    if role == "mess":
        party["role"] = "mess"
        party["fssai_fbo"] = row.get("fssai") or ""
        party["veg_default"] = row.get("veg_policy") or "veg"
    elif role == "ngo":
        party["role"] = "drop"
        party["fssai_sfdo"] = row.get("fssai") or ""
        party["veg_policy"] = row.get("veg_policy") or "veg_only"
        party["fostac_ok"] = True
    else:
        party["role"] = "rider"
        party["upi_id"] = row.get("upi_id") or ""
    return party


def list_rows() -> list[dict[str, Any]]:
    with _LOCK:
        return [_strip(row) for row in _read()["parties"]]


def is_registered(party_id: str) -> bool:
    return any(row["id"] == party_id for row in list_rows())


def lookup_party(party_id: str) -> dict[str, Any] | None:
    for row in list_rows():
        if row["id"] == party_id:
            return as_party(row)
    return None


def lookup_phone(number: str) -> dict[str, Any] | None:
    for row in list_rows():
        if _phones_match(row.get("phone") or "", number):
            return as_party(row)
    return None


def row_by_id(party_id: str) -> dict[str, Any] | None:
    for row in list_rows():
        if row["id"] == party_id:
            return row
    return None


def nearby_rider_ids(lat: float, lng: float) -> list[str]:
    from aftermess.config import load_directory

    pool: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rider in load_directory().get("riders") or []:
        pool.append(rider)
        seen.add(rider["id"])
    for row in list_rows():
        if row.get("role") != "rider" or row["id"] in seen:
            continue
        pool.append(as_party(row))
    ranked: list[tuple[float, str]] = []
    limit = nearby_km()
    for rider in pool:
        if not rider.get("active", True):
            continue
        rlat, rlng = rider.get("lat"), rider.get("lng")
        if rlat is None or rlng is None:
            continue
        distance = haversine(float(lat), float(lng), float(rlat), float(rlng))
        if distance <= limit:
            ranked.append((distance, rider["id"]))
    ranked.sort()
    return [rider_id for _, rider_id in ranked]


def _session(data: dict[str, Any], party_id: str) -> str:
    token = secrets.token_urlsafe(32)
    data["sessions"].append(
        {
            "token": token,
            "party_id": party_id,
            "expires": (_now() + timedelta(days=14)).isoformat(),
        }
    )
    return token


def _same_secret(stored: str, incoming: str) -> bool:
    if not stored or not incoming or len(stored) != len(incoming):
        return False
    return secrets.compare_digest(stored, incoming)


def _find_session(data: dict[str, Any], token: str) -> dict[str, Any] | None:
    now = _now()
    live = []
    found = None
    for row in data["sessions"]:
        try:
            expires = datetime.fromisoformat(row["expires"])
        except (TypeError, ValueError):
            continue
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= now:
            continue
        live.append(row)
        if _same_secret(str(row.get("token") or ""), token):
            found = row
    data["sessions"] = live
    return found


def register(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    role = str(payload.get("role") or "").strip().lower()
    if role not in {"mess", "ngo", "rider"}:
        raise AccountError("Choose mess, NGO, or rider.")
    name = " ".join(str(payload.get("display_name") or "").split())
    if not 2 <= len(name) <= 80:
        raise AccountError("Enter the name people should see.")
    phone = normalize_phone(str(payload.get("phone") or ""))
    pin = _check_pin(str(payload.get("pin") or ""))
    area = " ".join(str(payload.get("area") or "").split())
    if not 2 <= len(area) <= 80:
        raise AccountError("Set a location: use your pin, or pick a demo area.")
    try:
        lat = float(payload.get("lat"))
        lng = float(payload.get("lng"))
    except (TypeError, ValueError):
        raise AccountError("Set a location: use your pin, or pick a demo area.") from None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise AccountError("That location is not valid.")
    fssai = str(payload.get("fssai") or "").strip()
    upi = str(payload.get("upi_id") or "").strip()
    veg = str(payload.get("veg_policy") or "").strip()
    if role == "ngo":
        if veg not in {"veg_only", "nonveg_ok", "nonveg_only"}:
            raise AccountError("Choose what food the NGO can take.")
        if len(fssai) < 5:
            raise AccountError("Enter the NGO FSSAI number.")
    elif role == "mess":
        if veg not in {"veg", "nonveg"}:
            raise AccountError("Choose whether this mess is veg or non-veg.")
        if len(fssai) < 5:
            raise AccountError("Enter the mess FSSAI number.")
        upi = ""
    else:
        veg = ""
        fssai = ""
        if "@" not in upi or " " in upi or len(upi) < 5:
            raise AccountError("Enter the rider UPI id, like name@oksbi.")
    salt = secrets.token_hex(16)
    with _LOCK:
        data = _read()
        if any(_phones_match(row.get("phone") or "", phone) for row in data["parties"]):
            raise AccountError("That phone is already registered. Sign in instead.")
        row = {
            "id": _new_id(role),
            "role": role,
            "display_name": name,
            "phone": phone,
            "pin_salt": salt,
            "pin_hash": _hash_pin(pin, salt),
            "area": area,
            "lat": lat,
            "lng": lng,
            "fssai": fssai,
            "veg_policy": veg,
            "upi_id": upi,
            "created_at": _now().isoformat(timespec="seconds"),
        }
        data["parties"].append(row)
        token = _session(data, row["id"])
        _write(data)
    return _public(row), token


_DEMOS: list[dict[str, str]] = [
    {
        "id": "mess_iiitd",
        "role": "mess",
        "display_name": "IIITD Mess",
        "phone": "9811100001",
        "pin": "1111",
        "preset": "iiitd",
        "fssai": "DEMO-FBO-IIITD",
        "veg_policy": "veg",
        "upi_id": "",
    },
    {
        "id": "ngo_govindpuri",
        "role": "ngo",
        "display_name": "Govindpuri Kitchen",
        "phone": "9811100002",
        "pin": "2222",
        "preset": "govindpuri",
        "fssai": "DEMO-SFDO-GOVINDPURI",
        "veg_policy": "nonveg_ok",
        "upi_id": "",
    },
    {
        "id": "rider_campus",
        "role": "rider",
        "display_name": "Campus Rider",
        "phone": "9811100003",
        "pin": "3333",
        "preset": "kalkaji",
        "fssai": "",
        "veg_policy": "",
        "upi_id": "campus@oksbi",
    },
]


def ensure_demo_accounts() -> None:
    """Create the three README sign-in accounts when this server has none."""
    from aftermess.geo import PRESETS

    pins = {row["id"]: row for row in PRESETS}
    with _LOCK:
        data = _read()
        changed = False
        for spec in _DEMOS:
            phone = normalize_phone(spec["phone"])
            existing = next(
                (item for item in data["parties"] if _phones_match(item.get("phone") or "", phone)),
                None,
            )
            if existing:
                if secrets.compare_digest(_hash_pin(spec["pin"], existing["pin_salt"]), existing["pin_hash"]):
                    continue
                salt = secrets.token_hex(16)
                existing["pin_salt"] = salt
                existing["pin_hash"] = _hash_pin(spec["pin"], salt)
                changed = True
                continue
            area = pins[spec["preset"]]
            salt = secrets.token_hex(16)
            data["parties"].append(
                {
                    "id": spec["id"],
                    "role": spec["role"],
                    "display_name": spec["display_name"],
                    "phone": phone,
                    "pin_salt": salt,
                    "pin_hash": _hash_pin(spec["pin"], salt),
                    "area": area["label"],
                    "lat": area["lat"],
                    "lng": area["lng"],
                    "fssai": spec["fssai"],
                    "veg_policy": spec["veg_policy"],
                    "upi_id": spec["upi_id"],
                    "created_at": _now().isoformat(timespec="seconds"),
                }
            )
            changed = True
        if changed:
            _write(data)


def login(phone_raw: str, pin_raw: str) -> tuple[dict[str, Any], str]:
    phone = normalize_phone(phone_raw)
    pin = _check_pin(pin_raw)
    with _LOCK:
        data = _read()
        row = next((item for item in data["parties"] if _phones_match(item.get("phone") or "", phone)), None)
        if not row:
            raise AccountError("That phone is not registered. Create an account, or use a demo account.")
        if not secrets.compare_digest(_hash_pin(pin, row["pin_salt"]), row["pin_hash"]):
            raise AccountError("Phone or PIN does not match.")
        token = _session(data, row["id"])
        _write(data)
    return _public(row), token


def logout(token: str | None) -> None:
    if not token:
        return
    with _LOCK:
        data = _read()
        data["sessions"] = [
            row for row in data["sessions"] if not _same_secret(str(row.get("token") or ""), token)
        ]
        _write(data)


def session_row(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with _LOCK:
        data = _read()
        found = _find_session(data, token)
        _write(data)
        if not found:
            return None
        row = next((item for item in data["parties"] if item["id"] == found["party_id"]), None)
        if not row:
            return None
        return _strip(row)
