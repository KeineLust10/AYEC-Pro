# AYEC Central Platform Resilience and Rollout Plan

Date: 2026-09-16
Status: Implementation plan
Owners: AYEC Core, Web_Arayuzu, Admin_Konsol, and product clients

## 1. Objective

Build one central integration for Technical Service, Barkod Okuyucu, Elek,
Ciro, and future AYEC products without making daily business operations depend
on a permanent internet connection. A temporary server, DNS, TLS, e-mail, or
network failure must not stop sales, stock, service, or accounting work.

The central platform remains the authority for licensing, identity, pricing,
backup records, and restore commands. Every product keeps its own local SQLite
business database and continues core business work offline.

## 2. Product contract before connection

Each product must declare the following in `ecosystem/products.json` before
integration starts:

- `product_code`, public name, local database name, and backup folder;
- tenant and installation identity;
- trial duration and signed offline-license policy;
- automatic backup interval and local retention limits;
- required SQLite tables for restore validation;
- supported central commands and smart-import support;
- minimum AYEC Core and database schema versions.

Business databases must never be merged. The central service indexes backups by
tenant, product, installation, and hardware identity.

## 3. Shared client components

AYEC Core will expose one product-neutral client composed of these services:

1. `IdentityStore`: stable installation ID, tenant ID, product code, and device
   identity. Secrets are stored with Windows protection or the product's
   existing encrypted store.
2. `LicenseCache`: signed entitlement, validity dates, last successful server
   check, monotonic timing evidence, and revocation epoch.
3. `Outbox`: durable SQLite queue for backup uploads, audit events, command
   acknowledgements, and other retryable requests.
4. `BackupEngine`: SQLite snapshot, integrity check, checksum, encryption, local
   retention, and upload preparation.
5. `CommandWorker`: authenticated command polling, command deduplication, safe
   staging, and acknowledgement.
6. `ConnectivityMonitor`: distinguishes internet, DNS, TLS, authentication,
   server, and application errors.
7. `HealthState`: one compact status for the user and diagnostics for support.

Product applications use adapters for their database path, scheduler, UI
notifications, and restart behavior. Network operations never run on the UI
thread.

## 4. Offline-first operating rules

### 4.1 License behavior

The application stores only a server-signed, device-bound entitlement. A key's
length or local text format can never activate a product.

License states:

- `ACTIVE_ONLINE`: server recently confirmed the entitlement.
- `ACTIVE_OFFLINE`: signed cached entitlement is valid, but the server cannot be
  reached. Business functions continue.
- `RECHECK_REQUIRED`: the normal offline allowance expired. The product keeps a
  restricted safety window and shows a persistent warning.
- `EXPIRED`: the signed entitlement end date passed. Read-only access, export,
  local backup, and license renewal remain available.
- `REVOKED`: a verified server response revoked the entitlement. The product
  closes protected write operations after saving current work.
- `CLOCK_SUSPECT`: material clock rollback was detected. Use trusted monotonic
  and last-seen time evidence; do not immediately destroy access or data.

Recommended policy:

- normal offline allowance: 7 days after the last successful check;
- additional restricted safety window: 3 days;
- server checks: at startup, every 6 hours, and after connectivity returns;
- retry timing: 1, 5, 15, 30, and 60 minutes, then every 6 hours with jitter;
- the signed license expiry is always authoritative; the offline allowance must
  never extend a genuinely expired license.

The 7+3 day values must be central policy fields so they can be changed by
product without releasing a new client. A transient timeout, DNS failure, or
HTTP 5xx response is never treated as revocation. Only a valid authenticated
server response can set `REVOKED`.

### 4.2 Backup behavior

Every scheduled backup is created locally first. Success means that the SQLite
snapshot passed `PRAGMA integrity_check`, received a checksum, and was committed
to the local backup manifest. Upload is a separate state.

Backup states:

- `LOCAL_READY`: safe local backup exists;
- `QUEUED`: upload waits in the durable outbox;
- `UPLOADING`: server transfer is active;
- `REMOTE_CONFIRMED`: server returned a backup ID and matching checksum;
- `RETRYABLE_ERROR`: network or server error;
- `QUARANTINED`: integrity, identity, size, or checksum validation failed.

Rules:

- automatic local snapshot continues without internet;
- queued uploads survive application and computer restarts;
- retries are idempotent using a generated backup UUID and checksum;
- use exponential backoff with jitter and a maximum retry interval of 6 hours;
- keep at least the latest 10 valid local backups and at least 7 days of history;
- never delete the last known-good local backup because an upload succeeded;
- when disk space is low, prune only confirmed old backups and keep the newest
  known-good backup; warn the user and Admin_Konsol;
- large queues upload oldest valid backups first, but may coalesce redundant
  hourly backups while preserving daily checkpoints.

### 4.3 Restore behavior

Restore is intentionally stricter than backup. It is never silently applied
while the application is processing business data.

Restore command states:

- `RECEIVED`: authenticated and assigned to this tenant, product, installation,
  and device;
