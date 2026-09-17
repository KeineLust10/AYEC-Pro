# AYEC Pro Masaüstü Teknik Envanteri

## 1) Sistem Özeti
- Uygulama çekirdeği: `ModernDesktopApp.py`
- UI ana katmanı: `src/ui`
- Veri erişim katmanı: `src/db` + `src/database.py`
- Yardımcı servisler: `src/utils`
- Toplam sayfa eşlemesi: **34**

## 2) Ana Menü / Alt Menü Yapısı
- Servis Yönetimi
- Müşteri Hub
- Stok & Satış
- Proje Yönetimi
- Finans
- Personel
- Araçlar

## 3) Sayfa Modül Envanteri
| Index | Class | Module | Kullanım Senaryosu | Girdi/Çıktı |
|---|---|---|---|---|
| 10 | `PersonnelPage` | `ui.pages.personnel_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 21 | `CustomersPage` | `ui.pages.customers_page` | Müşteri/iş ortağı kayıtlarını yönetme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 25 | `ContractsPage` | `ui.pages.contracts_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 26 | `PartnersPage` | `ui.pages.customers_page` | Müşteri/iş ortağı kayıtlarını yönetme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 30 | `AppointmentsPage` | `ui.pages.appointments_page` | Randevu oluşturma ve takvim planlama | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 40 | `DashboardPage` | `ui.pages.dashboard_page` | KPI ve operasyon özeti görüntüleme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 41 | `ServiceBoardPage` | `ui.pages.service_board_page` | Servis iş akışını başlatma ve takip etme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 42 | `ServiceStatusPage` | `ui.pages.service_status_page` | Servis iş akışını başlatma ve takip etme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 45 | `SummaryPage` | `ui.pages.summary_page` | Raporlama, analiz ve izleme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 50 | `StockPage` | `ui.pages.stock_page` | Stok envanteri ve ürün/marka yönetimi | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 61 | `FieldServicePage` | `ui.pages.field_service_page` | Servis iş akışını başlatma ve takip etme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 65 | `ExternalTrackingPage` | `ui.pages.external_tracking_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 70 | `SupportPage` | `ui.pages.support_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 90 | `RemindersPage` | `ui.pages.reminders_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 101 | `AccountingPage` | `ui.pages.accounting_page` | Finansal hareketleri takip etme ve mutabakat | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 102 | `AccountingPage` | `ui.pages.accounting_page` | Finansal hareketleri takip etme ve mutabakat | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 103 | `AccountingPage` | `ui.pages.accounting_page` | Finansal hareketleri takip etme ve mutabakat | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 105 | `BankPage` | `ui.pages.finance.bank_page` | Finansal hareketleri takip etme ve mutabakat | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 106 | `CheckNotePage` | `ui.pages.finance.check_note_page` | Finansal hareketleri takip etme ve mutabakat | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 111 | `FinanceReportPage` | `ui.pages.finance.finance_report_page` | Finansal hareketleri takip etme ve mutabakat | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 115 | `InvoiceCreationPage` | `ui.pages.invoice_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 120 | `AnnouncementsPage` | `ui.pages.announcements_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 130 | `SettingsPage` | `ui.pages.settings_page` | Sistem ve kullanıcı ayarlarını yapılandırma | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 135 | `AuditLogPage` | `ui.pages.audit_log_page` | Raporlama, analiz ve izleme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 140 | `ServicesPage` | `ui.pages.services_page` | Servis iş akışını başlatma ve takip etme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 145 | `BrandsPage` | `ui.pages.brands_page` | Stok envanteri ve ürün/marka yönetimi | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 150 | `TransactionPage` | `ui.pages.transaction_page` | Servis iş akışını başlatma ve takip etme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 160 | `KnowledgeBasePage` | `ui.pages.knowledge_base_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 170 | `AIAssistantPage` | `ui.pages.ai_assistant_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 180 | `BackupPage` | `ui.pages.backup_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 200 | `ProjectsPage` | `ui.pages.project_management.projects_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 201 | `JobServiceTrackingPage` | `ui.pages.job_service_tracking_page` | Servis iş akışını başlatma ve takip etme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 220 | `QuickSalePage` | `ui.pages.quick_sale_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |
| 250 | `MobileGuidePage` | `ui.pages.mobile_guide_page` | İlgili modül iş akışını yürütme | Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |

