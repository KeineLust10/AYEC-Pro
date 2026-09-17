# AYEC Pro - Sunucu, Web ve Mobil Arayüz Kılavuzu

## 1. Genel Bakış
AYEC Pro, v2.10 itibariyle "Tek Program" mimarisine geçmiştir. Artık ayrı bir sunucu programı çalıştırmanıza gerek yoktur. Masaüstü uygulamasını açtığınızda, arka planda web sunucusu ve mobil API otomatik olarak başlatılır.

## 2. Sunucu Özellikleri
- **Otomatik Başlatma:** Program açıldığında arka planda çalışır.
- **Port:** Varsayılan olarak **8000** portunu kullanır.
- **Erişim:** Aynı ağdaki tüm cihazlardan erişilebilir.

## 3. Web Arayüzü Kullanımı
Web arayüzü, ofis dışındayken veya farklı bir bilgisayardan verilere erişmek için kullanılır.

### Nasıl Bağlanılır?
1. AYEC Pro masaüstü uygulamasını ana bilgisayarda çalıştırın.
2. Web tarayıcınızı (Chrome, Edge, Firefox vb.) açın.
3. Adres çubuğuna ana bilgisayarın IP adresini ve port numarasını yazın.
   - **Örnek:** `http://192.168.1.100:8000`
   - Eğer ana bilgisayardaysanız: `http://localhost:8000`

### Özellikler
- Müşteri Yönetimi
- Servis Durum Takibi
- Stok Sorgulama
- Randevu Takvimi
- Raporlar

## 4. Mobil Arayüz Kullanımı
Mobil arayüz, teknisyenler ve saha personeli için optimize edilmiştir.

### Nasıl Bağlanılır?
1. Akıllı telefonunuzun tarayıcısını açın.
2. Adres çubuğuna: `http://<ANA_BILGISAYAR_IP>:8000/mobile` yazın.
   - **Örnek:** `http://192.168.1.100:8000/mobile`

### Özellikler
- Barkod Okuma (Kamera ile)
- Hızlı Servis Durum Güncelleme
- Fotoğraf Yükleme
- Müşteri Arama ve Yol Tarifi

## 5. Teknik Detaylar ve Sorun Giderme

### Güvenlik Duvarı (Firewall) Uyarısı
Program ilk açıldığında Windows Güvenlik Duvarı uyarı verebilir. **"Erişime İzin Ver"** (Allow Access) seçeneğini işaretlemelisiniz. Aksi takdirde diğer cihazlardan erişim sağlanamaz.

### Bağlantı Sorunları
Eğer web veya mobil arayüze bağlanamıyorsanız:
1. Ana bilgisayarın açık ve AYEC Pro'nun çalışıyor olduğundan emin olun.
2. Ana bilgisayar ve mobil cihazın **aynı Wi-Fi ağında** olduğundan emin olun.
3. Windows Güvenlik Duvarı ayarlarından 8000 portuna izin verildiğini kontrol edin.
4. Ana bilgisayarın IP adresinin değişmediğinden emin olun (Statik IP önerilir).

### Port Değiştirme
Eğer 8000 portu başka bir program tarafından kullanılıyorsa, sistem otomatik olarak hata verebilir veya farklı bir port deneyebilir. Log dosyalarını (`hata_logu.txt`) kontrol ediniz.

---
**Destek:** teknik@ayecpro.com | 0534 878 10 47
