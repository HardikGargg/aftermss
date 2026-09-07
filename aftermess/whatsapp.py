"""WhatsApp Cloud API + Twilio adapters and inbound webhook. Simulator needs no tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from aftermess.config import load_config, party_by_whatsapp
from aftermess.loop import handle_inbound

GRAPH_BASE = os.environ.get("WHATSAPP_GRAPH_BASE", "https://graph.facebook.com/v21.0")


def _config_templates() -> dict[str, Any]:
    return (load_config().get("templates") or {})


def deliver(
    phone: str,
    body: str,
    template_key: str | None = None,
    params: list[str] | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    provider = (provider or os.environ.get("WHATSAPP_PROVIDER") or "simulator").lower()
    if provider == "twilio":
        return _twilio_send(phone, body, template_key, params or [])
    if provider in {"meta", "cloud", "whatsapp"}:
        return _meta_send(phone, body, template_key, params or [])
    return {"ok": True, "provider": "simulator", "skipped": True}


def _template_name(template_key: str | None) -> str | None:
    if not template_key:
        return None
    name = _config_templates().get(template_key)
    if not name:
        return None
    return str(name)


def _meta_send(phone: str, body: str, template_key: str | None, params: list[str]) -> dict[str, Any]:
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        return {"ok": False, "error": "missing_WHATSAPP_TOKEN_or_WHATSAPP_PHONE_ID"}
    to = "".join(ch for ch in phone if ch.isdigit())
    template = _template_name(template_key)
    if template:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": os.environ.get("WHATSAPP_TEMPLATE_LANG", "en")},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": p} for p in params]
                        or [{"type": "text", "text": body[:1024]}],
                    }
                ],
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body, "preview_url": False},
        }
    return _http_json(
        f"{GRAPH_BASE}/{phone_id}/messages",
        payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )


def _twilio_send(phone: str, body: str, template_key: str | None, params: list[str]) -> dict[str, Any]:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth = os.environ.get("TWILIO_AUTH_TOKEN")
    frm = os.environ.get("TWILIO_WHATSAPP_FROM")
    if not sid or not auth or not frm:
        return {"ok": False, "error": "missing_twilio_env"}
    to = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone if phone.startswith('+') else '+' + phone}"
    content_sid = _template_name(template_key)
    fields = {"From": frm if frm.startswith("whatsapp:") else f"whatsapp:{frm}", "To": to, "Body": body}
    if content_sid:
        fields["ContentSid"] = content_sid
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        data=data,
        method="POST",
    )
    basic = base64.b64encode(f"{sid}:{auth}".encode()).decode()
    req.add_header("Authorization", f"Basic {basic}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return {"ok": True, "provider": "twilio", "status": resp.status, "body": resp.read().decode()[:2000]}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "provider": "twilio", "status": exc.code, "body": exc.read().decode()[:2000]}


def _http_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return {"ok": True, "provider": "meta", "status": resp.status, "body": resp.read().decode()[:2000]}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "provider": "meta", "status": exc.code, "body": exc.read().decode()[:2000]}


def normalize_meta(body: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for entry in body.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                text = ""
                if msg.get("type") == "text":
                    text = (msg.get("text") or {}).get("body") or ""
                elif msg.get("type") == "button":
                    text = (msg.get("button") or {}).get("text") or ""
                elif msg.get("type") == "interactive":
                    interactive = msg.get("interactive") or {}
                    text = (
                        (interactive.get("button_reply") or {}).get("title")
                        or (interactive.get("list_reply") or {}).get("title")
                        or ""
                    )
                messages.append(
                    {
                        "id": msg.get("id") or "",
                        "from": msg.get("from") or "",
                        "text": text,
                    }
                )
    return messages


def normalize_twilio(form: dict[str, str]) -> dict[str, Any]:
    return {
        "id": form.get("MessageSid") or form.get("SmsMessageSid") or "",
        "from": form.get("From") or "",
        "text": form.get("Body") or "",
    }


def verify_meta_signature(raw: bytes, header: str | None) -> bool:
    secret = os.environ.get("WHATSAPP_APP_SECRET")
    if not secret:
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header[7:], expected)


def dispatch_text(phone: str, text: str, message_id: str = "") -> dict[str, Any]:
    party = party_by_whatsapp(phone)
    if not party:
        return {"ok": False, "error": "unknown_number", "from": phone}
    return handle_inbound(party["id"], text, message_id=message_id)


def create_app():
    from aftermess.server import create_app as _create

    return _create()


app = None


def get_app():
    global app
    if app is None:
        app = create_app()
    return app
