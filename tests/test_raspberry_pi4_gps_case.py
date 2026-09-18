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
        # The first print was too tight around the SMA: hole opened by 2 mm.
        self.assertEqual(module.SMA_HOLE_DIAMETER, 7.6)
        self.assertEqual(module.SMA_LOCAL_WALL, 2.0)
        self.assertGreater(module.SMA_RECESS_DIAMETER, module.SMA_HOLE_DIAMETER)

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
        self.assertEqual(module.PI_MOUNT_HOLE_DIAMETER, 2.7)
        # 1 mm side clearance: the measured reference case puts the mounting
        # holes at 6.95 mm, the old 2.5 mm clearance pushed them to 8.4 mm and
        # moved the connectors away from their openings.
        self.assertAlmostEqual(layout['x'], 2.9)
        self.assertAlmostEqual(layout['y'], 2.9)
        self.assertAlmostEqual(layout['mount_x'], 6.4)
        self.assertAlmostEqual(layout['mount_y'], 6.4)
        self.assertAlmostEqual(layout['bottom_z'], 5.5)
        self.assertAlmostEqual(layout['top_z'], 7.1)

    def test_pi_io_openings_are_derived_from_assembled_board_datum(self):
        openings = {opening['name']: opening
                    for opening in module.pi_io_openings()}

        expected = {
            'USB-C opening': ('front', 7.8, 13.8, 6.3, 6.1),
            'Micro-HDMI 1 opening': ('front', 24.1, 10.1, 6.3, 6.1),
            'Micro-HDMI 2 opening': ('front', 37.9, 10.1, 6.3, 6.1),
            'Audio opening': ('front', 51.7, 10.1, 6.3, 8.5),
            'USB 2 opening': ('right', 3.8, 16.3, 6.3, 17.2),
            'USB 3 opening': ('right', 20.8, 16.3, 6.3, 17.2),
            'Ethernet opening': ('right', 38.05, 19.5, 6.3, 15.2),
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
        self.assertAlmostEqual(microsd['start'], 21.945)
        self.assertEqual(microsd['span'], 18.0)
        self.assertAlmostEqual(microsd['z'], 3.0)
        self.assertEqual(microsd['height'], 8.0)

    def test_lid_mesh_has_two_millimetre_ribs_and_avoids_gps_cradle(self):
        outer_l = module.CASE_INNER_LENGTH + 2 * module.WALL
        outer_w = module.CASE_INNER_WIDTH + 2 * module.WALL
        cells, gps_keepout = module.lid_mesh_layout(outer_l, outer_w, 110.0)

        # 34 cells with the 90.8 x 61.8 footprint and the GPS keep-out.
        self.assertGreaterEqual(len(cells), 30)
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
        self.assertEqual(opening[4], 7.6)
        self.assertEqual(recess[4], 9.6)
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
        self.assertAlmostEqual(opening[2], 27.2)

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
                53.4, 24.7, 65.6, 7.6, 4.4,
            )

        point3d.create.assert_called_once_with(
            module.cm(53.4), module.cm(65.6), module.cm(24.7))
        sketch.modelToSketchSpace.assert_called_once_with(model_center)
        sketch.sketchCurves.sketchCircles.addByCenterRadius.assert_called_once_with(
            sketch_center, module.cm(3.8))
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


