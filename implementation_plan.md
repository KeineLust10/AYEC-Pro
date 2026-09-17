# Dashboard and Service List Implementation Plan

## Scope

- Rework the technical service dashboard composition toward the supplied reference: welcome header, colored status cards, quick metrics, and a service status area.
- Add a dedicated `Servis Listesi` entry under the `Servis Yonetimi` side-menu group, backed by the dashboard's device/service table and the same database queries used by its status cards.
- Make dashboard status cards actionable. A click opens the service list and applies the matching status filter so the related devices are visible immediately.
- Preserve the existing database, product isolation, and AYEC Core integration contract. No new licensing, authentication, pricing, backup, or restore path is introduced.

## Implementation steps

1. Register a stable page id for the service list and add its page name/parent metadata.
2. Add the menu item under `Servis Yonetimi`; keep existing service pages and permissions intact.
3. Extend `ServicesPage` with a status-filter entry point and normalize dashboard status keys.
4. Connect dashboard status tiles to the service-list page and pass the selected filter.
5. Adjust dashboard spacing and visual hierarchy to match the reference without replacing the existing theme system.
6. Run focused syntax/tests plus `tools/mojibake_guard.py` and `tools/ascii_diff_guard.py`.

## Verification

- The menu exposes `Servis Listesi` below `Servis Yonetimi`.
- Clicking each dashboard status card navigates to the service list and shows only matching devices.
- Existing dashboard refresh and direct service-list navigation still work.
- Source guards and focused PyQt/import checks pass.
