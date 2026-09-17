# AYEC Pro Menu, Signal And Dialog Audit

Date: 2026-03-31
Workspace: `C:\Users\yedek\Desktop\yapay zeka\AYEC Pro`

## Scope

This audit covers:

- top-level menus
- submenus
- page routing
- dialog entry points
- right-click/context menu surfaces
- import/export/print actions
- selected runtime smoke checks

This document distinguishes between:

- `Verified Broken`: reproduced or confirmed by code-path inspection with a clear root cause
- `Verified Fixed`: implemented and validated by compile or smoke test
- `Needs Live Click Confirmation`: wired in code, but not yet fully confirmed end-to-end on a live database/UI path

## Latest Update

Last remediation pass completed on: `2026-03-31`

Newly verified fixed in code:

- `Calisma Ortaklari -> + Gonderi Kaydi`
  - no longer depends on the generic logistics dialog
  - now uses dedicated `PartnerShipmentDialog`
- `Calisma Ortaklari -> Finans`
  - no longer depends on generic `ModernPaymentDialog`
  - now uses dedicated `PartnerFinanceDialog`
- partner shipment records now carry business fields:
  - partner cost
  - customer price
  - quote status
  - contract
  - SLA
  - partner notes
  - shipment / return cargo
- normal app startup no longer auto-arms fiscal-year test trigger
- `Calisma Ortaklari` benchmark-derived workspace features added:
  - `Belgeler` sekmesi
  - `Zaman Cizelgesi` sekmesi
  - partner-level quote / approval summary
  - document count and shipment timeline preview
  - partner action strip now includes a direct documents entry
  - partner scorecard
  - shipment-level invoice reconciliation
  - return quality-control checklist
  - shipment/history right-click context menu
  - partner shipment CSV export
  - unified partner document center
  - monthly trend tab

Current remaining live-confirmation bucket:

- `Stok Yonetimi -> Yeni Urun Ekle`
- `Stok Yonetimi -> Ice Aktar / Disa Aktar / PDF / Yazdir`
- right-click/context menu surfaces across stock/customer/service tables
- partner shipment save/load against the real production database path
- partner finance payment write flow against the real production database path

## Benchmark-Derived Product Additions

Implemented from external service/repair management benchmark review:

- partner-specific shipment object
  - separate from generic logistics / warranty tracking
- partner-specific finance ledger
  - separate from generic project / customer receivable dialog
- partner documents workspace
  - contracts, shipment documents, invoices, offers and attachments can now live under partner scope
- shipment timeline surface
  - shipment lifecycle events are now persisted and previewed under the partner page
- quote / approval context
  - quote amount, quote status and approval status are now first-class shipment fields
- SLA / contract visibility
  - partner workspace now exposes contract and SLA context in the finance/details area

Still missing from the benchmark backlog:

- unified documents center across service / logistics / partner / finance flows
- advanced partner scorecard slices
  - category-based efficiency
  - warranty comeback ratio
  - monthly trend chart visual
- stronger batch actions for non-partner modules

## Latest Partner Workspace Additions

- `Calisma Ortaklari -> Gonderilen Urunler`
  - sag tik menusu eklendi:
    - `Ac / Duzenle`
    - `Belgeler`
    - `Belge Merkezi`
    - `Partner Finans`
    - `CSV Disa Aktar`
- `Calisma Ortaklari -> Belgeler`
  - partner bazli belge havuzu aktif
- `Calisma Ortaklari -> Belge Merkezi`
  - partner belgeleri ve shipment fotograflari tek merkezde listeleniyor
- `Calisma Ortaklari -> Trendler`
  - aylik sevk, tamamlanan is, partner maliyeti, musteriye yansiyan tutar ve teklif toplami listeleniyor
- `Lojistik & Garanti Yonetimi -> Belge Merkezi`
  - genel lojistik fotograflari ayni belge merkezi dialogundan acilabiliyor
- `Calisma Ortaklari -> Scorecard`
  - geri donus orani kirilimi eklendi

Technical debt still present:

- `src/ui/pages/customers_page_parts.py`
  - duplicate `PartnersPage` class bodies remain in the file
  - active runtime path is fixed, but the file should be consolidated in a cleanup refactor

