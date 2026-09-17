# -*- coding: utf-8 -*-

import ctypes
import os


def print_pdf_file(path, printer_name=""):
    """Send a PDF to a Windows printer through the registered PDF handler."""
    if os.name != "nt":
        return False, "Do\u011frudan yazd\u0131rma yaln\u0131zca Windows ortam\u0131nda desteklenir."
    absolute_path = os.path.abspath(path)
    if not os.path.exists(absolute_path):
        return False, "Yazd\u0131r\u0131lacak PDF bulunamad\u0131."
    verb = "printto" if printer_name else "print"
    parameters = f'"{printer_name}"' if printer_name else None
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        verb,
        absolute_path,
        parameters,
        None,
        0,
    )
    if result <= 32:
        return False, f"Windows yazd\u0131rma komutu ba\u015far\u0131s\u0131z oldu ({result})."
    return True, absolute_path
