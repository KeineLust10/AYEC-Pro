# QSpinBox / QDateTimeEdit Stil Rehberi

## Problem ("Ghost Button" Issue)

QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit ve QDateTimeEdit kontrollerinin arttırma/azaltma butonları (oklar) yeterince görünür değildi. Kullanıcılar bu butonların varlığını fark etmekte zorlanıyordu.

## Çözüm

### 1. DesignTokens Güncellemesi

`src/utils/design_system.py` dosyasına yeni `get_spinbox_qss()` metodu eklendi:

#### Özellikler:
- **Yüksek Kontrast**: Ok işaretleri koyu renkli (@accent teması rengi)
- **Geniş Butonlar**: Minimum 24px genişliğinde butonlar
- **Hover/Pressed Efektleri**: Hover durumunda buton arka planı @accent rengine dönüşüyor
- **Tüm Widget'ları Destekler**:
  - QSpinBox
  - QDoubleSpinBox
  - QDateEdit
  - QTimeEdit
  - QDateTimeEdit
- **İki Yerleşim Seçeneği**:
  - Geleneksel: Yukarı/Aşağı oklar sağda üst üste
  - Side-by-Side: [-] Değer [+] formatında yatay yerleşim

### 2. Kullanım

#### A) Tüm Dialog'a Uygulama (Önerilen)

```python
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss

class MyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self._build_ui()
        
        # Dialog sonunda stil uygula
        self.setStyleSheet(theme_qss(
            DesignTokens.get_spinbox_qss(button_width=24, side_by_side=False)
        ))
```

#### B) Sadece Belirli Widget'lara Uygulama

```python
from src.utils.design_system import DesignTokens, apply_modern_spinbox_style

# Tek bir spinbox'a uygula
apply_modern_spinbox_style(my_spinbox, button_width=24)

# Veya widget grubuna uygula
apply_modern_spinbox_style(container_widget, button_width=24)
```

#### C) Global Uygulama (Tüm Uygulama)

```python
# main.py veya app başlangıcında
from src.utils.design_system import DesignTokens

DesignTokens.apply_spinbox_styles(button_width=24, side_by_side=False)
```

### 3. Stil Parametreleri

```python
DesignTokens.get_spinbox_qss(
    button_width=24,      # Buton genişliği (px)
    side_by_side=False    # True: Yatay [-] val [+], False: Dikey ↑↓
)
```

### 4. Örnek: Güncellenmiş Dialog

Bakım Kartı Dialog (`vehicle_maintenance_dialog.py`) güncellendi:

```python
# Eski kullanım (her spinbox'a ayrı stil):
self.spn_odometer.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

# Yeni kullanım (tüm dialog'a kapsamlı stil):
self.setStyleSheet(theme_qss(
    DesignTokens.get_spinbox_qss(button_width=24, side_by_side=False)
))
```

### 5. Görsel Özellikler

#### Geleneksel Dikey Yerleşim (side_by_side=False):
```
┌─────────────────┐
│  Değer       ▲  │  <- Up button (24px)
│              ▼  │  <- Down button (24px)
└─────────────────┘
```

#### Yatay Yerleşim (side_by_side=True):
```
┌─────────────────┐
│  ◀  Değer   ▶   │  <- Left/Right butonlar
└─────────────────┘
```

#### Renk Şeması:
- **Normal**: Açık gri arka plan (@surface_alt), koyu oklar (@text)
- **Hover**: Vurgu rengi arka plan (@accent), beyaz oklar (@selection_text)
- **Focus**: Mavi border (@accent), açık arka plan
- **Pressed**: Koyu vurgu rengi (@accent_pressed)

### 6. Diğer Dialog'ları Güncelleme

Aşağıdaki dialog'lar bu yeni stil sistemiyle güncellenebilir:

1. `add_stock_dialog.py` - Stok ekleme
2. `payment_dialog.py` - Ödeme dialogu
3. `smart_home_sales_page.py` - Satış sayfası
4. `new_transaction_v2_page.py` - Yeni işlem
5. `transaction_page.py` - İşlem sayfası
6. `bank_loans_widget.py` - Banka kredileri

#### Hızlı Güncelleme Şablonu:

```python
# 1. Import ekle (zaten varsa atla)
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss

# 2. Mevcut setStyleSheet çağrılarını kaldır
# self.spn_xxx.setStyleSheet(...)  # KALDIR

# 3. _build_ui() sonuna ekle:
self.setStyleSheet(theme_qss(
    DesignTokens.get_spinbox_qss(button_width=24, side_by_side=False)
))
```

### 7. Temaya Uyumluluk

Tüm stiller tema sistemine entegredir:
- `@accent` - Vurgu rengi
- `@surface_alt` - Alternatif yüzey rengi
- `@text` - Metin rengi
- `@selection_text` - Seçim metin rengi (beyaz)
- `@border` - Border rengi

Bu sayede dark/light mode değişimlerinde otomatik uyum sağlar.

### 8. İpuçları

- **Büyük Değerler**: Daha fazla tıklama alanı için `button_width=32` deneyin
- **Tablet Kullanımı**: Touch cihazlarda `button_width=36` önerilir
- **Modern Görünüm**: `side_by_side=True` daha modern bir görünüm sunar
- **Tutarlılık**: Tüm uygulamada aynı `button_width` değerini kullanın

## Sonuç

Bu güncelleme ile:
- ✅ Butonlar artık "hayalet" değil, belirgin
- ✅ Yeterli tıklama alanı (24px+)
- ✅ Açık hover/pressed durumları
- ✅ Tüm QAbstractSpinBox türevleri destekleniyor
- ✅ Tema uyumlu
- ✅ Kolay uygulanabilir
