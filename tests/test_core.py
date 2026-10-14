import os
import sys
import unittest

import FreeCAD as App


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from quickvarset_core import (  # noqa: E402
    QuickVarSetError,
    apply_input,
    parse_input,
)


class QuickVarSetCoreTests(unittest.TestCase):

    def setUp(self):
        self.doc = App.newDocument("QuickVarSetTest")
        self.varset = self.doc.addObject("App::VarSet", "VarSet")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def test_unit_slash_is_not_group_prefix(self):
        group, name, value, quantity = parse_input("Speed = 10 m/s")

        self.assertIsNone(group)
        self.assertEqual(name, "Speed")
        self.assertEqual(value, "10 m/s")
        self.assertEqual(quantity.Unit.Type, "Velocity")

    def test_velocity_value_creates_velocity_property(self):
        result = apply_input(
            self.doc,
            self.varset,
            "Speed = 10 m/s",
            "Base",
            confirm_change=lambda *args: True,
        )

        self.assertEqual(result["action"], "created")
        self.assertEqual(
            self.varset.getTypeIdOfProperty("Speed"),
            "App::PropertyVelocity",
        )
        self.assertAlmostEqual(self.varset.Speed.getValueAs("m/s"), 10.0)

    def test_dimensionless_value_creates_float_property(self):
        result = apply_input(
            self.doc,
            self.varset,
            "FrontTopSideCutHeight = 7",
            "Base",
            confirm_change=lambda *args: True,
        )

        self.assertEqual(result["action"], "created")
        self.assertEqual(
            self.varset.getTypeIdOfProperty("FrontTopSideCutHeight"),
            "App::PropertyFloat",
        )
        self.assertAlmostEqual(self.varset.FrontTopSideCutHeight, 7.0)

        updated = apply_input(
            self.doc,
            self.varset,
            "FrontTopSideCutHeight = 8",
            "Base",
            confirm_change=lambda *args: True,
        )

        self.assertEqual(updated["action"], "updated")
        self.assertAlmostEqual(self.varset.FrontTopSideCutHeight, 8.0)

    def test_create_and_update_quantity(self):
        created = apply_input(
            self.doc,
            self.varset,
            "Width = 10 mm",
            "Base",
            confirm_change=lambda *args: True,
        )
        self.assertEqual(created["action"], "created")
        self.assertEqual(
            self.varset.getTypeIdOfProperty("Width"),
            "App::PropertyLength",
        )

        updated = apply_input(
            self.doc,
            self.varset,
            "Width = 12 mm",
            "Base",
            confirm_change=lambda *args: True,
        )
        self.assertEqual(updated["action"], "updated")
        self.assertAlmostEqual(self.varset.Width.Value, 12.0)

    def test_negative_new_length_uses_distance(self):
        apply_input(
            self.doc,
            self.varset,
            "Offset -1 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        self.assertEqual(
            self.varset.getTypeIdOfProperty("Offset"),
            "App::PropertyDistance",
        )

    def test_negative_existing_length_is_recreated(self):
        apply_input(
            self.doc,
            self.varset,
            "Offset = 10 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        result = apply_input(
            self.doc,
            self.varset,
            "Offset = -1 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        self.assertEqual(result["action"], "recreated")
        self.assertEqual(
            self.varset.getTypeIdOfProperty("Offset"),
            "App::PropertyDistance",
        )
        self.assertAlmostEqual(self.varset.Offset.Value, -1.0)

    def test_different_unit_dimension_is_recreated(self):
        apply_input(
            self.doc,
            self.varset,
            "Value = 10 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        result = apply_input(
            self.doc,
            self.varset,
            "Value = 2 s",
            "Base",
            confirm_change=lambda *args: True,
        )

        self.assertEqual(result["action"], "recreated")
        self.assertEqual(
            self.varset.getTypeIdOfProperty("Value"),
            "App::PropertyTime",
        )
        self.assertAlmostEqual(self.varset.Value.Value, 2.0)

    def test_cancelled_type_change_keeps_original_property(self):
        apply_input(
            self.doc,
            self.varset,
            "Value = 10 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        with self.assertRaises(Exception):
            apply_input(
                self.doc,
                self.varset,
                "Value = 2 s",
                "Base",
                confirm_change=lambda *args: False,
            )

        self.assertEqual(
            self.varset.getTypeIdOfProperty("Value"),
            "App::PropertyLength",
        )
        self.assertAlmostEqual(self.varset.Value.Value, 10.0)

    def test_builtin_varset_names_are_rejected(self):
        with self.assertRaisesRegex(QuickVarSetError, "built-in VarSet"):
            apply_input(
                self.doc,
                self.varset,
                "Label = 10 mm",
                "Base",
                confirm_change=lambda *args: True,
            )

    def test_explicit_group_moves_existing_property(self):
        apply_input(
            self.doc,
            self.varset,
            "Width = 10 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        result = apply_input(
            self.doc,
            self.varset,
            "Common/Width = 15 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        self.assertEqual(result["group"], "Common")
        self.assertEqual(self.varset.getGroupOfProperty("Width"), "Common")


if __name__ == "__main__":
    unittest.main()