## Audit Method

- Static scan over menu/action/signal surfaces
- Page-map verification against menu IDs
- Targeted source inspection for reported broken flows
- Offscreen dialog smoke tests where safe
- GUI relaunch after fixes

## Coverage Summary

- Signal and trigger bindings scanned: `853`
- Menu/context action surfaces scanned: `450`
- Import/export/print related references scanned: `3537`
- Page routing source:
  - `src/utils/page_config.py`
  - `src/ui/main_window.py`
  - `src/ui/widgets/side_menu.py`

## Menu Routing Status

Verified in page map:

- `21 -> Müşteri Listesi`
- `26 -> Çalışma Ortaklarımız`
- `50 -> Stok Yönetimi`
- `61 -> Saha Servis Haritası`
- `65 -> Lojistik & Garanti Yönetimi`
- `101/105/106/115 -> Finans grubu`

Conclusion:

- `Çalışma Ortaklarımız` ayrı page ID ile yönleniyor.
- Menü haritasında partner sayfası eksik değil.
- Sorun, menü yönlendirmesinden çok sayfa içi davranış ve dialog bağlarında.

## Verified Broken Items

### P0 Fiscal year test trigger runs during normal app startup

- Surface: normal application launch
- Files:
  - `src/services/fiscal_year_service.py`
  - `src/ui/main_window.py`
- Runtime evidence:
  - log shows `Fiscal year test trigger armed for today`
  - archive is created automatically on startup
  - dry-run reset notification is emitted during normal launch
- Result:
  - startup is running year-end archive/reset test logic without explicit operator intent
  - this is unsafe for a production desktop application
- Status: `Verified Fixed`
- Fix applied:
  - automatic call to `configure_today_test_trigger()` was removed from normal startup flow
  - service now only checks explicit stored dates/settings

### P1 Static web root path is missing at startup

- Surface: app startup
- File:
  - `src/utils/server_main.py`
- Runtime evidence:
  - log shows `Static klasoru bulunamadi`
  - resolved path is `...\\AYEC Pro\\static`
- Result:
  - embedded web/static-dependent features may silently degrade
- Status: `Broken runtime dependency`
- Recommended fix:
  - ensure correct static asset path
  - or disable server feature when assets are unavailable

### P0 Partner finance opens the generic receivable dialog

- Surface: `Çalışma Ortakları -> Finans -> Tahsilat / Finans İşlemi`
- Files:
  - `src/ui/pages/customers_page_parts.py`
  - `src/ui/dialogs/payment_dialog.py`
- Root cause:
  - partner finance calls `ModernPaymentDialog`
  - `ModernPaymentDialog._load_debt_items()` reads generic `currency_transactions`
  - query scope is customer-wide `DEBIT`, not partner-shipment specific
- Result:
  - project or generic customer debt can appear in partner finance
  - user screenshot is correct: this is not a partner-specific finance model
- Status: `Verified Fixed`
- Fix applied:
  - partner page now opens dedicated `PartnerFinanceDialog`
  - partner finance reads partner shipment totals and partner payment ledger instead of generic project/customer debt dialog

### P0 Partner shipment still reuses logistics dialog

- Surface: `Çalışma Ortakları -> + Gönderi Kaydı`
- Files:
  - `src/ui/pages/customers_page_parts.py`
  - `src/ui/pages/external_tracking_page.py`
- Root cause:
  - button opens `ExternalTrackingDialog`
  - dialog language and fields are logistics/warranty centered
- Result:
  - partner shipment and `Lojistik & Garanti Yönetimi` are functionally too close
  - partner-specific business fields are missing from the record itself
- Missing fields:
  - partner cost
  - partner quote
  - customer charge
  - approval state
  - contract/SLA reference
  - partner-side notes
- Status: `Verified Fixed`
- Fix applied:
  - partner page now opens dedicated `PartnerShipmentDialog`
  - shared `ExternalTrackingDialog` remains reserved for logistics / warranty tracking

### P1 Photo save path exists, but shipment dialog still lacks partner-specific completion flow

