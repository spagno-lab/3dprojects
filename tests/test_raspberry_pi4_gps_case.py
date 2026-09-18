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
        # 1.0 mm side clearance, from pkoehlers/rpi-case-openscad, which uses
        # 1.2 for the same board. The 0.4 this once had was below what FDM
        # resolves across an 85 mm pocket.
        self.assertAlmostEqual(layout['x'], 3.5)
        self.assertAlmostEqual(layout['y'], 3.5)
        self.assertAlmostEqual(layout['mount_x'], 7.0)
        self.assertAlmostEqual(layout['mount_y'], 7.0)
        self.assertAlmostEqual(layout['bottom_z'], 5.5)
        self.assertAlmostEqual(layout['top_z'], 7.1)

    def test_pi_io_openings_are_derived_from_assembled_board_datum(self):
        openings = {opening['name']: opening
                    for opening in module.pi_io_openings()}

        # Every connector opening starts at the parting plane and is open at
        # its bottom edge, so the shell can come down over the board.
        expected = {
            'USB-C opening': ('front', 8.4, 13.8, 7.1, 5.3),
            'Micro-HDMI 1 opening': ('front', 24.7, 10.1, 7.1, 5.3),
            'Micro-HDMI 2 opening': ('front', 38.5, 10.1, 7.1, 5.3),
            'Audio opening': ('front', 52.3, 10.1, 7.1, 7.7),
            'USB 2 opening': ('right', 4.4, 16.3, 7.1, 16.4),
            'USB 3 opening': ('right', 21.4, 16.3, 7.1, 16.4),
            'Ethernet opening': ('right', 38.65, 19.5, 7.1, 14.4),
        }
        for name, (wall, start, span, z, height) in expected.items():
            opening = openings[name]
            self.assertEqual(opening['wall'], wall)
            self.assertAlmostEqual(opening['start'], start)
            self.assertAlmostEqual(opening['span'], span)
            self.assertAlmostEqual(opening['z'], z)
            self.assertAlmostEqual(opening['height'], height)
            self.assertAlmostEqual(opening['z'], module.PARTING_Z)
            self.assertTrue(opening['open_bottom'], name)
            self.assertEqual(opening['part'], 'shell')

        # The card sits under the board, so its slot belongs to the base and
        # stops at the parting plane.
        microsd = openings['MicroSD opening']
        self.assertEqual(microsd['wall'], 'left')
        self.assertAlmostEqual(microsd['start'], 22.545)
        self.assertEqual(microsd['span'], 18.0)
        self.assertAlmostEqual(microsd['z'], 3.0)
        self.assertAlmostEqual(microsd['z'] + microsd['height'],
                               module.PARTING_Z)
        self.assertEqual(microsd['part'], 'base')

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
    def test_pocket_is_sized_for_the_board_not_for_the_bare_pcb(self):
        self.assertEqual(
            module.CASE_INNER_LENGTH,
            module.PI_BOARD_LENGTH + 2 * module.PI_SIDE_CLEARANCE)
        self.assertEqual(
            module.CASE_INNER_WIDTH,
            module.PI_BOARD_WIDTH + 2 * module.PI_SIDE_CLEARANCE)
        self.assertEqual(
            module.PI_BOARD_EDGE_CLEARANCE, module.PI_SIDE_CLEARANCE)
        # This is the assumption that broke two prints. The Pi 4 is not
        # 85 x 56: the USB and Ethernet stack stands 2.81 mm outside the PCB
        # outline, so no pocket sized to the PCB can ever be entered from the
        # side. The clearance is a printing fit, and the connectors are
        # handled by splitting the case instead.
        self.assertGreaterEqual(module.PI_SIDE_CLEARANCE, 0.8)
        self.assertLessEqual(module.PI_SIDE_CLEARANCE, 1.5)
        self.assertGreater(module.PI_CONNECTOR_PROUD_RIGHT,
                           module.PI_SIDE_CLEARANCE)

    def test_no_screw_posts_and_nothing_in_the_mounting_holes(self):
        source = script.read_text()
        self.assertNotIn('Pi post', source)
        self.assertNotIn('PI_PEG_DIAMETER', source)

    def _part_features(self, builder):
        """Capture what one part builder emits, without touching Fusion."""
        cylinders, rectangles = [], []

        def capture_cylinder(comp, name, cx, cy, z, diameter, height,
                             operation='join', participant_bodies=None):
            cylinders.append({'name': name, 'x': cx, 'y': cy, 'z': z})
            return mock.Mock()

        def capture_rectangle(comp, name, x, y, z, length, width, height,
                              operation='new-body', participant_bodies=None):
            rectangles.append({
                'name': name, 'x': x, 'y': y, 'z': z,
                'length': length, 'width': width, 'height': height,
                'operation': operation,
            })
            return mock.Mock()

        with mock.patch.object(module, 'cylinder_feature', capture_cylinder), \
                mock.patch.object(module, 'gps_sma_wall_features'), \
                mock.patch.object(module, 'rectangle_feature', capture_rectangle):
            builder()
        return cylinders, rectangles

    def test_board_is_trapped_between_the_base_and_the_shell(self):
        """Nothing snaps over the board any more. It sits on four standoffs in
        the base and the shell comes down and holds it there."""
        cylinders, base = self._part_features(lambda: module.base_plate(None))
        _, shell = self._part_features(lambda: module.shell(None))

        self.assertEqual(
            len([c for c in cylinders if 'standoff' in c['name']]), 4)
        self.assertEqual(len([c for c in cylinders if 'peg' in c['name']]), 0)
        self.assertFalse(hasattr(module, 'PI_PEG_DIAMETER'))

        pads = [r for r in shell if 'press pad' in r['name']]
        self.assertEqual(len(pads), len(module.PI_PADS))

        # The pads reach below the parting plane, so the board is clamped
        # rather than free to rattle between the standoffs and the shell.
        for pad in pads:
            self.assertLess(pad['z'], module.PARTING_Z)
            self.assertAlmostEqual(module.PARTING_Z - pad['z'],
                                   module.PI_PAD_PRELOAD)

        # And the base wall stops at the parting plane, so no connector ever
        # meets it.
        outer = next(r for r in base if r['name'] == 'Base outer body')
        self.assertAlmostEqual(outer['height'], module.PARTING_Z)

    def test_retention_never_crosses_a_port_opening(self):
        """The right wall is all USB and Ethernet and the left wall carries the
        microSD slot, so everything that holds anything lives in the free
        stretches. This is the check the rear lips failed."""
        for pad_name, rect, _z, _h in module.pi_pad_layout():
            wall = pad_name.split()[3]
            for opening in module.pi_io_openings():
                if opening['wall'] != wall:
                    continue
                if wall in ('front', 'rear'):
                    lo, hi = rect[0], rect[0] + rect[2]
                else:
                    lo, hi = rect[1], rect[1] + rect[3]
                overlaps = not (hi <= opening['start']
                                or lo >= opening['start'] + opening['span'])
                self.assertFalse(
                    overlaps, f"{pad_name} crosses {opening['name']}")

        for index, tab in enumerate(module.base_tab_layout(), 1):
            arm = tab['arm']
            for opening in module.pi_io_openings():
                if opening['wall'] != tab['wall']:
                    continue
                if tab['wall'] in ('front', 'rear'):
                    lo, hi = arm[0], arm[0] + arm[2]
                else:
                    lo, hi = arm[1], arm[1] + arm[3]
                overlaps = not (hi <= opening['start']
                                or lo >= opening['start'] + opening['span'])
                self.assertFalse(
                    overlaps, f"tab {index} crosses {opening['name']}")

    def test_nothing_that_holds_the_board_lands_on_a_component(self):
        """The rear lip that made the case unassemblable sat on top of the
        8.5 mm GPIO header, because clip placement and the reference body were
        worked out separately. They now share pi_component_footprints()."""
        layout = module.pi_layout()
        parts = module.pi_component_footprints()

        def clash(rect, other):
            ax, ay, al, aw = rect
            bx, by, bl, bw = other
            return (min(ax + al, bx + bl) - max(ax, bx) > 1e-9
                    and min(ay + aw, by + bw) - max(ay, by) > 1e-9)

        for pad_name, rect, _z, _h in module.pi_pad_layout():
            for name, part_rect, _height in parts:
                self.assertFalse(clash(rect, part_rect),
                                 f'{pad_name} lands on {name}')

        for index, tab in enumerate(module.base_tab_layout(), 1):
            for name, part_rect, _height in parts:
                self.assertFalse(clash(tab['arm'], part_rect),
                                 f'tab {index} runs into {name}')

        # And each pad really does hold the board down.
        board = (layout['x'], layout['y'],
                 module.PI_BOARD_LENGTH, module.PI_BOARD_WIDTH)
        for pad_name, rect, _z, _h in module.pi_pad_layout():
            dx = min(rect[0] + rect[2], board[0] + board[2]) - max(rect[0], board[0])
            dy = min(rect[1] + rect[3], board[1] + board[3]) - max(rect[1], board[1])
            self.assertAlmostEqual(min(dx, dy), module.PI_PAD_REACH)

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
                mock.patch.object(module, 'gps_sma_wall_features'), \
                mock.patch.object(module, 'rectangle_mesh_feature'), \
                mock.patch.object(module, 'rectangle_feature',
                                  side_effect=capture(case_features)):
            module.shell(None)

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

    def test_outside_of_the_case_stays_flat(self):
        """No bosses, no bumps: every added feature must stay within the
        outer footprint. The snap joint fits inside the wall instead of
        growing one outward to make room for itself."""
        outer_l = module.CASE_INNER_LENGTH + 2 * module.WALL
        outer_w = module.CASE_INNER_WIDTH + 2 * module.WALL
        features = []

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body', participant_bodies=None):
            features.append({
                'name': name, 'x': x, 'y': y,
                'length': length, 'width': width, 'operation': operation,
            })
            return mock.Mock()

        for builder, outer_name in ((module.shell, 'Shell outer body'),
                                    (module.base_plate, 'Base outer body')):
            features.clear()
            with mock.patch.object(module, 'cylinder_feature'), \
                    mock.patch.object(module, 'gps_sma_wall_features'), \
                    mock.patch.object(module, 'rectangle_feature',
                                      side_effect=capture):
                builder(None)

            for feature in features:
                if feature['name'] == outer_name:
                    continue
                if feature['operation'] == \
                        module.adsk.fusion.FeatureOperations.CutFeatureOperation:
                    continue
                self.assertGreaterEqual(feature['x'], 0.0, feature['name'])
                self.assertGreaterEqual(feature['y'], 0.0, feature['name'])
                self.assertLessEqual(
                    feature['x'] + feature['length'], outer_l, feature['name'])
                self.assertLessEqual(
                    feature['y'] + feature['width'], outer_w, feature['name'])

        self.assertFalse(hasattr(module, 'BASE_TAB_BOSS'))
        self.assertNotIn('tab boss', script.read_text())

        # And the joint really does fit inside the wall.
        skin = (module.WALL - module.BASE_TAB_THICKNESS
                - module.BASE_TAB_CLEARANCE - module.BASE_TAB_BUMP)
        self.assertGreaterEqual(skin, 0.8)

    def test_both_snaps_stay_within_the_strain_petg_tolerates(self):
        """Cantilever snap strain, 1.5 * t * deflection / L^2. PETG yields
        around 5 per cent; the clip once sat at 10 and the lid latch at 60."""
        def strain(thickness, deflection, length):
            return 1.5 * thickness * deflection / length ** 2

        # The snap tabs are the only flexing feature left on the case.
        tab = strain(module.BASE_TAB_THICKNESS, module.BASE_TAB_BUMP,
                     module.BASE_TAB_BUMP_CENTRE)
        self.assertLess(tab, 0.05)
        # The bump has to sit near the tip, which is what keeps it there.
        self.assertGreater(module.BASE_TAB_HEIGHT, module.BASE_TAB_BUMP_CENTRE)

        free_rim = module.LID_RIM_HEIGHT - module.LID_LATCH_BELOW_TOP
        latch = strain(module.LID_RIM_THICKNESS, module.LID_LATCH_DEPTH,
                       free_rim)
        self.assertLess(latch, 0.05)

    def test_the_case_parts_on_the_top_face_of_the_pcb(self):
        """Above that plane the board is gone and only its connectors remain,
        which is what lets every opening be open at its bottom edge."""
        self.assertAlmostEqual(module.PARTING_Z, module.pi_layout()['top_z'])
        self.assertAlmostEqual(
            module.PARTING_Z,
            module.FLOOR + module.PI_STANDOFF_HEIGHT
            + module.PI_BOARD_THICKNESS)

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
        # 0.25 mm is the PETG sliding fit; what matters is that the latch
        # engages far more than the clearance.
        self.assertLessEqual(module.LID_RIM_CLEARANCE, 0.3)
        self.assertGreaterEqual(
            module.LID_LATCH_DEPTH, 2 * module.LID_RIM_CLEARANCE)
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


