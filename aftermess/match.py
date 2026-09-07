"""Fill-one-drop matching. Deterministic. No LLM."""

from __future__ import annotations

from typing import Any


def need_policy(need: dict[str, Any], drop: dict[str, Any]) -> str:
    override = need.get("veg_policy")
    if override:
        return override
    return drop.get("veg_policy") or "veg_only"


def compatible(release: dict[str, Any], policy: str) -> bool:
    if release.get("status") != "offered":
        return False
    remaining = int(release.get("plates_remaining", release.get("plates") or 0))
    if remaining <= 0:
        return False
    veg = str(release.get("veg") or "").strip().lower()
    if policy == "veg_only":
        return veg == "veg"
    if policy == "nonveg_only":
        return veg == "nonveg"
    if policy == "nonveg_ok":
        return veg in {"veg", "nonveg"}
    return False


def _drop_map(directory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {d["id"]: d for d in directory.get("drops") or []}


def plan_trips(
    needs: list[dict[str, Any]],
    releases: list[dict[str, Any]],
    directory: dict[str, Any],
) -> list[dict[str, Any]]:
    """Assign leftover to drops. Prefer filling one drop well; second drop only if remainder."""
    drops = _drop_map(directory)
    live_needs = []
    for need in needs:
        drop = drops.get(need["drop_id"])
        if not drop:
            continue
        if not drop.get("fostac_ok", True):
            continue
        if not (drop.get("fssai_sfdo") or "").strip():
            continue
        plates = int(need.get("plates") or 0)
        if plates <= 0:
            continue
        live_needs.append({**need, "_policy": need_policy(need, drop)})

    remaining = {
        rel["id"]: int(rel.get("plates_remaining", rel.get("plates") or 0))
        for rel in releases
        if rel.get("status") == "offered"
    }
    rel_by_id = {rel["id"]: rel for rel in releases if rel.get("status") == "offered"}
    assigned_need_ids: set[str] = set()
    trips: list[dict[str, Any]] = []

    while True:
        scored: list[tuple[int, str, dict[str, Any]]] = []
        for need in live_needs:
            if need["id"] in assigned_need_ids:
                continue
            usable = 0
            for rel_id, left in remaining.items():
                if left <= 0:
                    continue
                if compatible({**rel_by_id[rel_id], "plates_remaining": left, "status": "offered"}, need["_policy"]):
                    usable += left
            score = min(int(need["plates"]), usable)
            if score > 0:
                scored.append((score, need.get("created_at") or "", need))
        if not scored:
            break
        scored.sort(key=lambda row: (-row[0], row[1], row[2]["id"]))
        _, _, winner = scored[0]
        still_need = int(winner["plates"])
        assignments: dict[str, int] = {}
        mess_ids: list[str] = []
        ranked = sorted(
            remaining.items(),
            key=lambda kv: (
                -kv[1],
                rel_by_id[kv[0]].get("mess_id") or "",
            ),
        )
        for rel_id, left in ranked:
            if still_need <= 0 or left <= 0:
                continue
            rel = rel_by_id[rel_id]
            if not compatible({**rel, "plates_remaining": left, "status": "offered"}, winner["_policy"]):
                continue
            take = min(left, still_need)
            assignments[rel["mess_id"]] = assignments.get(rel["mess_id"], 0) + take
            remaining[rel_id] = left - take
            still_need -= take
            if rel["mess_id"] not in mess_ids:
                mess_ids.append(rel["mess_id"])
        moved = int(winner["plates"]) - still_need
        if moved <= 0:
            break
        assigned_need_ids.add(winner["id"])
        trips.append(
            {
                "need_id": winner["id"],
                "drop_id": winner["drop_id"],
                "mess_ids": mess_ids,
                "assigned_plates": assignments,
                "plates": moved,
                "veg_policy": winner["_policy"],
                "state": "draft_match",
            }
        )
    return trips
