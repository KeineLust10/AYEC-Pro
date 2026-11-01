# Web API 502 and Google Sign-In Audit

## Scope and evidence

- The observed browser response is an IIS HTTP 502 for `panel.ayecpro.com`.
- The public deployment probe checks the root document, auth status, desktop bootstrap, and a harmless profile POST. A 502 at the root and unrelated API routes indicates that IIS cannot reach the Python backend; it is not a customer-note or stock validation response.
- Ordinary authenticated table writes return application-level 4xx/5xx responses from `Main.py`. They do not convert SQLite errors to HTTP 502. Therefore a common 502 across notes, stock, and uploads is consistent with an unavailable or misrouted backend.
- Explicit application-generated 502 responses are limited to TomTom traffic/vector calls, Google Drive backup upload, e-invoice runtime failures, and field-service geocoding/routing. These paths do not explain ordinary CRM note or stock writes.
- A server startup log supplied during the investigation showed `Device model catalog read failed` followed by a PowerShell `NativeCommandError` at the Python launcher. Its traceback was not included, so the precise database exception is unconfirmed. The model-catalog endpoint now creates a missing legacy `device_brands` table before seeding. The Windows launcher no longer treats Python stderr as a terminating PowerShell error, and `AYEC_START.cmd` restarts or launches the service hidden and waits for health. This prevents an ordinary API traceback from taking down the process; any other catalog exception still requires the server error log to identify its exact cause.
- The local Ollama endpoint and an Ollama MCP/API bridge were unavailable during this audit. The scan therefore used bounded `rg` searches and focused source inspection, not model classification.

## Fixes in this change

- Public deployment diagnostics now classify HTTP 502/503/504 as `backend_unavailable`. They do not report derivative frontend-build or anonymous-bootstrap errors when the upstream is unavailable.
- Google sign-up remains subject to verified Google email, a one-use nonce, tenant registration rules, and license access. Registration collects the company address required by central tenant onboarding.
- Desktop Google sign-in uses the same central Google Identity Services client and account mapping as web. A short-lived, one-use PKCE handoff binds browser approval to the native client. Only an already linked Google identity may approve desktop access; a password or bearer token is never placed in a URL.
- The native client receives the normal central session cookie through its existing AYEC Core session store. Handoffs expire after ten minutes and are held in memory, so a server restart safely requires the user to retry.

## Deployment boundary

Repository changes cannot repair a remote IIS host whose Python task is stopped, crashing, or listening on a different port. The server must pass the local health URL configured by the installer before the public proxy can serve any API writes. If the public probe still reports `backend_unavailable`, run `Web_Arayuzu/tools/diagnose_server_502.ps1` on that host. It records the task state, listener, local backend health, IIS API health, and rewrite target without collecting credentials. Also inspect the host's `logs/server.error.log`. Do not infer production recovery from local tests or package creation.

Google buttons also require the server-side `AYEC_GOOGLE_CLIENT_ID` or `google_client_id` in the existing official service configuration. Never put a Google client secret in the browser bundle.
