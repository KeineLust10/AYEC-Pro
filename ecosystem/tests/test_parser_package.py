"""Check the installed parser without importing a desktop checkout."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ParserPackageTests(unittest.TestCase):
    def test_installed_parser_reads_csv_without_desktop_source_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stock.csv"
            path.write_text(
                "barkod;urun;adet;alis;satis\n"
                "0012345678905;Kursun Kalem;8;5;10\n",
                encoding="utf-8",
            )
            script = (
                "import json, sys; from ayec_core.smart_import import StockImportParser; "
                "result = StockImportParser.parse_file(sys.argv[1]); "
                "assert not any(n == 'src' or n.startswith('src.') for n in sys.modules); "
                "print(json.dumps(result['rows']))"
            )
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, "-c", script, str(path)], cwd=directory,
                env=env, capture_output=True, text=True, check=True,
                timeout=30,
            )
            rows = json.loads(result.stdout)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["code"], "0012345678905")
            self.assertEqual(rows[0]["stock"], 8)
            self.assertEqual(rows[0]["price"], 10)
