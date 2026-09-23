"""Product-scoped central API client shared by AYEC applications."""
import json
import hashlib
import ssl
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .backup import snapshot_upload
from .session import (load_session, protect_current_user, save_session,
                      unprotect_current_user, update_cookies)
from .restore import stage_restore


class CentralApiError(RuntimeError):
    def __init__(self, message, *, status_code=None, error_code="", retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = str(error_code or "")
        self.retry_after = retry_after


def _retry_after_seconds(value):
    """Parse a bounded Retry-After value without making another request."""
    if value is None:
        return None
    try:
        seconds = float(str(value).strip())
        if seconds >= 0:
            return min(seconds, 6 * 60 * 60)
    except (TypeError, ValueError):
        pass
    try:
        target = parsedate_to_datetime(str(value))
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        return min(max(0.0, (target - datetime.now(timezone.utc)).total_seconds()), 6 * 60 * 60)
    except (TypeError, ValueError, OverflowError):
        return None


class CentralClient:
    def __init__(self, base_url, *, product_code, device_id="", tenant_id="", installation_id="", timeout=20):
        self.base_url = str(base_url).strip().rstrip('/')
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise CentralApiError("Invalid central API address")
        if parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise CentralApiError("HTTPS is required for the central API")
        if parsed.query or parsed.fragment:
            raise CentralApiError("Invalid central API address")
        self.product_code = product_code
        self.device_id = device_id
        self.tenant_id = str(tenant_id or "")
        self.installation_id = str(installation_id or "")
        self.timeout = timeout
        self.cookies = {}
        self.context = ssl.create_default_context()

    def _request(self, path, method='GET', payload=None, *, binary=False, headers=None):
        values = {'Accept': 'application/json', 'User-Agent': 'AYEC-Core/0.3',
                  **(headers or {}), 'X-AYEC-Product-Code': self.product_code,
                  'X-AYEC-Device-ID': self.device_id}
        if self.tenant_id:
            values['X-AYEC-Tenant-ID'] = self.tenant_id
        if self.installation_id:
            values['X-AYEC-Installation-ID'] = self.installation_id
        if self.cookies:
            values['Cookie'] = '; '.join(f'{k}={v}' for k, v in self.cookies.items())
        body = payload
        if isinstance(payload, dict):
            body = json.dumps(payload, ensure_ascii=True).encode()
            values['Content-Type'] = 'application/json'
        request = Request(self.base_url + path, data=body, method=method, headers=values)
        try:
            with urlopen(request, timeout=self.timeout, context=self.context) as response:
                update_cookies(self.cookies, response.headers)
                raw = response.read(1024 * 1024 * 1024 + 1 if binary else 2_000_001)
        except HTTPError as error:
            if error.code == 401:
                self.cookies.clear()
            raise CentralApiError(
                f'Central API HTTP {error.code}', status_code=error.code,
                retry_after=_retry_after_seconds(error.headers.get('Retry-After')),
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise CentralApiError('Central API connection failed') from error
        if binary:
            if len(raw) > 1024 * 1024 * 1024:
                raise CentralApiError('Backup exceeds size limit')
            return raw
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise CentralApiError('Invalid central API response') from error
        if not isinstance(result, dict) or result.get('error'):
            raise CentralApiError(str(result.get('error')) if isinstance(result, dict) else 'Invalid response object')
        return result

    def login(self, identifier, password, tenant_id=''):
        if tenant_id:
            self.tenant_id = str(tenant_id)
        result = self._request('/api/auth/login', 'POST', {'identifier': identifier,
                             'password': password, 'remember': True, 'tenant_id': tenant_id})
        user = result.get('user') if isinstance(result, dict) else None
        if isinstance(user, dict) and (user.get('_tenant_id') or user.get('tenant_id')):
            self.tenant_id = str(user.get('_tenant_id') or user['tenant_id'])
        elif isinstance(result, dict) and result.get('tenant_id'):
            self.tenant_id = str(result['tenant_id'])
        return result

    def save_session(self, path, metadata=None):
        scoped = dict(metadata or {})
        scoped.update(tenant_id=self.tenant_id, installation_id=self.installation_id,
                      hardware_id=self.device_id)
        save_session(path, base_url=self.base_url, product_code=self.product_code,
                     cookies=self.cookies, metadata=scoped,
                     protect=protect_current_user)

    def load_session(self, path):
        metadata = load_session(path, base_url=self.base_url,
                            product_code=self.product_code, cookies=self.cookies,
                            unprotect=unprotect_current_user)
        expected = {'tenant_id': self.tenant_id, 'installation_id': self.installation_id,
                    'hardware_id': self.device_id}
        if any(value and metadata.get(key) != value for key, value in expected.items()):
            self.cookies.clear()
            return {}
        if metadata.get('tenant_id'):
            self.tenant_id = str(metadata['tenant_id'])
        return metadata

    def clear_session(self, path):
        from pathlib import Path
        self.cookies.clear()
        Path(path).expanduser().resolve().unlink(missing_ok=True)

    def auth_status(self):
        return self._request('/api/auth/status')

    def catalog(self):
        return self._request('/api/license/catalog')

    def create_order(self, payload):
        return self._request('/api/license/orders/device', 'POST', {**payload, 'product_code': self.product_code})

    def status_for_device(self, payload):
        return self._request('/api/license/status/device', 'POST', {
            **payload, 'product_code': self.product_code, 'hardware_id': self.device_id,
            'installation_id': self.installation_id, 'tenant_id': self.tenant_id})

    def pending_commands(self):
        return self._request('/api/support/desktop/commands').get('commands') or []

    def complete_command(self, command_id, success, result=None):
        return self._request('/api/support/desktop/complete', 'POST',
                             {'command_id': command_id, 'success': success, 'result': result or {}})

    def upload_backup(self, path, *, program_name, database_name):
        payload, headers = snapshot_upload(path, product_code=self.product_code,
                                            program_name=program_name, database_name=database_name)
        digest = hashlib.sha256(payload).hexdigest()
        headers['X-AYEC-Backup-SHA256'] = digest
        response = self._request('/api/support/backups/upload', 'POST', payload, headers=headers)
        if (response.get('ok') is not True or not response.get('backup_id')
                or response.get('sha256') != digest or response.get('size_bytes') != len(payload)):
            raise CentralApiError('Backup acknowledgement does not match the uploaded snapshot')
        return response

    def download_backup(self, backup_id):
        return self._request(f'/api/support/backups/{int(backup_id)}', binary=True)

    def stage_restore_command(self, command, path, required_tables=()):
        return stage_restore(command, path, self.download_backup,
                             product_code=self.product_code,
                             tenant_id=self.tenant_id,
                             hardware_id=self.device_id,
                             installation_id=self.installation_id,
                             required_tables=required_tables)
