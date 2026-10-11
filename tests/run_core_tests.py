import importlib.util
import os
import sys
import unittest


runner_file = globals().get("__file__")

if runner_file:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(runner_file)))
    TEST_DIR = os.path.dirname(runner_file)
else:
    ROOT = os.getcwd()
    TEST_DIR = os.path.join(ROOT, "tests")

TEST_PATHS = [
    os.path.join(TEST_DIR, "test_core.py"),
    os.path.join(TEST_DIR, "test_macro.py"),
]

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

test_modules = []
for index, test_path in enumerate(TEST_PATHS):
    module_name = f"quickvarset_test_{index}"
    spec = importlib.util.spec_from_file_location(module_name, test_path)
    test_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_module)
    test_modules.append(test_module)

suite = unittest.TestSuite(
    unittest.defaultTestLoader.loadTestsFromModule(test_module)
    for test_module in test_modules
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)