class ScrewlessRetentionTest(unittest.TestCase):
    def test_cavity_hugs_the_pcb_so_connectors_reach_their_openings(self):
        self.assertEqual(
            module.CASE_INNER_LENGTH,
            module.PI_BOARD_LENGTH + 2 * module.PI_SIDE_CLEARANCE)
        self.assertEqual(
            module.CASE_INNER_WIDTH,
            module.PI_BOARD_WIDTH + 2 * module.PI_SIDE_CLEARANCE)
        self.assertEqual(
            module.PI_BOARD_EDGE_CLEARANCE, module.PI_SIDE_CLEARANCE)
        self.assertLessEqual(module.PI_SIDE_CLEARANCE, 1.0)

    def test_no_screw_posts_and_nothing_in_the_mounting_holes(self):
        source = script.read_text()
        self.assertNotIn('Pi post', source)
        self.assertNotIn('PI_PEG_DIAMETER', source)

    def _retention_features(self):
        cylinders, rectangles = [], []

        def capture_cylinder(comp, name, cx, cy, z, diameter, height,
                             operation='join', participant_bodies=None):
            cylinders.append({'name': name, 'x': cx, 'y': cy, 'z': z})

        def capture_rectangle(comp, name, x, y, z, length, width, height,
                              operation='new-body', participant_bodies=None):
            rectangles.append({
                'name': name, 'x': x, 'y': y, 'z': z,
                'length': length, 'width': width, 'height': height,
                'operation': operation,
            })

        with mock.patch.object(module, 'cylinder_feature', capture_cylinder), \
                mock.patch.object(module, 'rectangle_feature', capture_rectangle):
            module.pi_retention(None)
        return cylinders, rectangles

    def test_retention_is_tilt_and_snap_with_nothing_in_the_holes(self):
        cylinders, rectangles = self._retention_features()

        # Four supports, and deliberately no peg: a peg would block the tilt.
        self.assertEqual(len([c for c in cylinders if 'standoff' in c['name']]), 4)
        self.assertEqual(len([c for c in cylinders if 'peg' in c['name']]), 0)
        self.assertFalse(hasattr(module, 'PI_PEG_DIAMETER'))

        lips = [r for r in rectangles if 'retaining lip' in r['name']]
        hooks = [r for r in rectangles if 'clip hook' in r['name']]
        self.assertEqual(len(lips), 2)
        self.assertEqual(len(hooks), 2)

    def test_retention_never_crosses_a_port_opening(self):
        """The right wall is all USB and Ethernet and the left wall carries the
        microSD slot, so retention has to live in the free stretches."""
        _, rectangles = self._retention_features()
        layout = module.pi_layout()
        board_x = layout['x']
        board_y = layout['y']

        for opening in module.pi_io_openings():
            for feature in rectangles:
                if not feature['name'].startswith('Pi clip'):
                    continue
                if opening['wall'] == 'front' and feature['y'] < board_y:
                    overlaps = not (
                        feature['x'] + feature['length'] <= opening['start']
                        or feature['x'] >= opening['start'] + opening['span'])
                    self.assertFalse(
                        overlaps,
                        f"{feature['name']} crosses {opening['name']}")
                if opening['wall'] == 'left' and feature['x'] < board_x:
                    overlaps = not (
                        feature['y'] + feature['width'] <= opening['start']
                        or feature['y'] >= opening['start'] + opening['span'])
                    self.assertFalse(
                        overlaps,
                        f"{feature['name']} crosses {opening['name']}")

    def test_clips_actually_grip_the_board_and_can_flex(self):
        """The first attempt had hooks tangent to the PCB edge and arms buried
        in the wall, so nothing retained the board and nothing could bend."""
        rectangles = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body', participant_bodies=None):
            rectangles.append({
                'name': name, 'x': x, 'y': y, 'z': z,
                'length': length, 'width': width, 'height': height,
                'operation': operation,
            })

        with mock.patch.object(module, 'cylinder_feature'), \
                mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.pi_retention(None)

        layout = module.pi_layout()
        board_x = (layout['x'], layout['x'] + module.PI_BOARD_LENGTH)
        board_y = (layout['y'], layout['y'] + module.PI_BOARD_WIDTH)

        def overlap(feature, axis):
            if axis == 'x':
                return (min(feature['x'] + feature['length'], board_x[1])
                        - max(feature['x'], board_x[0]))
            return (min(feature['y'] + feature['width'], board_y[1])
                    - max(feature['y'], board_y[0]))

        # Every retaining feature must actually sit over the board.
        for lip in [r for r in rectangles if 'retaining lip' in r['name']]:
            self.assertAlmostEqual(overlap(lip, 'y'), module.PI_LIP_OVERHANG)
        for hook in [r for r in rectangles if 'clip hook' in r['name']]:
            axis = 'y' if hook['name'].endswith('front') else 'x'
            self.assertAlmostEqual(overlap(hook, axis), module.PI_CLIP_OVERHANG)

        # The arm can only bend by the width of its relief slot.
        self.assertGreater(module.PI_CLIP_RELIEF, module.PI_CLIP_OVERHANG)

        reliefs = [r for r in rectangles if 'clip relief' in r['name']]
        self.assertEqual(len(reliefs), 2)
        for relief in reliefs:
            self.assertEqual(relief['operation'],
                             module.adsk.fusion.FeatureOperations.CutFeatureOperation)
            # Blind slot: the locally thickened wall must survive behind it.
            remaining = (module.PI_CLIP_BOSS + module.WALL - module.PI_CLIP_RELIEF
                         - module.PI_CLIP_THICKNESS - module.PI_SIDE_CLEARANCE
                         - module.PI_CLIP_EDGE_GAP)
            self.assertGreaterEqual(remaining, 1.2)

        self.assertEqual(
            len([r for r in rectangles if 'clip arm' in r['name']]), 2)

    def test_every_lid_bump_has_a_matching_pocket_in_the_case(self):
        """A bump with no pocket does not latch, it just stops the lid from
        closing: the pockets were lost in an earlier reconciliation."""
        lid_features, case_features = [], []

        def capture(store):
            def inner(comp, name, x, y, z, length, width, height,
                      operation='new-body', participant_bodies=None):
                store.append({
                    'name': name, 'x': x, 'y': y, 'z': z,
                    'length': length, 'width': width, 'height': height,
                    'operation': operation,
                })
                return mock.Mock()
            return inner

        with mock.patch.object(module, 'rectangle_mesh_feature'), \
                mock.patch.object(module, 'rectangle_feature',
                                  side_effect=capture(lid_features)):
            module.lid(None, 110.0)
        with mock.patch.object(module, 'cylinder_feature'), \
                mock.patch.object(module, 'pi_retention'), \
                mock.patch.object(module, 'gps_sma_wall_features'), \
                mock.patch.object(module, 'rectangle_mesh_feature'), \
                mock.patch.object(module, 'rectangle_feature',
                                  side_effect=capture(case_features)):
            module.body_shell(None)

        bumps = [r for r in lid_features if 'latch bump' in r['name']]
        pockets = [r for r in case_features if 'latch pocket' in r['name']]
        self.assertEqual(len(bumps), 4)
        self.assertEqual(len(pockets), len(bumps))

        for pocket in pockets:
            self.assertEqual(
                pocket['operation'],
                module.adsk.fusion.FeatureOperations.CutFeatureOperation)
            # The pocket must be at least as deep and as tall as the bump.
            self.assertGreaterEqual(pocket['width'], module.LID_LATCH_DEPTH)
            self.assertGreaterEqual(pocket['height'], module.LID_LATCH_HEIGHT)

        # Bump and pocket must sit at the same depth below the case rim.
        bump_depth = module.LID_RIM_HEIGHT - (bumps[0]['z'] - module.LID_THICKNESS)
        pocket_depth = (module.FLOOR + module.CASE_INNER_HEIGHT
                        - pockets[0]['z'])
        self.assertAlmostEqual(bump_depth, pocket_depth)

    def test_side_clearance_alone_locates_the_board(self):
        # Without pegs the cavity itself has to hold the board laterally.
        self.assertLessEqual(module.PI_SIDE_CLEARANCE, 0.5)

    def test_every_opening_stays_inside_the_board_footprint(self):
        layout = module.pi_layout()
        for opening in module.pi_io_openings():
            start, span = opening['start'], opening['span']
            if opening['wall'] == 'front':
                self.assertGreaterEqual(start, layout['x'] - 1.0)
                self.assertLessEqual(
                    start + span, layout['x'] + module.PI_BOARD_LENGTH + 1.0)
            else:
                self.assertGreaterEqual(start, layout['y'] - 1.0)
                self.assertLessEqual(
                    start + span, layout['y'] + module.PI_BOARD_WIDTH + 1.0)

    def test_lid_latches_engage_instead_of_floating(self):
        # The first print failed because the rim cleared the wall by 0.6 mm.
        self.assertLessEqual(module.LID_RIM_CLEARANCE, 0.2)
        self.assertGreater(module.LID_LATCH_DEPTH, module.LID_RIM_CLEARANCE)

        case_latches = module.lid_latch_positions()
        lid_latches = module.lid_latch_positions(110.0)
        self.assertEqual(len(case_latches['x_positions']), 2)
        for lid_x, case_x in zip(lid_latches['x_positions'],
                                 case_latches['x_positions']):
            self.assertAlmostEqual(lid_x - 110.0, case_x)

    def test_lid_bumps_and_case_pockets_share_the_same_height(self):
        rectangles = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body', participant_bodies=None):
            rectangles.append((name, x, y, z, length, width, height))
            return mock.Mock()

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture), \
                mock.patch.object(module, 'rectangle_mesh_feature'):
            module.lid(None, 110.0)

        bumps = [r for r in rectangles if 'latch bump' in r[0]]
        self.assertEqual(len(bumps), 4)
        bump_z = {round(r[3], 3) for r in bumps}
        self.assertEqual(len(bump_z), 1)

        expected = (module.LID_THICKNESS + module.LID_RIM_HEIGHT
                    - module.LID_LATCH_BELOW_TOP)
        self.assertAlmostEqual(bump_z.pop(), expected)


if __name__ == '__main__':
    unittest.main()
