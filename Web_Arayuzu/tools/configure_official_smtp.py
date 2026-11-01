"""Configure and verify the server-only AYEC password-reset mail transport."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import smtplib
import ssl
import subprocess
import tempfile


def configure(application_path: Path) -> Path:
    requested_root = application_path.resolve()
    candidates = [requested_root, requested_root / "Web_Arayuzu"]
    candidates.extend(list(requested_root.parents)[:4])
    root = next((candidate for candidate in candidates if (candidate / "Main.py").is_file()), None)
    if root is None:
        searched = ", ".join(str(candidate) for candidate in candidates)
        raise SystemExit("AYEC application directory was not found. Checked: " + searched)

    target = root / "official-services.json"
    config = json.loads(target.read_text(encoding="utf-8-sig")) if target.is_file() else {}
    if not isinstance(config, dict):
        raise SystemExit("The official service settings file is invalid.")

    host = input("SMTP host [srvm07.trwww.com]: ").strip() or str(
        config.get("smtp_host") or "srvm07.trwww.com"
    )
    port_text = input("SMTP port [465]: ").strip() or str(config.get("smtp_port") or 465)
    try:
        port = int(port_text)
    except ValueError:
        raise SystemExit("SMTP port must be 465 or 587.") from None
    if port not in (465, 587):
        raise SystemExit("SMTP port must be 465 or 587.")
    password = getpass.getpass("info@ayecpro.com mailbox password (hidden): ").strip()
    password = password or str(config.get("smtp_password") or "")
    if not host or not password:
        raise SystemExit("SMTP host and mailbox password are required. No settings changed.")

    print("Verifying SMTP login. No email will be sent.")
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(
                host, port, timeout=20, context=ssl.create_default_context()
            )
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        with server:
            server.login("info@ayecpro.com", password)
    except Exception as error:
        raise SystemExit(
            "SMTP login failed (" + type(error).__name__ + "). No settings changed."
        ) from None

    config.update(smtp_host=host, smtp_port=port, smtp_password=password)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".official-services-", dir=root)
    temporary = Path(temporary_name)
    try:
        if os.name == "nt":
            os.close(descriptor)
            descriptor = -1
            result = subprocess.run(
                [
                    "icacls",
                    str(temporary),
                    "/inheritance:r",
                    "/grant:r",
                    "*S-1-5-18:F",
                    "*S-1-5-32-544:F",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode:
                raise SystemExit("Could not restrict settings file permissions.")
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
    args = parser.parse_args()
    target = configure(args.application_path)
    print("SMTP login verified and settings saved securely: " + str(target))
    print("Existing Google OAuth settings were preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
