# AYEC Pro demo environment

This package creates a public demo landing page and a separate AYEC Pro demo application. It must never point at `panel.ayecpro.com` or reuse the production registry, tenant folder, uploads, or backups.

## Isolation model

The landing page posts to `https://demo-panel.ayecpro.com/api/demo/session`. The demo-only backend creates a new SQLite tenant from `data/demo_template.db` for each click, inserts a restricted `User` account named `admin`, starts a two-hour session, and redirects into the demo app. Tenants are separate database files, so one visitor cannot read or overwrite another visitor's demo records. The demo app uses a separate code copy, registry database, tenant directory, upload area, and backup area. The cleanup job removes expired session databases and their registry references.

The visible `admin / admin` values are public demo credentials. They are not production credentials and are not intended for manual sign-in. The demo app rejects ordinary authentication and account creation; users enter through the landing button, which creates a fresh tenant and sets a host-only demo session cookie. The account role is `User`, so platform administration and user management remain unavailable.

## Hostnames

- `demo.ayecpro.com`: static landing page from `index.html` (no PHP runtime required).
- `demo-panel.ayecpro.com`: HTTPS reverse proxy to a dedicated AYEC Pro web process on `127.0.0.1:8502`.
- `panel.ayecpro.com`: production only; never use it as the demo target.

The extra `demo-panel` hostname keeps the application session cookie host-only. Setting a cookie for `.ayecpro.com` could leak demo sessions to the production panel.

## Install

1. Use a Turhost VPS (Linux or Windows) or another server that can run the AYEC Python service. A shared PHP-only hosting plan can serve the landing page but cannot safely host the AYEC backend process.
2. Create the HTTPS host `demo.ayecpro.com` and upload this directory as its document root. Enable PHP 8 and Apache `mod_headers`; the included `.htaccess` disables directory listing and blocks access to local database/config artifacts.
3. Create a separate app directory, such as `/srv/ayecpro-demo/app`, and copy the complete `Web_Arayuzu` application source and its runtime dependencies there. Do not copy the production `.env`, registry DB, tenant databases, backups, signing keys, or uploads.
4. Create `/srv/ayecpro-demo/data/.ayec-demo-sandbox` as an empty marker file. Create the `tenants`, `backups`, `support-backups`, and `downloads` subdirectories. Copy only `Web_Arayuzu/data/demo_template.db` to `/srv/ayecpro-demo/data/demo_template.db`.
5. Copy `demo.env.example` to `/etc/ayecpro/demo.env`, edit the paths if needed, and keep it outside both web document roots. Protect it so only the AYEC service account and administrators can read it.
6. Start the separate AYEC service using the demo environment file:

   ```sh
   cd /srv/ayecpro-demo/app
   set -a
   . /etc/ayecpro/demo.env
   set +a
   exec python3 Main.py --host "$AYEC_HOST" --port "$AYEC_PORT" --db "$AYEC_DB_PATH" --tenant-dir "$AYEC_TENANT_DIR"
   ```

7. Configure the HTTPS reverse proxy for `demo-panel.ayecpro.com` to send all paths, including `/api/` and the static web assets, to `http://127.0.0.1:8502`. The proxy must pass the original `Host`, set `X-Forwarded-Proto: https`, and must not forward this host to the production AYEC process.
8. Set the `AYEC_DEMO_ENTRY_URL` PHP environment variable to `https://demo-panel.ayecpro.com/api/demo/session` if using a non-default application hostname. The landing page must be HTTPS.
9. Confirm the PHP form POST reaches the demo host with `Origin: https://demo.ayecpro.com`. The backend accepts session creation only from that exact origin and exact `AYEC_DEMO_APP_HOST`.

For cPanel/Plesk, the landing page can be hosted in the site's PHP document root. The Python demo backend still needs a separate VPS process and reverse proxy. Do not run the demo under the production service account or production data directory.

### Windows and IIS deployment

The AYEC live application server is a Windows/IIS host at `85.117.239.60`. The Turhost WordPress host is a separate address. At the time this package was prepared, `demo.ayecpro.com` and `demo-panel.ayecpro.com` resolve to the WordPress address `176.62.166.134`; `panel.ayecpro.com` resolves to `85.117.239.60`. Do not publish or change these DNS records until both IIS sites and HTTPS bindings are ready.

1. Build a clean transfer package from the repository root with `python demo_site/build_demo_bundle.py`. The package includes the demo template but excludes local tenant databases, production databases, logs, signing keys, private service configuration, and local environment files.
   The Windows repair script refreshes the isolated app source and static web assets, the demo landing page, and the seed template while preserving `demo.env`, tenant databases, and other live demo data.
