import socket
import unittest
from urllib.error import HTTPError, URLError

from ayec_core.connectivity import classify_error, is_retryable


class ConnectivityTests(unittest.TestCase):
    def test_network_and_server_errors_are_retryable(self):
        self.assertEqual(classify_error(URLError(socket.gaierror())), "dns")
        self.assertEqual(classify_error(TimeoutError()), "timeout")
        server = HTTPError("https://example.test", 503, "down", {}, None)
        self.assertEqual(classify_error(server), "server")
        self.assertTrue(is_retryable(server))

    def test_authentication_is_not_revocation_or_retryable(self):
        authentication = HTTPError("https://example.test", 401, "auth", {}, None)
        self.assertEqual(classify_error(authentication), "authentication")
        self.assertFalse(is_retryable(authentication))
