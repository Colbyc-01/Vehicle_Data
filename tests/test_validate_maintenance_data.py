import json
import tempfile
import unittest
from pathlib import Path

from Maintenance.Utils.validate_maintenance_data import Audit, CATEGORIES, Category, record_identity


class MaintenanceAuditTests(unittest.TestCase):
    def test_flags_incompatible_oil_and_inline_filter_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seeds = root / "Maintenance" / "Seeds"
            canonical = root / "data" / "canonical"
            seeds.mkdir(parents=True)
            canonical.mkdir(parents=True)

            self.write(canonical / "vehicles.json", {"vehicles": []})
            self.write(
                canonical / "engines.json",
                {"DIESEL_67": {"fuel_type": "Diesel", "displacement_l": 6.7, "cylinders": 6}},
            )
            self.write(
                seeds / "oil_specs_seed.json",
                {"items": [{"engine_code": "DIESEL_67", "oil_spec_key": "ms_6395_5w20"}]},
            )
            self.write(seeds / "oil_product_groups.json", {"items": {"ms_6395_5w20": {}}})
            self.write(
                seeds / "oil_change_parts_seed.json",
                {
                    "items": [
                        {
                            "engine_code": "DIESEL_67",
                            "oil_filter_group": "FILTER_A",
                            "oil_filter": {"oem": {"brand": "Wrong", "part_number": "1"}},
                        }
                    ]
                },
            )
            self.write(
                seeds / "oil_filter_groups.json",
                {"FILTER_A": {"oem": {"brand": "Correct", "part_number": "2"}}},
            )

            audit = Audit(root)
            audit.engines = audit.load(canonical / "engines.json")
            audit.audit_category(next(category for category in CATEGORIES if category.name == "oil_specs"))
            audit.audit_category(next(category for category in CATEGORIES if category.name == "oil_filters"))

            codes = {issue.code for issue in audit.issues}
            self.assertIn("diesel_gas_oil", codes)
            self.assertIn("inline_group_mismatch", codes)

    def test_part_without_number_or_name_is_warning(self):
        audit = Audit(Path("."))

        audit.audit_group_parts("wiper_blades", "WIPER_TEST", {"oem": {"brand": "Acme"}})

        self.assertEqual(audit.issues[0].code, "unsearchable_part")
        self.assertEqual(audit.issues[0].severity, "warning")

    def test_vehicle_year_ranges_have_distinct_identities(self):
        category = Category("wipers", "wipers.json", "vehicle_key")

        first = record_identity(category, {"vehicle_key": "ram_2500", "years": [2010, 2012]})
        second = record_identity(category, {"vehicle_key": "ram_2500", "years": [2013, 2018]})

        self.assertNotEqual(first, second)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
