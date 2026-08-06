import json
import unittest
from collections import Counter
from pathlib import Path

from Maintenance.Utils.validate_maintenance_data import Audit


REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS = REPO_ROOT / "Maintenance" / "Seeds"


class MaintenanceReleaseReadinessTests(unittest.TestCase):
    @staticmethod
    def _load_spark_plug_docs():
        seed_items = json.loads(
            (SEEDS / "spark_plug_seed.json").read_text(encoding="utf-8")
        )["items"]
        groups = json.loads(
            (SEEDS / "spark_plug_groups.json").read_text(encoding="utf-8")
        )["groups"]
        vehicles = json.loads(
            (REPO_ROOT / "data" / "canonical" / "vehicles.json").read_text(encoding="utf-8")
        )["vehicles"]
        return seed_items, groups, vehicles

    def test_release_targets_have_no_blockers(self):
        report = Audit().run()

        self.assertEqual(report["summary"]["release_blockers"], 0)
        self.assertEqual(report["categories"]["spark_plugs"].get("warning", 0), 0)

    def test_13b_rew_uses_ngk_manufacturer_application(self):
        seed_items, groups, _ = self._load_spark_plug_docs()

        seed = next(item for item in seed_items if item["engine_code"] == "MAZDA_13B-REW")
        group = groups[seed["plug_group"]]

        self.assertTrue(seed["verified"])
        self.assertEqual(group["qty_per_engine"], 4)
        self.assertEqual(group["primary"]["brand"], "NGK")
        self.assertEqual(group["primary"]["part_number"], "BUR9EQP")
        self.assertIn("ngkntk.com", group["primary"]["source_url"])

    def test_verified_spark_plug_records_reference_exact_part_numbers(self):
        seed_items, groups, _ = self._load_spark_plug_docs()

        for item in seed_items:
            if item.get("verified") is not True:
                continue
            group = groups[item["plug_group"]]
            primary = group.get("primary", {})

            self.assertTrue(
                primary.get("brand") and primary.get("part_number"),
                msg=f"{item['engine_code']} missing verified primary part details",
            )

    def test_top_common_verified_spark_plug_groups_have_bosch_ngk_champion_options(self):
        seed_items, groups, vehicles = self._load_spark_plug_docs()
        verified_by_engine = {
            item["engine_code"]: item
            for item in seed_items
            if item.get("verified") is True
        }
        vehicle_counts = Counter()
        for vehicle in vehicles:
            for engine_code in vehicle.get("engine_codes") or []:
                if engine_code in verified_by_engine:
                    vehicle_counts[engine_code] += 1

        specialist_primary_parts = {"BUR9EQP", "PFR7S8EG"}
        ranked_common_engines = []
        for engine_code, _ in vehicle_counts.most_common():
            group = groups[verified_by_engine[engine_code]["plug_group"]]
            primary_part = (group.get("primary") or {}).get("part_number")
            if primary_part in specialist_primary_parts:
                continue
            ranked_common_engines.append(engine_code)

        self.assertGreaterEqual(len(ranked_common_engines), 100)

        for engine_code in ranked_common_engines[:150]:
            group = groups[verified_by_engine[engine_code]["plug_group"]]
            primary = group.get("primary", {})
            alternatives = group.get("alternatives", [])
            brand_to_part_number = {}
            if primary.get("brand"):
                brand_to_part_number[primary["brand"]] = primary.get("part_number")
            for alternative in alternatives:
                brand = alternative.get("brand")
                if brand:
                    brand_to_part_number[brand] = alternative.get("part_number")

            for brand in ("Bosch", "NGK", "Champion"):
                self.assertTrue(
                    brand_to_part_number.get(brand),
                    msg=f"{engine_code} missing {brand} part number",
                )

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