## 4) Dialog Pencereleri
- Toplam tespit edilen dialog sınıfı: **60**
- `add_customer_dialog.py` → `AddCustomerDialog`
- `add_device_dialog.py` → `AddDeviceDialog`
- `add_kb_article_dialog.py` → `AddKBArticleDialog`
- `add_service_definition_dialog.py` → `AddServiceDefinitionDialog`
- `add_stock_dialog.py` → `AddStockDialog`
- `admin_approval_dialog.py` → `AdminApprovalDialog`
- `advanced_filter.py` → `AdvancedFilterDialog`
- `app_lock_dialog.py` → `AppLockDialog`
- `archive_detail_dialog.py` → `ArchiveDetailDialog`
- `bank_detail_dialog.py` → `BankDetailDialog`
- `bank_detail_dialog.py` → `BankCardDialog`
- `bank_detail_dialog.py` → `AlertEditDialog`
- `base_modern_dialog.py` → `BaseModernDialog`
- `brand_edit_dialog.py` → `BrandEditDialog`
- `bulk_payment_dialog.py` → `BulkPaymentDialog`
- `critical_alert_dialog.py` → `CriticalAlertDialog`
- `customer_360_dialog.py` → `Customer360Dialog`
- `customer_history_dialog.py` → `CustomerHistoryDialog`
- `customer_notes_dialog.py` → `CustomerNotesDialog`
- `customer_select_dialog.py` → `CustomerSelectDialog`
- `device_history_dialog.py` → `DeviceHistoryDialog`
- `device_selection_dialog.py` → `DeviceSelectionDialog`
- `early_closure_dialog.py` → `EarlyClosureDialog`
- `global_search_dialog.py` → `GlobalSearchDialog`
- `label_editor_dialog.py` → `LabelEditorDialog`
- `license_keygen_dialog.py` → `LicenseKeygenDialog`
- `license_lock_screen.py` → `LicenseLockScreen`
- `loan_detail_dialog.py` → `LoanDetailDialog`
- `loan_wizard_dialog.py` → `LoanWizardDialog`
- `location_picker_dialog.py` → `LocationPickerDialog`
- `login_dialog.py` → `LoginDialog`
- `modern_confirm.py` → `ModernConfirmDialog`
- `modern_input_dialog.py` → `ModernInputDialog`
- `modern_select_dialog.py` → `ModernSelectDialog`
- `new_service_dialog.py` → `NewServiceDialog`
- `password_prompt_dialog.py` → `PasswordPromptDialog`
- `password_reset_dialog.py` → `PasswordResetDialog`
- `payment_dialog.py` → `ModernPaymentDialog`
- `personnel_edit_dialog.py` → `PersonnelEditDialog`
- `photo_gallery_dialog.py` → `PhotoGalleryDialog`
- `premium_dialogs.py` → `PremiumDialogBase`
- `premium_dialogs.py` → `PremiumWarningDialog`
- `premium_dialogs.py` → `PasswordConfirmDialog`
- `project_transaction_dialog.py` → `ProjectTransactionDialog`
- `project_unit_sale_dialog.py` → `ProjectUnitSaleDialog`
- `quick_sale_dialog.py` → `QuickSaleDialog`
- `registration_dialog.py` → `RegistrationDialog`
- `report_dialog.py` → `ReportDialog`
- `security_confirm_dialog.py` → `SecurityConfirmDialog`
- `send_sms_dialog.py` → `SendSMSDialog`
- `service_invoice_dialog.py` → `ServiceInvoiceDialog`
- `simple_confirm.py` → `SimpleConfirmDialog`
- `sms_settings_dialog.py` → `SMSSettingsDialog`
- `technician_login_dialog.py` → `TechnicianLoginDialog`
- `technician_panel.py` → `ImageGalleryDialog`
- `technician_panel.py` → `ModernManualProductDialog`
- `template_manager.py` → `TemplateManagerDialog`
- `transaction_detail_dialog.py` → `TransactionDetailDialog`
- `transaction_dialog.py` → `TransactionAddDialog`
- `user_switch_dialog.py` → `UserSwitchDialog`

## 5) Ayarlar Alt Modülleri
- `background_settings`
- `backup_settings`
- `bank_settings`
- `cargo_settings`
- `company_settings`
- `integration_hub`
- `language_settings`
- `license_settings`
- `location_settings`
- `remote_settings`
- `sms_settings`
- `smtp_settings`
- `stock_settings`
- `system_identity_settings`
- `telegram_settings`
- `user_management`
- `user_management_rbac`
- `voice_assistant_settings`
- `voice_assistant_shortcuts`
- `voice_training_widget`
- `whatsapp_settings`

## 6) İş Mantığı Özeti
- Sayfalar `page_mapping` üzerinden lazy-load edilir.
- Menü tıklaması `on_menu_click(index)` ile yönlenir ve breadcrumb güncellenir.
- Temalar `ThemeManager` ile palette + QSS + runtime remap şeklinde uygulanır.
- Lisans, hatırlatıcı, asistan ve websocket süreçleri ana pencerede zamanlayıcı/worker tabanlı yürür.
- Form süreçlerinde doğrulama + DB commit + toast bildirimi deseni kullanılır.

