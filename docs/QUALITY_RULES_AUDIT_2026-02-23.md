# Kural Uyum Denetimi (2026-02-23)

## ?zet
- Toplam Python dosyas?: 293
- 1000 sat?r ?st? dosya: 15
- Geni? except (except/except Exception): 1181
- Sessiz exception blo?u (pass/return/continue): 234

## 1) 1000 Sat?r ?st? Dosyalar
- `src\database.py`: 4705 sat?r
- `src\ui\pages\settings_page.py`: 3066 sat?r
- `src\ui\modern_login_window.py`: 2542 sat?r
- `src\ui\pages\dashboard_page.py`: 1933 sat?r
- `src\ui\pages\transaction_page.py`: 1889 sat?r
- `src\ui\dialogs\technician_panel.py`: 1570 sat?r
- `src\ui\dialogs\bank_detail_dialog.py`: 1450 sat?r
- `src\ui\pages\customers_page.py`: 1432 sat?r
- `src\ui\pages\finance\bank_page.py`: 1365 sat?r
- `src\ui\pages\settings_widgets\user_management.py`: 1327 sat?r
- `src\ui\pages\accounting_page.py`: 1289 sat?r
- `src\ui\dialogs\new_service_dialog.py`: 1223 sat?r
- `src\ui\pages\field_service_page.py`: 1134 sat?r
- `src\ui\pages\project_management\project_detail_page.py`: 1079 sat?r
- `src\utils\theme_manager.py`: 1054 sat?r

## 2) Geni? Except Yo?unlu?u (?lk 20)
- `src\database.py`: 198
- `src\ui\modern_login_window.py`: 61
- `src\ui\pages\dashboard_page.py`: 37
- `src\ui\dialogs\new_service_dialog.py`: 31
- `src\ui\dialogs\technician_panel.py`: 30
- `src\db\mixins\finance_mixin.py`: 27
- `src\utils\theme_manager.py`: 22
- `src\ui\dialogs\bank_detail_dialog.py`: 21
- `src\ui\pages\settings_widgets\user_management.py`: 20
- `src\db\mixins\stock_mixin.py`: 20
- `src\ui\pages\customers_page.py`: 19
- `src\ui\pages\transaction_page.py`: 19
- `src\utils\cloud_backup.py`: 18
- `src\utils\server_main.py`: 18
- `src\ui\pages\finance\bank_page.py`: 15
- `src\utils\ai_prediction.py`: 14
- `src\ui\pages\job_service_tracking_page.py`: 14
- `src\utils\auth_manager.py`: 13
- `src\ui\pages\accounting_page.py`: 13
- `src\ui\widgets\side_menu.py`: 13

## 3) Sessiz Exception Yo?unlu?u (?lk 20)
- `src\database.py`: 30
- `src\ui\dialogs\new_service_dialog.py`: 23
- `src\utils\theme_manager.py`: 18
- `src\ui\modern_login_window.py`: 13
- `src\ui\dialogs\technician_panel.py`: 11
- `src\ui\widgets\side_menu.py`: 10
- `src\ui\pages\dashboard_page.py`: 8
- `src\ui\pages\settings_widgets\user_management.py`: 8
- `src\ui\pages\job_service_tracking_page.py`: 6
- `src\ui\pages\finance\bank_page.py`: 6
- `src\db\mixins\finance_mixin.py`: 6
- `src\ui\pages\customers_page.py`: 5
- `src\ui\pages\settings_widgets\voice_assistant_shortcuts.py`: 5
- `src\utils\ai_prediction.py`: 4
- `src\ui\dialogs\bank_detail_dialog.py`: 4
- `src\ui\dialogs\technician_wizard_page2.py`: 4
- `src\utils\security_manager.py`: 3
- `src\ui\pages\field_service_page.py`: 3
- `src\ui\pages\settings_page.py`: 3
- `src\ui\widgets\quick_stats_widget.py`: 3

## 4) ?lk M?dahale S?ras?
- P0: `src/database.py` (hem 1000+ sat?r hem exception yo?unlu?u en y?ksek)
- P0: `src/ui/pages/settings_page.py`, `src/ui/modern_login_window.py`
- P1: `src/ui/pages/finance/bank_page.py`, `src/ui/pages/accounting_page.py`, `src/utils/theme_manager.py`
- P2: Dialog/panel dosyalar? (`technician_panel.py`, `bank_detail_dialog.py`, `new_service_dialog.py`)

## 5) Uygulama Plan? (Kural Bazl?)
1. Dosya b?lme: 1000 sat?r ?zeri dosyalar? mod?llere ay?r.
2. Exception politikas?: geni? except bloklar?n? daralt, log+yeniden y?kseltme kurallar?n? uygula.
3. Test katman?: unit/integration/ui smoke listesi ile her mod?l ge?i?inde do?rula.
4. Refactor sonras? ikinci denetim: ayn? raporu tekrar ?ret, kalan ihlali indir.
