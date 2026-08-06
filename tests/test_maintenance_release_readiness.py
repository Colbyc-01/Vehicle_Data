import json
import unittest
from pathlib import Path

from Maintenance.Utils.validate_maintenance_data import Audit


REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS = REPO_ROOT / "Maintenance" / "Seeds"


class MaintenanceReleaseReadinessTests(unittest.TestCase):
    def test_release_targets_have_no_blockers(self):
        report = Audit().run()

        self.assertEqual(report["summary"]["release_blockers"], 0)
        self.assertEqual(report["categories"]["spark_plugs"].get("warning", 0), 0)

    def test_13b_rew_uses_ngk_manufacturer_application(self):
        seed_items = json.loads(
            (SEEDS / "spark_plug_seed.json").read_text(encoding="utf-8")
        )["items"]
        groups = json.loads(
            (SEEDS / "spark_plug_groups.json").read_text(encoding="utf-8")
        )["groups"]

        seed = next(item for item in seed_items if item["engine_code"] == "MAZDA_13B-REW")
        group = groups[seed["plug_group"]]

        self.assertTrue(seed["verified"])
        self.assertEqual(group["qty_per_engine"], 4)
        self.assertEqual(group["primary"]["brand"], "NGK")
        self.assertEqual(group["primary"]["part_number"], "BUR9EQP")
        self.assertIn("ngkntk.com", group["primary"]["source_url"])

    def test_ram_truck_wiper_fitment_uses_verified_generation_sizes(self):
        seed_items = json.loads(
            (SEEDS / "wiper_seed.json").read_text(encoding="utf-8")
        )["items"]
        groups = json.loads(
            (SEEDS / "wiper_group.json").read_text(encoding="utf-8")
        )["groups"]

        ram_items = [
            item
            for item in seed_items
            if item["make"] == "Ram" and item["model"] in {"1500", "2500", "3500"}
        ]

        self.assertTrue(ram_items)
        self.assertTrue(all(item["coverage"] == "covered" for item in ram_items))
        for item in ram_items:
            group = groups[item["wiper_group_key"]]
            expected_size = 24 if item["model"] == "1500" and item["years"][0] >= 2019 else 22
            for position in item["required_positions"]:
                self.assertEqual(group["positions"][position]["spec"]["length_in"], expected_size)
                self.assertEqual(group["positions"][position]["spec"]["blade_type"], "beam")
                self.assertIn("rainx.com", group["positions"][position]["oem"]["source_url"])


if __name__ == "__main__":
    unittest.main()
