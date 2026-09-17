# COLUMN_MISMATCH_AUDIT

Tarih: 2026-04-03

Kapsam:
- UI tablo kolonlari
- DB row / dict alan erisimleri
- sektor plugin kolon adlari ile ekran render eslesmeleri
- banka/accounting ekranlarinda eski tuple index varsayimlari

## Uygulanan Tarama

- `setColumnCount`, `setHorizontalHeaderLabels`, `setItem` kullanan sayfalar tarandi.
- `row[n]`, `acc[n]`, `record[n]`, `customer[n]`, `project[n]`, `part[n]` gibi tuple-index erisimleri tarandi.
- `SELECT ... FROM` sorgulari ile ayni fonksiyondaki indeks erisimleri manuel karsilastirildi.
- Sektor plugin `get_stock_columns()` ciktisi ile `stock_page.py` kolon key map'i karsilastirildi.
- `Database` MRO kontrol edilerek `get_bank_accounts()` runtime sahibinin `BankMixin` oldugu dogrulandi.

## Dogrulanmis ve Duzeltilmis Kolon Uyumsuzluklari

### 1) Stok tablosu plugin kolonlari ile UI key map uyusmuyordu

Dosya:
- `src/ui/pages/stock_page.py`

Sorun:
- teknik servis plugin'i `quantity`, `unit`, `sale_price`, `location` veriyor.
- otomotiv plugin'i `oem_no`, `cross_ref`, `vehicle_brand`, `vehicle_model` veriyor.
- ekran ise yalniz `stock`, `currency`, `price`, `shelf_number`, `oem_code`, `equivalent_code`, `compatible_models` bekliyordu.
- Sonuc: `Miktar`, `Birim`, `Satis Fiyati`, `Raf Yeri` ve bazi otomotiv kolonlari bos gorunuyordu.

Fix:
- UI row map'e plugin key alias'lari eklendi.
- `quantity -> stock`
- `unit -> currency`
- `sale_price -> price`
- `location -> shelf_number`
- `oem_no / cross_ref / vehicle_brand / vehicle_model` alias'lari eklendi.

### 2) Product -> Bank mapping ekraninda banka satirlari eski tuple sirasi ile okunuyordu

Dosya:
- `src/ui/pages/settings_widgets/product_bank_mapping.py`

Sorun:
- `get_bank_accounts()` runtime'da raw `bank_accounts` satiri donduruyor.
- Ekran `acc[3]` alanini hesap adi gibi okuyordu; raw schema'da `acc[3] = iban`.
- Bu, banka secim etiketlerinde yanlis alan gosterebiliyordu.

Fix:
- `_bank_field()` helper eklendi.
- Banka satirlari once kolon adi ile, yoksa tuple fallback ile okunuyor.
- `account_holder`, `account_number`, `is_active`, `id` alanlari dogru schema ile hizalandi.

### 3) job_service_number_widget icinde banka hesap tablosu eski legacy tuple sirasi ile render ediliyordu

Dosya:
- `src/ui/pages/settings_widgets/job_service_number_widget.py`

Sorun:
- `acc[2], acc[3], acc[6], acc[7]` eski normalize tuple varsayimina gore okunuyordu.
- Runtime `BankMixin.get_bank_accounts()` ise raw `SELECT * FROM bank_accounts` donduruyor.
- Raw schema sirasi:
  `id, bank_name, account_holder, iban, account_number, branch_code, currency, is_active, created_at, current_balance, ...`
- Sonuc: sube, hesap sahibi, bakiye ve aktiflik alanlari yanlis kolondan okunabiliyordu.

Fix:
- `_bank_field()` helper eklendi.
- `branch_code`, `account_holder`, `account_number`, `iban`, `current_balance`, `is_active`, `id` dogru kolon adlariyla okunuyor.

### 4) Banka detay dialog fallback okumalari eski tuple sirasi kullaniyordu

Dosya:
- `src/ui/dialogs/bank_detail_dialog.py`

