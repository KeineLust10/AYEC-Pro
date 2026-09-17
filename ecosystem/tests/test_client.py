"""Exercise HTTP transport without production accounts."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import closing
import json
import threading
import unittest
from pathlib import Path
import tempfile
import hashlib
import sqlite3
from unittest.mock import patch
from ayec_core.connectivity import classify_error
from ayec_core.client import CentralClient, CentralApiError


class ClientTests(unittest.TestCase):
    def test_transport(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                received.append((dict(self.headers), json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200)
                self.send_header('Set-Cookie', 'ayec_session=fixture; HttpOnly')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())

            def do_GET(self):
                self.send_response(401)
                self.end_headers()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            client = CentralClient(f'http://127.0.0.1:{server.server_port}', product_code='elek', device_id='pc', tenant_id='tenant-1')
            client.login('fixture@example.test', 'fixture-password')
            client.create_order({'product_code': 'ciro'})
            headers = {k.lower(): v for k, v in received[-1][0].items()}
            self.assertEqual(received[-1][1]['product_code'], 'elek')
            self.assertEqual(headers['x-ayec-product-code'], 'elek')
            self.assertEqual(headers['x-ayec-device-id'], 'pc')
            self.assertEqual(headers['x-ayec-tenant-id'], 'tenant-1')
            self.assertEqual(headers['cookie'], 'ayec_session=fixture')
            with self.assertRaises(CentralApiError) as failure:
                client.auth_status()
            self.assertEqual(failure.exception.status_code, 401)
            self.assertEqual(classify_error(failure.exception), 'authentication')
            self.assertEqual(client.cookies, {})
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_remote_http_is_rejected(self):
        with self.assertRaises(CentralApiError):
            CentralClient('http://example.test', product_code='elek')

    def test_backup_requires_matching_remote_checksum_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.db'
            with closing(sqlite3.connect(path)) as connection:
                connection.execute('CREATE TABLE sample(value)')
                connection.commit()
            client = CentralClient('https://example.test', product_code='elek')
            def accept(route, method, raw, **kwargs):
                return {'ok': True, 'backup_id': 1, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'size_bytes': len(raw)}
            with patch.object(client, '_request', side_effect=accept):
                self.assertEqual(client.upload_backup(path, program_name='Elek', database_name='Elek.db')['backup_id'], 1)
            with patch.object(client, '_request', return_value={'ok': True, 'backup_id': 1}):
                with self.assertRaises(CentralApiError):
                    client.upload_backup(path, program_name='Elek', database_name='Elek.db')

    def test_saved_session_is_bound_to_tenant_installation_and_device(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session'
            client = CentralClient('https://example.test', product_code='elek',
                                   device_id='pc', installation_id='install-1', tenant_id='t1')
            client.cookies = {'ayec_session': 'fixture'}
            client.save_session(path)
            loaded = CentralClient('https://example.test', product_code='elek',
                                   device_id='pc', installation_id='install-1')
            self.assertEqual(loaded.load_session(path)['tenant_id'], 't1')
            self.assertEqual(loaded.tenant_id, 't1')
            for field, value in (('device_id', 'other'), ('installation_id', 'other'),
                                 ('tenant_id', 'other'), ('product_code', 'ciro')):
                kwargs = dict(product_code='elek', device_id='pc', installation_id='install-1', tenant_id='t1')
                kwargs[field] = value
                foreign = CentralClient('https://example.test', **kwargs)
                self.assertEqual(foreign.load_session(path), {})
                self.assertEqual(foreign.cookies, {})
