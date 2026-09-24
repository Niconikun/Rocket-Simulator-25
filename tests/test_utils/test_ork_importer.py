import os
import tempfile
import unittest

from src.utils.ork_importer import OrkExporter, OrkImporter


class TestOrkRoundTrip(unittest.TestCase):
    def test_export_then_import_preserves_geometry(self):
        config = {
            "name": "RoundTrip",
            "initial_mass": 2.0,
            "geometry": {"total_length": 1.5},
            "nosecone": {
                "shape": "haack",
                "length": 0.2,
                "diameter": 0.08,
                "ogive_radius": 0.4,
                "haack_type": "LD-Haack",
            },
            "fuselage": {"length": 1.0, "diameter": 0.08},
            "rear_section": {"length": 0.3, "diameter": 0.08},
            "fins": {
                "N_fins": 3,
                "span": 0.05,
                "chord_root": 0.12,
                "chord_tip": 0.04,
                "mid_chord": 0.08,
                "sweep_angle": 20.0,
            },
            "engine": {},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "roundtrip.ork")
            OrkExporter(config).export(path)
            parsed = OrkImporter(path).parse()

        self.assertAlmostEqual(parsed["nosecone"]["diameter"], 0.08, places=5)
        self.assertEqual(parsed["nosecone"]["haack_type"], "LD-Haack")
        self.assertAlmostEqual(parsed["fuselage"]["length"], 1.0, places=5)
        self.assertAlmostEqual(parsed["fuselage"]["diameter"], 0.08, places=5)
        self.assertEqual(parsed["fins"]["N_fins"], 3)
        self.assertAlmostEqual(parsed["fins"]["sweep_angle"], 20.0, places=3)


if __name__ == "__main__":
    unittest.main()