class PiReferenceBodyTest(unittest.TestCase):
    def _features(self):
        features = []
        first = mock.Mock()
        first.bodies.item.return_value = mock.Mock()

        def capture(comp, name, x, y, z, length, width, height,
                    operation='new-body', participant_bodies=None):
            features.append({
                'name': name, 'x': x, 'y': y, 'z': z,
                'length': length, 'width': width, 'height': height,
                'operation': operation,
                'participants': participant_bodies,
            })
            return first

        with mock.patch.object(module, 'rectangle_feature', side_effect=capture):
            module.pi_reference(None)
        return features

    def test_reference_is_one_body_at_the_assembled_datum(self):
        features = self._features()
        board = features[0]
        layout = module.pi_layout()

        self.assertEqual(board['name'], 'Pi reference PCB')
        self.assertEqual(
            (board['length'], board['width'], board['height']),
            (module.PI_BOARD_LENGTH, module.PI_BOARD_WIDTH,
             module.PI_BOARD_THICKNESS))
        self.assertAlmostEqual(board['x'], layout['x'])
        self.assertAlmostEqual(board['y'], layout['y'])
        self.assertAlmostEqual(board['z'], layout['bottom_z'])

        # Everything else joins that one body so it stays removable.
        for feature in features[1:]:
            self.assertEqual(
                feature['operation'],
                module.adsk.fusion.FeatureOperations.JoinFeatureOperation)
            self.assertIsNotNone(feature['participants'])

    def test_every_connector_lands_inside_its_opening(self):
        """This is the point of the body: if a connector misses here, it will
        miss in plastic too."""
        features = self._features()
        openings = {o['name']: o for o in module.pi_io_openings()}

        checked = 0
        for feature in features:
            name = feature['name'].replace('Pi reference ', '') + ' opening'
            opening = openings.get(name)
            if opening is None:
                continue
            checked += 1
            if opening['wall'] == 'front':
                start, end = feature['x'], feature['x'] + feature['length']
            else:
                start, end = feature['y'], feature['y'] + feature['width']
            self.assertGreaterEqual(start, opening['start'])
            self.assertLessEqual(end, opening['start'] + opening['span'])
            self.assertGreaterEqual(feature['z'], opening['z'])
            self.assertLessEqual(
                feature['z'] + feature['height'],
                opening['z'] + opening['height'])
        self.assertEqual(checked, 7)

    def test_board_and_gps_cradle_do_not_share_the_same_space(self):
        features = self._features()
        tallest = max(f['z'] + f['height'] for f in features)
        lid_inner = module.FLOOR + module.CASE_INNER_HEIGHT
        cradle_drop = (module.GPS_BACK_COMPONENT_DEPTH + module.GPS_FIT_CLEARANCE
                       + module.GPS_BOARD_THICKNESS + 0.8)
        self.assertGreater(lid_inner - cradle_drop - tallest, 1.0)


if __name__ == '__main__':
    unittest.main()
