import hashlib
import json
from pathlib import Path

from scripts.release_manager import ReleaseManager


def test_release_manifest_uses_https_and_checksum(tmp_path):
    setup = tmp_path / "AYECPro_Setup_v9.8.7.exe"
    payload = b"release-payload"
    setup.write_bytes(payload)

    manager = ReleaseManager.__new__(ReleaseManager)
    manager.output_dir = str(tmp_path)
    manager.root_dir = str(tmp_path)

    manager.create_release_artifacts("9.8.7", "Manifest test")

    manifest_path = tmp_path / "Releases" / "v9.8.7" / "version.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["url"] == (
        "https://lisans.ayecpro.com/Update/AYECPro_Setup_v9.8.7.exe"
    )
    assert manifest["sha256"] == hashlib.sha256(payload).hexdigest()
    assert (tmp_path / "Releases" / "v9.8.7" / "setup.exe").read_bytes() == payload
