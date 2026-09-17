# Veritabanı Şema Analizi

- Kaynak DB: `bulut_tech.db`
- Toplam tablo: **31**

## Tablo Envanteri
### `accounting`
- Kolon sayısı: 12
- Index sayısı: 2
- `ix_accounting_id` -> id
- `ix_accounting_date` -> date
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `type` `VARCHAR(5)` NOT NULL 
  - `category` `VARCHAR(100)` NULL 
  - `amount` `FLOAT` NOT NULL 
  - `description` `TEXT` NULL 
  - `customer_id` `INTEGER` NULL 
  - `customer_name` `VARCHAR(255)` NULL 
  - `is_invoiced` `BOOLEAN` NULL 
  - `invoice_no` `VARCHAR(50)` NULL 
  - `date` `DATE` NOT NULL 
  - `created_at` `DATETIME` NULL 
  - `updated_at` `DATETIME` NULL 

### `active_devices`
- Kolon sayısı: 4
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `device_name` `VARCHAR(255)` NULL 
  - `hwid` `VARCHAR(255)` NOT NULL 
  - `last_login` `DATETIME` NULL 

### `announcements`
- Kolon sayısı: 6
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `title` `VARCHAR(500)` NOT NULL 
  - `content` `TEXT` NOT NULL 
  - `priority` `VARCHAR(20)` NULL 
  - `author` `VARCHAR(100)` NULL 
  - `date` `DATETIME` NULL 

### `appointments`
- Kolon sayısı: 17
- Index sayısı: 1
- `ix_appointments_date` -> date
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `title` `VARCHAR(255)` NULL 
  - `customer` `VARCHAR(255)` NULL 
  - `customer_name` `VARCHAR(255)` NULL 
  - `phone` `VARCHAR(20)` NULL 
  - `date` `DATE` NOT NULL 
  - `time` `TIME` NOT NULL 
  - `personnel` `VARCHAR(100)` NULL 
  - `brand` `VARCHAR(100)` NULL 
  - `model` `VARCHAR(100)` NULL 
  - `serial_no` `VARCHAR(100)` NULL 
  - `device` `VARCHAR(100)` NULL 
  - `urgency` `VARCHAR(20)` NULL 
  - `fault` `TEXT` NULL 
  - `description` `TEXT` NULL 
  - `status` `VARCHAR(10)` NULL 
  - `created_at` `DATETIME` NULL 

### `audit_logs`
- Kolon sayısı: 6
- Index sayısı: 1
- `ix_audit_logs_created_at` -> created_at
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `user_id` `VARCHAR(100)` NULL 
  - `table_name` `VARCHAR(100)` NOT NULL 
  - `action` `VARCHAR(20)` NOT NULL 
  - `details` `TEXT` NULL 
  - `created_at` `DATETIME` NULL 

### `bank_accounts`
- Kolon sayısı: 7
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `bank_name` `VARCHAR(100)` NOT NULL 
  - `branch_name` `VARCHAR(100)` NULL 
  - `account_name` `VARCHAR(255)` NULL 
  - `account_no` `VARCHAR(50)` NULL 
  - `iban` `VARCHAR(50)` NULL 
  - `created_at` `DATETIME` NULL 

### `contract_attachments`
- Kolon sayısı: 5
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `contract_id` `INTEGER` NOT NULL 
  - `file_path` `VARCHAR(500)` NOT NULL 
  - `filename` `VARCHAR(255)` NOT NULL 
  - `uploaded_at` `DATETIME` NULL 

### `contracts`
- Kolon sayısı: 10
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `customer_id` `INTEGER` NOT NULL 
  - `title` `VARCHAR(255)` NULL 
  - `contract_type` `VARCHAR(100)` NULL 
  - `description` `TEXT` NULL 
  - `start_date` `DATE` NOT NULL 
  - `end_date` `DATE` NOT NULL 
  - `price` `FLOAT` NULL 
  - `status` `VARCHAR(5)` NULL 
  - `created_at` `DATETIME` NULL 

