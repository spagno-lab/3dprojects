import importlib.util
import tempfile
import unittest
from pathlib import Path
import zipfile


script = (
    Path(__file__).parents[1]
    / 'raspberry-pi4-gps-case'
    / 'export_3mf.py'
)
spec = importlib.util.spec_from_file_location('export_3mf', script)
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class RaspberryPi4GpsCaseExportTest(unittest.TestCase):
    def test_recorded_primitives_translate_to_openscad(self):
        operations = [
            ('box', 'new', (0, 0, 1, 2, 3, 4)),
            ('cyl_z', 'join', (1, 2, 3, 4, 5)),
            ('cyl_y', 'cut', (1, 2, 3, 4, 5)),
            ('ellipse_z', 'cut', (1, 2, 3, 4, 2, 0.5, 5)),
        ]

        source = export.part_scad(operations, -1.0)

        self.assertIn('difference()', source)
        self.assertIn('cube([2,3,4])', source)
        self.assertIn('rotate([-90,0,0])', source)
        self.assertIn('scale([4,2,1])', source)
        self.assertIn('translate([0,0,-1])', source)

    def test_join_after_cut_is_not_removed_by_the_earlier_cut(self):
        operations = [
            ('box', 'new', (0, 0, 0, 10, 10, 2)),
            ('box', 'cut', (1, 1, 1, 8, 8, 2)),
            ('cyl_z', 'join', (5, 5, 1, 1, 4)),
        ]

        source = export.part_scad(operations)

        # The late join must wrap the earlier difference. Grouping every cut
        # at the end would erase standoffs that are added inside a cavity.
        self.assertLess(source.index('union()'), source.index('difference()'))

    def test_three_object_archive_is_valid_and_reproducible(self):
        vertices = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ]
        parts = [
            {
                'name': name,
                'vertices': vertices,
                'triangles': [(0, 1, 2)],
                'bounds': ((0.0, 0.0, 0.0), (1.0, 1.0, 0.0)),
            }
            for name in ('shell', 'lid', 'base')
        ]
        settings = b'{"print_settings_id":"test"}'

        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / 'first.3mf'
            second = Path(temp) / 'second.3mf'
            export.write_3mf(first, parts, settings)
            export.write_3mf(second, parts, settings)
            export.validate_3mf(first)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    archive.read('Metadata/project_settings.config'), settings)


if __name__ == '__main__':
    unittest.main()
