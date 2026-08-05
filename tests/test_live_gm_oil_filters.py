import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "Maintenance" / "Seeds"
PF66_ENGINE_CODES = {"GM_L3T", "GM_LM2", "GM_LSY"}


class LiveGmOilFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parts = json.loads(
            (SEEDS / "oil_change_parts_seed.json").read_text(encoding="utf-8")
        )
        cls.items = {item["engine_code"]: item for item in parts["items"]}
        cls.groups = json.loads(
            (SEEDS / "oil_filter_groups.json").read_text(encoding="utf-8")
        )

    def test_live_pf66_records_match_filter_group(self):
        expected = self.groups["ACDELCO_PF66"]

        for engine_code in PF66_ENGINE_CODES:
            item = self.items[engine_code]
            self.assertEqual(item["oil_filter_group"], "ACDELCO_PF66")
            self.assertEqual(item["oil_filter"], expected)

    def test_l82_uses_current_pf63_filter(self):
        item = self.items["GM_L82_V8_GEN5_53"]

        self.assertEqual(item["oil_filter_group"], "ACDELCO_PF63")
        self.assertEqual(item["oil_filter"], self.groups["ACDELCO_PF63"])
        self.assertEqual(item["oil_filter"]["oem"]["part_number"], "PF63")


if __name__ == "__main__":
    unittest.main()