- Surface: `Çalışma Ortakları -> + Gönderi Kaydı -> Fotoğraf Galerisi`
- Files:
  - `src/ui/dialogs/photo_gallery_dialog.py`
  - `src/ui/pages/external_tracking_page.py`
- Current state:
  - gallery persistence path exists
  - `Kaydet ve Kapat` exists
- Current state:
  - partner shipment flow now has its own dialog
  - gallery still writes through shared `photos` storage, but from partner-specific shipment context
- Status: `Improved, needs live confirmation`

### P0 Partner finance uses the shared customer debt model

- Surface: `Çalışma Ortaklarımız -> Finans -> Tahsilat / Finans İşlemi`
- Files:
  - `src/ui/pages/customers_page_parts.py`
  - `src/ui/dialogs/payment_dialog.py`
- Root cause:
  - partner finance currently opens `ModernPaymentDialog`
  - `ModernPaymentDialog._load_debt_items()` reads all `currency_transactions` rows for the selected `customer_id`
  - query is:
    - `WHERE customer_id = ? AND transaction_type = 'DEBIT'`
  - there is no partner-shipment-only filter
- Result:
  - project-related debit rows can appear in partner finance
  - user report is correct: partner finance is currently backed by the generic receivable/debt flow, not a dedicated partner finance ledger
- Status: `Verified Fixed`
- Fix applied:
  - partner finance now uses `partner_finance_entries`
  - partner debt summary is computed from `partner_shipments.partner_cost`

### P0 Partner shipment and logistics flow are still conceptually the same model

- Surface:
  - `Çalışma Ortakları -> + Gönderi Kaydı`
  - `Lojistik & Garanti Yönetimi -> Yeni Takip Başlat`
- Files:
  - `src/ui/pages/customers_page_parts.py`
  - `src/ui/pages/external_tracking_page.py`
- Current behavior:
  - partner shipment creation opens `ExternalTrackingDialog`
  - the dialog fields are logistics/warranty-oriented:
    - emanet no
    - müşteri
    - ürün
    - gönderilen yer
    - servis kayıt no
    - gidiş / dönüş kargo no
    - durum
    - fotoğraf galerisi
- Conclusion:
  - the current partner shipment form is effectively the same behavioral model as `Lojistik & Garanti Yönetimi`
  - it is not yet a true partner workflow
- Why this is wrong:
  - partner shipment should also carry partner-specific business context:
    - partner agreement / contract type
    - SLA / expected return rule
    - partner-side cost / borç
    - partner-side tahsilat / ödeme durumu
    - product/service notes specific to that partner relationship
- Status: `Verified Fixed`
- Fix applied:
  - dedicated partner shipment model introduced
  - logistics and partner workflows now use separate dialogs and separate persistence targets

### P1 Partner shipment flow still reuses logistics dialog model

- Surface: `Çalışma Ortakları -> + Gönderi Kaydı`
- Files:
  - `src/ui/pages/customers_page_parts.py`
  - `src/ui/pages/external_tracking_page.py`
- Root cause:
  - partner shipment creation still opens `ExternalTrackingDialog`
  - this makes the behavior and fields very close to `Lojistik & Garanti Yönetimi`
- Result:
  - conceptually wrong separation
  - user-facing confusion between partner shipment and external logistics tracking
- Status: `Verified Fixed`
- Fix applied:
  - partner shipment dialog now locks partner context and carries partner-specific business fields

### P1 Partner finance method had duplicate definitions

- Surface: `Çalışma Ortakları -> Finans`
- File:
  - `src/ui/pages/customers_page_parts.py`
- Root cause:
  - `record_payment_for_partner()` exists multiple times in the class body
- Result:
  - edits can land on the wrong implementation
  - behavior can drift and become hard to maintain
- Status: `Risk Present`
- Recommended fix:
  - collapse to a single canonical method

## Verified Fixed Items

### Stock add dialog constructor failure

- Surface: `Stok Yönetimi -> Yeni Ürün Ekle`
- File:
  - `src/utils/design_system.py`
- Root cause:
  - `DesignTokens.apply_spinbox_styles()` called missing API `ThemeManager.resolve_placeholders()`
- Fix:
  - switched to `theme_qss(...)`
