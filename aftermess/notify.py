"""Outbound messages: always land in the local outbox; live WhatsApp only if a number exists."""

from __future__ import annotations

from typing import Any

from aftermess import store
from aftermess.config import get_party, load_config, load_directory


def emit(
    party_id: str,
    body: str,
    template_key: str | None = None,
    params: list[str] | None = None,
) -> dict[str, Any]:
    directory = load_directory()
    party = get_party(party_id, directory)
    rec = store.append_outbox(
        {
            "party_id": party_id,
            "role": party["role"],
            "to": party.get("whatsapp") or f"sim:{party_id}",
            "template_key": template_key,
            "params": params or [],
            "body": body,
        }
    )
    cfg = load_config()
    provider = cfg.get("whatsapp_provider") or "simulator"
    phone = str(party.get("whatsapp") or "").strip()
    if provider == "simulator" or not phone:
        return rec
    from aftermess.whatsapp import deliver

    delivery = deliver(
        phone,
        body,
        template_key=template_key,
        params=params or [],
        provider=provider,
    )
    rec = {**rec, "delivery": delivery}
    return rec
