import unittest

try:
    from api.app_monolith import _find_by_vehicle_key
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal test environments
    _find_by_vehicle_key = None


@unittest.skipIf(_find_by_vehicle_key is None, "backend dependencies are not installed")
class YearSpecificVehicleLookupTests(unittest.TestCase):
    def test_duplicate_vehicle_keys_respect_seed_year_ranges(self):
        items = [
            {"vehicle_key": "ram_1500", "years": [2011, 2018], "group": "22-inch"},
            {"vehicle_key": "ram_1500", "years": [2019, 2024], "group": "24-inch"},
        ]

        self.assertEqual(_find_by_vehicle_key(items, "ram_1500", year=2018)["group"], "22-inch")
        self.assertEqual(_find_by_vehicle_key(items, "ram_1500", year=2019)["group"], "24-inch")

    def test_vehicle_lookup_without_seed_years_preserves_existing_behavior(self):
        item = {"vehicle_key": "ram_1500", "group": "default"}

        self.assertIs(_find_by_vehicle_key([item], "ram_1500", year=2024), item)


if __name__ == "__main__":
    unittest.main()
