import json
import sqlite3

from src.utils.cloud_backup import CloudBackupManager


def test_remote_settings_control_backup_provider_endpoint(tmp_path):
    db_path = tmp_path / "settings.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.executemany(
        "INSERT INTO settings(key, value) VALUES (?, ?)",
        [
            ("remote_enabled", "1"),
            ("remote_server_ip", "https://backup.example.test"),
            ("remote_server_port", "9443"),
            ("remote_logging", "1"),
        ],
    )
    conn.commit()
    conn.close()

    config_path = tmp_path / "cloud_config.json"
    config_path.write_text(
        json.dumps(
            {
                "remote_server": {
                    "enabled": False,
                    "url": "https://old.example.test/api/support/backups/upload",
                    "auth_token": "",
                }
            }
        ),
        encoding="utf-8",
    )

    manager = CloudBackupManager(str(db_path), str(config_path))

    assert manager.config["remote_server"]["enabled"] is True
    assert manager.config["remote_server"]["logging_enabled"] is True
    provider = manager.providers["remote"]
    assert provider._endpoint_url("upload") == (
        "https://backup.example.test:9443/api/backup/upload"
    )
    assert provider._endpoint_url("download") == (
        "https://backup.example.test:9443/api/backup/download"
    )


def test_remote_settings_can_disable_provider(tmp_path):
    db_path = tmp_path / "settings.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO settings(key, value) VALUES ('remote_enabled', '0')")
    conn.commit()
    conn.close()
    config_path = tmp_path / "cloud_config.json"
    config_path.write_text(
        json.dumps(
            {
                "remote_server": {
                    "enabled": True,
                    "url": "https://backup.example.test/api/support/backups/upload",
                }
            }
        ),
        encoding="utf-8",
    )

    manager = CloudBackupManager(str(db_path), str(config_path))

    assert manager.config["remote_server"]["enabled"] is False
    assert "remote" not in manager.providers
