# -*- coding: utf-8 -*-
import os
import sys
import subprocess

def main():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.getcwd()

    bin_exe = os.path.join(base_dir, "bin", "AYECPro.Core.exe")
    if not os.path.exists(bin_exe):
        bin_exe = os.path.join(base_dir, "AYECPro.Core.exe")

    if os.path.exists(bin_exe):
        args = [bin_exe] + sys.argv[1:]
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 5  # SW_SHOW
        subprocess.Popen(args, cwd=base_dir, startupinfo=startupinfo)
    else:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"AYEC Pro ana calistirilabilir dosyasi bulunamadi:\n{bin_exe}",
            "AYEC Pro Hata",
            0x10
        )

if __name__ == "__main__":
    main()
