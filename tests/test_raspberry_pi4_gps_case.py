import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


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
    def test_user_measured_dimensions(self):
        self.assertEqual(module.GPS_BOARD_WIDTH, 18.0)
        self.assertEqual(module.GPS_BOARD_LENGTH, 23.0)
        self.assertEqual(module.SMA_PROJECTION, 10.0)
        self.assertEqual(module.SMA_CENTER_FROM_RIGHT, 6.0)
        self.assertEqual(module.SMA_SLOT_WIDTH, 9.0)

    def test_cradle_centres_board_and_faces_offset_sma_toward_rear(self):
        outer_l = module.CASE_INNER_LENGTH + 2 * module.WALL
        outer_w = module.CASE_INNER_WIDTH + 2 * module.WALL
        layout = module.gps_cradle_layout(outer_l, outer_w, 110.0)

        self.assertEqual(layout['center_x'], 110.0 + outer_l / 2)
        self.assertEqual(
            layout['x'] + module.GPS_BOARD_WIDTH - layout['sma_center_x'],
            module.SMA_CENTER_FROM_RIGHT,
        )
        right_clip_inner_x = (
            layout['x'] + module.GPS_BOARD_WIDTH + module.CLEARANCE
        )
        self.assertAlmostEqual(
            right_clip_inner_x - layout['sma_center_x'],
            module.SMA_CENTER_FROM_RIGHT + module.CLEARANCE,
        )
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
        self.assertEqual(
            layout['sma_tip_y'] - layout['rear_y'],
            module.SMA_PROJECTION,
        )

    def test_rear_right_stop_does_not_obstruct_offset_sma(self):
        features = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body'):
            features.append((name, x, y, z, length, width, height, operation))

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.lid(None, 110.0)

        names = {feature[0] for feature in features}
        self.assertIn('GPS rear stop left', names)
        self.assertNotIn('GPS rear stop right', names)
        self.assertTrue(all(min(feature[4:7]) > 0 for feature in features))


if __name__ == '__main__':
    unittest.main()
