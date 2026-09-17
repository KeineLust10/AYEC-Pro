# AYEC Pro Central Platform Plan

## Product roles

- AYEC Pro Technical Service: desktop product and reference implementation.
- AYEC Pro Barkod Okuyucu: desktop POS product.
- AYEC Pro Elek: desktop trade and inventory product.
- AYEC Pro Ciro: desktop finance product.
- Web_Arayuzu: central API and tenant data service.
- Admin_Konsol: management center for products, companies, licenses, backups, restores, and audit records.

## Delivery phases

1. Establish one product registry and remove duplicated name-to-code mappings.
2. Standardize license requests, device checks, pricing, and revocation by `product_code`.
3. Standardize tenant-authenticated SQLite snapshot upload, retention, and staged restore.
4. Connect Barkod Okuyucu, Elek, and Ciro to the shared session and backup contract.
5. Adapt the Technical Service smart import parser to Barkod Okuyucu with product-field mapping and preview.
6. Add Admin_Konsol product filters and backup/license visibility from the shared registry.
7. Verify every product with contract, migration, integration, and UI smoke tests.

## Storage contract

`C:\AYECPro Programlar\<product folder>\<backup folder>\tenants\<tenant_id>\devices\<device hash>\current\<database name>` stores the latest verified snapshot per installation. Historical snapshots are stored under `versions`. Missing legacy device identity uses the `legacy` directory. Registry and archive retention are independent per product and device; pending restore sources remain protected.

## Implementation status

- Done: shared product registry at `ecosystem/products.json`.
- Done: Admin_Konsol product selectors and filters read the shared registry.
- Done: Web_Arayuzu validates tenant product codes against the shared registry, with a safe fallback for packaged deployments.
- Done: Barkod Okuyucu backup requests carry the product identity and create consistent SQLite snapshots.
- Done: Barkod Okuyucu has preview and confirmation before Excel/CSV import writes production rows.
- In progress: move Barkod Okuyucu from token-only backup configuration to the Technical Service session/cookie flow. Login, encrypted local credential storage, and cookie transport are now supported; full sync parity remains.
- In progress: add staged remote restore and pending-command processing to Barkod Okuyucu.
- In progress: share the Technical Service parser and synchronization client as a distributable AYEC Core package.
  The initial ayec-core 0.1.0 wheel now owns SQLite snapshot generation and
  product-scoped backup headers, consumed by Technical Service and Barkod.
  Version 0.2.0 packages the Technical Service document parser. Barkod imports
  the installed parser without a developer checkout; Technical Service keeps
  its old import path through a compatibility module. Web release staging
  includes the shared sources. Shared staged restore now verifies checksum,
  SQLite integrity, exact staging path, and product identity before replacement.
  Both desktop clients consume it; Barkod also checks its required tables and
  runs scheduled central backup work outside the UI thread. Shared session
  persistence and cookie handling are consumed by both clients, with their
  existing encryption preserved. Elek/Ciro adapters, shared licensing transport
  and deployed verification remain open. Server backup records and restore commands
  now carry product identity; device-specific restores can only be claimed,
  downloaded, and acknowledged by the matching product/device request. Admin
  backup rows expose product and device. The web release includes products.json.
  See ecosystem/README.md.
