"""Distance for nearby messes, NGOs, and riders. No maps service."""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Any

# Delhi pins so a demo can show "nearby" without browser location.
PRESETS: list[dict[str, Any]] = [
    {"id": "iiitd", "label": "IIIT Delhi", "lat": 28.5463, "lng": 77.2730},
    {"id": "govindpuri", "label": "Govindpuri", "lat": 28.5355, "lng": 77.2639},
    {"id": "kalkaji", "label": "Kalkaji", "lat": 28.5494, "lng": 77.2586},
    {"id": "saket", "label": "Saket", "lat": 28.5244, "lng": 77.2066},
    {"id": "cp", "label": "Connaught Place", "lat": 28.6315, "lng": 77.2167},
    {"id": "dwarka", "label": "Dwarka", "lat": 28.5523, "lng": 77.0581},
]


def nearby_km() -> float:
    from aftermess.config import load_config

    raw = load_config().get("nearby_km")
    if raw in (None, ""):
        return 10.0
    return float(raw)


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lng2 - lng1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * radius * atan2(sqrt(a), sqrt(1 - a))


def release_reaches(release: dict[str, Any], drop: dict[str, Any]) -> bool:
    """Parties without a pin stay on the closed campus list and can match each other."""
    coords = (
        release.get("lat"),
        release.get("lng"),
        drop.get("lat"),
        drop.get("lng"),
    )
    if any(value is None or value == "" for value in coords):
        return True
    try:
        distance = haversine(float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3]))
    except (TypeError, ValueError):
        return True
    return distance <= nearby_km()