- Validation:
  - `AddStockDialog` offscreen smoke passed
- Status: `Fixed in code`

### Partner photo gallery persistence path

- Surface: `Çalışma Ortakları -> Gönderi Kaydı -> Fotoğraf Galerisi`
- File:
  - `src/ui/dialogs/photo_gallery_dialog.py`
- Root cause:
  - gallery persistence was tied to the wrong data path
- Fix:
  - now uses generic photos persistence
  - added explicit `Kaydet ve Kapat`
- Validation:
  - `PhotoGalleryDialog` smoke passed
- Status: `Fixed in code`

### Table row selection focus box

- Surface: `Çalışma Ortakları -> Gönderilen Ürünler tablosu`
- File:
  - `src/ui/pages/customers_page_parts.py`
- Root cause:
  - cell focus outline remained visible while selecting rows
- Fix:
  - `SelectRows`
  - `SingleSelection`
  - `NoEditTriggers`
  - `NoFocus`
  - focus outline removed in stylesheet
- Status: `Fixed in code`

## Needs Live Click Confirmation

These items are wired and compile, but still require direct runtime confirmation on the live app/database:

### Partner flows

- `Çalışma Ortakları -> + Gönderi Kaydı`
  - dialog opens, but still uses the shared logistics model
- `Çalışma Ortakları -> Finans -> Tahsilat / Finans İşlemi`
  - opens, but data source is functionally wrong for partner finance
- `Çalışma Ortakları -> Fotoğraf Ekle / Galeri`
  - save path fixed in code; full user flow should be clicked once end-to-end

### Stock actions

- `Stok Yönetimi -> Yeni Ürün Ekle`
  - constructor path fixed in code
  - button is wired in `stock_page.py`
  - still requires live click confirmation because the latest user report says the dialog does not open in the running app
- `Stok Yönetimi -> İçe Aktar`
- `Stok Yönetimi -> Dışa Aktar`
- `Stok Yönetimi -> PDF`
- `Stok Yönetimi -> Yazdır`

### Context menu surfaces

Detected context menu surfaces include:

- `src/ui/pages/stock_page.py`
- `src/ui/pages/accounting_page.py`
- `src/ui/pages/appointments_page.py`
- `src/ui/pages/loaner_devices_page.py`
- `src/ui/pages/services_page.py`
- `src/ui/pages/dashboard_page.py`
- `src/ui/pages/check_note_page.py`
- `src/ui/pages/personnel_page.py`
- `src/ui/dialogs/customer_select_dialog.py`

Status:

- signal bindings exist
- not all right-click actions have been manually executed in this pass

## Menu/Signal Findings Summary

### Working / Present

- page IDs for core menus are present
- top-level menu routing exists
- submenu routing exists for customer hub, stock, service, finance, system
- many toolbar and button signals are connected
- multiple context menus are registered with `customContextMenuRequested.connect(...)`

### Missing or Functionally Wrong

- partner finance is not isolated from generic customer/project debt
- partner shipment creation is not yet its own dialog/workflow
- partner page still contains maintenance risk due duplicate finance method definitions

### Not Yet Fully Confirmed

- every submenu item by live click
- every dialog by live click
- all export targets with real file dialog interaction
- all print preview / printer flows

## Concrete Recommendation Order

1. Build a dedicated partner finance dialog or partner-only debt filter
2. Split partner shipment dialog away from `ExternalTrackingDialog`
3. Remove duplicate `record_payment_for_partner()` definitions
4. Run a second pass of live click audit on:
   - all menu items
   - all submenus
   - all dialog openers
   - all context menus
   - all import/export/pdf/print actions
5. Save a second report containing only runtime-confirmed failures

## Final Assessment

The current state is:

- menu routing is mostly intact
- signal wiring exists widely
- several previously broken dialogs are fixed in code
- the biggest remaining business-logic problem is `Çalışma Ortakları -> Finans`
- the biggest remaining UX-architecture problem is `Çalışma Ortakları -> + Gönderi Kaydı`

This means the program is not missing the partner menu itself; the remaining issue is that the partner page still reuses generic project/logistics flows where it should have a dedicated partner workflow.

