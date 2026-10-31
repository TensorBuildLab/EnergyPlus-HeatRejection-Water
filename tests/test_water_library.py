"""The sourced water library loads for every site x treatment and gives physical cycles."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from tower_water.chemistry import ChemistryModel  # noqa: E402

LIB = os.path.join(ROOT, "data", "water_sources_sourced.json")


class TestSourcedLibrary(unittest.TestCase):
    def test_all_pairs(self):
        lib = json.load(open(LIB))
        self.assertEqual(len(lib["sources"]), 14)
        for s, src in lib["sources"].items():
            self.assertTrue(src.get("source_url"), s)
            for t, tr in lib["treatments"].items():
                for mode in ("constituent", "dynamic"):
                    n, which = ChemistryModel.from_library(LIB, s, t, None, mode).cycles(t_hot=35.0, t_cold=27.0)
                    self.assertGreaterEqual(n, tr.get("min_cycles", 1.5))
                    self.assertLessEqual(n, tr.get("max_cycles", 10.0))

    def test_hard_water_limits_cycles(self):
        # Colorado River water (Phoenix) must be more limited than soft Bull Run water (Portland)
        t = "evapco_galvanized_inhibitor"
        phx = ChemistryModel.from_library(LIB, "phoenix_tmyx", t).cycles()[0]
        pdx = ChemistryModel.from_library(LIB, "portland_or", t).cycles()[0]
        self.assertLess(phx, pdx)


if __name__ == "__main__":
    unittest.main()
