# OCR Regression Guard

The OCR and smart import pipeline is protected by a read-only regression guard.
It compares parser output with known expectations without changing source files,
application data, or OCR behavior.

Keep real customer invoices outside the repository. Create a local JSON file:

```json
{
  "cases": [
    {
      "name": "known-invoice",
      "source": "C:/private/invoices/known.pdf",
      "min_rows": 2,
      "metadata": {
        "invoice_no": "INV-42",
        "supplier_company": "ACME"
      },
      "rows": [
        {
          "code": "CAM-1",
          "currency": "USD",
          "stock": 2
        },
        {
          "name_contains": "camera"
        }
      ],
      "forbidden_name_contains": [
        "grand total",
        "discount"
      ]
    }
  ]
}
```

Run the guard before packaging a desktop release:

```powershell
& '.\.venv_active\Scripts\python.exe' tools\ocr_regression_guard.py C:\private\ocr-manifest.json
```

Exit code `0` means every contract passed. Exit code `1` blocks the release and
prints the mismatched metadata, rows, or summary-line leakage.
