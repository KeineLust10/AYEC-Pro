# Automatically load qt_compat for this project when Python starts
import sys
import io
import os
import glob
import shutil

# Force UTF-8 for standard streams to fix Turkish character issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

def _clear_stale_comtypes_sapi_cache():
    """Remove stale Windows SAPI typelib wrappers before pyttsx3 imports comtypes."""
    patterns = []
    try:
        patterns.append(os.path.join(sys.prefix, "Lib", "site-packages", "comtypes", "gen"))
    except Exception:
        pass
    try:
        patterns.append(os.path.join(os.path.dirname(__file__), ".venv_ai", "Lib", "site-packages", "comtypes", "gen"))
        patterns.append(os.path.join(os.path.dirname(__file__), ".venv_active", "Lib", "site-packages", "comtypes", "gen"))
    except Exception:
        pass

    for gen_dir in patterns:
        if not gen_dir or not os.path.isdir(gen_dir):
            continue
        try:
            for path in glob.glob(os.path.join(gen_dir, "_C866CA3A_32F7_11D2_9602_00C04F8EE628_*.py*")):
                try:
                    os.remove(path)
                except OSError:
                    pass
            pycache = os.path.join(gen_dir, "__pycache__")
            if os.path.isdir(pycache):
                for path in glob.glob(os.path.join(pycache, "_C866CA3A_32F7_11D2_9602_00C04F8EE628_*")):
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path, ignore_errors=True)
                        else:
                            os.remove(path)
                    except OSError:
                        pass
        except Exception:
            pass

_clear_stale_comtypes_sapi_cache()

try:
    import qt_compat  # noqa: F401
except Exception:
    try:
        import importlib
        importlib.import_module('qt_compat')
    except Exception:
        pass
