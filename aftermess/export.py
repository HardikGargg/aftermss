"""Schedule II register and Eat Right Campus evidence pack. No kg invention."""

from __future__ import annotations

import json
from typing import Any

from aftermess import store
from aftermess.config import get_party, load_directory
from aftermess.loop import sitting_status
from aftermess.paths import runtime_dir


def write_schedule_ii_for_trip(trip_id: str) -> list[dict[str, Any]]:
    existing = store.schedule_ii_for_trip(trip_id)
    if existing:
        return existing
    trip = store.get_trip(trip_id)
    if not trip:
        raise KeyError(f"unknown trip {trip_id}")
    directory = load_directory()
    drop = get_party(trip["drop_id"], directory)
    rows = []
    for mess_id, qty in (trip.get("assigned_plates") or {}).items():
        mess = get_party(mess_id, directory)
        rel = store.get_release(mess_id, trip["sitting_date"], trip["sitting"]) or {}
        row = {
            "trip_id": trip_id,
            "sitting_date": trip["sitting_date"],
            "sitting": trip["sitting"],
            "donor_name": mess.get("display_name"),
            "donor_address": mess.get("address"),
            "donor_fssai": mess.get("fssai_fbo"),
            "sfdo_name": drop.get("display_name"),
            "sfdo_address": drop.get("address"),
            "sfdo_fssai": drop.get("fssai_sfdo"),
            "donation_date": trip.get("picked_at") or trip.get("received_at") or trip["sitting_date"],
            "food_name": rel.get("dishes"),
            "batch_number": rel.get("batch") or "fresh-cooked",
            "manufacturing_date": rel.get("prep_at"),
            "best_before_or_expiry": rel.get("use_by"),
            "quantity_donated_plates": qty,
            "quantity_kg": rel.get("kg"),
            "temperature_c": rel.get("temp_c"),
            "quantity_distributed_plates": qty,
            "area_distributed": drop.get("address") or drop.get("display_name"),
            "distribution_date": trip.get("received_at") or trip["sitting_date"],
            "veg": rel.get("veg"),
            "rider_id": trip.get("rider_id"),
            "mess_id": mess_id,
        }
        rows.append(store.append_schedule_ii(row))
    return rows


def eat_right_pack(sitting_date: str, sitting: str) -> dict[str, Any]:
    status = sitting_status(sitting_date, sitting)
    kg_values = [r.get("kg") for r in status["releases"] if r.get("kg") not in (None, "")]
    return {
        "campus": "IIITD",
        "programme": "Eat Right Campus",
        "part_c_no_food_waste": {
            "item_4_daily_waste_monitoring": {
                "note": "kg only if a mess typed kg. Plates are not converted to kg.",
                "plates_unmatched": status["plates_unmatched"],
                "kg_reported": kg_values,
            },
            "item_7_surplus_shared": {
                "shared": status["plates_moved"] > 0,
                "plates_moved": status["plates_moved"],
                "drops": sorted({t["drop_id"] for t in status["trips"] if t.get("state") not in {"no_match", "no_rider"}}),
            },
        },
        "sitting": status,
        "claims_we_do_not_make": [
            "No 80G deduction for in-kind leftover food.",
            "No CSR credit for own-cooked leftover.",
            "No Good Samaritan immunity clause verified in the 2019 Gazette operative text.",
        ],
    }


def export_files(sitting_date: str, sitting: str) -> dict[str, str]:
    status = sitting_status(sitting_date, sitting)
    pack = eat_right_pack(sitting_date, sitting)
    out_dir = runtime_dir() / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{sitting_date}_{sitting}"
    sii_path = out_dir / f"schedule_ii_{stem}.json"
    pack_path = out_dir / f"eat_right_{stem}.json"
    sheet_path = out_dir / f"schedule_ii_{stem}.txt"
    sii_path.write_text(json.dumps(status["schedule_ii"], indent=2) + "\n", encoding="utf-8")
    pack_path.write_text(json.dumps(pack, indent=2, default=str) + "\n", encoding="utf-8")
    sheet_path.write_text(_sheet(status["schedule_ii"], sitting_date, sitting), encoding="utf-8")
    return {
        "schedule_ii_json": str(sii_path),
        "schedule_ii_sheet": str(sheet_path),
        "eat_right_json": str(pack_path),
    }


def _sheet(rows: list[dict[str, Any]], sitting_date: str, sitting: str) -> str:
    lines = [
        f"FSSAI Schedule II surplus food register — {sitting} {sitting_date}",
        "Food is donated free of cost. Rider UPI is transport, not a food price.",
        "",
    ]
    if not rows:
        lines.append("(no rows)")
        return "\n".join(lines) + "\n"
    for i, row in enumerate(rows, 1):
        lines.extend(
            [
                f"Row {i}",
                f"  Donor: {row.get('donor_name')} | {row.get('donor_address')} | {row.get('donor_fssai')}",
                f"  SFDO: {row.get('sfdo_name')} | {row.get('sfdo_address')} | {row.get('sfdo_fssai')}",
                f"  Donation date: {row.get('donation_date')}",
                f"  Food: {row.get('food_name')} | batch {row.get('batch_number')} | veg={row.get('veg')}",
                f"  Manufactured/prep: {row.get('manufacturing_date')}",
                f"  Best before / use-by: {row.get('best_before_or_expiry')}",
                f"  Quantity donated (plates): {row.get('quantity_donated_plates')} | kg: {row.get('quantity_kg')}",
                f"  Temperature C: {row.get('temperature_c')}",
                f"  Quantity distributed (plates): {row.get('quantity_distributed_plates')}",
                f"  Area: {row.get('area_distributed')}",
                f"  Distribution date: {row.get('distribution_date')}",
                "",
            ]
        )
    return "\n".join(lines)
