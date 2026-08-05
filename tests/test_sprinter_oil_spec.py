import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_CODE = "CHRYSLER_ENF"


class SprinterOilSpecTests(unittest.TestCase):
    def test_live_27l_diesel_uses_verified_mb_oil(self):
        document = json.loads(
            (
                ROOT / "Maintenance" / "Seeds" / "oil_specs_seed.json"
            ).read_text(encoding="utf-8")
        )
        item = next(
            item
            for item in document["items"]
            if item.get("engine_code") == ENGINE_CODE
        )

        self.assertEqual(item["oil_spec_key"], "mb_2295_0w40")
        self.assertEqual(item["status"], "OEM_VERIFIED")
        self.assertTrue(item["verified"])


if __name__ == "__main__":
    unittest.main()
