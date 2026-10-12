import ast
import os
import unittest

import FreeCAD as App


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACRO_PATH = os.path.join(ROOT, "QuickVarSet.FCMacro")
ALLOWED_MACRO_IMPORTS = frozenset(
    {
        "FreeCAD",
        "FreeCADGui",
        "PySide",
        "re",
        "traceback",
    }
)


def load_macro_definitions():
    with open(MACRO_PATH, encoding="utf-8") as macro_file:
        source = macro_file.read()

    tree = ast.parse(source, filename=MACRO_PATH)
    tree.body.pop()
    namespace = {"__file__": MACRO_PATH, "__name__": "quickvarset_macro"}
    exec(compile(tree, MACRO_PATH, "exec"), namespace)
    return source, namespace


def get_import_roots(source):
    roots = set()

    for node in ast.walk(ast.parse(source, filename=MACRO_PATH)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])

    return roots


class QuickVarSetMacroTests(unittest.TestCase):

    def setUp(self):
        self.doc = App.newDocument("QuickVarSetMacroTest")
        self.varset = self.doc.addObject("App::VarSet", "VarSet")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def test_macro_embeds_varset_logic(self):
        source, namespace = load_macro_definitions()

        self.assertNotIn("from quickvarset_core", source)
        self.assertLessEqual(get_import_roots(source), ALLOWED_MACRO_IMPORTS)

        group, name, value, quantity = namespace["parse_input"](
            "Speed = 10 m/s"
        )
        self.assertIsNone(group)
        self.assertEqual(name, "Speed")
        self.assertEqual(value, "10 m/s")
        self.assertEqual(quantity.Unit.Type, "Velocity")

        result = namespace["apply_input"](
            self.doc,
            self.varset,
            "Width = 10 mm",
            "Base",
        )
        self.assertEqual(result["action"], "created")
        self.assertEqual(
            self.varset.getTypeIdOfProperty("Width"),
            "App::PropertyLength",
        )

    def test_group_summary_preserves_group_names_and_default(self):
        _, namespace = load_macro_definitions()

        summary = namespace["format_group_summary"](
            ["Base", "MotionControls"],
            "MotionControls",
        )

        self.assertEqual(
            summary,
            "Existing groups (default marked by [square brackets]): "
            "Base, [MotionControls]",
        )

    def test_preview_fuzzy_matches_across_groups_and_filters_explicit_group(self):
        _, namespace = load_macro_definitions()
        apply_input = namespace["apply_input"]

        apply_input(
            self.doc,
            self.varset,
            "TotalLength = 100 mm",
            "Base",
            confirm_change=lambda *args: True,
        )
        apply_input(
            self.doc,
            self.varset,
            "Controls/TotalWidth = 200 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        matches = namespace["get_parameter_matches"](
            self.varset,
            "Total",
        )
        self.assertEqual(
            [(match["group"], match["name"]) for match in matches],
            [
                ("Base", "TotalLength"),
                ("Controls", "TotalWidth"),
            ],
        )
        self.assertIn("100", matches[0]["value"])
        self.assertIn("200", matches[1]["value"])

        fuzzy_matches = namespace["get_parameter_matches"](
            self.varset,
            "twd",
        )
        self.assertEqual(
            [match["name"] for match in fuzzy_matches],
            ["TotalWidth"],
        )

        group_matches = namespace["get_parameter_matches"](
            self.varset,
            "Controls/Total",
        )
        self.assertEqual(
            [match["name"] for match in group_matches],
            ["TotalWidth"],
        )

    def test_preview_navigation_selects_value_and_left_restores_query(self):
        _, namespace = load_macro_definitions()
        apply_input = namespace["apply_input"]

        apply_input(
            self.doc,
            self.varset,
            "TotalLength = 100 mm",
            "Base",
            confirm_change=lambda *args: True,
        )
        apply_input(
            self.doc,
            self.varset,
            "Controls/TotalWidth = 200 mm",
            "Base",
            confirm_change=lambda *args: True,
        )

        QtWidgets = namespace["_qt_widgets"]()
        application = QtWidgets.QApplication.instance()
        if application is None:
            application = QtWidgets.QApplication([])

        dialog = namespace["QuickVarDialog"](
            None,
            "VarSet (VarSet)",
            "Base",
            ["Base", "Controls"],
            target_varset=self.varset,
        )
        self.assertEqual(dialog._matches, [])
        dialog._handle_input_key(
            namespace["_qt_constant"]("Key", "Key_Down")
        )
        self.assertEqual(dialog._preview.count(), 2)
        self.assertEqual(
            [
                dialog._preview.item(index).text().split(" = ", 1)[0]
                for index in range(dialog._preview.count())
            ],
            ["Base/TotalLength", "Controls/TotalWidth"],
        )
        dialog._handle_input_key(
            namespace["_qt_constant"]("Key", "Key_Left")
        )
        self.assertEqual(dialog._input.text(), "")

        dialog._input.setText("Total")
        dialog._handle_input_key(
            namespace["_qt_constant"]("Key", "Key_Down")
        )

        expected_value = dialog._matches[0]["value"]
        self.assertEqual(
            dialog._input.text(),
            f"Base/TotalLength = {expected_value}",
        )
        self.assertEqual(dialog._input.selectedText(), expected_value)
        self.assertEqual(
            dialog._input.cursorPosition(),
            len(dialog._input.text()),
        )

        dialog._handle_input_key(
            namespace["_qt_constant"]("Key", "Key_Left")
        )
        self.assertEqual(dialog._input.text(), "Total")

        dialog._handle_input_key(
            namespace["_qt_constant"]("Key", "Key_Down")
        )
        dialog._input.insert("250")
        self.assertEqual(
            dialog._input.text(),
            "Base/TotalLength = 250",
        )
        dialog._dialog.close()


if __name__ == "__main__":
    unittest.main()