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
        self.assertEqual(module.GPS_MODULE_DEPTH, 8.0)
        self.assertEqual(module.GPS_PIN_COUNT, 5)
        self.assertEqual(module.GPS_PIN_LENGTH, 8.0)
        self.assertEqual(module.SMA_BASE_LENGTH, 7.0)
        self.assertEqual(module.SMA_BASE_WIDTH, 7.0)
        self.assertEqual(module.SMA_BASE_DEPTH, 1.0)
        self.assertEqual(module.SMA_THREAD_DIAMETER, 5.0)
        self.assertEqual(module.SMA_PROJECTION, 8.0)
        self.assertEqual(module.SMA_CENTER_FROM_RIGHT, 3.5)
        self.assertEqual(module.SMA_SLOT_WIDTH, 5.6)
        self.assertEqual(module.SMA_LOCAL_WALL, 2.0)

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
            layout['x'] + module.GPS_BOARD_WIDTH + module.GPS_FIT_CLEARANCE
        )
        self.assertAlmostEqual(
            right_clip_inner_x - layout['sma_center_x'],
            module.SMA_CENTER_FROM_RIGHT + module.GPS_FIT_CLEARANCE,
        )
        self.assertEqual(
            layout['rear_y'],
            outer_w - module.WALL,
        )
        self.assertEqual(
            layout['rear_y'] - layout['y'],
            module.GPS_BOARD_LENGTH,
        )
        self.assertEqual(
            layout['sma_tip_y'] - layout['rear_y'],
            module.SMA_PROJECTION,
        )

    def test_cradle_supports_edges_and_leaves_sma_and_pins_open(self):
        features = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body'):
            features.append((name, x, y, z, length, width, height, operation))

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.lid(None, 110.0)

        names = {feature[0] for feature in features}
        self.assertIn('GPS left edge support', names)
        self.assertIn('GPS right edge support', names)
        self.assertIn('GPS front stop left', names)
        self.assertIn('GPS front stop right', names)
        self.assertNotIn('GPS rear stop left', names)
        self.assertNotIn('GPS rear stop right', names)
        self.assertTrue(all(min(feature[4:7]) > 0 for feature in features))

    def test_body_has_narrow_sma_slot_and_two_millimetre_local_wall(self):
        features = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body'):
            features.append((name, x, y, z, length, width, height, operation))

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            outer_l = module.CASE_INNER_LENGTH + 2 * module.WALL
            outer_w = module.CASE_INNER_WIDTH + 2 * module.WALL
            outer_h = module.CASE_INNER_HEIGHT + module.FLOOR
            module.gps_sma_wall_features(None, outer_l, outer_w, outer_h)

        by_name = {feature[0]: feature for feature in features}
        opening = by_name['GPS SMA opening']
        recess = by_name['GPS SMA outside recess']
        self.assertEqual(opening[4], 5.6)
        self.assertEqual(opening[6], module.SMA_SLOT_HEIGHT + 1.0)
        self.assertAlmostEqual(recess[5] - 1.0,
                               module.WALL - module.SMA_LOCAL_WALL)
        self.assertEqual(recess[4], 7.6)

    def test_gps_reference_models_measured_module_parts(self):
        features = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body'):
            features.append((name, x, y, z, length, width, height, operation))

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.gps_reference(None, 110.0)

        pcb, keepout, sma_base, sma_thread, *pins = features
        self.assertEqual(pcb[0], 'GPS reference PCB')
        self.assertEqual(pcb[4:7], (18.0, 23.0, 1.6))
        self.assertEqual(pcb[7], 'new-body')
        self.assertEqual(keepout[0], 'GPS reference component keepout')
        self.assertEqual(keepout[6], 8.0)
        self.assertEqual(sma_base[0], 'GPS reference SMA base')
        self.assertEqual(sma_base[4:7], (7.0, 7.0, 1.0))
        self.assertEqual(sma_thread[0], 'GPS reference SMA thread')
        self.assertEqual(sma_thread[4:7], (5.0, 8.0, 5.0))
        self.assertEqual(len(pins), 5)
        self.assertTrue(all(pin[5] == 8.0 for pin in pins))
        self.assertTrue(all(pin[7] == 'join' for pin in pins))
        self.assertEqual(
            pcb[1] + pcb[4] - (sma_thread[1] + sma_thread[4] / 2),
            module.SMA_CENTER_FROM_RIGHT,
        )

    def test_five_pin_bank_is_centred_and_keeps_corner_latches_clear(self):
        features = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body'):
            features.append((name, x, y, z, length, width, height, operation))

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.gps_reference(None, 110.0)

        pins = [feature for feature in features
                if feature[0].startswith('GPS reference pin ')]
        pin_left = min(pin[1] for pin in pins)
        pin_right = max(pin[1] + pin[4] for pin in pins)
        pcb = features[0]
        self.assertGreater(pin_left - pcb[1], module.GPS_EDGE_SUPPORT_WIDTH)
        self.assertGreater(pcb[1] + pcb[4] - pin_right,
                           module.GPS_EDGE_SUPPORT_WIDTH)


if __name__ == '__main__':
    unittest.main()