## Partner Vs Logistics Comparison

### Same today

- both flows use the same shipment dialog model
- both collect shipment/tracking/service-number style data
- both use the same photo gallery path style
- partner finance currently falls back to the same generic debt collection dialog used for normal customer balances

### Should be different

`Çalışma Ortakları` should be partner-relationship management:

- partner card
- agreement / contract
- SLA
- shipped product history per partner
- partner-specific borç / maliyet
- partner-specific tahsilat / ödeme
- notes tied to that partner

`Lojistik & Garanti Yönetimi` should remain generic external service / warranty tracking:

- outside service destination
- cargo/service progress
- warranty process photos
- return status
- generic shipment lifecycle

### Verdict

- right now: `Same core logic reused`
- target state: `Different business flows with different dialogs and finance models`

## Web Benchmark Findings

Comparable products reviewed on official sites:

- OpenRMA - https://www.openrma.com/openrma365
- RepairShopr - https://www.repairshopr.com/features
- ServiceReady / Workforce - https://serviceready.io/
- RepairFlow - https://repairflow.pro/
- MaxyService - https://maxyservice.com/
- Shop-Ware - https://shop-ware.com/

### Benchmark summary

The repeated product pattern is:

- subcontractor / vendor work is separated from customer CRM
- partner shipment records are richer than a generic outside-service form
- finance is tied to the shipment or job object, not only to the generic customer ledger
- SLA, turnaround, approval, and cost tracking are visible in the same workspace
- attachment and shipment timeline live together with the record

### Common patterns seen in similar products

These patterns repeat across repair, field-service, RMA, and partner-driven systems:

1. Separate operational objects
- customer repair ticket
- external vendor / RMA / subcontractor job
- field dispatch job
- partner finance / payout or partner cost ledger

2. Partner or vendor records are not just customer clones
- partner profile
- service category / specialization
- SLA / turnaround rules
- contract terms
- contact roles
- commercial terms such as commission, labor rate, fixed handling fee, cargo responsibility

3. Shipment or repair records carry full business context
- product / serial / model
- reason for sending
- fault summary
- included accessories
- outbound and inbound cargo tracking
- expected return date
- partner-side quote / cost
- photo and attachment timeline
- approval states

4. Finance is attached to the job object, not only to the generic customer ledger
- job cost
- vendor invoice amount
- expected reimbursement / warranty claim amount
- commission
- amount paid to partner
- amount collected from customer
- gross margin on that specific outside-service job

5. Premium UI patterns are consistent
- split workspace: list on left, active record workspace on right
- dense summary cards for current record
- tabs by workflow stage, not by generic data tables
- visible status timeline
- explicit CTA buttons for next step
- attachment and note history in the same workspace

### What AYEC Pro already has in this direction

- partner list and separate page entry
- partner detail hero area
- tabs for active/history/notes/finance
- logistics-style shipment creation
- photo gallery support
- partner metadata placeholders such as commission, contract, SLA

### What is still missing for AYEC Pro

#### 1. Dedicated partner shipment object

Current issue:

- partner shipment uses the same dialog and mostly the same model as logistics / warranty tracking

Needed:

- a separate `Partner Shipment` record type
- own dialog
- own DB persistence surface

Suggested fields:

- partner id
- shipment no
- customer
- product / model / serial
- sent reason
- sent date
- expected return date
- returned date
- partner quote / partner cost
- customer charge
- commission
- warranty / out-of-warranty flag
- cargo responsibility
- attached files / photos
- internal notes

#### 2. Partner-specific finance ledger

Current issue:

- partner finance opens the generic customer receivable dialog and reads all customer debit items

Needed:

- partner finance must be job-based and partner-based

Suggested sections:

- `Partner Borçları`
- `Partner Ödemeleri`
- `Müşteri Tahsilatı`
- `Komisyon`
- `Net Karlılık`

Suggested record links:

- each partner shipment should have:
  - cost side
  - customer charge side
  - payment status side
  - profit summary

#### 3. Shipment lifecycle timeline

Needed:

- instead of a flat status only, a visible step flow:
  - oluşturuldu
  - partnere gönderildi
  - teslim alındı
  - işlemde
  - teklif geldi
  - onaylandı / reddedildi
  - geri gönderildi
  - müşteriye teslim edildi

