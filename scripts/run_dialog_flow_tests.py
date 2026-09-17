import os
import sys
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def main():
    tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests"))
    suite = unittest.defaultTestLoader.discover(tests_dir, pattern="test_dialog_flows.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    code = 0 if result.wasSuccessful() else 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    main()
