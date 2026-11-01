"""Set the server-only Google web OAuth client ID without changing SMTP."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def save_client_id(application_path: Path, client_id: str) -> Path:
    root = application_path.resolve()
    if not (root / "Main.py").is_file():
        raise ValueError("AYEC Pro application directory was not found.")
    if client_id and not client_id.endswith(".apps.googleusercontent.com"):
        raise ValueError("Enter a Google Web OAuth Client ID ending in .apps.googleusercontent.com.")
    target = root / "official-services.json"
    if target.is_file():
        config = json.loads(target.read_text(encoding="utf-8-sig"))
        if not isinstance(config, dict):
            raise ValueError("The official service configuration must be a JSON object.")
    else:
        config = {}
    if client_id:
        config["google_client_id"] = client_id
    else:
        config.pop("google_client_id", None)

    descriptor, temporary_name = tempfile.mkstemp(prefix=".official-services-", dir=root)
    temporary = Path(temporary_name)
    try:
        if os.name == "nt":
            os.close(descriptor)
            descriptor = -1
            result = subprocess.run(
                [
                    "icacls", str(temporary), "/inheritance:r", "/grant:r",
                    "*S-1-5-18:F", "*S-1-5-32-544:F",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode:
                raise OSError("Could not restrict configuration file permissions.")
        else:
            os.fchmod(descriptor, 0o600)
        if descriptor < 0:
            stream = temporary.open("w", encoding="utf-8")
        else:
            stream = os.fdopen(descriptor, "w", encoding="utf-8")
            descriptor = -1
        with stream:
            json.dump(config, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application-path", required=True, type=Path)
    parser.add_argument("--client-id", help="Google Web OAuth Client ID; omit to prompt")
    parser.add_argument("--disable", action="store_true", help="Remove the configured client ID")
    args = parser.parse_args()
    if args.disable and args.client_id is not None:
        parser.error("--disable cannot be combined with --client-id")
    current = args.client_id
    if current is None and not args.disable:
        current = input("Google Web OAuth Client ID (blank keeps the current value): ").strip()
        if not current:
            print("No changes made.")
            return 0
    target = save_client_id(args.application_path, "" if args.disable else str(current or "").strip())
    print("Google sign-in configuration saved securely: " + str(target))
    print("The AYEC Web process reads the client ID from this server-only file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