Sorun:
- Fallback hesap yukleme ve hesap adi label uretimi eski normalize tuple duzenine goreydi.
- Raw schema'da `acc[3]` iban, `acc[9]` current_balance.

Fix:
- `_bank_field()` helper eklendi.
- Fallback account mapping ve hesap label uretimi schema-adli hale getirildi.

### 5) Gelir/Gider dialog banka hesap dropdown ve success label eski tuple sirasi ile okuyordu

Dosyalar:
- `src/ui/pages/accounting_dialogs/add_income_dialog.py`
- `src/ui/pages/accounting_dialogs/add_expense_dialog.py`

Sorun:
- Banka dropdown doldururken `acc_id, bank, branch, acc_name, ... = acc` varsayimi raw schema ile uyumlu degildi.
- Kayit sonrasi success metninde `account[3]` hesap sahibi gibi okunuyordu; raw schema'da iban.

Fix:
- `_bank_field()` helper eklendi.
- Dropdown label ve success label `bank_name`, `account_holder`, `account_number`, `is_active`, `id` ile hizalandi.

### 6) Islem detay dialog banka hesabi etiketi eski tuple sirasi ile uretiliyordu

Dosya:
- `src/ui/pages/accounting_dialogs/transaction_details_dialog.py`

Sorun:
- Dict branch `account_name`, tuple branch `acc[3]` okuyordu.
- Raw schema'da dogru alan `account_holder`, tuple index fallback ise `2`.

Fix:
- `_bank_field()` helper eklendi.
- Banka hesap etiketi `bank_name`, `account_holder`, `account_number` ile uretiliyor.

### 7) Banka transfer dialogu kaynak/hedef hesaplari eski tuple sirasi ile okuyordu

Dosya:
- `src/ui/pages/accounting_dialogs/add_transfer_dialog.py`

Sorun:
- `for acc in self.accounts` icinde satir direkt `acc_id, bank, branch, acc_name, acc_no, iban, balance_val, is_active_val, created_at = acc`
  seklinde unpack ediliyordu.
- Runtime `bank_accounts` raw schema'sinda `acc[2] = account_holder`, `acc[3] = iban`, `acc[4] = account_number`, `acc[7] = is_active`.
- Eski unpack sirasi bu alanlari yanlis yorumlayabiliyordu.

Fix:
- `_bank_field()` helper eklendi.
- Kaynak/hedef hesap dropdownlari `id`, `bank_name`, `account_holder`, `account_name`, `account_number`, `account_no`, `is_active`
  alanlarini once kolon adi ile, sonra fallback indeks ile okuyor.

### 8) Customer history API string-key ile tuple satir okuyordu

Dosya:
- `src/utils/server_main.py`

Sorun:
- `/api/customers/{cid}/history` endpoint'i cihaz sorgusu sonucunu `row['tracking_no']`, `row['id']`, `row['entry_date']`
  gibi string-key erisimleriyle okuyordu.
- Ancak bu endpoint'te `conn.row_factory = sqlite3.Row` acilmadigi icin `cursor.fetchall()` tuple satir dondurebiliyordu.
- Sonuc: servis/cari gecmis API akisi runtime'da patlayabilir veya bos donebilirdi.

Fix:
- Bu endpoint icin `conn.row_factory = sqlite3.Row` eklendi.

### 9) Musteri gecmisi sorgusu OR onceligi yuzunden soft-deleted servis satirlarini sizdirabiliyordu

Dosya:
- `src/db/mixins/customer_mixin.py`
- `src/ui/dialogs/customer_history_dialog.py`
- `src/ui/dialogs/customer_360_dialog.py`

Sorun:
- `get_customer_history()` ve `get_customer_history_summary()` sorgularinda `customer_id` ve `customer_name`
  kosullari parantezsiz `OR` ile baglanmisti.
- Bu yapiya soft-delete filtresi eklendiginde veya ayni isimde eski kayitlar oldugunda yanlis servis satirlari
  musteri gecmisine karisabilirdi.