- `DOWNLOADED`: payload checksum and size match central metadata;
- `VALIDATED`: SQLite integrity and required schema/table checks passed;
- `STAGED`: current database was backed up and restore is ready for restart;
- `APPLIED`: startup migration and post-restore health checks passed;
- `ROLLED_BACK`: post-restore checks failed and the preserved database returned;
- `REJECTED`: identity, version, integrity, or authorization check failed.

If internet disappears during download, the partial file is discarded or
resumed only when the server supports verified ranges. The current database is
untouched. If internet disappears after staging, the local validated restore can
still be applied at restart and its acknowledgement remains queued.

Restore requires either explicit local confirmation or a centrally marked
emergency command allowed by policy. Before replacement, the client closes
database writers, creates a separate `before_restore` snapshot, validates it,
and records an atomic restore journal. Failed startup health checks trigger an
automatic rollback.

### 4.4 Session and commands

An expired central session must not stop local business work. The client queues
retryable work and asks for login only when a central operation needs it.
Credentials are never stored in the outbox. Session cookies or tokens are
encrypted and scoped to base URL, tenant, product, and installation.

Commands have a unique ID and are processed exactly once from the product's
point of view. The server may deliver a command more than once; the local
command journal returns the stored result instead of applying it again.

## 5. Failure scenarios and expected behavior

| Scenario | Immediate behavior | Recovery | Proof required |
| --- | --- | --- | --- |
| Internet is lost during normal use | Core business work continues; status becomes offline | Retry in background after connectivity returns | No UI freeze, no lost transaction |
| Internet is lost before a license check | Use valid signed cache within policy | Recheck immediately after reconnection | State changes to `ACTIVE_OFFLINE`, not revoked |
| Internet is absent longer than offline allowance | Warn, enter restricted safety window | Server confirmation restores normal state | Policy timing tests |
| License expires while offline | Finish and save active transaction; enter read-only mode | Renew and verify online | Export and local backup still work |
| Server revokes a license | Apply only after authenticated response; save open work | Admin renews/reactivates and client rechecks | Revocation end-to-end test |
| DNS works but TLS fails | Classify as TLS error; do not fall back to HTTP | Repair certificate/binding and retry HTTPS | Valid chain, host name, expiry, TLS test |
| API returns 5xx or times out | Queue operation; do not infer license revocation | Backoff retry with jitter | Fault-injection tests |
| Authentication expires | Keep local work; pause central calls | Reauthenticate and drain queue | No credentials stored in queue |
| Backup schedule runs offline | Create local backup and enqueue upload | Upload and checksum-confirm later | Restart-persistent queue test |
| App closes during upload | Keep item queued; temporary transfer is not success | Resume/retry idempotently | Kill-and-restart test |
| Disk becomes full | Stop new snapshot safely; keep database untouched | Prune eligible confirmed backups or request space | Low-disk test |
| Backup database is corrupt | Quarantine; do not upload as valid | Create another snapshot or report repair need | Integrity failure test |
| Restore download is interrupted | Current database remains active | Redownload and validate | Interruption test |
| Restore targets wrong tenant/device | Reject before download or staging | Admin selects correct identity | Cross-tenant isolation test |
| Power loss occurs during restore | Atomic journal detects incomplete operation | Roll back to `before_restore` backup | Forced-termination test |
| Client clock moves backward | Enter `CLOCK_SUSPECT`; do not extend license | Compare trusted server time on reconnection | Clock rollback test |
| Duplicate command arrives | Return prior result; do not repeat mutation | Server records acknowledgement | Idempotency test |
| Client is too old for server schema | Keep local work and block incompatible central action | Require signed update/migration | Version compatibility test |
| Central database is unavailable | API returns service error; clients queue work | Restore central DB/service and drain queues | Server outage exercise |

## 6. Implementation phases

### Phase 0 - Inventory and freeze the contract

- Record every current license, database, backup, restore, pricing, and session
  implementation in Technical Service, Barkod, Elek, and Ciro.
- Map API routes and database migrations; remove no legacy path yet.
- Define central error codes, version headers, idempotency keys, and audit fields.
- Back up existing customer databases and configuration before migrations.

Exit: product contract table and migration/rollback plan are reviewed.

### Phase 1 - Harden AYEC Core

- Add the durable outbox, command journal, connectivity classification, signed
  license cache, retry policy, and health state.
- Make backup snapshots and restore journals atomic.
- Add fault-injection unit tests without involving product UI code.

Exit: AYEC Core passes offline, restart, duplicate, corruption, and clock tests.

### Phase 2 - Complete Web_Arayuzu and Admin_Konsol

- Add idempotent backup upload and checksum confirmation.
- Return signed entitlements, server time, revocation epoch, policy fields, and
  stable error codes.
- Enforce tenant/product/installation/device filters on backup and commands.
- Show local-created time, remote-confirmed time, queue delay, checksum, and
  restore result in Admin_Konsol.
- Add audit records for license, backup selection, restore issue, completion,
  failure, and rollback.

Exit: API integration tests prove isolation and duplicate safety.

