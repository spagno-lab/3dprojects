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
        self.assertEqual(module.GPS_PIN_FORWARD, 5.0)
        self.assertEqual(module.GPS_PIN_DROP, 8.0)
        self.assertEqual(module.SMA_BASE_LENGTH, 7.0)
        self.assertEqual(module.SMA_BASE_WIDTH, 7.0)
        self.assertEqual(module.SMA_BASE_DEPTH, 1.0)
        self.assertEqual(module.SMA_THREAD_DIAMETER, 5.0)
        self.assertEqual(module.SMA_PROJECTION, 8.0)
        self.assertEqual(module.SMA_CENTER_FROM_RIGHT, 3.5)
        self.assertEqual(module.SMA_HOLE_DIAMETER, 5.6)
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
        lid_body = object()
        lid_feature = mock.Mock()
        lid_feature.bodies.item.return_value = lid_body

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body', participant_bodies=None):
            features.append((name, x, y, z, length, width, height, operation))
            return lid_feature if name == 'Lid' else mock.Mock()

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture), \
                mock.patch.object(module, 'rectangle_mesh_feature') as mesh:
            module.lid(None, 110.0)

        names = {feature[0] for feature in features}
        self.assertIn('GPS left edge support', names)
        self.assertIn('GPS right edge support', names)
        self.assertIn('GPS front stop left', names)
        self.assertIn('GPS front stop right', names)
        self.assertNotIn('GPS rear stop left', names)
        self.assertNotIn('GPS rear stop right', names)
        self.assertTrue(all(min(feature[4:7]) > 0 for feature in features))
        self.assertIs(mesh.call_args.args[1], lid_body)

    def test_pi_board_datum_matches_official_mounting_pattern(self):
        layout = module.pi_layout()

        self.assertEqual(module.PI_BOARD_LENGTH, 85.0)
        self.assertEqual(module.PI_BOARD_WIDTH, 56.0)
        self.assertEqual(module.PI_MOUNT_X, 58.0)
        self.assertEqual(module.PI_MOUNT_Y, 49.0)
        self.assertEqual(module.PI_MOUNT_EDGE_OFFSET, 3.5)
        self.assertEqual(module.PI_MOUNT_HOLE_DIAMETER, 3.0)
        self.assertAlmostEqual(layout['x'], 4.9)
        self.assertAlmostEqual(layout['y'], 4.9)
        self.assertAlmostEqual(layout['mount_x'], 8.4)
        self.assertAlmostEqual(layout['mount_y'], 8.4)
        self.assertAlmostEqual(layout['bottom_z'], 6.4)
        self.assertAlmostEqual(layout['top_z'], 8.0)

    def test_pi_io_openings_are_derived_from_assembled_board_datum(self):
        openings = {opening['name']: opening
                    for opening in module.pi_io_openings()}

        expected = {
            'USB-C opening': ('front', 9.8, 13.8, 7.2, 6.1),
            'Micro-HDMI 1 opening': ('front', 26.1, 10.1, 7.2, 6.1),
            'Micro-HDMI 2 opening': ('front', 39.9, 10.1, 7.2, 6.1),
            'Audio opening': ('front', 53.7, 10.1, 7.2, 8.5),
            'USB 2 opening': ('right', 5.8, 16.3, 7.2, 17.2),
            'USB 3 opening': ('right', 22.8, 16.3, 7.2, 17.2),
            'Ethernet opening': ('right', 40.05, 19.5, 7.2, 15.2),
        }
        for name, (wall, start, span, z, height) in expected.items():
            opening = openings[name]
            self.assertEqual(opening['wall'], wall)
            self.assertAlmostEqual(opening['start'], start)
            self.assertAlmostEqual(opening['span'], span)
            self.assertAlmostEqual(opening['z'], z)
            self.assertAlmostEqual(opening['height'], height)

        microsd = openings['MicroSD opening']
        self.assertEqual(microsd['wall'], 'left')
        self.assertAlmostEqual(microsd['start'], 23.945)
        self.assertEqual(microsd['span'], 18.0)
        self.assertAlmostEqual(microsd['z'], 4.0)
        self.assertEqual(microsd['height'], 8.0)

    def test_lid_mesh_has_two_millimetre_ribs_and_avoids_gps_cradle(self):
        outer_l = module.CASE_INNER_LENGTH + 2 * module.WALL
        outer_w = module.CASE_INNER_WIDTH + 2 * module.WALL
        cells, gps_keepout = module.lid_mesh_layout(outer_l, outer_w, 110.0)

        self.assertGreater(len(cells), 40)
        self.assertEqual(module.LID_MESH_PITCH - module.LID_MESH_OPENING, 2.0)
        self.assertTrue(all(
            110.0 + module.LID_MESH_EDGE_MARGIN <= cell[0]
            and cell[0] + cell[2] <= 110.0 + outer_l - module.LID_MESH_EDGE_MARGIN
            and module.LID_MESH_EDGE_MARGIN <= cell[1]
            and cell[1] + cell[3] <= outer_w - module.LID_MESH_EDGE_MARGIN
            for cell in cells
        ))
        self.assertTrue(all(
            not module.rectangles_overlap(cell, gps_keepout)
            for cell in cells
        ))

    def test_body_has_round_sma_hole_at_axis_and_two_millimetre_local_wall(self):
        holes = []
        case_body = object()

        def capture(comp, target_body, name, center_x, center_z, wall_y,
                    diameter, depth):
            self.assertIs(target_body, case_body)
            holes.append((name, center_x, center_z, wall_y, diameter, depth))

        with mock.patch.object(module, 'rear_wall_hole', side_effect=capture):
            outer_l = module.CASE_INNER_LENGTH + 2 * module.WALL
            outer_w = module.CASE_INNER_WIDTH + 2 * module.WALL
            outer_h = module.CASE_INNER_HEIGHT + module.FLOOR
            module.gps_sma_wall_features(
                None, case_body, outer_l, outer_w, outer_h)

        by_name = {hole[0]: hole for hole in holes}
        opening = by_name['GPS SMA hole']
        recess = by_name['GPS SMA outside recess']
        self.assertEqual(opening[4], 5.6)
        self.assertEqual(recess[4], 7.6)
        self.assertAlmostEqual(
            recess[5] - 0.2, module.WALL - module.SMA_LOCAL_WALL)
        axis_below_lid_inner_face = (
            module.GPS_BACK_COMPONENT_DEPTH + module.GPS_FIT_CLEARANCE
            + module.GPS_BOARD_THICKNESS / 2
        )
        lid_layout = module.gps_cradle_layout(outer_l, outer_w)
        self.assertAlmostEqual(
            opening[1], outer_l - lid_layout['sma_center_x'])
        self.assertAlmostEqual(
            outer_l - opening[1], lid_layout['sma_center_x'])
        self.assertAlmostEqual(
            opening[2], outer_h - axis_below_lid_inner_face)
        self.assertAlmostEqual(opening[2], 27.1)

    def test_rear_wall_hole_converts_model_coordinates_and_targets_case_body(self):
        comp = mock.Mock()
        plane_input = mock.Mock()
        plane = object()
        sketch = mock.Mock()
        model_center = object()
        sketch_center = object()
        target_body = object()
        extrude_input = mock.Mock()
        feature = mock.Mock()

        comp.constructionPlanes.createInput.return_value = plane_input
        comp.constructionPlanes.add.return_value = plane
        comp.sketches.add.return_value = sketch
        sketch.modelToSketchSpace.return_value = sketch_center
        comp.features.extrudeFeatures.createInput.return_value = extrude_input
        comp.features.extrudeFeatures.add.return_value = feature

        point3d = types.SimpleNamespace(create=mock.Mock(return_value=model_center))
        with mock.patch.object(module.adsk.core, 'Point3D', point3d, create=True), \
                mock.patch.object(module, 'value', side_effect=lambda mm: mm):
            result = module.rear_wall_hole(
                comp, target_body, 'GPS SMA hole',
                53.4, 24.7, 65.6, 5.6, 4.4,
            )

        point3d.create.assert_called_once_with(
            module.cm(53.4), module.cm(65.6), module.cm(24.7))
        sketch.modelToSketchSpace.assert_called_once_with(model_center)
        sketch.sketchCurves.sketchCircles.addByCenterRadius.assert_called_once_with(
            sketch_center, module.cm(2.8))
        self.assertEqual(extrude_input.participantBodies, [target_body])
        extrude_input.setSymmetricExtent.assert_called_once_with(4.4, False)
        self.assertIs(result, feature)

    def test_gps_reference_models_measured_module_parts(self):
        features = []
        gps_body = mock.Mock()
        first_feature = mock.Mock()
        first_feature.bodies.item.return_value = gps_body

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body', participant_bodies=None):
            features.append((name, x, y, z, length, width, height, operation))
            return first_feature if name == 'GPS reference PCB' else mock.Mock()

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.gps_reference(None, 110.0)

        pcb, keepout, sma_base, sma_thread, *pin_legs = features
        self.assertEqual(pcb[0], 'GPS reference PCB')
        self.assertEqual(pcb[4:7], (18.0, 23.0, 1.6))
        self.assertEqual(pcb[7], 'new-body')
        self.assertEqual(keepout[0], 'GPS reference component keepout')
        self.assertEqual(keepout[6], 8.0)
        self.assertEqual(sma_base[0], 'GPS reference SMA base')
        self.assertEqual(sma_base[4:7], (7.0, 7.0, 1.0))
        self.assertEqual(sma_thread[0], 'GPS reference SMA thread')
        self.assertEqual(sma_thread[4:7], (5.0, 8.0, 5.0))
        self.assertEqual(len(pin_legs), 10)
        forward_legs = [leg for leg in pin_legs if leg[0].endswith('forward')]
        drop_legs = [leg for leg in pin_legs if leg[0].endswith('drop')]
        self.assertEqual(len(forward_legs), 5)
        self.assertEqual(len(drop_legs), 5)
        self.assertTrue(all(
            leg[6] == module.GPS_PIN_FORWARD + module.GPS_JOIN_OVERLAP
            for leg in forward_legs
        ))
        self.assertTrue(all(
            leg[5] == module.GPS_PIN_DROP + module.GPS_PIN_WIDTH / 2
            for leg in drop_legs
        ))
        self.assertTrue(all(leg[7] == 'join' for leg in pin_legs))
        self.assertEqual(gps_body.name, 'GPS module - removable fit reference')
        self.assertEqual(
            pcb[1] + pcb[4] - (sma_thread[1] + sma_thread[4] / 2),
            module.SMA_CENTER_FROM_RIGHT,
        )

    def test_five_pin_bank_is_centred_and_keeps_corner_latches_clear(self):
        features = []
        first_feature = mock.Mock()
        first_feature.bodies.item.return_value = mock.Mock()

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body', participant_bodies=None):
            features.append((name, x, y, z, length, width, height, operation))
            return first_feature if name == 'GPS reference PCB' else mock.Mock()

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.gps_reference(None, 110.0)

        pins = [feature for feature in features
                if feature[0].endswith('forward')]
        pin_left = min(pin[1] for pin in pins)
        pin_right = max(pin[1] + pin[4] for pin in pins)
        pcb = features[0]
        self.assertGreater(pin_left - pcb[1], module.GPS_EDGE_SUPPORT_WIDTH)
        self.assertGreater(pcb[1] + pcb[4] - pin_right,
                           module.GPS_EDGE_SUPPORT_WIDTH)


if __name__ == '__main__':
    unittest.main()
