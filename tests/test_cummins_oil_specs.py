import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "Maintenance" / "Seeds"
CUMMINS_ENGINE_CODES = {
    "DODGE_6BT",
    "DODGE_6BT-P7100",
    "DODGE_6BT5.9",
    "DODGE_ISB",
    "DODGE_ISB-CM2100",
    "DODGE_ISB-CM849",
    "DODGE_ISB-CM850",
    "DODGE_ISB-CR",
    "DODGE_ISB-VP44",
    "DODGE_ISB24V",
    "DODGE_ISB5.9-CR",
    "DODGE_ISB6.7",
}


class CumminsOilSpecTests(unittest.TestCase):
    def test_live_cummins_variants_use_verified_diesel_oil(self):
        document = json.loads(
            (SEEDS / "oil_specs_seed.json").read_text(encoding="utf-8")
        )
        items = {
            item["engine_code"]: item
            for item in document["items"]
            if item.get("engine_code") in CUMMINS_ENGINE_CODES
        }

        self.assertEqual(set(items), CUMMINS_ENGINE_CODES)
        for item in items.values():
            self.assertEqual(item["oil_spec_key"], "api_ck4_15w40")
            self.assertEqual(item["status"], "OEM_VERIFIED")
            self.assertTrue(item["verified"])


if __name__ == "__main__":
    unittest.main()
