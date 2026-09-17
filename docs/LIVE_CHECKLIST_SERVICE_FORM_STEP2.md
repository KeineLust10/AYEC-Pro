# Canlı Doğrulama Checklist (Servis Formu 2. Sayfa)

## Akış
1. `Yeni Servis Kaydı Oluştur` dialogunu aç.
2. 2. adıma (`Servis Detayları`) geç.
3. `Toggle-Switch Düzenle` butonuna tıkla.
4. `Hızlı Notlar / Makrolar Düzenleyici` içinde bir toggle aktif/pasif değiştir.
5. Dialogu `Kapat` ile kapat.
6. Servis Formu 2. sayfaya geri dön.
7. Toggle durumunun korunduğunu kontrol et.
8. Dialogu tekrar aç ve aynı kategoriyi kontrol et.

## Beklenen Sonuçlar
- Toggle değişikliği anında DB'ye yazılır.
- Tekrar açıldığında toggle durumu kaybolmaz.
- 2. sayfada `İleri/Geri` butonları tek kopya görünür.
- Form başlık/metinleri tema (Nord/Forest/Bulut) altında okunur.
- Koyu temada siyah metin kalmaz.

## Hata Yakalama
- `Hızlı Notlar` ekranında dikey scroll sadece satır sayısı yüksekse görünmeli.
- Kapanış sonrası `RecursionError` veya donma olmamalı.
- Log’da `UPDATE fast_notes` SQL hatası olmamalı.
