
import os
import json
import secrets
import stat
from pathlib import Path
from .path_helper import PathHelper
from .logger import logger

class Config:
    _instance = None
    _secret_key = None
    _config_path = None
    _database_key = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        try:
            app_data = PathHelper.get_app_data_dir()
            self._config_path = os.path.join(app_data, "ayec_server_secrets.json")
            
            if os.path.exists(self._config_path):
                try:
                    with open(self._config_path, 'r', encoding="utf-8") as f:
                        data = json.load(f)
                        self._secret_key = data.get("secret_key")
                        self._database_key = data.get("database_key")
                except Exception as e:
                    logger.error("Error loading secrets: %s", e)
            
            if not self._secret_key:
                self._secret_key = secrets.token_hex(32)
                self._save_config()
            if not self._database_key:
                self._database_key = secrets.token_urlsafe(48)
                self._save_config()
                
        except Exception as e:
            logger.critical("CRITICAL CONFIG ERROR: %s", e)
            self._secret_key = os.environ.get("AYEC_SECRET_KEY") or secrets.token_hex(32)
            self._database_key = os.environ.get("AYEC_DATABASE_KEY") or secrets.token_urlsafe(48)

    def _save_config(self):
        try:
            config_dir = os.path.dirname(self._config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            if os.name == "nt" and os.path.exists(self._config_path):
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(self._config_path, 0x80)
                except Exception:
                    pass
            with open(self._config_path, 'w', encoding="utf-8") as f:
                json.dump(
                    {
                        "secret_key": self._secret_key,
                        "database_key": self._database_key,
                    },
                    f,
                )
            if os.name != "nt":
                os.chmod(self._config_path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            logger.error("Error saving secrets: %s", e)

    @property
    def secret_key(self):
        return self._secret_key

    @property
    def database_key(self):
        return self._database_key

# Global instance
config = Config()
