import os
import subprocess
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run_step(title, command):
    print(f"\n[QUALITY] {title}")
    print(">", " ".join(command))
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        print(f"[QUALITY] FAILED: {title} (exit={completed.returncode})")
        return completed.returncode
    print(f"[QUALITY] OK: {title}")
    return 0


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    steps = [
        (
            "PyCompile",
            [
                sys.executable,
                "-m",
                "py_compile",
                "src/ui/dialogs/add_customer_dialog.py",
                "src/ui/dialogs/new_service_dialog.py",
                "src/ui/widgets/modern_dialog.py",
                "tests/test_dialog_flows.py",
            ],
        ),
        (
            "Dialog Flow Tests",
            [sys.executable, "-m", "unittest", "tests.test_dialog_flows"],
        ),
    ]

    for title, command in steps:
        code = run_step(title, command)
        if code != 0:
            return code

    print("\n[QUALITY] All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