### `customer_notes`
- Kolon sayısı: 5
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `customer_id` `INTEGER` NOT NULL 
  - `type` `VARCHAR(50)` NULL 
  - `content` `TEXT` NOT NULL 
  - `created_at` `DATETIME` NULL 

### `customers`
- Kolon sayısı: 20
- Index sayısı: 2
- `ix_customers_name` -> name
- `ix_customers_id` -> id
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `name` `VARCHAR(255)` NOT NULL 
  - `phone` `VARCHAR(20)` NULL 
  - `phone2` `VARCHAR(20)` NULL 
  - `email` `VARCHAR(255)` NULL 
  - `type` `VARCHAR(8)` NULL 
  - `tax_id` `VARCHAR(50)` NULL 
  - `tax_no` `VARCHAR(50)` NULL 
  - `tax_office` `VARCHAR(100)` NULL 
  - `tc_no` `VARCHAR(11)` NULL 
  - `address` `TEXT` NULL 
  - `city` `VARCHAR(100)` NULL 
  - `district` `VARCHAR(100)` NULL 
  - `zip_code` `VARCHAR(10)` NULL 
  - `company_name` `VARCHAR(255)` NULL 
  - `sms_enabled` `BOOLEAN` NULL 
  - `is_problematic` `BOOLEAN` NULL 
  - `notes` `TEXT` NULL 
  - `created_at` `DATETIME` NULL 
  - `updated_at` `DATETIME` NULL 

### `device_tests`
- Kolon sayısı: 7
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `tracking_no` `VARCHAR(50)` NOT NULL 
  - `test_name` `VARCHAR(100)` NOT NULL 
  - `result` `VARCHAR(20)` NULL 
  - `note` `TEXT` NULL 
  - `technician` `VARCHAR(100)` NULL 
  - `test_date` `DATETIME` NULL 

### `devices`
- Kolon sayısı: 35
- Index sayısı: 5
- `ix_devices_entry_date` -> entry_date
- `ix_devices_brand` -> brand
- `ix_devices_status` -> status
- `ix_devices_tracking_no` -> tracking_no
- `ix_devices_id` -> id
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `tracking_no` `VARCHAR(50)` NOT NULL 
  - `customer_id` `INTEGER` NULL 
  - `customer_name` `VARCHAR(255)` NULL 
  - `customer_contact` `VARCHAR(20)` NULL 
  - `customer_type` `VARCHAR(20)` NULL 
  - `customer_tax_id` `VARCHAR(50)` NULL 
  - `device_type` `VARCHAR(100)` NULL 
  - `brand` `VARCHAR(100)` NULL 
  - `model` `VARCHAR(100)` NULL 
  - `serial_no` `VARCHAR(100)` NULL 
  - `imei` `VARCHAR(50)` NULL 
  - `pattern_lock` `VARCHAR(50)` NULL 
  - `fault_category` `VARCHAR(255)` NULL 
  - `fault_description` `TEXT` NULL 
  - `urgency` `VARCHAR(20)` NULL 
  - `status` `VARCHAR(14)` NULL 
  - `approval_status` `VARCHAR(50)` NULL 
  - `priority` `VARCHAR(20)` NULL 
  - `entry_date` `DATETIME` NULL 
  - `estimated_date` `DATETIME` NULL 
  - `exit_date` `DATETIME` NULL 
  - `price` `FLOAT` NULL 
  - `labor_cost` `FLOAT` NULL 
  - `is_invoiced` `BOOLEAN` NULL 
  - `invoice_no` `VARCHAR(50)` NULL 
  - `technician` `VARCHAR(100)` NULL 
  - `repair_details` `TEXT` NULL 
  - `warranty` `VARCHAR(50)` NULL 
  - `photo_path` `TEXT` NULL 
  - `payment_status` `VARCHAR(50)` NULL 
  - `payment_method` `VARCHAR(50)` NULL 
  - `is_archived` `BOOLEAN` NULL 
  - `created_at` `DATETIME` NULL 
  - `updated_at` `DATETIME` NULL 

