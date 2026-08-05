import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_CODE = "FORD_POWERSTROKE_30"


class FordPowerstrokeEngineKeyTests(unittest.TestCase):
    def test_canonical_key_matches_referenced_engine_code(self):
        engines = json.loads(
            (ROOT / "data" / "canonical" / "engines.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(ENGINE_CODE, engines)
        self.assertEqual(engines[ENGINE_CODE]["engine_code"], ENGINE_CODE)


if __name__ == "__main__":
    unittest.main()
