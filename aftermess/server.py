"""Public HTTP surface: WhatsApp webhook, judge demo, AgentCore /invocations + /ping."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from aftermess.config import get_party, load_directory, sitting_date_str
from aftermess.demo import run_locked_demo
from aftermess.loop import handle_inbound, sitting_status, tick
from aftermess.whatsapp import (
    dispatch_text,
    normalize_meta,
    normalize_twilio,
    verify_meta_signature,
)


def _demo_allowed(header_token: str | None) -> bool:
    expected = os.environ.get("AFTERMESS_DEMO_TOKEN")
    if not expected:
        return True
    return header_token == expected


def _invocation_prompt(payload: dict[str, Any]) -> str:
    if "prompt" in payload and isinstance(payload["prompt"], str):
        return payload["prompt"]
    inner = payload.get("input")
    if isinstance(inner, dict):
        return str(inner.get("prompt") or "")
    return ""


def create_app():
    app = FastAPI(title="AfterMess", version="1.0.0")

    @app.get("/")
    async def home():
        return RedirectResponse(url="/app", status_code=302)

    @app.get("/ping")
    async def ping():
        return {"status": "healthy"}

    @app.get("/health")
    async def health():
        return {"ok": True, "service": "aftermess"}

    @app.get("/webhook")
    async def verify(request: Request):
        params = request.query_params
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")
        if mode == "subscribe" and token == os.environ.get("WHATSAPP_VERIFY_TOKEN"):
            return PlainTextResponse(challenge or "")
        raise HTTPException(status_code=403, detail="verify failed")

    @app.post("/webhook")
    async def inbound(request: Request, x_hub_signature_256: str | None = Header(default=None)):
        raw = await request.body()
        ctype = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
            form = dict(await request.form())
            msg = normalize_twilio({k: str(v) for k, v in form.items()})
            dispatch_text(msg["from"], msg["text"], msg["id"])
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                media_type="application/xml",
            )
        if not verify_meta_signature(raw, x_hub_signature_256):
            raise HTTPException(status_code=403, detail="bad signature")
        payload = json.loads(raw.decode() or "{}")
        results = [dispatch_text(m["from"], m["text"], m["id"]) for m in normalize_meta(payload)]
        return {"results": results}

    @app.post("/demo")
    async def demo(x_aftermess_token: str | None = Header(default=None)):
        if not _demo_allowed(x_aftermess_token):
            raise HTTPException(status_code=401, detail="bad demo token")
        return run_locked_demo()

    @app.post("/inbound")
    async def sim_inbound(body: dict[str, Any]):
        party_id = str(body.get("party_id") or "")
        text = str(body.get("text") or "")
        if not party_id or not text:
            raise HTTPException(status_code=400, detail="party_id and text required")
        directory = load_directory()
        get_party(party_id, directory)
        return handle_inbound(
            party_id,
            text,
            message_id=str(body.get("message_id") or ""),
            sitting=body.get("sitting"),
            sitting_date=body.get("sitting_date"),
        )

    @app.post("/tick")
    async def sim_tick(body: dict[str, Any]):
        sitting = str(body.get("sitting") or "")
        if sitting not in {"lunch", "dinner"}:
            raise HTTPException(status_code=400, detail="sitting lunch|dinner")
        return tick(sitting, phase=body.get("phase"), sitting_date=body.get("sitting_date"))

    @app.get("/status")
    async def status(sitting: str = "lunch", sitting_date: str | None = None):
        date = sitting_date or sitting_date_str()
        return sitting_status(date, sitting)

    @app.post("/invocations")
    async def invocations(request: Request):
        payload = await request.json()
        prompt = _invocation_prompt(payload).strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt found in input")
        lowered = prompt.lower()
        if lowered in {"demo", "run demo", "lunch demo"}:
            result = run_locked_demo()
            return {
                "output": {
                    "message": (
                        f"Lunch demo settled. Plates moved: {result['status']['plates_moved']}. "
                        f"Trip state: {(result['status']['trips'] or [{}])[0].get('state')}."
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "model": "aftermess",
                    "status": {
                        "plates_moved": result["status"]["plates_moved"],
                        "trips": result["status"]["trips"],
                    },
                }
            }
        from aftermess.agent import build_agent

        agent = build_agent()
        result = agent(prompt)
        text = getattr(result, "message", None) or str(result)
        return {
            "output": {
                "message": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": "strands-aftermess",
            }
        }

    from aftermess.webapi import mount

    mount(app)
    return app


_app = None


def get_app():
    global _app
    if _app is None:
        _app = create_app()
    return _app
