# QuickVarSet Agent Instructions

QuickVarSet is a standalone FreeCAD macro. Its tests must run inside a
FreeCAD AppImage because system Python does not provide the `FreeCAD` module.

## Context

To get the context first read the README.md file in the project root.

## Test Command

From the project root, run:

```bash
./tests/run_tests.sh
```

The script searches `~/apps` by default, selects the newest matching
FreeCAD AppImage with version sorting, extracts it into ignored
`.test/freecad/`, and runs the core tests with its `freecadcmd`.

The extraction cache is local to the project. Do not use `/tmp` for the
normal test workflow and do not commit `.test/`.

## Test Configuration

Copy `.env.example` to `.env` to override defaults. Supported variables:

- `APPS_DIR`: directory searched for FreeCAD AppImages.
- `FREECAD_BIN_PATTERN`: sed regex prefix used for AppImage discovery.
- `FREECAD_TEST_DIR`: extraction cache directory, relative to the project or
  an absolute path.
- `FREECAD_APPIMAGE`: exact AppImage path; overrides discovery and version
  sorting.
- `QT_QPA_PLATFORM`: defaults to `offscreen` for tests.

To force a fresh extraction:

```bash
./tests/extract_freecad.sh --force
```

## Implementation Constraints

- Keep `[QuickVarSet]` console logging and detailed GUI error reporting.
- Keep addon runtime imports limited to Python standard-library modules,
  FreeCAD built-ins (`FreeCAD`, optional `FreeCADGui`, and `PySide`), and
  third-party packages listed in the target Python version's
  [Allowed-Packages](https://github.com/FreeCAD/Addons/tree/main/Data/Python)
  file.
- Use FreeCAD's `PySide` compatibility bridge for Qt imports.
  Do not import `PySide2` or `PySide6` directly.
- Treat `Allowed-Packages` as the dependency allowlist for packages that an
  addon may request to install.
  Do not add an unlisted third-party runtime dependency.
- Treat `ExpressionEngine`, `Label`, `Label2`, and `Visibility` as built-in
  VarSet properties, not user variables.
- Preserve parsing for unit values containing `/`, such as `10 m/s`.
- Do not open a document transaction around dynamic `App::VarSet` property
  creation. FreeCAD 1.1.1 can terminate in that case.