This is common in repair tracking products and makes outside-service work easier to audit.

#### 4. Partner scorecard

This is one of the strongest missing premium features.

Per partner show:

- ortalama dönüş süresi
- zamanında dönüş oranı
- tekrar arıza / iade oranı
- toplam gönderi sayısı
- toplam maliyet
- toplam tahsilat
- net kâr
- açık iş sayısı

This mirrors what modern service platforms show for profitability and operational quality.

#### 5. Contract and SLA block as first-class data

Right now these fields exist conceptually but are not central enough.

Needed in partner workspace:

- contract type
- contract start / end
- SLA target
- penalty rule / special condition
- supported product categories
- service coverage region

This should sit in a visible partner card, not only in edit form metadata.

#### 6. Partner communication and approvals

Strong products commonly include:

- estimate / approval state
- message log
- partner-side document attachments
- sent/received timestamps

AYEC Pro should add:

- partner offer amount
- partner approval note
- internal approval checkbox
- sent-to-partner and received-from-partner timestamps

#### 7. Better command area in partner page

For a more premium feel, the right-side partner workspace should have a stronger action strip:

- `Yeni Gönderi`
- `Teklif Gir`
- `Tahsilat / Ödeme`
- `Belge / Fotoğraf`
- `Partner Kartı`

Current buttons are useful but still generic. They should reflect workflow steps more clearly.

#### 8. Separate logistics vs partner pages in behavior and language

Today the forms are too close.

Recommendation:

- `Lojistik & Garanti Yönetimi`
  - generic external service / warranty / cargo lifecycle
- `Çalışma Ortakları`
  - commercial partner workspace with shipment + finance + SLA + scorecard

The wording, fields, and actions should differ immediately when the user opens the page.

## Product Design Recommendation

For `Çalışma Ortakları`, the best next design direction is:

1. Left column
- partner cards
- search and filters
- partner health chip

2. Right header
- partner name
- badge / logo / type
- contract + SLA strip
- action buttons

3. KPI row
- active jobs
- avg turnaround
- outstanding partner debt
- collected from customer
- margin

4. Main tabs
- `Aktif Gönderiler`
- `Geçmiş`
- `Finans`
- `Belgeler`
- `Notlar`

5. Finance tab
- split cards:
  - `Partner Borcu`
  - `Ödenen`
  - `Tahsil Edilen`
  - `Komisyon`
  - `Net Kar`

This would move the page from "customer-like list with partner filter" to a true premium partner operations workspace.

## Additional Missing Features After Benchmark Review

These items also stand out as missing when compared with stronger repair and vendor workflow products:

### 1. Partner shipment package details

AYEC Pro should track what exactly was sent to the partner:

- included accessories
- charger / adapter / cable / battery
- accessory count
- package condition
- serial verification at handoff

This reduces disputes when the item returns.

### 2. Quote and approval workflow

Before outside work starts, partner quote flow should exist:

- partner quote amount
- quote received date
- internal approval status
- customer approval status
- approved amount
- rejected / revised quote history

This is a major missing operational control point.

### 3. Partner invoice reconciliation

Outside-service systems usually track:

- partner invoice no
- invoice date
- invoice total
- matched shipment/job
- payment date
- remaining payable

AYEC Pro currently needs a clear `partner invoice reconciliation` layer.

### 4. Return quality control

When a product comes back from a partner, the receiving side should record:

- return test result
- missing parts check
- cosmetic condition check
- return accepted / rejected
- rework required

This should be part of partner shipment closure, not an external note only.

### 5. Warranty claim and cost responsibility

For outside repair or warranty work, the system should show:

- who pays cargo
- who pays labor
- who pays part replacement
- whether the job is reimbursable
- whether the vendor owes a credit or refund

This belongs beside finance, not hidden in notes.

### 6. Timeline and audit trail

Each partner shipment should have a visible timeline:

- created
- packed
- shipped
- received by partner
- diagnosis completed
- quote received
- approved
- repaired
- returned
- customer informed
- closed

This should be a first-class audit surface.

