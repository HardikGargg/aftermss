"""Load static directory + config. Env vars overlay OPEN numeric/clock fields without inventing names."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aftermess.paths import config_path, directory_path

_ENV_CLOCKS = {
    "AFTERMESS_LUNCH_NEED_CUTOFF": ("clocks", "lunch_need_cutoff"),
    "AFTERMESS_LUNCH_END": ("clocks", "lunch_end"),
    "AFTERMESS_DINNER_NEED_CUTOFF": ("clocks", "dinner_need_cutoff"),
    "AFTERMESS_DINNER_END": ("clocks", "dinner_end"),
}

_ENV_TIMEOUTS = {
    "AFTERMESS_TIMEOUT_MESS_RELEASE": "mess_release",
    "AFTERMESS_TIMEOUT_RIDER_ACCEPT": "rider_accept",
    "AFTERMESS_TIMEOUT_PICKED": "picked",
    "AFTERMESS_TIMEOUT_DROPPED": "dropped",
    "AFTERMESS_TIMEOUT_RECEIVED": "received",
    "AFTERMESS_TIMEOUT_PAID": "paid",
    "AFTERMESS_TIMEOUT_CHASE": "chase",
}


def _read_json(path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_directory() -> dict[str, Any]:
    return _read_json(directory_path())


def load_config() -> dict[str, Any]:
    cfg = deepcopy(_read_json(config_path()))
    rupees = os.environ.get("AFTERMESS_TRIP_RUPEES")
    if rupees not in (None, ""):
        cfg["trip_rupees"] = int(rupees)
    hours = os.environ.get("AFTERMESS_USE_BY_HOURS")
    if hours not in (None, ""):
        cfg["use_by_hours"] = float(hours)
    lang = os.environ.get("AFTERMESS_LANGUAGE")
    if lang not in (None, ""):
        cfg["language"] = lang
    tz = os.environ.get("AFTERMESS_TIMEZONE")
    if tz:
        cfg.setdefault("clocks", {})["timezone"] = tz
    for env_key, (section, field) in _ENV_CLOCKS.items():
        val = os.environ.get(env_key)
        if val not in (None, ""):
            cfg.setdefault(section, {})[field] = val
    for env_key, field in _ENV_TIMEOUTS.items():
        val = os.environ.get(env_key)
        if val not in (None, ""):
            cfg.setdefault("timeouts_minutes", {})[field] = int(val)
    provider = os.environ.get("WHATSAPP_PROVIDER")
    if provider:
        cfg["whatsapp_provider"] = provider.lower()
    else:
        cfg["whatsapp_provider"] = "simulator"
    return cfg


def timezone(cfg: dict[str, Any] | None = None) -> ZoneInfo:
    cfg = cfg or load_config()
    name = (cfg.get("clocks") or {}).get("timezone") or "Asia/Kolkata"
    return ZoneInfo(name)


def now_local(cfg: dict[str, Any] | None = None, now: datetime | None = None) -> datetime:
    tz = timezone(cfg)
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)


def sitting_date_str(cfg: dict[str, Any] | None = None, now: datetime | None = None) -> str:
    return now_local(cfg, now).date().isoformat()


def party_index(directory: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    directory = directory or load_directory()
    out: dict[str, dict[str, Any]] = {}
    for mess in directory.get("messes") or []:
        out[mess["id"]] = {**mess, "role": "mess"}
    for drop in directory.get("drops") or []:
        out[drop["id"]] = {**drop, "role": "drop"}
    for rider in directory.get("riders") or []:
        out[rider["id"]] = {**rider, "role": "rider"}
    return out


def get_party(party_id: str, directory: dict[str, Any] | None = None) -> dict[str, Any]:
    idx = party_index(directory)
    if party_id not in idx:
        raise KeyError(f"unknown party {party_id}")
    return idx[party_id]


def party_by_whatsapp(number: str, directory: dict[str, Any] | None = None) -> dict[str, Any] | None:
    digits = _digits(number)
    if not digits:
        return None
    for party in party_index(directory).values():
        if _digits(str(party.get("whatsapp") or "")) == digits:
            return party
    return None


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def roster_ids(directory: dict[str, Any] | None = None) -> list[str]:
    directory = directory or load_directory()
    return list(directory.get("rider_ids_in_order") or [])
