"""Unit tests for parse, safety, match, rider walk, Schedule II. No LLM."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class AfterMessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="aftermess_")
        os.environ["AFTERMESS_DATA_DIR"] = self.tmp
        src = ROOT / "data" / "aftermess"
        shutil.copy(src / "directory.json", Path(self.tmp) / "directory.json")
        shutil.copy(src / "config.json", Path(self.tmp) / "config.json")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_parse_need(self):
        from aftermess.parse import parse_inbound

        got = parse_inbound("NEED 40 LUNCH VEG")
        self.assertEqual(got["intent"], "need")
        self.assertEqual(got["plates"], 40)
        self.assertEqual(got["sitting"], "lunch")
        self.assertEqual(got["veg_policy"], "veg_only")
        zero = parse_inbound("NEED 0 DINNER")
        self.assertEqual(zero["plates"], 0)

    def test_parse_release_incomplete(self):
        from aftermess.parse import parse_inbound

        got = parse_inbound("RELEASE 15 VEG veg")
        self.assertEqual(got["intent"], "release_incomplete")
        self.assertIn("temp_c", got["missing"])

    def test_safety_requires_temp_and_unused(self):
        from aftermess.safety import check_release

        mess = {"fssai_fbo": "DEMO-FBO-MESSA", "display_name": "Mess A"}
        cfg = json.loads((Path(self.tmp) / "config.json").read_text(encoding="utf-8"))
        now = datetime.fromisoformat("2026-09-08T14:30:00+05:30")
        bad = {
            "plates": 10,
            "dishes": "dal",
            "veg": "veg",
            "unused_not_served": False,
            "prep_at": "2026-09-08T13:00:00+05:30",
            "use_by": "2026-09-08T18:00:00+05:30",
            "temp_c": None,
            "packed_covered": True,
            "insulated": True,
        }
        reasons = check_release(bad, mess, cfg, now)
        self.assertIn("not_unused_unserved", reasons)
        self.assertIn("temperature_missing", reasons)

    def test_fill_one_drop(self):
        from aftermess.config import load_directory
        from aftermess.match import plan_trips

        directory = load_directory()
        needs = [
            {
                "id": "n1",
                "drop_id": "drop_a",
                "plates": 40,
                "veg_policy": "veg_only",
                "created_at": "2026-09-08T10:00:00+00:00",
            },
            {
                "id": "n2",
                "drop_id": "drop_b",
                "plates": 20,
                "veg_policy": "nonveg_ok",
                "created_at": "2026-09-08T10:05:00+00:00",
            },
        ]
        releases = [
            {
                "id": "r1",
                "mess_id": "mess_a",
                "plates": 15,
                "veg": "veg",
                "status": "offered",
            },
            {
                "id": "r2",
                "mess_id": "mess_b",
                "plates": 20,
                "veg": "veg",
                "status": "offered",
            },
        ]
        trips = plan_trips(needs, releases, directory)
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]["drop_id"], "drop_a")
        self.assertEqual(trips[0]["plates"], 35)
        self.assertEqual(trips[0]["assigned_plates"]["mess_a"], 15)
        self.assertEqual(trips[0]["assigned_plates"]["mess_b"], 20)

    def test_veg_only_skips_nonveg(self):
        from aftermess.config import load_directory
        from aftermess.match import plan_trips

        trips = plan_trips(
            [
                {
                    "id": "n1",
                    "drop_id": "drop_a",
                    "plates": 40,
                    "veg_policy": "veg_only",
                    "created_at": "a",
                }
            ],
            [
                {
                    "id": "r1",
                    "mess_id": "mess_a",
                    "plates": 30,
                    "veg": "nonveg",
                    "status": "offered",
                }
            ],
            load_directory(),
        )
        self.assertEqual(trips, [])

    def test_demo_loop_schedule_ii_and_idempotency(self):
        from aftermess import store
        from aftermess.loop import handle_inbound, remind_rider_pay, sitting_status, tick

        store.reset_runtime()
        now = datetime.fromisoformat("2026-09-08T14:30:00+05:30")
        date = "2026-09-08"
        sitting = "lunch"
        rel = (
            "RELEASE {n} DISHES dal,rice VEG veg UNUSED yes "
            "PREP 2026-09-08T13:00:00+05:30 USEBY 2026-09-08T18:00:00+05:30 "
            "TEMP 65 PACKED yes INSULATED yes BATCH fresh-cooked PERISHABLE yes"
        )

        def send(party: str, text: str, message_id: str | None = None):
            return handle_inbound(
                party,
                text,
                message_id=message_id or store.new_id("msg"),
                sitting=sitting,
                sitting_date=date,
                now=now,
            )

        first = send("drop_a", "NEED 40 LUNCH VEG", "need-a-1")
        self.assertTrue(first.get("ok"))
        dup = send("drop_a", "NEED 40 LUNCH VEG", "need-a-1")
        self.assertTrue(dup.get("duplicate"))
        send("drop_b", "NEED 20 LUNCH EITHER")
        self.assertEqual(len(store.needs_for(date, sitting)), 2)

        early_match = tick(sitting, "match", date, now)
        self.assertEqual(early_match.get("error"), "waiting_for_mess")

        tick(sitting, "needs_cutoff", date, now)
        tick(sitting, "closeout", date, now)
        send("mess_a", rel.format(n=15))
        send("mess_b", rel.format(n=20))
        matched = tick(sitting, "match", date, now)
        self.assertEqual(matched.get("match_result"), "matched")
        trips = store.trips_for(date, sitting)
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]["plates"], 35)
        self.assertEqual(trips[0]["rider_id"], "rider_1")

        send("rider_1", "CANCEL")
        trip = store.trips_for(date, sitting)[0]
        self.assertEqual(trip["rider_id"], "rider_2")
        send("rider_2", "ACCEPT")
        send("rider_2", "PICKED")
        send("rider_2", "DROPPED")
        rec = send("drop_a", "RECEIVED")
        self.assertTrue(rec.get("schedule_ii"))
        paid = send("drop_a", "PAID")
        self.assertTrue(paid.get("ok"))
        trip = store.trips_for(date, sitting)[0]
        self.assertEqual(trip["state"], "settled")
        self.assertEqual(len(store.load_runtime()["schedule_ii"]), 2)

        other = send("drop_b", "PAID")
        self.assertFalse(other.get("ok"))
        self.assertFalse(remind_rider_pay(trip["id"]).get("ok"))
        status = sitting_status(date, sitting)
        self.assertEqual(status["plates_moved"], 35)

    def test_whatsapp_env_overlay(self):
        os.environ["AFTERMESS_WA_MESS_A"] = "+919876543210"
        try:
            from aftermess.config import party_by_whatsapp

            party = party_by_whatsapp("whatsapp:+919876543210")
            self.assertIsNotNone(party)
            self.assertEqual(party["id"], "mess_a")
        finally:
            os.environ.pop("AFTERMESS_WA_MESS_A", None)

    def test_http_ping_and_demo(self):
        from fastapi.testclient import TestClient

        from aftermess.server import create_app

        client = TestClient(create_app())
        ping = client.get("/ping")
        self.assertEqual(ping.status_code, 200)
        self.assertEqual(ping.json()["status"], "healthy")
        demo = client.post("/invocations", json={"input": {"prompt": "demo"}})
        self.assertEqual(demo.status_code, 200)
        moved = demo.json()["output"]["status"]["plates_moved"]
        self.assertEqual(moved, 35)


if __name__ == "__main__":
    unittest.main()