Fix:
- Kimlik eslesme kosulu paranteze alindi.
- `COALESCE(is_deleted, 0) = 0` filtresi eklendi.
- UI dialoglarindaki musteri servis sorgulari da ayni kimlik parantezi ve soft-delete filtresine hizalandi.

### 10) Yaklasan randevular sorgusunda eksik SQL placeholder vardi

Dosya:
- `src/db/mixins/database_legacy_part5_mixin.py`

Sorun:
- `get_upcoming_appointments()` icindeki sorgu `WHERE date= AND status='Aktif'` seklindeydi.
- `date` filtresinin `?` placeholder'i eksikti; bu sorgu runtime'da hata verebilir veya randevu hatirlatma akisini bozabilirdi.

Fix:
- Sorgu `WHERE date=? AND status='Aktif'` olarak duzeltildi.

### 11) Dashboard/ozet istatistikleri silinmis kayitlari sayiyor ve saatli tarihleri kaciriyordu

Dosya:
- `src/db/mixins/reports_mixin.py`

Sorun:
- `get_stats()`, `get_summary_data()`, `get_weekly_stats()` ve `get_sectoral_widget_data()`
  cihaz/musteri/stok sayimlarinda `is_deleted` filtresini tutarli uygulamiyordu.
- `entry_date=?` ve `exit_date=?` tam eslesmeleri, alan datetime formatinda saklandiginda
  ayni gun kayitlarini kacirabiliyordu.
- `pending_repair` once toplam sorguyla yazilip hemen ardindan tum `devices` statulerinden
  yeniden hesaplandigi icin silinmis kayitlar da dolayli olarak sayima karisabiliyordu.

Fix:
- Tum aktif sayim sorgulari `COALESCE(is_deleted, 0) = 0` filtresine cekildi.
- Gunluk ve haftalik tarih filtreleri `COALESCE(entry_date, created_at, '') LIKE 'YYYY-MM-DD%'`
  ve `COALESCE(exit_date, '') LIKE 'YYYY-MM-DD%'` desenine alindi.
- `pending_repair` sadece aktif kayit statulerinden normalize edilerek hesaplaniyor.

### 12) Otomotiv gecmis ekraninda silinmis servis kayitlari gorunebiliyordu

Dosya:
- `src/db/mixins/maintenance_mixin.py`

Sorun:
- `get_vehicle_history_snapshot()` arac plakasina bagli `devices` servis gecmisini cekerken
  `is_deleted` filtresi uygulamiyordu.
- Soft-delete yapilmis servis kayitlari otomotiv gecmisinde tekrar gorunebilirdi.

Fix:
- `devices` sorgusuna `AND COALESCE(is_deleted, 0)=0` filtresi eklendi.
- `get_automotive_vehicle_history_360()` icindeki plaka/musteri kimlik OR grubu paranteze alindi.

### 13) Dashboard / Servis Panosu / Teknisyen Paneli tracking_no lookup'lari soft-deleted servis kayitlarini geri acabiliyordu

Dosyalar:
- `src/ui/pages/dashboard_actions_mixin.py`
- `src/ui/pages/service_board_page.py`
- `src/ui/dialogs/technician_panel.py`

Sorun:
- `SELECT * FROM devices WHERE tracking_no=?` ve benzeri tekil cihaz lookup'lari soft-delete filtresi olmadan calisiyordu.
- Silinmis bir servis kaydi stale `tracking_no` uzerinden tekrar detay/panel/dialog akisini acabilirdi.

Fix:
- Tekil `tracking_no` tabanli cihaz/musteri lookup sorgulari `AND COALESCE(is_deleted, 0)=0` filtresine alindi.

### 14) Stok ve musteri edit dialog fallback sorgulari soft-deleted kayitlari yukleyebiliyordu

Dosyalar:
- `src/ui/dialogs/add_stock_dialog.py`
- `src/ui/dialogs/add_customer_dialog.py`

