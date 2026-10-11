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
            "Existing groups (default marked by [braces]): "
            "Base, {MotionControls}",
        )


if __name__ == "__main__":
    unittest.main()