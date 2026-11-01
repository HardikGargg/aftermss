"""JSON API and the black / orange / white signup site."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from aftermess import accounts, platform
from aftermess.accounts import AccountError
from aftermess.geo import PRESETS, nearby_km

WEB = Path(__file__).resolve().parent / "web"
COOKIE = "aftermess_session"


def _token(request: Request) -> str | None:
    raw = request.cookies.get(COOKIE)
    return raw or None


def _viewer(request: Request) -> dict:
    row = accounts.session_row(_token(request))
    if not row:
        raise HTTPException(status_code=401, detail="Sign in again.")
    return row


def _cookie(response: JSONResponse, token: str) -> JSONResponse:
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=14 * 24 * 3600,
        path="/",
    )
    return response


def _run(fn):
    try:
        return fn()
    except AccountError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _page(name: str) -> FileResponse:
    return FileResponse(WEB / name, headers={"Cache-Control": "no-store"})


def mount(app: FastAPI) -> None:
    @app.get("/app")
    @app.get("/app/")
    async def app_page():
        return _page("index.html")

    @app.get("/app/app.css")
    async def app_css():
        return _page("app.css")

    @app.get("/app/app.js")
    async def app_js():
        return _page("app.js")

    @app.get("/api/areas")
    async def areas():
        return {"nearby_km": nearby_km(), "areas": PRESETS}

    @app.post("/api/register")
    async def register(payload: dict):
        me, token = _run(lambda: accounts.register(payload))
        if me["role"] == "rider":
            platform.retry_unassigned()
        return _cookie(JSONResponse({"ok": True, "me": me}), token)

    @app.post("/api/login")
    async def login(payload: dict):
        me, token = _run(lambda: accounts.login(str(payload.get("phone") or ""), str(payload.get("pin") or "")))
        return _cookie(JSONResponse({"ok": True, "me": me}), token)

    @app.post("/api/logout")
    async def logout(request: Request):
        accounts.logout(_token(request))
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE, path="/")
        return response

    @app.get("/api/me")
    async def me(request: Request):
        row = _viewer(request)
        body = {
            "id": row["id"],
            "role": row["role"],
            "display_name": row["display_name"],
            "phone": row.get("phone") or "",
            "area": row.get("area") or "",
            "veg_policy": row.get("veg_policy") or "",
        }
        if row["role"] == "rider":
            body["upi_id"] = row.get("upi_id") or ""
        return body

    @app.get("/api/board")
    async def board(request: Request, sitting: str = "lunch"):
        row = _viewer(request)
        return _run(lambda: platform.board(row, sitting))

    @app.post("/api/need")
    async def need(request: Request, payload: dict):
        row = _viewer(request)
        return _run(
            lambda: platform.post_need(
                row,
                plates=payload.get("plates"),
                sitting=str(payload.get("sitting") or ""),
                veg_policy=payload.get("veg_policy"),
            )
        )

    @app.post("/api/release")
    async def release(request: Request, payload: dict):
        row = _viewer(request)
        return _run(lambda: platform.post_release(row, payload, sitting=str(payload.get("sitting") or "")))

    @app.post("/api/none")
    async def none(request: Request, payload: dict):
        row = _viewer(request)
        return _run(lambda: platform.post_no(row, sitting=str(payload.get("sitting") or "")))

    @app.post("/api/match")
    async def match(request: Request, payload: dict):
        row = _viewer(request)
        sitting = str(payload.get("sitting") or "lunch")

        def _go():
            platform.match_posted(sitting)
            return {"ok": True, "message": "Checked for a nearby match."}

        _ = row
        return _run(_go)

    @app.post("/api/trips/{trip_id}/{action}")
    async def trip_action(request: Request, trip_id: str, action: str):
        row = _viewer(request)
        return _run(lambda: platform.act(row, trip_id, action))