### Phase 3 - Pilot Technical Service

- Integrate the hardened AYEC Core using an adapter and feature flags.
- Run old and new status reporting in observation mode before switching writes.
- Test with copied data in a clean environment; do not use the only customer DB.

Exit: a 7-day pilot shows no data loss, UI blockage, or duplicate operation.

### Phase 4 - Barkod Okuyucu

- Adopt the same license state machine, outbox, and backup/restore worker.
- Keep POS sales fully local and nonblocking.
- Adapt Smart Import to preview, row errors, explicit confirmation, and one
  transaction.
- Generate offline display prices from the approved central catalog.

Exit: POS continues through simulated outages and drains its queue afterward.

### Phase 5 - Elek

- Connect automatic local backup, central upload, command polling, and staged
  restore to the application scheduler.
- Preserve the already implemented local startup restore behavior.
- Add a clear local/queued/remote-confirmed backup status.

Exit: offline backup and Admin_Konsol restore work end to end.

### Phase 6 - Ciro

- Install and pin the same AYEC Core version in a clean supported Python
  environment.
- Add product adapters and tests for license, session, backup, restore, and data
  preservation.
- Treat old Windows builds separately; do not weaken TLS or license validation
  for compatibility.

Exit: supported builds pass clean-install and migration tests.

### Phase 7 - Live TLS and workflow verification

- Verify DNS, IIS 443 binding, certificate chain, host name, expiration, renewal,
  firewall, and HTTPS-only client configuration.
- Perform controlled real license request, e-mail delivery, activation, expiry,
  revocation, backup upload, Admin_Konsol download, restore command, application
  restart, and rollback tests.
- Record timestamps, request/backup/command IDs, checksums, and audit entries.

Exit: every live claim has reproducible evidence. HTTP catalog success alone is
not sufficient.

### Phase 8 - Staged release

- Release to internal devices, then a small customer group, then wider cohorts.
- Use feature flags and a per-product kill switch for central synchronization;
  the kill switch disables network workers without disabling local business
  functions.
- Monitor license-check success, queue age, upload failures, restore failures,
  storage pressure, and client versions.

Exit: rollout metrics remain within limits and rollback has been rehearsed.

## 7. Rollback and incident controls

- Keep the previous AYEC Core package and product adapter available for one
  release window.
- Database migrations are additive first; destructive cleanup happens only in a
  later release after verified adoption.
- Every migration creates a validated local backup and records schema version.
- A remote feature flag can pause uploads and command polling. It cannot remotely
  delete business data or bypass license verification.
- Restore commands can be cancelled until staging and are never applied twice.
- Support diagnostics export contains versions, error classes, queue metadata,
  and redacted IDs; it excludes passwords, tokens, and business records.
- Incident order: preserve business DB, stop the failing worker, export
  diagnostics, preserve queued work, roll back adapter/package if needed, then
  reconcile server records by idempotency key.

## 8. Test matrix and release gates

Required automated tests:

- unit: signature, HWID binding, expiry, clock rollback, retry, queue persistence,
  snapshot integrity, checksum, restore journal, deduplication, and migrations;
- integration: API authentication, tenant isolation, license lifecycle, upload,
  download, command acknowledgement, session expiry, and version compatibility;
- fault injection: no network, DNS failure, TLS failure, timeout, 401, 403, 409,
  429, 5xx, disk full, corrupt DB, process kill, and power-loss simulation;
- clean environment: Web, Technical Service, Barkod, Elek, and Ciro installation,
  upgrade, downgrade/rollback where supported, and existing-data preservation;
- UI smoke: no startup block, no modal retry storm, clear status, and renewal or
  login actions remain reachable.

Release is blocked if any of these are true:

- business operations freeze because the network is unavailable;
- an unverified local key activates a product;
- a timeout is interpreted as revocation;
- a backup is reported as remote before checksum confirmation;
- restore can overwrite the current database without a validated preservation
  backup;
- a tenant, product, installation, or device can access another identity's data;
- migration or rollback loses existing customer data;
- live HTTPS, e-mail, activation, revocation, backup, and restore evidence is
  incomplete.

## 9. Operational targets

- local business operation availability during internet outage: 100 percent,
  subject only to local application/device health;
- UI network call timeout: no synchronous network call on the UI thread;
- recovery point: latest successful local scheduled snapshot;
- upload recovery: queue begins draining within 1 minute of detected recovery;
- restore recovery: automatic rollback after failed post-restore health check;
- observability: every central mutation has correlation ID, idempotency key,
  product, tenant, installation, device, timestamp, and result.

## 10. First implementation slice

The first code change should be limited to AYEC Core and a test harness:

1. durable outbox and idempotency keys;
2. connectivity/error classification;
3. signed license cache state machine and central policy fields;
4. backup manifest with local and remote states;
5. command journal and staged restore journal;
6. fault-injection tests for offline, restart, duplicate delivery, corruption,
   disk full, clock rollback, and interrupted restore.

After this slice passes, integrate one product at a time. This keeps failures
isolated and gives every later product the same tested behavior.
