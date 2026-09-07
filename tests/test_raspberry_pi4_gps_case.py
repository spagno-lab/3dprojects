import importlib.util
import sys
import types
import unittest
from pathlib import Path


adsk = types.ModuleType('adsk')
adsk.core = types.ModuleType('adsk.core')
adsk.fusion = types.ModuleType('adsk.fusion')
adsk.fusion.FeatureOperations = types.SimpleNamespace(
    NewBodyFeatureOperation='new-body',
    CutFeatureOperation='cut',
    JoinFeatureOperation='join',
)
sys.modules['adsk'] = adsk
sys.modules['adsk.core'] = adsk.core
sys.modules['adsk.fusion'] = adsk.fusion

script = (
    Path(__file__).parents[1]
    / 'raspberry-pi4-gps-case'
    / 'raspberry_pi4_gps_case.py'
)
spec = importlib.util.spec_from_file_location('raspberry_pi4_gps_case', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RaspberryPi4GpsCaseTest(unittest.TestCase):
    def test_photo_reference_dimensions(self):
        self.assertEqual(module.GPS_BOARD_WIDTH, 22.0)
        self.assertEqual(module.GPS_BOARD_LENGTH, 30.0)
        self.assertEqual(module.SMA_SLOT_WIDTH, 9.0)

    def test_cradle_centres_board_and_faces_sma_toward_rear(self):
        outer_l = module.CASE_INNER_LENGTH + 2 * module.WALL
        outer_w = module.CASE_INNER_WIDTH + 2 * module.WALL
        layout = module.gps_cradle_layout(outer_l, outer_w, 110.0)

        self.assertEqual(layout['center_x'], 110.0 + outer_l / 2)
        self.assertEqual(
            layout['rear_y'],
            outer_w
            - module.WALL
            - module.GPS_CLIP_THICKNESS
            - module.CLEARANCE,
        )
        self.assertEqual(
            layout['rear_y'] - layout['y'],
            module.GPS_BOARD_LENGTH,
        )


if __name__ == '__main__':
    unittest.main()
