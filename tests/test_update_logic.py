import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.utils.startup_updater import UpdateWorker

class TestUpdateLogic(unittest.TestCase):
    def setUp(self):
        self.worker = UpdateWorker("1.0.0")

    @patch('urllib.request.urlopen')
    def test_compare_versions_newer(self, mock_urlopen):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.geturl.return_value = "https://85.117.239.60:8000/Update/version.json"
        mock_response.read.return_value = json.dumps({
            "version": "1.1.0",
            "url": "https://85.117.239.60:8000/Update/setup.exe",
            "notes": "Test Update",
            "sha256": "a" * 64,
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Connect verify signal
        self.update_found = False
        def on_finished(has_update, version, url, notes, sha256):
            self.update_found = has_update
            self.assertEqual(version, "1.1.0")
            self.assertEqual(url, "https://85.117.239.60:8000/Update/setup.exe")
            self.assertEqual(notes, "Test Update")
            self.assertEqual(sha256, "a" * 64)
            
        self.worker.finished.connect(on_finished)
        self.worker.run()
        
        self.assertTrue(self.update_found)

    @patch('urllib.request.urlopen')
    def test_compare_versions_older(self, mock_urlopen):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.geturl.return_value = "https://85.117.239.60:8000/Update/version.json"
        mock_response.read.return_value = json.dumps({
            "version": "0.9.0",
            "url": "https://85.117.239.60:8000/Update/setup.exe",
            "sha256": "b" * 64,
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Connect verify signal
        self.update_found = True # Expect False
        def on_finished(has_update, version, url, notes, sha256):
            self.update_found = has_update
            
        self.worker.finished.connect(on_finished)
        self.worker.run()
        
        self.assertFalse(self.update_found)

if __name__ == '__main__':
    # Initializing QApplication is needed for QThread but suppressed here for unit logic test
    # We really just wanted to test run() logic. QThread might need a qapp instance.
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    unittest.main(exit=False)
