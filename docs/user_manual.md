# 📚 AYEC PRO - KAPSAMLI KULLANIM KILAVUZU

**Versiyon:** 3.2.0  
**Son Güncelleme:** 31 Ocak 2026  
**Hedef Kullanıcılar:** Teknik Servis İşletmeleri, Güvenlik Sistemleri Firmaları  
**İletişim:** destek@ayecpro.com | 0534 878 10 47 | www.ayecpro.com

---

## 📋 İÇİNDEKİLER

1. [Giriş ve Genel Bakış](#1-giriş-ve-genel-bakış)
2. [Kurulum ve İlk Yapılandırma](#2-kurulum-ve-ilk-yapılandırma)
3. [Kullanıcı Yönetimi ve Yetkilendirme](#3-kullanıcı-yönetimi-ve-yetkilendirme)
4. [Müşteri Yönetimi](#4-müşteri-yönetimi)
5. [Servis Takip Sistemi](#5-servis-takip-sistemi)
6. [Stok ve Depo Yönetimi](#6-stok-ve-depo-yönetimi)
7. [Personel Takibi ve Saha Servisi](#7-personel-takibi-ve-saha-servisi)
8. [Finans ve Muhasebe](#8-finans-ve-muhasebe)
9. [Jarvis AI Asistanı](#9-jarvis-ai-asistanı)
10. [Yedekleme ve Veri Güvenliği](#10-yedekleme-ve-veri-güvenliği)
11. [Web ve Mobil Arayüz](#11-web-ve-mobil-arayüz)
12. [Raporlama ve Analiz](#12-raporlama-ve-analiz)
13. [Entegrasyonlar](#13-entegrasyonlar)
14. [Sorun Giderme](#14-sorun-giderme)
15. [SSS (Sık Sorulan Sorular)](#15-sss-sık-sorulan-sorular)

---

## 1. GİRİŞ VE GENEL BAKIŞ

### AYEC Pro Nedir?

AYEC Pro, teknik servis işletmeleri için geliştirilmiş, yapay zeka destekli, bulut entegrasyonlu kapsamlı bir yönetim sistemidir. Masaüstü, web ve mobil platformlarda çalışarak işletmenizin tüm süreçlerini tek bir merkezden yönetmenizi sağlar.

### Temel Özellikler

#### 🎯 Müşteri ve Servis Yönetimi
- Detaylı müşteri profilleri ve servis geçmişi
- 360 derece müşteri görünümü
- Otomatik SMS/E-posta bildirimleri
- Hızlı servis durumu güncelleme

#### 📦 Stok ve Envanter Kontrolü
- Gerçek zamanlı stok takibi
- Kritik stok uyarıları
- Otomatik stok düşüm sistemi
- Çoklu depo yönetimi

#### 👥 Personel ve Saha Yönetimi
- Telegram entegrasyonu ile konum takibi
- Harita üzerinde personel görüntüleme
- İş atama ve takip sistemi
- Performans raporları

#### 💰 Finans ve Muhasebe
- Gelir/Gider takibi
- Banka hesapları yönetimi
- Detaylı finansal raporlar
- Kar/Zarar analizi

#### 🤖 Yapay Zeka Asistanı (Jarvis)
- Doğal dil ile veri sorgulama
- Otomatik raporlama
- Akıllı öneriler
- SSS desteği

#### ☁️ Bulut Entegrasyonu
- Otomatik uzak yedekleme
- Web arayüzü erişimi
- Mobil uygulama desteği
- Çoklu cihaz senkronizasyonu

### Sistem Gereksinimleri

**Minimum Gereksinimler:**
- İşletim Sistemi: Windows 10 veya üzeri (64-bit)
- İşlemci: Intel Core i3 veya eşdeğeri
- RAM: 4 GB
- Disk Alanı: 500 MB (kurulum için), 2 GB (veri için)
- Ekran Çözünürlüğü: 1366x768 piksel
- İnternet Bağlantısı: Bulut özellikleri için gerekli

**Önerilen Gereksinimler:**
- İşletim Sistemi: Windows 11 (64-bit)
- İşlemci: Intel Core i5 veya üzeri
- RAM: 8 GB veya üzeri
- Disk Alanı: 5 GB (SSD önerilir)
- Ekran Çözünürlüğü: 1920x1080 piksel veya üzeri
- İnternet Bağlantısı: 10 Mbps veya üzeri

---

## 2. KURULUM VE İLK YAPILANDIRMA

### Kurulum Adımları

1. **Kurulum Dosyasını İndirin**
   - `AYECPro_Setup_v3.2.0.exe` dosyasını çalıştırın
   - Güvenlik uyarısı çıkarsa "Daha fazla bilgi" → "Yine de çalıştır" seçeneğini kullanın

2. **Kurulum Sihirbazı**
   - Hoş geldiniz ekranında "İleri" butonuna tıklayın
   - Lisans sözleşmesini okuyup kabul edin
   - Kurulum yeri: `C:\Users\{KullanıcıAdı}\AppData\Local\AYECPro`
   - Masaüstü kısayolu oluşturma seçeneğini işaretleyin

3. **İlk Başlatma**
   - Kurulum tamamlandığında program otomatik başlar
   - Firewall uyarısı çıkarsa "Erişime izin ver" seçeneğini seçin

### İlk Giriş

**Varsayılan Kullanıcı Bilgileri:**
- Kullanıcı Adı: `admin`
- Şifre: `admin123`

> [!WARNING]
> Güvenlik için ilk girişten sonra mutlaka şifrenizi değiştirin!

### İlk Yapılandırma Adımları

#### 1. Firma Bilgilerini Güncelleyin

**Ayarlar → Firma Ayarları**
- Firma adı
- Logo (PNG/JPG formatında, önerilen boyut: 200x200 piksel)
- Adres bilgileri
- Telefon ve e-posta
- Vergi dairesi ve numarası

#### 2. E-posta (SMTP) Ayarlarını Yapın

**Ayarlar → E-Posta (SMTP)**
- SMTP Sunucu: `smtp.gmail.com` (Gmail için)
- Port: `587` (TLS için)
- Kullanıcı Adı: E-posta adresiniz
- Şifre: E-posta şifreniz veya uygulama şifresi

**Gmail İçin Uygulama Şifresi Oluşturma:**
1. Google Hesabı → Güvenlik
2. 2 Adımlı Doğrulama'yı etkinleştirin
3. Uygulama şifreleri → Mail → Windows Bilgisayar
4. Oluşturulan şifreyi kopyalayıp SMTP ayarlarına yapıştırın

#### 3. SMS Ayarlarını Yapın (Opsiyonel)

**Ayarlar → SMS Ayarları**
- SMS sağlayıcınızı seçin (NetGSM, İleti Merkezi, vb.)
- API bilgilerinizi girin
- Test mesajı göndererek ayarları doğrulayın

#### 4. Yönetici Şifresini Değiştirin

**Ayarlar → Güvenlik Ayarları**
- Mevcut şifre: `admin123`
- Yeni şifre: Güçlü bir şifre belirleyin
- Şifre onayı: Yeni şifreyi tekrar girin

---

## 3. KULLANICI YÖNETİMİ VE YETKİLENDİRME

### Yeni Kullanıcı Oluşturma

**Ayarlar → Kullanıcı Yönetimi → Yeni Kullanıcı**

1. Kullanıcı bilgilerini girin:
   - Kullanıcı adı (benzersiz olmalı)
   - Şifre (minimum 6 karakter)
   - E-posta adresi
   - Tam ad

2. Yetki grubu seçin:
   - **Yönetici:** Tüm yetkilere sahip
   - **Muhasebe:** Finans ve raporlama yetkileri
   - **Teknisyen:** Servis ve stok yetkileri
   - **Özel:** Özelleştirilmiş yetkiler

### Yetki Grupları Yönetimi

**Ayarlar → Yetkilendirme Grupları**

Her yetki grubu için sayfa erişim izinlerini ayarlayabilirsiniz:

- ✅ **Müşteriler:** Müşteri listesi ve detayları
- ✅ **Servisler:** Servis takip ekranı
- ✅ **Stok:** Envanter yönetimi
- ✅ **Finans:** Gelir/gider ve raporlar
- ✅ **Personel:** Personel yönetimi
- ✅ **Ayarlar:** Sistem ayarları
- ✅ **Raporlar:** Analiz ve raporlar

**Örnek Yetkilendirme:**

**Teknisyen Grubu:**
- Müşteriler: ✅ Görüntüleme, ❌ Silme
- Servisler: ✅ Tüm yetkiler
- Stok: ✅ Görüntüleme ve kullanım, ❌ Fiyat değiştirme
- Finans: ❌ Erişim yok
- Ayarlar: ❌ Erişim yok

---

## 4. MÜŞTERİ YÖNETİMİ

### Yeni Müşteri Ekleme

**Müşteriler → Yeni Müşteri**

**Temel Bilgiler:**
- Ad Soyad / Firma Adı
- Telefon (birden fazla eklenebilir)
- E-posta
- Adres
- Vergi No / TC Kimlik No

**Ek Bilgiler:**
- Müşteri tipi (Bireysel / Kurumsal)
- Müşteri grubu (VIP, Normal, vb.)
- Notlar ve özel bilgiler

**Hızlı Ekleme İpucu:**
> Sadece ad ve telefon bilgisi ile hızlı kayıt yapabilir, diğer bilgileri sonra tamamlayabilirsiniz.

### Müşteri Arama ve Filtreleme

**Arama Yöntemleri:**
- İsme göre arama
- Telefon numarasına göre arama
- E-posta adresine göre arama
- Gelişmiş filtreleme (müşteri tipi, grup, borç durumu)

**Klavye Kısayolları:**
- `Ctrl + F`: Hızlı arama
- `Ctrl + N`: Yeni müşteri
- `F5`: Listeyi yenile

### Müşteri Detay Ekranı

Bir müşteriye tıkladığınızda 360 derece görünüm açılır:

**Sekmeler:**
1. **Genel Bilgiler:** Temel müşteri bilgileri
2. **Servis Geçmişi:** Tüm servisler kronolojik sırada
3. **Finansal Durum:** Borç/alacak özeti
4. **Cihazlar:** Kayıtlı cihaz listesi
5. **Notlar:** Özel notlar ve hatırlatmalar

**Hızlı İşlemler:**
- 📞 Telefon et (sistem telefon uygulamasını açar)
- ✉️ E-posta gönder
- 📄 Servis oluştur
- 💰 Ödeme kaydet
- 🗑️ Müşteri sil (yönetici yetkisi gerekir)

---

## 5. SERVİS TAKİP SİSTEMİ

### Yeni Servis Kaydı Oluşturma

**Servisler → Yeni Servis**

**Adım 1: Müşteri Seçimi**
- Mevcut müşteri seçin veya yeni müşteri ekleyin
- Müşteri bilgileri otomatik doldurulur

**Adım 2: Cihaz Bilgileri**
- Cihaz tipi (Telefon, Tablet, Bilgisayar, Güvenlik Sistemi, vb.)
- Marka ve model
- Seri numarası / IMEI
- Şifre / Kilit bilgisi
- Aksesuar listesi (Şarj aleti, kılıf, vb.)

**Adım 3: Arıza Tanımı**
- Müşteri şikayeti (müşterinin anlattığı sorun)
- Teknisyen notu (tespit edilen arıza)
- Tahmini maliyet
- Tahmini teslim tarihi

**Adım 4: Fiyatlandırma**
- İşçilik ücreti
- Parça maliyeti (stoktan otomatik çekilir)
- Toplam tutar
- Ön ödeme (varsa)

### Servis Durumları

Servisler yaşam döngüsü boyunca farklı durumlardan geçer:

1. **🟡 Beklemede:** Yeni kayıt, işlem başlamadı
2. **🔵 İşlemde:** Teknisyen üzerinde çalışıyor
3. **🟢 Hazır:** Tamir tamamlandı, teslime hazır
4. **🟣 Teslim Edildi:** Müşteriye teslim edildi
5. **🔴 İptal:** Servis iptal edildi
6. **⚫ Arşiv:** Eski kayıtlar

### Servis Durumu Güncelleme

**Yöntem 1: Hızlı Güncelleme**
- Servis listesinde servise sağ tıklayın
- "Durum Değiştir" menüsünden yeni durumu seçin
- Otomatik SMS/E-posta gönderimi (ayarlarda aktifse)

**Yöntem 2: Detaylı Güncelleme**
- Servise çift tıklayın
- Detay ekranında "Durum" alanını değiştirin
- Not ekleyin
- "Kaydet" butonuna tıklayın

### Servis Wizard (Sihirbaz)

Hızlı servis işlemleri için Wizard kullanın:

**Servisler → Wizard**

1. Müşteri seç veya ekle
2. Cihaz bilgilerini gir
3. Hızlı arıza seçimi (önceden tanımlı şablonlar)
4. Otomatik fiyatlandırma
5. Tek tıkla kaydet

**Wizard Şablonları:**
- Ekran değişimi
- Batarya değişimi
- Yazılım güncelleme
- Kamera arızası
- Şarj soketi tamiri

---

## 6. STOK VE DEPO YÖNETİMİ

### Stok Kartı Oluşturma

**Stok → Yeni Parça**

**Temel Bilgiler:**
- Parça adı
- Kategori (Ekran, Batarya, Anakart, vb.)
- Stok kodu (benzersiz)
- Birim (Adet, Kutu, Metre, vb.)

**Fiyat Bilgileri:**
- Alış fiyatı
- Satış fiyatı
- KDV oranı
- Kar marjı (otomatik hesaplanır)

**Stok Bilgileri:**
- Mevcut stok miktarı
- Minimum stok seviyesi (kritik stok uyarısı için)
- Maksimum stok seviyesi
- Raf konumu

### Stok Hareketleri

**Stok Girişi:**
- Stok → Stok Hareketi → Giriş
- Parça seçin
- Miktar girin
- Tedarikçi bilgisi (opsiyonel)
- Fatura no ve tarih

**Stok Çıkışı:**
- Manuel çıkış: Stok → Stok Hareketi → Çıkış
- Otomatik çıkış: Serviste parça kullanıldığında

**Stok Sayımı:**
- Stok → Sayım Yap
- Fiziksel sayımı girin
- Sistem farkları gösterir
- Onaylayarak stok güncellenir

### Kritik Stok Uyarıları

Ana ekran panelinde kritik stok seviyesinin altındaki parçalar kırmızı renkte gösterilir:

**Uyarı Kriterleri:**
- Mevcut stok < Minimum stok seviyesi
- Stok = 0 (Tükenmiş)

**Hızlı Sipariş:**
- Kritik stok uyarısına tıklayın
- "Sipariş Oluştur" butonuna basın
- Tedarikçi ve miktar bilgisi otomatik doldurulur

### Çoklu Depo Yönetimi

**Ayarlar → Depolar**

Birden fazla depo tanımlayabilirsiniz:
- Ana depo
- Şube depoları
- Saha servisi araçları

**Depo Transferi:**
- Stok → Transfer
- Kaynak depo seçin
- Hedef depo seçin
- Parça ve miktar girin
- Transfer kaydı oluşturulur

---

## 7. PERSONEL TAKİBİ VE SAHA SERVİSİ

### Personel Kaydı

**Personel → Yeni Personel**

**Kişisel Bilgiler:**
- Ad Soyad
- TC Kimlik No
- Telefon
- E-posta
- Adres

**İş Bilgileri:**
- Pozisyon (Teknisyen, Muhasebe, Yönetici, vb.)
- Başlangıç tarihi
- Maaş bilgisi
- Çalışma saatleri

**Telegram Entegrasyonu:**
- Telegram kullanıcı adı
- Bot ile eşleştirme

### Telegram Bot Kurulumu

**Adım 1: Bot Oluşturma**
1. Telegram'da @BotFather'ı bulun
2. `/newbot` komutunu gönderin
3. Bot adı ve kullanıcı adı belirleyin
4. API Token'ı kopyalayın

**Adım 2: Uygulamaya Entegre Etme**
1. Ayarlar → Telegram Bot
2. API Token'ı yapıştırın
3. "Bağlantıyı Test Et" butonuna tıklayın
4. Bot aktif olduğunda ✅ işareti görünür

**Adım 3: Personel Eşleştirme**
1. Personel, Telegram'da botunuzu bulur
2. `/start` komutunu gönderir
3. Kullanıcı adını gönderir
4. Sistem otomatik eşleştirir

### Konum Takibi

**Personelin Konum Paylaşması:**
1. Telegram'da botunuza gidin
2. Konum paylaş butonuna tıklayın
3. "Canlı Konum" seçeneğini seçin (8 saat)
4. Konum otomatik güncellenir

**Harita Görünümü:**
- Saha Servis → Harita
- Tüm personel emoji ikonları ile gösterilir
- İkon renkler:
  - 🟢 Yeşil: Son 30 dakika içinde güncellenen
  - 🟡 Sarı: 30-60 dakika arası
  - 🔴 Kırmızı: 60 dakikadan eski

**İş Atama:**
- Haritada personele tıklayın
- "İş Ata" butonuna basın
- Müşteri ve servis bilgisi girin
- Personel Telegram'dan bildirim alır

---

## 8. FİNANS VE MUHASEBE

### Gelir Kaydı

**Finans → Gelir Ekle**

**Gelir Tipleri:**
- Servis geliri (otomatik oluşur)
- Parça satışı
- Danışmanlık hizmeti
- Diğer gelirler

**Bilgiler:**
- Tutar
- Kategori
- Açıklama
- Ödeme yöntemi (Nakit, Kredi Kartı, Havale)
- Fatura bilgisi

### Gider Kaydı

**Finans → Gider Ekle**

**Gider Kategorileri:**
- Kira
- Maaşlar
- Elektrik / Su / Doğalgaz
- Parça alımı
- Pazarlama
- Vergi ve harçlar
- Diğer giderler

### Banka Hesapları

**Ayarlar → Banka Bilgileri**

Birden fazla banka hesabı tanımlayın:
- Banka adı
- Şube
- Hesap no / IBAN
- Hesap tipi (Vadesiz, Vadeli, Kredi)
- Başlangıç bakiyesi

**Banka Hareketleri:**
- Para yatırma
- Para çekme
- Havale / EFT
- Otomatik bakiye güncelleme

### Finansal Raporlar

**Raporlar → Finans**

**Kar/Zarar Raporu:**
- Dönem seçin (Günlük, Haftalık, Aylık, Yıllık)
- Toplam gelir
- Toplam gider
- Net kar/zarar
- Grafik görünümü

**Kategori Bazlı Analiz:**
- Gelir kategorileri dağılımı (pasta grafik)
- Gider kategorileri dağılımı
- Trend analizi (çizgi grafik)

**Müşteri Bazlı Gelir:**
- En çok gelir getiren müşteriler
- Müşteri başına ortalama gelir
- Tekrar eden müşteri oranı

---

## 9. JARVIS AI ASİSTANI

### Jarvis Nedir?

Jarvis, Google Gemini AI altyapısını kullanarak işletme verilerinizi analiz eden ve sorularınızı yanıtlayan akıllı asistanınızdır.

### Jarvis Kurulumu

**Adım 1: Gemini API Anahtarı Alma**
1. https://makersuite.google.com/app/apikey adresine gidin
2. Google hesabınızla giriş yapın
3. "Create API Key" butonuna tıklayın
4. API anahtarını kopyalayın

**Adım 2: Uygulamaya Entegre Etme**
1. Ayarlar → Jarvis (Gemini) Ayarları
2. API anahtarını yapıştırın
3. "Bağlantıyı Test Et" butonuna tıklayın
4. Başarılı olduğunda ✅ işareti görünür

### Jarvis Kullanım Örnekleri

**SSS (Sık Sorulan Sorular):**
- Jarvis Asistan → SSS
- "Nasıl yeni müşteri eklerim?"
- "Stok nasıl güncellenir?"
- "Yedekleme nasıl yapılır?"

**Veri Analizi:**
- Jarvis Asistan → Veri Analizi
- "Bu ayki gelirimi göster"
- "En çok satan parçalar hangileri?"
- "Hangi müşterim en fazla servis getirdi?"
- "Kritik stok seviyesindeki parçalar neler?"

**Akıllı Öneriler:**
- "Bu ay kar marjımı nasıl artırabilirim?"
- "Hangi servislere öncelik vermeliyim?"
- "Stok optimizasyonu için önerilerin neler?"

### Jarvis Komutları

**Finansal Sorgular:**
- "Bugünkü gelirimi göster"
- "Bu ayki toplam giderlerim ne kadar?"
- "Geçen aya göre kar durumum nasıl?"

**Stok Sorguları:**
- "Kritik stok seviyesindeki parçalar"
- "En çok kullanılan parçalar"
- "Stok değeri ne kadar?"

**Müşteri Sorguları:**
- "Borçlu müşterilerim kimler?"
- "VIP müşterilerim kimler?"
- "Bu ay kaç yeni müşteri ekledim?"

**Servis Sorguları:**
- "Bekleyen servisler kaç tane?"
- "Teslim edilmemiş servisler"
- "Ortalama servis tamamlanma süresi"

---

## 10. YEDEKLEME VE VERİ GÜVENLİĞİ

### Otomatik Yerel Yedekleme

**Ayarlar → Yedekleme**

**Otomatik Yedekleme Ayarları:**
- Yedekleme sıklığı: Günlük (varsayılan: 02:00)
- Yedekleme konumu: `C:\Users\{Kullanıcı}\AppData\Local\AYECPro\backups`
- Saklama süresi: 30 gün (eski yedekler otomatik silinir)
- Maksimum yedek sayısı: 30 adet

**Manuel Yedekleme:**
- Yedekleme → Yedek Al
- Yedek adı girin (otomatik tarih eklenir)
- "Yedekle" butonuna tıklayın
- İşlem tamamlandığında bildirim alırsınız

### Uzak Sunucu Yedekleme

**Bulut Yedekleme Ayarları:**
- Sunucu IP: `85.117.239.60`
- Port: `8000`
- Otomatik yükleme: Her gece 02:30
- Şifreleme: AES-256

**Manuel Bulut Yedekleme:**
- Yedekleme → Sunucuya Gönder
- Yedek dosyası seçin
- "Gönder" butonuna tıklayın
- İlerleme çubuğu yükleme durumunu gösterir

### Yedekten Geri Yükleme

**Yerel Yedekten Geri Yükleme:**
1. Yedekleme → Geri Yükle
2. Yedek dosyası seçin
3. "Geri Yükle" butonuna tıklayın
4. Onay verin (mevcut veri silinecek!)
5. Program yeniden başlar

**Bulut Yedekten Geri Yükleme:**
1. Yedekleme → Sunucudan İndir
2. Mevcut yedekleri listeleyin
3. İstediğiniz yedeği seçin
4. İndirme tamamlandıktan sonra geri yükleyin

### Veri Güvenliği

**Şifreleme:**
- Veritabanı: SQLite encryption
- Yedek dosyaları: AES-256 şifreleme
- Ağ iletişimi: TLS/SSL

**Erişim Kontrolü:**
- Kullanıcı bazlı yetkilendirme
- Oturum zaman aşımı (30 dakika)
- Başarısız giriş denemesi kilitleme (5 deneme)

**Audit Log:**
- Tüm kritik işlemler kaydedilir
- Kim, ne zaman, ne yaptı
- Raporlar → Denetim Günlüğü

---

## 11. WEB VE MOBİL ARAYÜZ

### Web Arayüzü Erişimi

**Sunucu Başlatma:**
1. Masaüstü uygulamasını açın
2. Ayarlar → Sunucu Ayarları
3. "Sunucuyu Başlat" butonuna tıklayın
4. Yeşil ✅ işareti sunucunun aktif olduğunu gösterir

**Web Arayüzüne Bağlanma:**
- Yerel ağ: `http://localhost:8000`
- Aynı ağdaki diğer cihazlar: `http://{BilgisayarIP}:8000`
- Örnek: `http://192.168.1.100:8000`

**Firewall Ayarları:**
- İlk başlatmada Windows Firewall uyarısı çıkar
- "Erişime izin ver" seçeneğini seçin
- Manuel ayar: `ConfigureFirewall.cmd` dosyasını çalıştırın

### Web Arayüzü Özellikleri

**Erişilebilir Modüller:**
- 📊 Dashboard (Özet görünüm)
- 👥 Müşteri listesi
- 🔧 Servis takibi
- 📦 Stok görüntüleme
- 📅 Randevu takvimi
- 📈 Raporlar

**Responsive Tasarım:**
- Masaüstü bilgisayar
- Tablet
- Akıllı telefon

### Mobil Uygulama

**Android Kurulum:**
1. Web arayüzünde Ayarlar → İndirmeler
2. "Android APK İndir" butonuna tıklayın
3. APK dosyasını telefonunuza aktarın
4. "Bilinmeyen kaynaklardan yükleme" iznini verin
5. APK'yı yükleyin

**iOS Kurulum:**
- App Store'dan "AYEC Pro" uygulamasını indirin
- (Şu anda geliştirme aşamasında)

**Mobil Özellikler:**
- Müşteri ve servis görüntüleme
- Hızlı servis durumu güncelleme
- Fotoğraf çekme ve ekleme
- Konum paylaşımı
- Push bildirimleri

### Senkronizasyon

Tüm platformlar aynı veritabanını kullanır:
- Masaüstü uygulamasında yapılan değişiklik anında web'de görünür
- Web'de yapılan değişiklik masaüstünde güncellenir
- Mobil uygulama gerçek zamanlı senkronize olur

---

## 12. RAPORLAMA VE ANALİZ

### Hazır Raporlar

**Raporlar Menüsü:**

1. **Finansal Raporlar**
   - Kar/Zarar raporu
   - Gelir/Gider detayı
   - Kategori bazlı analiz
   - Banka hesap özeti

2. **Servis Raporları**
   - Servis durum özeti
   - Teknisyen performansı
   - Ortalama tamamlanma süresi
   - Müşteri memnuniyeti

3. **Stok Raporları**
   - Stok durum raporu
   - Kritik stok listesi
   - Stok hareket raporu
   - Parça karlılık analizi

4. **Müşteri Raporları**
   - Müşteri listesi
   - Borç/Alacak raporu
   - En değerli müşteriler
   - Yeni müşteri analizi

### Rapor Filtreleme

**Tarih Filtreleri:**
- Bugün
- Bu hafta
- Bu ay
- Bu yıl
- Özel tarih aralığı

**Diğer Filtreler:**
- Müşteri grubu
- Servis durumu
- Ödeme yöntemi
- Personel
- Kategori

### Rapor Dışa Aktarma

**Desteklenen Formatlar:**
- 📄 PDF (yazdırma için ideal)
- 📊 Excel (XLSX) (veri analizi için)
- 📋 CSV (diğer programlara aktarım)
- 🖼️ PNG (grafik görselleri)

**Dışa Aktarma:**
1. Raporu oluşturun
2. "Dışa Aktar" butonuna tıklayın
3. Format seçin
4. Kayıt konumunu belirleyin
5. Dosya otomatik oluşturulur

### Özel Raporlar

**Jarvis ile Özel Rapor:**
- Jarvis Asistan → Veri Analizi
- İstediğiniz raporu doğal dille tanımlayın
- Örnek: "Son 3 aydaki en karlı servislerim"
- Jarvis raporu oluşturur ve gösterir

---

## 13. ENTEGRASYONLAR

### E-posta Entegrasyonu

**Otomatik E-posta Gönderimi:**
- Servis durumu değişikliği
- Ödeme hatırlatması
- Randevu onayı
- Fatura gönderimi

**E-posta Şablonları:**
- Ayarlar → E-posta Şablonları
- Özelleştirilebilir içerik
- Değişkenler: {MusteriAdi}, {ServisNo}, {Tutar}, vb.

### SMS Entegrasyonu

**Desteklenen Sağlayıcılar:**
- NetGSM
- İleti Merkezi
- Mutlucell
- Jeton SMS

**SMS Şablonları:**
- Servis hazır bildirimi
- Ödeme hatırlatması
- Randevu hatırlatması

### Telegram Entegrasyonu

**Özellikler:**
- Personel konum takibi
- Anlık bildirimler
- İş atama
- Durum güncellemeleri

### Muhasebe Programı Entegrasyonu

**XML Dışa Aktarım:**
- Raporlar → Muhasebe Entegrasyonu
- Dönem seçin
- "XML Oluştur" butonuna tıklayın
- Muhasebe programınıza aktarın

**Desteklenen Formatlar:**
- Logo Tiger XML
- Mikro XML
- Genel XML

---

## 14. SORUN GİDERME

### Sık Karşılaşılan Sorunlar

#### Program Açılmıyor

**Çözüm 1: Yönetici Olarak Çalıştır**
1. Program kısayoluna sağ tıklayın
2. "Yönetici olarak çalıştır" seçeneğini seçin

**Çözüm 2: Veritabanı Onarımı**
1. `C:\Users\{Kullanıcı}\AppData\Local\AYECPro` klasörüne gidin
2. `repair_database.cmd` dosyasını çalıştırın

**Çözüm 3: Temiz Kurulum**
1. Programı kaldırın
2. `AppData\Local\AYECPro` klasörünü silin (yedek alın!)
3. Programı yeniden kurun

#### Türkçe Karakterler Bozuk Görünüyor

**Çözüm:**
1. `kokten_cozum.py` dosyasını çalıştırın
2. Veritabanı otomatik onarılır
3. Programı yeniden başlatın

#### Web Arayüzüne Bağlanamıyorum

**Kontrol Listesi:**
- ✅ Sunucu başlatıldı mı? (Ayarlar → Sunucu Ayarları)
- ✅ Firewall izni verildi mi?
- ✅ Doğru IP adresi kullanılıyor mu?
- ✅ Port 8000 başka program tarafından kullanılmıyor mu?

**Çözüm:**
1. `ConfigureFirewall.cmd` dosyasını yönetici olarak çalıştırın
2. Sunucuyu yeniden başlatın

#### Yedekleme Başarısız Oluyor

**Yerel Yedekleme:**
- Disk alanı yeterli mi kontrol edin
- `backups` klasörü yazma izni var mı kontrol edin

**Uzak Yedekleme:**
- İnternet bağlantısı aktif mi?
- Sunucu IP adresi doğru mu?
- Sunucu erişilebilir durumda mı?

#### Lisans Hatası

**Çözüm:**
1. Ayarlar → Lisans Durumu
2. HWID kodunu kopyalayın
3. gnnckrk@gmail.com adresine gönderin
4. Alacağınız aktivasyon kodunu girin

### Hata Raporlama

**Otomatik Hata Raporu:**
- Program çöktüğünde otomatik rapor oluşturulur
- `crash_reports.log` dosyasına kaydedilir
- Destek ekibine otomatik gönderilir (izin verirseniz)

**Manuel Hata Bildirimi:**
1. Yardım → Hata Bildir
2. Sorunu detaylı açıklayın
3. Ekran görüntüsü ekleyin
4. "Gönder" butonuna tıklayın

---

## 15. SSS (SIK SORULAN SORULAR)

### Genel Sorular

**S: Program kaç kullanıcıyı destekliyor?**
C: Sınırsız kullanıcı tanımlayabilirsiniz. Her kullanıcı için ayrı yetkilendirme yapılabilir.

**S: Veritabanı nerede saklanıyor?**
C: `C:\Users\{Kullanıcı}\AppData\Local\AYECPro\bulut_tech.db` konumunda.

**S: İnternet olmadan çalışır mı?**
C: Evet, temel özellikler internet olmadan çalışır. Bulut yedekleme, web arayüzü ve AI asistan için internet gereklidir.

**S: Mobil uygulama ücretsiz mi?**
C: Evet, mobil uygulama masaüstü lisansınıza dahildir.

### Lisans ve Güncelleme

**S: Lisans kaç bilgisayarda kullanılabilir?**
C: Standart lisans 1 bilgisayar içindir. Çoklu lisans için iletişime geçin.

**S: Güncellemeler otomatik mi?**
C: Evet, program başlangıcında otomatik güncelleme kontrolü yapar. İsterseniz manuel güncelleyebilirsiniz.

**S: Lisans süresi var mı?**
C: Hayır, bir kez satın aldığınızda ömür boyu kullanabilirsiniz.

### Teknik Sorular

**S: Hangi veritabanını kullanıyor?**
C: SQLite veritabanı kullanılmaktadır. Hafif, hızlı ve güvenilirdir.

**S: Maksimum müşteri/servis sayısı var mı?**
C: Hayır, sınırsız kayıt ekleyebilirsiniz. Performans bilgisayarınızın özelliklerine bağlıdır.

**S: Eski sistemden veri aktarımı yapılabilir mi?**
C: Evet, Excel formatında verilerinizi içe aktarabilirsiniz. Destek ekibi yardımcı olabilir.

### Destek

**S: Teknik destek nasıl alınır?**
C: 
- E-posta: gnnckrk@gmail.com
- Telefon: 0534 878 10 47
- Web: www.ayecpro.com
- Uygulama içi: Yardım → Destek Talebi

**S: Eğitim veriliyor mu?**
C: Evet, kurulum sonrası ücretsiz online eğitim verilmektedir. Talep için iletişime geçin.

---

## 📞 İLETİŞİM VE DESTEK

**AYEC Pro**

📧 E-posta: gnnckrk@gmail.com  
📱 Telefon: 0534 878 10 47  
🌐 Web: www.ayecpro.com  
🔄 Güncelleme: http://85.117.239.60:8000/update/version.txt

**Çalışma Saatleri:**
Pazartesi - Cuma: 09:00 - 18:00  
Cumartesi: 09:00 - 14:00  
Pazar: Kapalı

**Acil Destek:**
Kritik sorunlar için 7/24 e-posta desteği mevcuttur.

---

> [!NOTE]
> Bu kılavuz AYEC Pro v3.2.0 için hazırlanmıştır. Yeni sürümlerde özellikler değişebilir.

**Son Güncelleme:** 31 Ocak 2026  
**Hazırlayan:** AYEC Pro Geliştirme Ekibi  
© 2026 AYEC Pro - Tüm hakları saklıdır.