Sorun:
- Edit modundaki fallback sorgular `SELECT * FROM parts/customers WHERE id=?` seklinde soft-delete filtresi olmadan calisiyordu.
- Silinmis bir kayit stale ID ile dialog icine geri yuklenebilirdi.

Fix:
- Fallback sorgular `is_deleted` destekleyen semada aktif kayit filtresine alindi.
- `is_deleted` kolonu olmayan test/legacy semalarda eski `id=?` sorgusuna guvenli fallback eklendi.

### 15) Cihaz secim dialogu ve otomotiv tekil cihaz context lookup'lari soft-deleted servisleri dahil edebiliyordu

Dosyalar:
- `src/ui/dialogs/device_selection_dialog.py`
- `src/db/mixins/maintenance_mixin.py`

Sorun:
- Cihaz secim dialogu `devices` listesini kurarken `is_deleted` filtresini uygulamiyordu.
- Otomotiv maintenance context resolver tekil `tracking_no/id` lookup'larini soft-delete filtresiz yapiyordu.

Fix:
- `device_selection_dialog.py` sorgusuna semada varsa `COALESCE(is_deleted, 0)=0` filtresi eklendi.
- Memory fallback listesinden de `is_deleted` isaretli satirlar elendi.
- `maintenance_mixin.py::_resolve_automotive_device_context()` sema-duyarli soft-delete filtresiyle calisacak sekilde guncellendi.

### 16) Telefonla musteri lookup sorgusu silinmis kayitlari `phone` kolundan kacirabiliyordu

Dosya:
- `src/repositories/customer_repository.py`

Sorun:
- `WHERE phone = ? OR phone2 = ? AND (is_deleted = 0 OR is_deleted IS NULL)` sorgusunda
  `AND` operatoru `phone2 = ?` tarafina baglaniyordu.
- `phone = ?` eslesmesi silinmis musteriler icin de donebilirdi.

Fix:
- Kimlik grubu paranteze alindi:
  `WHERE (phone = ? OR phone2 = ?) AND (is_deleted = 0 OR is_deleted IS NULL)`.
- `get_top_customers()` icindeki `c.is_deleted` filtresi de acik parantezle netlestirildi.

### 17) Extension wrapper ve servis PDF lookup'lari soft-deleted kayitlari geri dondurebiliyordu

Dosyalar:
- `src/database.py`
- `src/utils/service_pdf_generator.py`

Sorun:
- `get_customer_with_extensions()`, `get_device_with_extensions()`, `get_part_with_extensions()`
  ve `ServiceFormPDF.generate()` tekil `id/tracking_no` lookup'larini soft-delete filtresi olmadan yapiyordu.

Fix:
- `COALESCE(is_deleted, 0)=0` filtresi eklendi.
- `is_deleted` kolonu olmayan legacy/test semalar icin eski sorguya guvenli fallback birakildi.

### 18) Destek ve sozlesme ekranlarinda silinmis musteri adi join ile geri gorunebiliyordu

Dosyalar:
- `src/db/mixins/support_mixin.py`
- `src/ui/pages/contracts_page.py`

Sorun:
- `LEFT JOIN customers` baglantilari soft-delete filtresi olmadan calisiyordu.
- Silinmis musteriler destek bileti ve sozlesme listelerinde tekrar isim olarak gorunebilirdi.

Fix:
- Join kosullarina `AND COALESCE(...is_deleted, 0)=0` filtresi eklendi.

### 19) Is/servis takip ekraninda silinmis cihazlar listeye karisabiliyordu

Dosya:
- `src/ui/pages/job_service_tracking_page.py`

Sorun:
- Servis listesi `FROM devices` sorgusunda soft-delete filtresi yoktu.
- Job listesi `LEFT JOIN customers` ile silinmis musterileri de isim olarak alabiliyordu.

Fix:
- `devices` listesine `WHERE COALESCE(is_deleted, 0)=0` eklendi.
- Musteri join kosulu `AND COALESCE(c.is_deleted, 0)=0` ile daraltildi.

