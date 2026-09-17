# AYEC Central Integration Contract

All products use `ecosystem/src/ayec_core` and the Web_Arayuzu central API. Product identity is declared in `ecosystem/products.json`; business SQLite databases remain separate per product, tenant, and installation.

## Required client contract

- License: submit `product_code`, `tenant_id`, `hardware_id`; accept activation only after server entitlement/signature validation; poll status so revoked entitlements lock the client.
- Session: use the central session token and send it with license, backup, restore, and status requests.
- Backup: create an SQLite-consistent snapshot, validate integrity, and upload metadata (`product_code`, tenant, hardware ID, checksum, size, timestamp, source).
- Restore: fetch only the selected tenant/product/device backup, validate checksum and SQLite integrity, preserve the current database, stage restore, and apply at startup.
- Commands: poll authenticated management commands; acknowledge each command once; connect `backup_now` and `restore_backup` to the application scheduler.
- Smart import: preview and validate all rows, require explicit confirmation, and perform an all-or-nothing transaction.

## Product registrations

`teknik_servis`, `barkod_okuyucu`, `elek`, and `ciro` are registered with independent database and backup names. Prices are owned by the central catalog; offline values are display-only fallbacks generated from that catalog.

## Verification gate

A release is complete only after unit/integration tests, clean-environment package installation, API reachability over HTTPS (443), license request/activation/revocation, email delivery, backup upload, Admin_Konsol selection, restore command, startup restore, and data-preservation checks succeed. Local tests must be reported separately from live evidence.