### `external_warranty_tracking`
- Kolon sayısı: 9
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `internal_tracking_no` `VARCHAR(50)` NOT NULL 
  - `external_tracking_no` `VARCHAR(50)` NULL 
  - `external_service_name` `VARCHAR(255)` NULL 
  - `sent_date` `DATE` NULL 
  - `expected_return_date` `DATE` NULL 
  - `status` `VARCHAR(50)` NULL 
  - `notes` `TEXT` NULL 
  - `created_at` `DATETIME` NULL 

### `fast_notes`
- Kolon sayısı: 5
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `category` `VARCHAR(100)` NOT NULL 
  - `label` `VARCHAR(255)` NOT NULL 
  - `is_active` `BOOLEAN` NULL 
  - `display_order` `INTEGER` NULL 

### `jarvis_notifications`
- Kolon sayısı: 6
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `message` `TEXT` NOT NULL 
  - `type` `VARCHAR(50)` NULL 
  - `is_critical` `BOOLEAN` NULL 
  - `status` `VARCHAR(20)` NULL 
  - `created_at` `DATETIME` NULL 

### `kb_articles`
- Kolon sayısı: 6
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `title` `VARCHAR(500)` NOT NULL 
  - `content` `TEXT` NOT NULL 
  - `tags` `VARCHAR(500)` NULL 
  - `created_at` `DATETIME` NULL 
  - `updated_at` `DATETIME` NULL 

### `license_info`
- Kolon sayısı: 6
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `encrypted_key` `TEXT` NOT NULL 
  - `license_type` `VARCHAR(50)` NULL 
  - `expiry_date` `DATE` NULL 
  - `hwid` `VARCHAR(255)` NULL 
  - `created_at` `DATETIME` NULL 

### `parts`
- Kolon sayısı: 13
- Index sayısı: 4
- `ix_parts_id` -> id
- `ix_parts_name` -> name
- `sqlite_autoindex_parts_2` -> barcode
- `sqlite_autoindex_parts_1` -> code
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `name` `VARCHAR(255)` NOT NULL 
  - `category` `VARCHAR(100)` NULL 
  - `description` `TEXT` NULL 
  - `code` `VARCHAR(50)` NULL 
  - `barcode` `VARCHAR(50)` NULL 
  - `stock` `INTEGER` NULL 
  - `min_stock` `INTEGER` NULL 
  - `shelf_number` `VARCHAR(50)` NULL 
  - `price` `FLOAT` NULL 
  - `purchase_price` `FLOAT` NULL 
  - `created_at` `DATETIME` NULL 
  - `updated_at` `DATETIME` NULL 

### `personnel`
- Kolon sayısı: 14
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `name` `VARCHAR(255)` NOT NULL 
  - `role` `VARCHAR(100)` NULL 
  - `department` `VARCHAR(100)` NULL 
  - `phone` `VARCHAR(20)` NULL 
  - `email` `VARCHAR(255)` NULL 
  - `tc_no` `VARCHAR(11)` NULL 
  - `start_date` `DATE` NULL 
  - `salary` `FLOAT` NULL 
  - `commission_rate` `FLOAT` NULL 
  - `is_active` `BOOLEAN` NULL 
  - `password_hash` `VARCHAR(255)` NULL 
  - `performance_score` `FLOAT` NULL 
  - `created_at` `DATETIME` NULL 

### `quick_notes`
- Kolon sayısı: 5
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `group_name` `VARCHAR(100)` NOT NULL 
  - `label` `VARCHAR(255)` NOT NULL 
  - `category` `VARCHAR(100)` NULL 
  - `is_active` `BOOLEAN` NULL 

### `registration`
- Kolon sayısı: 8
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `full_name` `VARCHAR(255)` NOT NULL 
  - `email` `VARCHAR(255)` NOT NULL 
  - `company_name` `VARCHAR(255)` NULL 
  - `phone` `VARCHAR(20)` NULL 
  - `purpose` `VARCHAR(100)` NULL 
  - `trial_start_date` `DATETIME` NULL 
  - `created_at` `DATETIME` NULL 