## Manuel Kontrol Edilen Yanlis-Pozitifler

- `src/db/mixins/stock_mixin.py::remove_used_part()`
  - `SELECT` 5 kolon donduruyor, `row[1]..row[4]` erisimleri uyumlu.
- `src/ui/dialogs/report_dialog.py::load_data()`
  - `row[...]` ve `p[...]` farkli veri kaynaklarina ait; statik script false positive uretmisti.
- `src/utils/server_main.py::get_customer_history_api()`
  - ayni fonksiyon icinde birden fazla sorgu oldugu icin SELECT-vs-row statik script false positive verdi.
- `src/ui/pages/job_service_tracking_page.py`
  - tablo columnCount/header/setItem duzeni manuel kontrolde uyumlu.
- `src/ui/pages/loaner_devices_page.py`
  - worker `conn.row_factory = sqlite3.Row` ile calisiyor ve tablo doldurma adli kolonlarla ilerliyor.
- `src/ui/pages/invoice_page.py`
  - banka dropdown sadece `id` ve `bank_name` okuyor; raw schema ile uyumlu.
- `src/ui/dialogs/technician_panel.py`
  - odeme dialogu banka dropdown sadece `id` ve `bank_name` okuyor; raw schema ile uyumlu.

## Kalan Manuel Runtime Dogrulama Noktalari

Bu dosyalarda tuple-index kullanimlari halen var; su an dogrudan mismatch kanitlanmadi ama real DB ile ekran bazli kontrol onerilir:

- `src/ui/dialogs/customer_select_dialog.py`

Ozellikle kontrol edilecek ekranlar:
- `Musteri 360`
- `Musteri secim dialogu`

Not:
- `customer_history_dialog.py` indeksleri `devices` schema sirasi ile manuel karsilastirildi:
  `tracking_no=row[1]`, `device_brand=row[3]`, `device_model=row[4]`, `fault_category=row[6]`,
  `status=row[8]`, `entry_date=row[9]`, `price=row[11]` su an schema ile uyumlu.
- `customer_select_dialog.py` indeksleri `customers` schema sirasi ile uyumlu:
  `id=row[0]`, `name=row[1]`, `phone=row[2]`, `type=row[4]`.

## Dogrulama

- `py_compile` gecti:
  - `src/ui/pages/stock_page.py`
  - `src/ui/pages/settings_widgets/product_bank_mapping.py`
  - `src/ui/pages/settings_widgets/job_service_number_widget.py`
  - `src/ui/dialogs/bank_detail_dialog.py`
  - `src/ui/pages/accounting_dialogs/add_income_dialog.py`
  - `src/ui/pages/accounting_dialogs/add_expense_dialog.py`
  - `src/ui/pages/accounting_dialogs/add_transfer_dialog.py`
  - `src/ui/pages/accounting_dialogs/transaction_details_dialog.py`
  - `src/utils/server_main.py`
  - `src/db/mixins/customer_mixin.py`
  - `src/db/mixins/database_legacy_part5_mixin.py`
  - `src/db/mixins/reports_mixin.py`
  - `src/db/mixins/maintenance_mixin.py`
  - `src/repositories/customer_repository.py`
  - `src/database.py`
  - `src/utils/service_pdf_generator.py`
  - `src/db/mixins/support_mixin.py`
  - `src/ui/pages/contracts_page.py`
  - `src/ui/pages/job_service_tracking_page.py`
  - `src/ui/pages/dashboard_actions_mixin.py`
  - `src/ui/pages/service_board_page.py`
  - `src/ui/dialogs/technician_panel.py`
  - `src/ui/dialogs/add_stock_dialog.py`
  - `src/ui/dialogs/add_customer_dialog.py`
  - `src/ui/dialogs/device_selection_dialog.py`
- `python -m unittest tests.test_update_logic tests.test_dialog_flows tests.test_input_validator_comprehensive`
  - `Ran 19 tests`
  - `OK`
