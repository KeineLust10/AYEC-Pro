# Tema Refactor Güncel Raporu

Tarih: 2026-02-20

## Özet
Bu çalışma ile tema sistemi iki canonical moda sadeleştirildi ve tema geçişinde kalan görsel artefakt/sızıntı sorunları giderildi.

- Canonical tema adları: `AYEC` (Aydınlık), `Bulut` (Koyu)
- Eski tema stringleri normalize edilerek bu iki değere mapleniyor.
- Tema geçişi tüm uygulamaya merkezden uygulanıyor.
- Global stil sızıntısına neden olan geniş `QWidget { ... }` kuralları scoped hale getirildi.
- Mojibake/Türkçe karakter bozulmaları için runtime onarım güçlendirildi.

## Yapılan Ana Değişiklikler

### 1) Tema İsimlendirme ve Yönetim Sadeleştirme
Dosya: `src/utils/theme_manager.py`

- `THEME_ALIASES` sadeleştirildi:
  - `AYEC -> AYEC`
  - `Bulut -> Bulut`
- `THEME_FILES` sadeleştirildi:
  - `AYEC -> light_theme.json/light_theme.qss`
  - `Bulut -> dark_theme.json/dark_theme.qss`
- `THEMES` yalnızca iki canonical anahtar içeriyor: `AYEC`, `Bulut`
- `_current_theme` varsayılanı `AYEC` olarak güncellendi.
- `normalize_theme_name()` güncellendi:
  - Eski değerler (`Dark`, `Karanlik`, `Koyu Modern` vb.) `Bulut`a normalize edilir.
  - Diğer/boş değerler `AYEC`e düşer.
- `get_available_themes()` artık yalnızca `AYEC`, `Bulut` döndürür.

### 2) Uygulama Düzeyi Tema Akışı
Dosya: `ModernDesktopApp.py`

- Başlangıç tema fallback’i `AYEC` olacak şekilde güncellendi.
- Header tema toggle akışı:
  - Koyu aktifse `AYEC`
  - Açık aktifse `Bulut`
- `color_theme_full` okuma/yazma akışı canonical isimlere taşındı.

### 3) Tema Geçişi Artefakt (Sol Üstte Kalan Parça) Düzeltmesi
Dosya: `src/utils/theme_manager.py`

- Tema geçiş overlay animasyonu için aktif referans havuzu eklendi: `_active_theme_anims`.
- Animasyon bitiminde güvenli cleanup ile overlay daima kaldırılıyor.
- Overlay mouse-event transparent hale getirildi.
- Uygulama çağrı tarafında geçiş stabilizasyonu için animasyon kapatıldı:
  - `ModernDesktopApp.apply_theme(..., animate=False)`

> Not: Bu değişiklik, tema değişiminde sol üstte kalan siyah/beyaz parça problemini ortadan kaldırmak için yapıldı.

### 4) Stil Sızıntısı (Global Selector) Temizliği
Aşağıdaki dosyalarda global etki yaratan `QWidget { ... }` stilleri objectName/scope ile sınırlandı:

- `src/ui/widgets/assistant_sidebar.py`
- `src/ui/widgets/ayec_notification.py`
- `src/ui/widgets/snoozeable_toast.py`
- `src/ui/pages/settings_widgets/user_management.py`
- `src/ui/pages/external_tracking_page.py`
- `src/ui/pages/settings_page.py`
- `src/ui/pages/settings_widgets/company_settings.py`

### 5) Mojibake / Türkçe Karakter Sorunları

#### Runtime Onarım (Merkezi)
Dosya: `src/utils/theme_manager.py`

- Style/Show/Polish eventlerinde widget metinleri onarılıyor.
- Kapsam genişletildi:
  - `QLabel`, `QAbstractButton`, `QLineEdit`, `QTextEdit`, `QTextBrowser`, `QPlainTextEdit`, `QComboBox`, `QGroupBox`, `QTabWidget`, window title
- `ftfy` + fallback decode stratejisi ile metin düzeltme güçlendirildi.

#### Kalıcı Dosya Düzeltmeleri
- `ModernDesktopApp.py` mojibake yoğunluğu temizlendi (yüksek hacimli düzeltme).
- Ayrıca:
  - `src/utils/finance_manager.py`
  - `src/utils/service_pdf_generator.py`

### 6) Önceki Kritik Hata Fixlerinin Korunması
- `KANBAN_COLORS` NameError giderildi (`src/ui/widgets/kanban_board.py`)
- `sqlite3.Row.get` hataları giderildi:
  - `src/ui/pages/settings_widgets/voice_training_widget.py`
  - `src/utils/alert_scheduler.py`
- Qt `box-shadow` uyarısı kaldırıldı (`src/ui/pages/settings_widgets/stock_settings.py`)

## Doğrulama

Çalıştırılan kontroller:
- `python -m compileall -q src`
- hedefli `py_compile` kontrolleri (theme_manager, alert_scheduler, ModernDesktopApp ve ilgili widget/page dosyaları)

Sonuç:
- Derleme hatası yok.
- Tema adlandırma canonical yapıda (`AYEC/Bulut`).
- Tema geçişinde overlay kaynaklı artefakt riski düşürüldü.

## Kalan İşler (Planlı Sonraki Adım)
1. `src/ui` altında kalan literal mojibake metinlerin dosya-bazlı batch temizliği (kalıcı kaynak düzeltmesi).
2. Tüm menü/alt menülerde görsel smoke test (Aydınlık/Koyu geçişte zebra/parça kontrolü).
3. Tema değişiminde manuel regresyon testi:
   - Dialoglar
   - Table/headers
   - Side menu + alt menüler
   - Toast/notification katmanı
