# AYEC Pro Web Test Senaryoları

## Fonksiyonel Testler
1. Kullanıcı giriş/çıkış ve token yenileme.
2. Müşteri CRUD + müşteri notları + borç hatırlatma akışı.
3. Servis formu oluşturma, durum güncelleme, parça ekleme.
4. Randevu planlama ve personel atama.
5. Stok giriş/çıkış ve kritik stok uyarısı.
6. Gelir/gider kaydı ve banka hesap mutabakatı.
7. Çek/senet kayıtları ve vade hatırlatmaları.
8. Rapor ekranlarında filtreleme, export (CSV/PDF).
9. Ayarlar ekranında tema/dil/entegrasyon değişikliklerinin kalıcılığı.

## Güvenlik Testleri
1. Yetkisiz endpoint erişim denemeleri (401/403).
2. Rol dışı işlem denemeleri (RBAC).
3. SQL injection/XSS payload testleri.
4. Brute-force giriş koruması.
5. Session hijack ve token replay testleri.

## Performans Testleri
1. Dashboard ilk yükleme süresi (`TTFB`, `LCP`).
2. Büyük liste endpointleri (100k kayıt simulasyonu) p95 latency.
3. Eşzamanlı kullanıcı testleri (k6/JMeter).
4. Frontend bundle boyutu ve code-splitting kontrolü.

## Cross-Browser
1. Chrome son 2 sürüm.
2. Edge son 2 sürüm.
3. Firefox son 2 sürüm.
4. Safari (macOS + iOS).

## PWA Testleri
1. İlk yükleme sonrası offline açılış.
2. Service worker cache invalidation.
3. Push notification izin + teslim.
4. Install prompt ve standalone açılış.
5. Kamera/GPS permission + fallback davranışları.

