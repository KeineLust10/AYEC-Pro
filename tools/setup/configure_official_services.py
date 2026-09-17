"""Configure AYEC-owned SMTP and Google sign-in on the application server."""
import argparse
import getpass
import json
import os
from pathlib import Path
import smtplib
import ssl
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--application-path", required=True)
    args = parser.parse_args()
    root = Path(args.application_path).resolve()
    if not (root / "Main.py").is_file():
        raise SystemExit("AYEC application directory not found.")
    target = root / "official-services.json"
    config = json.loads(target.read_text(encoding="utf-8-sig")) if target.is_file() else {}
    print("AYEC official sender: info@ayecpro.com | Support: destek@ayecpro.com")
    print("Use the SMTP hostname shown in Turhost email account settings.")
    host = input("SMTP hostname [srvm07.trwww.com]: ").strip() or config.get("smtp_host", "srvm07.trwww.com")
    port = int(input("SMTP port [465]: ").strip() or config.get("smtp_port", 465))
    if port not in (465, 587):
        raise SystemExit("Use TLS SMTP port 465 or 587.")
    password = getpass.getpass("info mailbox password (hidden; blank keeps current): ") or config.get("smtp_password", "")
    client_id = input("Google WEB OAuth Client ID (blank keeps current; - disables): ").strip()
    client_id = "" if client_id == "-" else client_id or config.get("google_client_id", "")
    if client_id and not client_id.endswith(".apps.googleusercontent.com"):
        raise SystemExit("A Google WEB OAuth Client ID is required, not a Gemini API key.")
    if not host or not password:
        raise SystemExit("SMTP hostname and mailbox password are required. No settings changed.")
    print("Checking encrypted SMTP login; no email will be sent...")
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        with server:
            server.login("info@ayecpro.com", password)
    except Exception as error:
        raise SystemExit("SMTP login failed (" + type(error).__name__ + "). No settings changed.") from None
    config.update(smtp_host=host, smtp_port=port, smtp_password=password, google_client_id=client_id)
    fd, name = tempfile.mkstemp(prefix=".official-services-", dir=root)
    temporary = Path(name)
    try:
        os.close(fd)
        if os.name == "nt":
            # Restrict before writing credentials. Production task runs as admin/SYSTEM.
            subprocess.run(["icacls", str(temporary), "/inheritance:r", "/grant:r", "*S-1-5-18:F", "*S-1-5-32-544:F"], check=True, stdout=subprocess.DEVNULL)
        else:
            temporary.chmod(0o600)
        temporary.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("Saved. SMTP authentication succeeded. Settings are loaded automatically.")
    print("Google sign-in: " + ("configured; verify authorized origins in Google Cloud" if client_id else "disabled until an OAuth Client ID is supplied"))
    print("Google authorized JavaScript origin: https://panel.ayecpro.com")


if __name__ == "__main__":
    main()
