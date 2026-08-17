import importlib.util
import sys
import types
import unittest
from pathlib import Path


adsk = types.ModuleType('adsk')
adsk.core = types.ModuleType('adsk.core')
adsk.fusion = types.ModuleType('adsk.fusion')
adsk.fusion.BooleanTypes = types.SimpleNamespace(
    UnionBooleanType='union',
    DifferenceBooleanType='difference',
)
sys.modules['adsk'] = adsk
sys.modules['adsk.core'] = adsk.core
sys.modules['adsk.fusion'] = adsk.fusion

script = Path(__file__).parents[1] / 'bracelet-display-stand' / 'bracelet_display_stand.py'
spec = importlib.util.spec_from_file_location('bracelet_display_stand', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeManager:
    def __init__(self):
        self.operations = []

    def booleanOperation(self, target, tool, operation):
        self.operations.append((target, tool, operation))
        return True


class FakeBaseFeature:
    def __init__(self):
        self.name = None
        self.started = False
        self.finished = False

    def startEdit(self):
        self.started = True

    def finishEdit(self):
        self.finished = True


class BraceletDisplayStandTest(unittest.TestCase):
    def test_bar_is_added_as_one_body_after_union_and_cut(self):
        manager = FakeManager()
        bodies = [object(), object(), object()]
        module.adsk.fusion.TemporaryBRepManager = types.SimpleNamespace(
            get=lambda: manager,
        )
        module.cylinder_body = lambda *args: bodies.pop(0)

        base_feature = FakeBaseFeature()
        added = []
        result = types.SimpleNamespace(name=None)
        comp = types.SimpleNamespace(
            features=types.SimpleNamespace(
                baseFeatures=types.SimpleNamespace(add=lambda: base_feature),
            ),
            bRepBodies=types.SimpleNamespace(
                add=lambda body, feature: added.append((body, feature)) or result,
            ),
        )

        module.build_bar(comp)

        self.assertEqual(
            [operation for _, _, operation in manager.operations],
            ['union', 'difference'],
        )
        self.assertEqual(len(added), 1)
        self.assertIs(added[0][0], manager.operations[0][0])
        self.assertTrue(base_feature.started)
        self.assertTrue(base_feature.finished)
        self.assertEqual(result.name, 'Bracelet display bar')


if __name__ == '__main__':
    unittest.main()
