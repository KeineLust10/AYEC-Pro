import ctypes
import os


def preload_windows_cpp_runtime():
    """Load the system MSVC runtime before Qt's bundled runtime is loaded."""
    if os.name != "nt":
        return
    system_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32")
    runtime_dll = os.path.join(system_dir, "msvcp140.dll")
    if not os.path.isfile(runtime_dll):
        return
    try:
        ctypes.WinDLL(runtime_dll)
    except OSError:
        return
