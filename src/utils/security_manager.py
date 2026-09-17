# -*- coding: utf-8 -*-

import base64
import hashlib
import os
import platform
import shutil
import subprocess
from datetime import datetime, timedelta

from cryptography.fernet import Fernet

from src.utils.logger import logger


class SecurityManager:
    _master_mode = False

    @classmethod
    def set_master_mode(cls, enabled):
        """Toggle temporary technical-service master mode."""
        cls._master_mode = bool(enabled)

    @classmethod
    def is_master_mode(cls):
        """Return current technical-service master mode state."""
        return bool(cls._master_mode)

    @staticmethod
    def hash_password(password):
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _run_windows_uuid_command(command):
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3,
                creationflags=creation_flags,
                check=False,
            )
            return (result.stdout or "").strip()
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("HWID command failed: %s", e)
            return ""

    @classmethod
    def get_hwid(cls):
        """Generate a stable hardware identifier."""
        uuid_raw = ""
        try:
            if platform.system() == "Windows":
                powershell = shutil.which("powershell") or shutil.which("powershell.exe")
                if powershell:
                    uuid_raw = cls._run_windows_uuid_command(
                        [
                            powershell,
                            "-NoProfile",
                            "-NonInteractive",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-Command",
                            "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
                        ]
                    )

                if not uuid_raw:
                    wmic = shutil.which("wmic")
                    if wmic:
                        raw = cls._run_windows_uuid_command([wmic, "csproduct", "get", "uuid"])
                        lines = [line.strip() for line in raw.splitlines() if line.strip()]
                        if len(lines) >= 2:
                            uuid_raw = lines[1]

                if not uuid_raw or "UUID" in uuid_raw or uuid_raw == "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF":
                    from uuid import getnode

                    uuid_raw = str(getnode())
            else:
                uuid_raw = platform.node()

            if not uuid_raw:
                uuid_raw = f"{platform.processor()}_{platform.node()}_{os.getlogin()}"

            return hashlib.sha256(uuid_raw.encode()).hexdigest()
        except Exception as e:
            logger.warning("get_hwid fallback path used: %s", e)
            fallback = f"{platform.processor()}_{platform.node()}_{os.getlogin()}"
            return hashlib.sha256(fallback.encode()).hexdigest()

    @staticmethod
    def generate_key_from_hwid(hwid):
        """Derive an AES key from the HWID."""
        key = hashlib.sha256(hwid.encode()).digest()
        return base64.urlsafe_b64encode(key)

    @classmethod
    def encrypt_data(cls, data, hwid):
        """Encrypt data with a key derived from HWID."""
        key = cls.generate_key_from_hwid(hwid)
        fernet = Fernet(key)
        return fernet.encrypt(data.encode()).decode()

    @classmethod
    def decrypt_data(cls, encrypted_data, hwid):
        """Decrypt data with a key derived from HWID."""
        try:
            key = cls.generate_key_from_hwid(hwid)
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.warning("decrypt_data failed: %s", e)
            return None

    @staticmethod
    def validate_license_format(key):
        """Validate XXXXX-XXXXX-XXXXX-XXXXX-XXXXX format."""
        import re

        pattern = r"^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$"
        return bool(re.match(pattern, key))

    @staticmethod
    def get_trial_status(trial_start_date_str):
        """Return remaining trial days and validity."""
        try:
            start_date = datetime.strptime(trial_start_date_str, "%Y-%m-%d %H:%M:%S")
            expiry_date = start_date + timedelta(days=15)
            now = datetime.now()

            remaining = expiry_date - now
            days_left = remaining.days

            if days_left < 0:
                return 0, False
            return days_left, True
        except (TypeError, ValueError) as e:
            logger.warning("get_trial_status parse failed: %s", e)
            return 0, False

    @staticmethod
    def generate_license_key(target_hwid):
        """Generate a deterministic license key for a target HWID."""
        salt = "BULUT_TEKNIK_SERVIS_2026_SECURE_SALT_!@#"
        raw_data = f"{target_hwid}{salt}"
        full_hash = hashlib.sha256(raw_data.encode()).hexdigest().upper()
        key_raw = full_hash[:25]
        parts = [key_raw[i : i + 5] for i in range(0, 25, 5)]
        return "-".join(parts)

    @staticmethod
    def verify_license_key(input_key, user_hwid):
        """Check if a key matches the current HWID."""
        from ayec_core.licensing import verify_legacy_key
        return verify_legacy_key(input_key, user_hwid)