### 7. Partner-specific export and print outputs

The partner module should not rely only on generic Excel/PDF outputs.

Needed outputs:

- partner shipment form
- service acceptance / handoff print
- partner quote approval sheet
- partner debt statement
- monthly partner performance summary

### 8. Exception and escalation handling

Partner workflow should support exceptions such as:

- overdue SLA
- no response from partner
- repeated failure
- wrong return item
- damaged return
- missing accessory on return

These should generate visible warning badges and filtered queues.

### 9. Multi-partner comparison view

For decision quality, AYEC Pro should offer a management view comparing partners by:

- average completion time
- average cost
- repeat failure rate
- active job load
- city / region
- specialization

This would make partner selection operational instead of memory-based.

### 10. Partner documents workspace

Besides shipment photos, the partner card should keep:

- agreement files
- offer PDFs
- invoice PDFs
- cargo receipts
- signed approval files

This should live in a dedicated `Belgeler` tab.

## Sources Reviewed

- OpenRMA: https://www.openrma.com/
- RepairShopr Features: https://www.repairshopr.com/features
- ServiceReady / Workforce: https://serviceready.io/
- RepairFlow: https://repairflow.pro/
- MaxyService: https://maxyservice.com/
- Shop-Ware: https://shop-ware.com/

## Latest Cross-Module Document Center Rollout

- `Musteri Listesi` toolbar now exposes `Belge Merkezi` and opens the unified document center.
- `Hizmet Tanimlari` header action strip now exposes `Belge Merkezi` and opens the unified document center.
- `Lojistik & Garanti Yonetimi` already exposes `Belge Merkezi`; these three modules now share the same document hub entry pattern.
- Context/export surface audit confirms `Musteri Listesi`, `Hizmet Tanimlari`, `Stok Yonetimi`, and `Lojistik & Garanti Yonetimi` already have active context menu and export/print entry points in code.

## Latest External Tracking Batch Actions

- `Lojistik & Garanti Yonetimi` now supports `Coklu Sec` on the main table.
- External tracking context menu now exposes `Secilileri CSV Disa Aktar`.
- This brings the external tracking page closer to the same batch/context standard already used in service and partner pages.

## Latest Batch And Refactor Pass

- `Musteri Listesi` now supports a `COKLU SEC` toolbar toggle and `Secilileri CSV Aktar` from the context menu while multiselect is active.
- `Stok Yonetimi` now supports a `Coklu Sec` toolbar toggle and `Secilileri CSV Disa Aktar` from the stock context menu while multiselect is active.
- The unified document center now aggregates:
  - partner documents
  - partner shipment photos
  - general logistics photos
  - stock photos
  - project contract files
  - contract attachments
- `customers_page_parts.py` duplicate class shadowing was reduced by renaming the stale secondary partner-page body to `LegacyPartnersPageUnused`, leaving the active `PartnersPage` unambiguous for runtime routing.

## Current Verified State

- Compiled successfully:
  - `src/ui/pages/customers_page.py`
  - `src/ui/pages/stock_page.py`
  - `src/ui/dialogs/unified_documents_center_dialog.py`
  - `src/ui/pages/customers_page_parts.py`
  - `src/ui/pages/external_tracking_page.py`
  - `src/ui/pages/services_page.py`
- Regression suite:
  - `tests.test_update_logic`
  - `tests.test_dialog_flows`
  - `tests.test_input_validator_comprehensive`
  - `24/24 OK`

## Remaining Manual Confirmation Items

- `Musteri Listesi -> COKLU SEC -> Secilileri CSV Aktar`
- `Stok Yonetimi -> Coklu Sec -> Secilileri CSV Disa Aktar`
- `Birlesik Belge Merkezi` icinde:
  - stok fotograflari
  - proje sozlesmeleri
  - contract attachments
  gorunum ve acilis davranisi

## Latest Menu Routing Audit

### Verified Good

- `PAGE_MAPPING` icindeki tum sayfalarin module/class importu basarili.
- `Teknisyen Paneli (60)` bilerek `MainWindow.on_menu_click()` icinde ozel dialog rotasina gidiyor; eksik mapping degil.

