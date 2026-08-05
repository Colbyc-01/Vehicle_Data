import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "Maintenance" / "Seeds"
ENGINE_CODE = "CHRYSLER_ETK"


def seed_item(filename):
    document = json.loads((SEEDS / filename).read_text(encoding="utf-8"))
    return next(
        item for item in document["items"] if item.get("engine_code") == ENGINE_CODE
    )


class RamCumminsMaintenanceDataTests(unittest.TestCase):
    def test_67l_cummins_uses_diesel_oil_spec_and_capacity(self):
        oil_spec = seed_item("oil_specs_seed.json")
        oil_capacity = seed_item("oil_capacity_seed.json")

        self.assertEqual(oil_spec["oil_spec_key"], "api_ck4_15w40")
        self.assertEqual(oil_capacity["capacity_quarts_with_filter"], 12.0)

    def test_67l_cummins_uses_cummins_filter_group(self):
        oil_parts = seed_item("oil_change_parts_seed.json")

        self.assertEqual(oil_parts["oil_filter_group"], "MOPAR_05083285AA")
        self.assertEqual(oil_parts["oil_filter"]["oem"]["part_number"], "05083285AA")


if __name__ == "__main__":
    unittest.main()
