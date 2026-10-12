# QuickVarSet

[![Tests](https://github.com/renkam/QuickVarSet/actions/workflows/tests.yml/badge.svg)](https://github.com/renkam/QuickVarSet/actions/workflows/tests.yml)
[![License: LGPL-2.1-or-later](https://img.shields.io/badge/License-LGPL--2.1--or--later-blue.svg)](LICENSE)

QuickVarSet is a standalone FreeCAD macro for creating and updating quantity
properties in `App::VarSet` objects.

It does not install or activate a workbench.
Run it from any workbench, including while a sketch is being edited.

The macro provides the following behavior:

- errors are printed with a `[QuickVarSet]` prefix and a full traceback in
  the FreeCAD console;
- GUI errors also show a dialog with expandable details;
- every created property and assigned value is verified;
- each mutation is checked because FreeCAD 1.1.1 can terminate when a
  dynamic VarSet property is added inside an open document transaction;
- `ExpressionEngine`, `Label`, `Label2`, and `Visibility` are treated as
  built-in VarSet properties, not user variables;
- unit expressions such as `10 m/s` are parsed correctly;
- type changes preserve the existing group unless a group is explicit.

## Install with Addon Manager

This repository contains `package.xml` with a `macro` content item.
Use the Addon Manager to install the repository as a custom package, or add
the repository to the FreeCAD Addon Index before publishing it for general use.

The package installs the self-contained `QuickVarSet.FCMacro` in FreeCAD's
macro directory.

## Install from a local checkout

For direct local use, copy the macro to FreeCAD's macro directory:

```text
~/.local/share/FreeCAD/v1-1/Macro/
```

Copy this file:

```text
QuickVarSet.FCMacro
```

The exact user data directory can vary by FreeCAD version and operating
system.
Restart FreeCAD after copying the files.

Open **Macro > Macros**, select **QuickVarSet**, and press **Execute**.
To use a keyboard shortcut, open **Tools > Customize > Macros**, add
`QuickVarSet`, and assign an available shortcut such as `Ctrl+Alt+V`.
`F1` is configurable, but FreeCAD commonly uses it for Help.

The macro creates a VarSet when the active document has none.
When the document has multiple VarSets, it asks you to choose one.
Enter values in one of these forms:

```text
Width = 10 mm
Speed = 10 m/s
Common/Width = 10 mm
```

The selected group is remembered for the next run.

## Run the tests

The tests use FreeCAD's Python runtime because the `FreeCAD` module is not
available in the system Python:

```bash
cd /path/to/QuickVarSet
./tests/run_tests.sh
```

The test script searches `~/apps` for the newest FreeCAD AppImage, extracts
it into the ignored project-local `.test/freecad/` directory, and runs the
core tests with its `freecadcmd`.
Copy `.env.example` to `.env` to override the AppImage directory, matching
pattern, extraction directory, or exact binary.
To remove all extracted FreeCAD runtimes, run
`./tests/extract_freecad.sh --cleanup`.

The FreeCAD console is the diagnostic log.
Look for lines beginning with `[QuickVarSet]` when an operation does not
complete.

## Formula editor names

FreeCAD 1.1.1 creates these properties on every new `App::VarSet`:
`ExpressionEngine`, `Label`, `Label2`, and `Visibility`.
QuickVarSet does not create them and does not treat them as user variables.
The formula editor may still list them because they are built-in object
properties.
Removing those suggestions would require a FreeCAD expression-editor change,
not a macro change.

## License

QuickVarSet is licensed under the GNU Lesser General Public License, version
2.1 or any later version.
See [LICENSE](LICENSE) for the full license text.