### Not Exposed In Current Side Menu

Bu sayfalar kodda mevcut, import oluyor, ancak mevcut yan menude yuzeye cikmiyor:

- `150` `SalesHubPage`
- `210` `Arac Bakim Takibi`

Sonuc: bunlar "acilmiyor" gibi algilanabilir cunku menude rotalari yok.

### High-Risk Routing Bug

- `src/ui/widgets/side_menu.py`
  - `_get_page_id_from_menu_item()` sadece su plugin id'lerini mapliyor:
    - `dashboard`
    - `vehicles`
    - `service_board`
    - `stock`
    - `customers`
    - `technician`
  - bunun disindaki tum plugin menu item'lari varsayilan olarak `40` yani `Dashboard` sayfasina dusuyor.

Sonuc: plugin tabanli sektor menulerinde tanimsiz item varsa kullanici tikladiginda dogru modulu degil `Dashboard` ekranini acabilir.

### Structural Debt

- `src/ui/widgets/side_menu.py` icinde eski/yeni menu olusturma katmanlari birlikte duruyor.
- duplicate/fallback-heavy govdeler menu auditini zorlastiriyor.
- partner modulu tarafinda oldugu gibi, menude de tek bir final routing govdesine indirme refactor'u gerekli.

## Latest Sector Menu Pass

### Updated Sector Visibility Rules

- `src/ui/widgets/side_menu.py`
  - `otomotiv` sektoru icin menu kisitli kalir ve sadece otomotiv odakli sayfalar gorunur.
  - `teknik_servis` sektoru icin gorunurluk artik `PAGE_MAPPING` uzerinden tum tanimli sayfalari kapsar.

### Newly Surfaced In Technical Service Menu

- `42` `Servis Durum Ekrani`
- `150` `Sales Hub`
- `210` `Arac Bakim Takibi`

### Routing Fix

- Plugin menu item routing artik yalniz dar bir string-id listesine bagli degil.
- `_get_page_id_from_menu_item()`:
  - varsa dogrudan `page_id` degerini kullanir
  - ek plugin id'leri de mapler
  - tanimsiz item'lari artik sessizce `Dashboard (40)` sayfasina dusurmez

### Verification

- `src/ui/widgets/side_menu.py` derleme: `OK`
- Regresyon:
  - `tests.test_update_logic`
  - `tests.test_dialog_flows`
  - `tests.test_input_validator_comprehensive`
- `19/19 OK`

## Latest Side Menu Hierarchy Pass

### Updated Runtime Hierarchy

- `Servis Yonetimi`
  - `Genel Bakis`
  - `Durum Paneli`
  - `Servis Durum Ekrani`
  - `Teknisyen Paneli`
  - `Saha Haritasi`
  - `Randevular`
  - `Lojistik ve Garanti`
  - `Is/Servis Takibi Raporlari`
  - `Arac Bakim Takibi`
  - `AI Asistan`

- `Musteri`
  - `Musteri Listesi`
  - `Sozlesmeler`
  - `Hatirlaticilar`
  - `Duyurular`
  - `Calisma Ortaklari`

- `Ticari`
  - `Stok Yonetimi`
  - `Sales Hub`
  - `Hizmet Tanimlari`
  - `Cihaz Bilgisi ve Markalar`
  - `Emanet (Konsinye) Cihazlar`
  - `Hizli Satis (POS)`
  - `Mobil Stok`
  - `PC Builder`
  - `Proje Yonetimi`

- `Finans`
  - `Gelir / Gider`
  - `Banka Hesaplari`
  - `Cek / Senet`
  - `Fatura Kes (E-Fatura)`

- `IK ve Personel`
  - `Personel`

- `Sistem`
  - `Bilgi Bankasi`
  - `Kullanim Kilavuzu`
  - `Ayarlar`
  - `Log Kayitlari`
  - `Yedekleme`
  - `Destek`

### Alignment Fixes

- `page_config.py` icindeki parent grup bilgileri menu hiyerarsisi ile hizalandi.
- `Cihaz Bilgisi ve Markalar`, `Emanet`, `Mobil Stok`, `PC Builder` artik `Ticari` altinda siniflanir.
