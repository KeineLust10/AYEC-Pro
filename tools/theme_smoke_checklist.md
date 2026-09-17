# Tema Smoke Test Checklist

Bu listeyi tema değiştirirken (Aydınlık <-> Karanlık) her adımda uygula.

## Hazırlık
- [ ] Uygulamayı aç, ana ekranda olduğundan emin ol.
- [ ] Sağ üstten tema ikonunu kullanarak tema değişimini test etmeye hazır ol.
- [ ] Test boyunca aynı oturumda en az 3 kez tema değiştir.

## Kontrol Adımları
1. [ ] **Global geçiş**: Tema değiştirince ana pencere, üst bar, yan menü ve içerik alanı aynı anda güncelleniyor.
2. [ ] **Yan menü**: Sol menüde siyah/beyaz blok, alaca parça, okunamayan yazı yok.
3. [ ] **Tablo ve başlıklar**: `QTableWidget` satır/başlık/selected durumları her iki temada da okunaklı.
4. [ ] **Form elemanları**: `QLineEdit`, `QTextEdit`, `QComboBox`, `QDateEdit` odak/hover durumlarında kontrast düzgün.
5. [ ] **Dialog pencereleri**: Açılan tüm dialoglarda arka plan/metin/buton renkleri tema ile tutarlı.
6. [ ] **Buton durumları**: normal/hover/pressed/disabled tüm buton durumları iki temada da doğru.
7. [ ] **Bildirimler**: Toast/notification kartlarında yazı okunabilir, arka plan doğru.
8. [ ] **Finans sayfaları**: Banka, gelir-gider, raporlar ekranında zebra/kararma/ters renk yok.
9. [ ] **Ayarlar sayfası**: Alt sekmeler ve kartlar arasında farklı tema kalıntısı yok.
10. [ ] **Tekrar geçiş testi**: 10 kez hızlı tema değiştir (1-2 sn arayla), flicker veya kırık stil oluşmuyor.

## Hata Kaydı Formatı
Her hatayı bu formatta not et:

- Sayfa:
- Bileşen:
- Tema:
- Beklenen:
- Gerçek:
- Ekran görüntüsü:

## Çıkış Kriteri
- [ ] Checklist 10/10 geçti
- [ ] Kritik (okunamaz/çakışan) renk hatası yok
- [ ] Tema değişimi sonrası yeniden başlatmadan UI tutarlı kalıyor
