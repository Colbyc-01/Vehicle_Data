import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "Maintenance" / "Seeds"
ENGINE_CODE = "GM_LWC"


def seed_item(filename):
    document = json.loads((SEEDS / filename).read_text(encoding="utf-8"))
    return next(
        item for item in document["items"] if item.get("engine_code") == ENGINE_CODE
    )


class GmLwcOilDataTests(unittest.TestCase):
    def test_16l_diesel_uses_verified_dexos2_oil(self):
        oil_spec = seed_item("oil_specs_seed.json")

        self.assertEqual(oil_spec["oil_spec_key"], "gm_dexos2_5w30")
        self.assertEqual(oil_spec["status"], "OEM_VERIFIED")
        self.assertTrue(oil_spec["verified"])

    def test_16l_diesel_uses_oem_capacity(self):
        oil_capacity = seed_item("oil_capacity_seed.json")

        self.assertEqual(oil_capacity["capacity_quarts_with_filter"], 5.3)
        self.assertEqual(oil_capacity["capacity_label_with_filter"], "5.3 qt (with filter)")


if __name__ == "__main__":
    unittest.main()