2. Transfer the package and `Install-Demo-Windows.ps1` to the Windows server. Run the installer in an elevated PowerShell session, supplying the archive and the full path to a machine-wide Python installation with the AYEC runtime dependencies installed: `-BundlePath C:\path\AYECPro_Demo_Server.zip -PythonPath C:\Python312\python.exe`. The installer refuses to overwrite an existing `C:\AYECPro-Demo` directory and creates a separate app, landing root, seed database, sandbox marker, and startup/cleanup scheduled tasks.
3. The landing site's physical root is `C:\AYECPro-Demo\Landing`; it contains only `index.html` and `web.config`. The application site's root is `C:\AYECPro-Demo\App\web`; its `web.config` proxies to loopback port `8502`. Do not map either IIS site to `C:\AYECPro-Demo` or the production application directory.
4. In IIS, create two separate sites and host bindings: `demo.ayecpro.com` rooted at `C:\AYECPro-Demo\Landing`, and `demo-panel.ayecpro.com` rooted at `C:\AYECPro-Demo\App\web`. Enable IIS URL Rewrite and ARR reverse proxy, and enable ARR's **Preserve host header** setting so the backend receives `Host: demo-panel.ayecpro.com`.
6. Install an HTTPS certificate whose SAN contains both demo hostnames and bind it to the corresponding IIS sites. The app uses `AYEC_COOKIE_SECURE=1`; don't expose a plain HTTP demo session. Confirm the app startup task is running and the cleanup task is registered before the DNS change.
7. Only after the IIS sites, backend task, and HTTPS bindings pass local host-header checks, change the DNS A records for `demo` and `demo-panel` to `85.117.239.60`. Leave the apex and `www` records untouched. DNS changes can take time to propagate.
8. Run the hourly cleanup task under the same isolated demo account. Set its `AYEC_DEMO_ROOT`, `AYEC_DB_PATH`, and `AYEC_TENANT_DIR` from the Windows env file. First run `reset_demo_sessions.py --age-hours 3 --dry-run`.

This workspace has no authorized WinRM access to the Windows host; the current interactive RDP session does not grant remote shell access. The steps above describe the required IIS changes and must be applied on that host before the public DNS switch. A cPanel/PHP upload alone cannot run this Python demo backend.

## Scheduled cleanup

The session expires after two hours. Run the cleanup every hour so old demo tenant DBs and registry rows are removed after three hours. The script refuses to act unless `.ayec-demo-sandbox` exists and all configured DB paths are inside `AYEC_DEMO_ROOT`.

Example crontab:

```cron
0 * * * * AYEC_DEMO_ENV_FILE=/etc/ayecpro/demo.env AYEC_DEMO_CLEANUP_SCRIPT=/srv/ayecpro-demo/demo_site/reset_demo_sessions.py /srv/ayecpro-demo/demo_site/cleanup-demo.sh >> /var/log/ayecpro-demo-cleanup.log 2>&1
```

Preview cleanup first:

```sh
set -a && . /etc/ayecpro/demo.env && set +a
python3 /srv/ayecpro-demo/demo_site/reset_demo_sessions.py --age-hours 3 --dry-run
```

On Windows, create a Task Scheduler job that runs `reset_demo_sessions.py --age-hours 3` hourly with the demo environment variables set. Keep the data root and task restricted to the demo service account.

## Safeguards and limits

- The backend refuses demo session creation unless `AYEC_DEMO_MODE=1`, the marker file exists, and the registry DB, tenant folder, and template all resolve below the dedicated demo data root.
- The demo endpoint allows at most ten starts per client IP per hour. Configure the reverse proxy to overwrite `X-Forwarded-For` from the real client address.
- Authentication, registration, password reset, and profile changes are disabled in demo mode. The landing action provisions a fresh session instead.
- Demo tenants use a non-admin role. Each visitor can modify their own seeded records; those writes stay in their own tenant DB and expire with that DB.
- The template's user/session rows are replaced. Credential-like setting keys are cleared in each new tenant. Configure SMTP and third-party API credentials as empty in the demo service.
- All demo backups and downloads must point under the demo data root. Never mount or expose the production DB, signing keys, backup folder, or upload directory to this process.

## Connection contract

Product code remains `teknik_servis`; the demo is an isolated deployment of the existing Technical Service product, not a new licensed product. It uses the same AYEC web API contract and tenant-scoped SQLite layout. No production `Admin_Konsol` registry, license catalog, or production customer/device data is mounted into the demo instance.