## 7) Form/Modal/Report Envanteri
### Form odaklı bileşenler
- `GeminiSettingsWidget` (`src\ui\pages\gemini_settings_widget.py`): veri girişi/doğrulama/kayıt akışı
- `InvoiceCreationPage` (`src\ui\pages\invoice_page.py`): veri girişi/doğrulama/kayıt akışı
- `QuickNotesSettingsWidget` (`src\ui\pages\quick_notes_settings_widget.py`): veri girişi/doğrulama/kayıt akışı
- `SecuritySettingsWidget` (`src\ui\pages\security_settings_widget.py`): veri girişi/doğrulama/kayıt akışı
- `SettingsPage` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `CompanySettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `SMSSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `SMTPSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `BackgroundSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `BankSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `JobServiceNumberSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `StockSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `CargoSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `LanguageSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `GeminiSettingsWidget` (`src\ui\pages\settings_page.py`): veri girişi/doğrulama/kayıt akışı
- `BackgroundSettingsWidget` (`src\ui\pages\settings_widgets\background_settings.py`): veri girişi/doğrulama/kayıt akışı
- `BackupSettingsWidget` (`src\ui\pages\settings_widgets\backup_settings.py`): veri girişi/doğrulama/kayıt akışı
- `BankSettingsWidget` (`src\ui\pages\settings_widgets\bank_settings.py`): veri girişi/doğrulama/kayıt akışı
- `CargoSettingsWidget` (`src\ui\pages\settings_widgets\cargo_settings.py`): veri girişi/doğrulama/kayıt akışı
- `CompanySettingsWidget` (`src\ui\pages\settings_widgets\company_settings.py`): veri girişi/doğrulama/kayıt akışı
- `LanguageSettingsWidget` (`src\ui\pages\settings_widgets\language_settings.py`): veri girişi/doğrulama/kayıt akışı
- `LocationSettingsWidget` (`src\ui\pages\settings_widgets\location_settings.py`): veri girişi/doğrulama/kayıt akışı
- `RemoteSettingsWidget` (`src\ui\pages\settings_widgets\remote_settings.py`): veri girişi/doğrulama/kayıt akışı
- `SMSSettingsWidget` (`src\ui\pages\settings_widgets\sms_settings.py`): veri girişi/doğrulama/kayıt akışı
- `SMTPSettingsWidget` (`src\ui\pages\settings_widgets\smtp_settings.py`): veri girişi/doğrulama/kayıt akışı
- `StockSettingsWidget` (`src\ui\pages\settings_widgets\stock_settings.py`): veri girişi/doğrulama/kayıt akışı
- `SystemIdentitySettingsWidget` (`src\ui\pages\settings_widgets\system_identity_settings.py`): veri girişi/doğrulama/kayıt akışı
- `TelegramSettingsWidget` (`src\ui\pages\settings_widgets\telegram_settings.py`): veri girişi/doğrulama/kayıt akışı
- `VoiceAssistantSettingsWidget` (`src\ui\pages\settings_widgets\voice_assistant_settings.py`): veri girişi/doğrulama/kayıt akışı
- `WhatsAppSettingsWidget` (`src\ui\pages\settings_widgets\whatsapp_settings.py`): veri girişi/doğrulama/kayıt akışı
- `TransactionPage` (`src\ui\pages\transaction_page.py`): veri girişi/doğrulama/kayıt akışı

### Raporlama odaklı bileşenler
- `AuditLogPage` (`src\ui\pages\audit_log_page.py`): filtreleme, metrik üretimi, export
- `ExternalTrackingPage` (`src\ui\pages\external_tracking_page.py`): filtreleme, metrik üretimi, export
- `FinanceReportPage` (`src\ui\pages\finance\finance_report_page.py`): filtreleme, metrik üretimi, export
- `JobServiceTrackingPage` (`src\ui\pages\job_service_tracking_page.py`): filtreleme, metrik üretimi, export
- `ReportsPage` (`src\ui\pages\reports_page.py`): filtreleme, metrik üretimi, export
- `SummaryPage` (`src\ui\pages\summary_page.py`): filtreleme, metrik üretimi, export

### Dialog tabanlı etkileşimler
- `AddCustomerDialog` (`src/ui/dialogs/add_customer_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AddDeviceDialog` (`src/ui/dialogs/add_device_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AddKBArticleDialog` (`src/ui/dialogs/add_kb_article_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AddServiceDefinitionDialog` (`src/ui/dialogs/add_service_definition_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AddStockDialog` (`src/ui/dialogs/add_stock_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AdminApprovalDialog` (`src/ui/dialogs/admin_approval_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AdvancedFilterDialog` (`src/ui/dialogs/advanced_filter.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AppLockDialog` (`src/ui/dialogs/app_lock_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ArchiveDetailDialog` (`src/ui/dialogs/archive_detail_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `BankDetailDialog` (`src/ui/dialogs/bank_detail_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `BankCardDialog` (`src/ui/dialogs/bank_detail_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `AlertEditDialog` (`src/ui/dialogs/bank_detail_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `BaseModernDialog` (`src/ui/dialogs/base_modern_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `BrandEditDialog` (`src/ui/dialogs/brand_edit_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `BulkPaymentDialog` (`src/ui/dialogs/bulk_payment_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `CriticalAlertDialog` (`src/ui/dialogs/critical_alert_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `Customer360Dialog` (`src/ui/dialogs/customer_360_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `CustomerHistoryDialog` (`src/ui/dialogs/customer_history_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `CustomerNotesDialog` (`src/ui/dialogs/customer_notes_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `CustomerSelectDialog` (`src/ui/dialogs/customer_select_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `DeviceHistoryDialog` (`src/ui/dialogs/device_history_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `DeviceSelectionDialog` (`src/ui/dialogs/device_selection_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `EarlyClosureDialog` (`src/ui/dialogs/early_closure_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `GlobalSearchDialog` (`src/ui/dialogs/global_search_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `LabelEditorDialog` (`src/ui/dialogs/label_editor_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `LicenseKeygenDialog` (`src/ui/dialogs/license_keygen_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `LicenseLockScreen` (`src/ui/dialogs/license_lock_screen.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `LoanDetailDialog` (`src/ui/dialogs/loan_detail_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `LoanWizardDialog` (`src/ui/dialogs/loan_wizard_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `LocationPickerDialog` (`src/ui/dialogs/location_picker_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `LoginDialog` (`src/ui/dialogs/login_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ModernConfirmDialog` (`src/ui/dialogs/modern_confirm.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ModernInputDialog` (`src/ui/dialogs/modern_input_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ModernSelectDialog` (`src/ui/dialogs/modern_select_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `NewServiceDialog` (`src/ui/dialogs/new_service_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `PasswordPromptDialog` (`src/ui/dialogs/password_prompt_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `PasswordResetDialog` (`src/ui/dialogs/password_reset_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ModernPaymentDialog` (`src/ui/dialogs/payment_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `PersonnelEditDialog` (`src/ui/dialogs/personnel_edit_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `PhotoGalleryDialog` (`src/ui/dialogs/photo_gallery_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `PremiumDialogBase` (`src/ui/dialogs/premium_dialogs.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `PremiumWarningDialog` (`src/ui/dialogs/premium_dialogs.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `PasswordConfirmDialog` (`src/ui/dialogs/premium_dialogs.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ProjectTransactionDialog` (`src/ui/dialogs/project_transaction_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ProjectUnitSaleDialog` (`src/ui/dialogs/project_unit_sale_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `QuickSaleDialog` (`src/ui/dialogs/quick_sale_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `RegistrationDialog` (`src/ui/dialogs/registration_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ReportDialog` (`src/ui/dialogs/report_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `SecurityConfirmDialog` (`src/ui/dialogs/security_confirm_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `SendSMSDialog` (`src/ui/dialogs/send_sms_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ServiceInvoiceDialog` (`src/ui/dialogs/service_invoice_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `SimpleConfirmDialog` (`src/ui/dialogs/simple_confirm.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `SMSSettingsDialog` (`src/ui/dialogs/sms_settings_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `TechnicianLoginDialog` (`src/ui/dialogs/technician_login_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ImageGalleryDialog` (`src/ui/dialogs/technician_panel.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `ModernManualProductDialog` (`src/ui/dialogs/technician_panel.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `TemplateManagerDialog` (`src/ui/dialogs/template_manager.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `TransactionDetailDialog` (`src/ui/dialogs/transaction_detail_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `TransactionAddDialog` (`src/ui/dialogs/transaction_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu
- `UserSwitchDialog` (`src/ui/dialogs/user_switch_dialog.py`): Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, Girdi=parent state + DB, Çıktı=save/cancel sonucu

## 8) Web'e Dönüşüm Notları
- Her `index` değeri web router path eşlemesine dönüştürülecek.
- Dialog sınıfları webde modal drawer/overlay bileşenlerine çevrilecek.
- Sayfa bazlı iş mantığı API + frontend state management'e ayrıştırılacak.
