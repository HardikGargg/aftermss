"""Signup, 10 km nearby match, nearest rider. No LLM."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.fromisoformat("2026-09-08T14:30:00+05:30")


class PlatformTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="aftermess_web_")
        os.environ["AFTERMESS_DATA_DIR"] = self.tmp
        src = ROOT / "data" / "aftermess"
        shutil.copy(src / "directory.json", Path(self.tmp) / "directory.json")
        shutil.copy(src / "config.json", Path(self.tmp) / "config.json")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_preset_radius(self):
        from aftermess.geo import PRESETS, haversine, nearby_km

        pins = {row["id"]: row for row in PRESETS}
        limit = nearby_km()
        self.assertEqual(limit, 10)
        self.assertLess(haversine(pins["iiitd"]["lat"], pins["iiitd"]["lng"], pins["saket"]["lat"], pins["saket"]["lng"]), limit)
        self.assertGreater(haversine(pins["iiitd"]["lat"], pins["iiitd"]["lng"], pins["cp"]["lat"], pins["cp"]["lng"]), limit)
        self.assertGreater(haversine(pins["iiitd"]["lat"], pins["iiitd"]["lng"], pins["dwarka"]["lat"], pins["dwarka"]["lng"]), limit)

    def _party(self, role, name, phone, pin, preset, **extra):
        from aftermess.accounts import register
        from aftermess.geo import PRESETS

        area = {row["id"]: row for row in PRESETS}[preset]
        payload = {
            "role": role,
            "display_name": name,
            "phone": phone,
            "pin": pin,
            "area": area["label"],
            "lat": area["lat"],
            "lng": area["lng"],
            "fssai": extra.get("fssai", "DEMO-FSSAI-1"),
            "veg_policy": extra.get("veg_policy", "veg_only"),
            "upi_id": extra.get("upi_id", ""),
        }
        me, _token = register(payload)
        return me

    def _release(self, row, plates):
        from aftermess.platform import post_release

        return post_release(
            row,
            {
                "plates": plates,
                "dishes": "dal, rice",
                "veg": "veg",
                "unused_not_served": True,
                "prep_at": "2026-09-08T13:00:00+05:30",
                "use_by": "2026-09-08T18:00:00+05:30",
                "temp_c": 65,
                "packed_covered": True,
                "insulated": True,
                "perishable": True,
            },
            sitting="lunch",
            now=NOW,
        )

    def test_nearby_match_and_pay(self):
        from aftermess import store
        from aftermess.accounts import row_by_id
        from aftermess.platform import act, board, post_need

        ngo = self._party("ngo", "Seva Kitchen", "9000000001", "1234", "iiitd", veg_policy="veg_only", fssai="DEMO-SFDO-1")
        mess_big = self._party("mess", "North Mess", "9000000002", "1234", "iiitd", veg_policy="veg", fssai="DEMO-FBO-NORTH")
        mess_small = self._party("mess", "Kalkaji Mess", "9000000003", "1234", "kalkaji", veg_policy="veg", fssai="DEMO-FBO-KALK")
        mess_far = self._party("mess", "Dwarka Mess", "9000000004", "1234", "dwarka", veg_policy="veg", fssai="DEMO-FBO-DWK")
        rider_a = self._party("rider", "Rider A", "9000000005", "1234", "iiitd", upi_id="a@oksbi")
        rider_b = self._party("rider", "Rider B", "9000000006", "1234", "govindpuri", upi_id="b@oksbi")
        self._party("rider", "Rider Far", "9000000007", "1234", "dwarka", upi_id="far@oksbi")

        post_need(row_by_id(ngo["id"]), plates=40, sitting="lunch", now=NOW)
        self._release(row_by_id(mess_big["id"]), 20)
        second = self._release(row_by_id(mess_small["id"]), 15)
        self.assertIn("35 plates matched", second["message"])
        far = self._release(row_by_id(mess_far["id"]), 50)
        self.assertIn("unchanged", far["message"])

        trips = store.trips_for("2026-09-08", "lunch")
        self.assertEqual(len(trips), 1)
        trip = trips[0]
        self.assertEqual(trip["plates"], 35)
        self.assertEqual(set(trip["assigned_plates"]), {mess_big["id"], mess_small["id"]})
        self.assertNotIn(mess_far["id"], trip["assigned_plates"])
        self.assertEqual(trip["rider_id"], rider_a["id"])

        view = board(row_by_id(ngo["id"]), "lunch", now=NOW)
        names = [item["display_name"] for item in view["nearby"]]
        self.assertIn("Kalkaji Mess", names)
        self.assertIn("Rider B", names)
        self.assertNotIn("Dwarka Mess", names)
        self.assertNotIn("Rider Far", names)

        act(row_by_id(rider_a["id"]), trip["id"], "cancel")
        trip = store.get_trip(trip["id"])
        self.assertEqual(trip["rider_id"], rider_b["id"])
        act(row_by_id(rider_b["id"]), trip["id"], "accept")
        act(row_by_id(rider_b["id"]), trip["id"], "picked")
        act(row_by_id(rider_b["id"]), trip["id"], "dropped")
        act(row_by_id(ngo["id"]), trip["id"], "received")
        paid = act(row_by_id(ngo["id"]), trip["id"], "paid")
        self.assertEqual(paid["state"], "settled")
        self.assertEqual(len(store.load_runtime()["schedule_ii"]), 2)
        mess_record = board(row_by_id(mess_big["id"]), "lunch", now=NOW)["record"]
        self.assertEqual(mess_record["plates_handed_over"], 20)
        self.assertTrue(mess_record["item_7"])
        self.assertEqual(mess_record["rows"][0]["plates"], 20)
        self.assertEqual(mess_record["rows"][0]["kitchen"], "Seva Kitchen")
        card = board(row_by_id(ngo["id"]), "lunch", now=NOW)["trips"][0]
        self.assertEqual(card["state"], "settled")

    def test_unsafe_release_does_not_match(self):
        from aftermess import store
        from aftermess.accounts import row_by_id
        from aftermess.platform import post_need, post_release

        ngo = self._party("ngo", "Seva Kitchen", "9000000011", "1234", "iiitd")
        mess = self._party("mess", "North Mess", "9000000012", "1234", "iiitd", veg_policy="veg", fssai="DEMO-FBO-NORTH")
        post_need(row_by_id(ngo["id"]), plates=10, sitting="lunch", now=NOW)
        refused = post_release(
            row_by_id(mess["id"]),
            {
                "plates": 10,
                "dishes": "dal",
                "veg": "veg",
                "unused_not_served": False,
                "prep_at": "2026-09-08T13:00:00+05:30",
                "use_by": "2026-09-08T18:00:00+05:30",
                "temp_c": 65,
                "packed_covered": True,
                "insulated": True,
            },
            sitting="lunch",
            now=NOW,
        )
        self.assertFalse(refused["ok"])
        self.assertIn("never served", refused["message"])
        self.assertEqual(store.trips_for("2026-09-08", "lunch"), [])

    def test_http_register_login_and_page(self):
        from fastapi.testclient import TestClient

        from aftermess.geo import PRESETS
        from aftermess.server import create_app

        pin = {row["id"]: row for row in PRESETS}["iiitd"]
        client = TestClient(create_app())
        page = client.get("/app")
        self.assertEqual(page.status_code, 200)
        self.assertIn("After", page.text)
        self.assertIn("food is free", page.text)

        body = {
            "role": "ngo",
            "display_name": "Seva Kitchen",
            "phone": "9000000021",
            "pin": "4321",
            "area": pin["label"],
            "lat": pin["lat"],
            "lng": pin["lng"],
            "fssai": "DEMO-SFDO-WEB",
            "veg_policy": "veg_only",
        }
        created = client.post("/api/register", json=body)
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["me"]["role"], "ngo")
        again = client.post("/api/register", json=body)
        self.assertEqual(again.status_code, 400)

        bad = client.post("/api/login", json={"phone": "9000000021", "pin": "0000"})
        self.assertEqual(bad.status_code, 400)
        client.post("/api/logout")
        denied = client.get("/api/board")
        self.assertEqual(denied.status_code, 401)
        good = client.post("/api/login", json={"phone": "9000000021", "pin": "4321"})
        self.assertEqual(good.status_code, 200)
        board = client.get("/api/board?sitting=lunch")
        self.assertEqual(board.status_code, 200)
        self.assertTrue(board.json()["need_open"])
