# AYEC Core

Build the shared wheel from the Technical Service repository root:

```powershell
python -m pip wheel --no-deps ./ecosystem --wheel-dir ./ecosystem/wheels
```

Install that wheel into each desktop application's Python environment before
building or starting it. Include the wheel in release dependencies; no source
checkout or developer-specific path is required at runtime.

```powershell
python -m pip install "path/to/ayec_core-0.2.0-py3-none-any.whl[smart-import]"
python -m pip install --find-links ./ecosystem/wheels -r ./ecosystem/requirements-desktop.txt
python -m unittest discover -s ecosystem/tests -v
```

The initial shared contract implements validated SQLite snapshot generation
and product-scoped upload headers. Technical Service and Barkod consume it.
The smart-import extra supplies the shared CSV/Excel/PDF/XML/DOCX parser.
Technical Service delegates its old import path to this package. Barkod imports
it directly. Web release staging includes the same package sources.
Install the ocr extra for EasyOCR, or configure Tesseract and its language data.
An isolated OCR Python environment can be selected with AYEC_OCR_PYTHON.
No developer checkout is searched at runtime.
Shared session persistence now provides atomic writes, server/product binding,
legacy-session compatibility and multiple Set-Cookie handling. Technical Service
and Barkod call the shared module with their existing encryption adapters.
Shared staged restore is consumed by both desktop products. Server-side backup
and restore routing isolates product, tenant and device. Elek/Ciro adapters,
shared licensing transport and deployed verification remain migration work.
