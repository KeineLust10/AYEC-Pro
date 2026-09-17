from __future__ import annotations

import fitz
import pymupdf


def main() -> int:
    document = pymupdf.open()
    document.new_page()
    if document.page_count != 1:
        return 2
    if fitz.open is not pymupdf.open:
        return 3
    print(f"PYMUPDF_RUNTIME_OK {pymupdf.__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
