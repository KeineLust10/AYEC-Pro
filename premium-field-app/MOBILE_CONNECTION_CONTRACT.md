# AYEC Pro Technical Service Mobile Contract

## Product identity

- Product code: `teknik_servis` (already registered in `ecosystem/products.json`)
- Public name: AYEC Pro Technical Service
- Android application id: `com.ayecpro.teknikservis`
- Local cache: `ayec-field-service.db` (SQLite, partitioned by central tenant id)
- Licensing, authentication, tenant registry, backups, and restore remain owned by AYEC Core and the central Web API.

## API connection

- Configure `EXPO_PUBLIC_API_URL` as the HTTPS base URL of the central Web_Arayuzu API, including its `/api` prefix.
- `POST /auth/login` authenticates the field user. The mobile app stores the returned bearer token using Android SecureStore.
- `POST /license/activate` uses the central invitation and licensing flow when the API requires activation.
- `GET /desktop/bootstrap` loads the authenticated tenant's service data. The mobile client does not select or override tenant identity.
- `POST /mobile/personnel/status` changes the authenticated technician status.
- `POST /mobile/personnel/location` sends the authenticated technician location while tracking is enabled.
- `GET /mobile/service/detail?tracking_no=...` returns one service record, its part usage, and its tenant-scoped evidence metadata.
- `POST /mobile/service/update` saves the service status, reported fault, and repair report.
- `POST /mobile/service/evidence` stores before/after photos and customer signatures in the active tenant SQLite database.
- `GET /mobile/service/evidence?id=...` streams an evidence image after checking the authenticated tenant.
- Requests use the central API's bearer-token session and tenant context. No mobile-side license or pricing catalog is created.

## Full program modules

- The mobile drawer includes an AYEC Pro full-program entry backed by the central responsive Web_Arayuzu client. It exposes the account-authorized desktop module menu, including Smart Import and the existing document and data libraries.
- The bridge reads the current bearer token from Android SecureStore and attaches it only to same-origin `/api/` requests inside the HTTPS WebView. It does not place the token in a URL or send it to other origins.
- Web modules require network access. The native service list, service detail, cached records, and outbox remain available through the mobile field workflow.
- Smart Import parsing, PDF/OCR, Excel/XML, and other parser libraries run in the central AYEC Core/Web_Arayuzu runtime. The mobile APK is a client and does not bundle a second Python parser stack. Runtime library availability is governed by `Web_Arayuzu/requirements.txt` and `ecosystem/requirements-desktop.txt`.

## Data and sync rules

- Cached bootstrap and service detail payloads, queued edits, and queued evidence are stored in SQLite under the authenticated tenant id.
- The offline queue replays status changes, service notes, photos, and signatures in order when network access returns. Authentication or authorization failures pause replay.
- Evidence images are stored as SQLite blobs, so tenant database backups include their bytes and metadata.
- A user response without a central `tenant_id` or `company_id` is not cached or queued offline.
- Backup and restore are not implemented by this mobile client; central AYEC Core commands and registries remain authoritative.

## Remaining rollout requirements

- Set a production HTTPS `EXPO_PUBLIC_API_URL` in the EAS build environment; never ship the development HTTP fallback.
- Validate mobile API authorization and all data returned by `/desktop/bootstrap` with tenant-isolation integration tests.
- The scan screen searches the existing tenant service list by scanned value. A dedicated barcode-to-service API is not required for that lookup flow.
- Deploy the matching Web_Arayuzu API changes and verify them against an isolated tenant database before field rollout.
- Configure an EAS signing credential owned by the organization and archive the signing and recovery procedure.
