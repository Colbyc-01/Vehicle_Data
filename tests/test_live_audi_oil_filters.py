import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "Maintenance" / "Seeds"


class LiveAudiOilFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parts = json.loads(
            (SEEDS / "oil_change_parts_seed.json").read_text(encoding="utf-8")
        )
        cls.items = {item["engine_code"]: item for item in parts["items"]}
        cls.groups = json.loads(
            (SEEDS / "oil_filter_groups.json").read_text(encoding="utf-8")
        )

    def test_22t_five_cylinder_uses_spin_on_filter(self):
        item = self.items["AUDI_22TI5"]

        self.assertEqual(item["oil_filter_group"], "AUDI_06A115561B")
        self.assertEqual(item["oil_filter"], self.groups["AUDI_06A115561B"])

    def test_06d_filter_records_have_no_false_alternatives(self):
        expected = self.groups["AUDI_06D115562"]

        self.assertEqual(expected["alternatives"], [])
        engine_codes = {
            item["engine_code"]
            for item in self.items.values()
            if item.get("oil_filter_group") == "AUDI_06D115562"
        }
        for engine_code in engine_codes:
            item = self.items[engine_code]
            self.assertEqual(item["oil_filter_group"], "AUDI_06D115562")
            self.assertEqual(item["oil_filter"], expected)


if __name__ == "__main__":
    unittest.main()
