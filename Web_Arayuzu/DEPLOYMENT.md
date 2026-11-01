# AYEC Pro Web Server Deployment

This package runs the AYEC Pro web API and interface with Docker Compose. It
does not start automatically while you inspect or edit the source tree.

## Files to copy

Copy the complete `Web_Arayuzu` directory to the server. Keep these files
together:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `requirements.txt`, `requirements-ocr.txt`, and `requirements-paddle.txt`
- `Main.py`, `web/`, and the remaining application files

Do not copy local `.env`, database, backup, log, or virtual-environment files
from a developer machine. The Docker build context excludes these local files.

To create a clean upload archive from the current source, run:

```powershell
python tools/build_deployment_bundle.py
```

The archive is written to `../dist/AYEC_Pro_Web_Server.zip`. It contains the
web runtime and deployment configuration while excluding local databases,
tenant, backup, upload, private signing key, and virtual-environment data.

## Configure and validate

From the copied `Web_Arayuzu` directory, create the environment file and edit
the public port and dependency profile if required:

```powershell
Copy-Item .env.example .env
```

Validate the Compose file before starting the service:

```powershell
docker compose config --quiet
```

Build and start the service when the server is ready:

```powershell
docker compose build ayec-web
docker compose up -d ayec-web
docker compose logs -f ayec-web
```

## Reset the platform admin password

After the service is running, open PowerShell in the extracted deployment
folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RESET_ADMIN_PASSWORD.ps1
```

Enter a password with at least 8 characters when prompted. The script applies
it to `ayecpro@gmail.com` in the running `ayec-web` container. It does not put
the password in the command line, and the reset utility retains a database
backup before changing the account.

The Compose file publishes the selected host port to container port `8501`.
Its bind mounts keep `/data`, tenant data, and web uploads outside the
container. Back up the host data, tenant data, and upload directories together.
Do this before moving or restoring the deployment.

## Network and operations

Place the service behind an HTTPS reverse proxy for public access. Restrict
the application port to the proxy and trusted administration networks. Do not
publish SQLite files or the data directories as static web content.

The proxy must forward `/api/` requests to the AYEC web service without
redirecting them to the public site or its SPA fallback. In particular,
`POST /api/auth/login` must reach the running service and return JSON. If the
login page reports that the API returned HTML with HTTP 200, the proxy or
hosting rewrite is serving the website document for an API URL; correct that
route and rebuild/restart the AYEC service before testing sign-in again.

Use `docker compose stop ayec-web` to stop the service and
`docker compose start ayec-web` to start it again. Updating source files
requires rebuilding the image before replacing the running container.

## Verification boundary

The Compose configuration can be validated without starting the application.
An image build requires an available Docker Engine and access to the package
registries used by the Dockerfile. Application screenshots and runtime checks
must be performed on the server deployment after you start it.

Run the credential-free deployment probe after the service is online:

```powershell
python check_public_deployment.py --base-url https://panel.ayecpro.com
```

This checks the served asset key, backend build ID, JSON status response, root server/date/cache metadata, and
unauthenticated profile behavior without submitting a login attempt. Root response metadata helps distinguish a stale deployment from a cache issue. To also
verify the login POST route, run with `--check-login-post` only after the
expected build is active. That option submits one empty credential payload;
older server versions may count it as a failed sign-in.

## Update an existing Windows and IIS deployment

Uploading only a ZIP, `index.html`, or `Main.py` does not replace the running AYEC service. IIS forwards API requests to the `AYEC Pro Web` scheduled task, so the frontend and Python backend must come from the same complete build.

1. Back up and retain the server's `data`, tenant directory, uploads, backups, and existing `config` signing key. The deployment archive intentionally excludes local databases and tenant data.
2. Extract the complete `AYEC_Pro_Web_Server` archive so its top-level `Web_Arayuzu` folder is the installed project directory. Do not extract it into a nested `Web_Arayuzu\Web_Arayuzu` path.
3. Restore the retained server data directories into that project directory, then run PowerShell as Administrator from it:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\server-windows-install.ps1
   ```

   The installer copies the packaged `web` assets into the selected IIS site's physical root, backs up replaced files under `%ProgramData%\AYEC Pro\backups\iis-web-*`, and preserves the existing `web/uploads` contents. It also updates the scheduled task and IIS reverse-proxy configuration, restarts IIS, and runs local frontend/API deployment checks. Its credential-free `POST /api/auth/login` probe sends an empty JSON object and requires a JSON 400 or 401 response; it does not attempt an account sign-in.
   `AYEC_START.cmd` restarts the matching scheduled task (or safely replaces only an AYEC process using this database), waits for `/api/desktop/health`, and checks that the API build matches the package. It does not reset or prompt for an admin password. Python error output stays in `logs/server.error.log`.
   The installer selects the IIS site bound to `panel.ayecpro.com` on HTTP port 80, then verifies it through a loopback request with that `Host` header. For another domain, pass `-IisHostName your.host`; if site binding detection is ambiguous, pass `-IisSiteName "Your IIS Site"`.
   To manually probe a named IIS site from the server, use `python .\check_public_deployment.py --base-url http://127.0.0.1 --host-header panel.ayecpro.com`.
   To enable Google sign-in or registration, create/configure a Google OAuth Web client in Google Cloud, set the AYEC Pro application branding and consent screen, and add `https://panel.ayecpro.com` as an authorized JavaScript origin. Then run `CONFIGURE_GOOGLE_SIGNIN.cmd` as Administrator and enter the Web OAuth Client ID. This updates only the protected `official-services.json` setting and leaves SMTP configuration untouched. The server verifies Google ID tokens; the web flow requests profile identity only and does not receive the user's Google password. Google sign-in and registration remain unavailable until this central setting is configured.

   To enable password-reset email delivery, run `CONFIGURE_AYEC_OFFICIAL_SERVICES.cmd` as Administrator. It uses the official `info@ayecpro.com` sender and defaults to the SMTP host and port already used by AYEC Pro. Enter the mailbox password when prompted. The tool verifies SMTP login without sending a message, saves credentials in the protected server-only `official-services.json`, and preserves the Google Client ID.
4. Verify the public host without sending a login attempt:

   ```powershell
   python .\check_public_deployment.py --base-url https://panel.ayecpro.com
   ```

The frontend key and API build ID must match, and the anonymous profile request must return JSON HTTP 401. An HTTP 400 mentioning a missing `require_user` handler means an older or mixed backend is still running. An API request returning HTML with HTTP 200 means IIS is still serving a web fallback for that API route. If the public probe reports `backend_unavailable`, run `tools\diagnose_server_502.ps1` on the server and inspect `logs\server.error.log`; this is a backend or IIS upstream outage, not a normal form validation response. Do not retry sign-in until the deployment probe passes.