### `reminders`
- Kolon sayısı: 9
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `title` `VARCHAR(255)` NOT NULL 
  - `description` `TEXT` NULL 
  - `personnel` `VARCHAR(100)` NULL 
  - `personnel_id` `INTEGER` NULL 
  - `date` `DATETIME` NOT NULL 
  - `status` `VARCHAR(20)` NULL 
  - `is_read` `BOOLEAN` NULL 
  - `created_at` `DATETIME` NULL 

### `service_logs`
- Kolon sayısı: 6
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `device_tracking_no` `VARCHAR(50)` NOT NULL 
  - `log_type` `VARCHAR(50)` NULL 
  - `message` `TEXT` NOT NULL 
  - `user` `VARCHAR(100)` NULL 
  - `created_at` `DATETIME` NULL 

### `services`
- Kolon sayısı: 6
- Index sayısı: 1
- `sqlite_autoindex_services_1` -> barcode
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `name` `VARCHAR(255)` NOT NULL 
  - `price` `FLOAT` NOT NULL 
  - `description` `TEXT` NULL 
  - `barcode` `VARCHAR(50)` NULL 
  - `created_at` `DATETIME` NULL 

### `settings`
- Kolon sayısı: 2
- Index sayısı: 1
- `sqlite_autoindex_settings_1` -> key
- Kolonlar:
  - `key` `VARCHAR(100)` NOT NULL PK
  - `value` `TEXT` NULL 

### `sms_log`
- Kolon sayısı: 6
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `tracking_no` `VARCHAR(50)` NULL 
  - `phone` `VARCHAR(20)` NOT NULL 
  - `message` `TEXT` NOT NULL 
  - `twilio_sid` `VARCHAR(100)` NULL 
  - `sent_at` `DATETIME` NULL 

### `stock_movements`
- Kolon sayısı: 8
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `part_id` `INTEGER` NOT NULL 
  - `type` `VARCHAR(20)` NULL 
  - `amount` `INTEGER` NOT NULL 
  - `current_stock` `INTEGER` NOT NULL 
  - `description` `TEXT` NULL 
  - `date` `DATETIME` NULL 
  - `user` `VARCHAR(100)` NULL 

### `tickets`
- Kolon sayısı: 8
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `customer_id` `INTEGER` NULL 
  - `subject` `VARCHAR(500)` NOT NULL 
  - `description` `TEXT` NOT NULL 
  - `status` `VARCHAR(11)` NULL 
  - `priority` `VARCHAR(20)` NULL 
  - `created_at` `DATETIME` NULL 
  - `updated_at` `DATETIME` NULL 

### `used_parts`
- Kolon sayısı: 6
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `tracking_no` `VARCHAR(50)` NOT NULL 
  - `part_name` `VARCHAR(255)` NOT NULL 
  - `price` `FLOAT` NULL 
  - `quantity` `INTEGER` NULL 
  - `created_at` `DATETIME` NULL 

### `users`
- Kolon sayısı: 6
- Index sayısı: 2
- `ix_users_username` -> username
- `ix_users_id` -> id
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `username` `VARCHAR(100)` NOT NULL 
  - `password` `VARCHAR(255)` NOT NULL 
  - `role` `VARCHAR(9)` NULL 
  - `created_at` `DATETIME` NULL 
  - `is_active` `BOOLEAN` NULL 

### `whatsapp_templates`
- Kolon sayısı: 3
- Index sayısı: 0
- Kolonlar:
  - `id` `INTEGER` NOT NULL PK
  - `name` `VARCHAR(100)` NOT NULL 
  - `content` `TEXT` NOT NULL 

## Web Optimizasyon Önerileri
- Sorgu ağırlıklı alanlara birleşik index ekleyin (örn. `devices(status, created_at)`).
- Soft-delete yaklaşımı olan tablolarda `is_active` + tarih alanı indexleyin.
- Audit ve log tablolarını zaman bazlı partition/archival stratejisine taşıyın.
- API pagination için liste endpointlerinde `ORDER BY + LIMIT/OFFSET` standardize edin.
- Raporlama için ağır join'ler adına materialized snapshot/job tablosu tasarlayın.
