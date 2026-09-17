# 🚀 AYEC Pro - Teknik Kurulum Rehberi

Bu belge, **AYEC Pro Teknik Servis Yönetim Yazılımı**'nın kurulumu, yapılandırılması ve yayına alınması için gerekli teknik adımları içerir.

---

## 📦 1. Paket İçeriği ve Dosya Yapısı

Uygulamanın sağlıklı çalışması için ana dizinde aşağıdaki yapı korunmalıdır:

```text
AYEC Pro/
├── AYECPro.exe          # Ana uygulama dosyası
├── ayecpro.db             # Veritabanı dosyası (SQLite)
├── assets/                   # Görsel kaynaklar (Logolar, ikonlar)
├── fonts/                    # Uygulama fontları
├── web_interface/            # Dashboard ve analiz arayüz dosyaları
├── backups/                  # Otomatik ve manuel yedekleme klasörü
└── logs/                     # Hata ve sistem kayıtları
```

---

## 🛠️ 2. Sistem Gereksinimleri

*   **İşletim Sistemi:** Windows 10 veya Windows 11 (64-bit önerilir).
*   **İşlemci:** 2.0 GHz veya üzeri (Çift çekirdek minimum).
*   **Bellek (RAM):** 4 GB (8 GB önerilir).
*   **Disk Alanı:** Uygulama için 200 MB + Veritabanı büyümesi için ek alan.
*   **İnternet Erişimi:** Gemini AI özellikleri, harita entegrasyonu ve lisans kontrolü için gereklidir.

---

## ⚙️ 3. İlk Kurulum ve Yapılandırma

### Step 1: Dosyaların Konumlandırılması
1. Size iletilen klasörü `C:\Program Files\AYEC Pro` veya istediğiniz bir dizine kopyalayın.
2. `AYECPro.exe` dosyasına sağ tıklayarak "Masaüstüne Kısayol Oluştur" seçeneğini kullanın.

### Step 2: Veritabanı Bağlantısı
Uygulama ilk kez çalıştırıldığında, aynı dizinde `ayecpro.db` dosyasını arayacaktır. Eğer dosya mevcut değilse, sistem boş bir şablon oluşturacaktır. Mevcut verilerinizi korumak için `.db` dosyasının EXE ile yan yana olduğundan emin olun.

### Step 3: Jarvis (Yapay Zeka) Aktivasyonu
Uygulama içindeki akıllı asistan özelliklerini kullanmak için:
1. **Ayarlar > AI Asistan** sekmesine gidin.
2. [Google AI Studio](https://aistudio.google.com/) üzerinden aldığınız **Gemini API Key**'i ilgili alana girin.
3. "Bağlantıyı Test Et" butonuna tıklayarak aktivasyonu tamamlayın.

---

## 📧 4. E-Posta (SMTP) Yapılandırması

Müşterilere bilgilendirme e-postaları göndermek için:
1. **Ayarlar > E-Posta** sekmesine gidin.
2. SMTP Sunucusu (örn: smtp.gmail.com), Port, Kullanıcı Adı ve Şifre bilgilerini girin.
3. TLS/SSL seçeneğini sunucunuza göre işaretleyin.

---

## 🔑 5. Lisanslama ve Aktivasyon

1. Uygulama açılışında karşınıza gelen **Kayıt Formunu** doldurun.
2. Şirket verileriniz ve donanım kimliğiniz (HWID) üzerinden 7 günlük deneme süreniz başlayacaktır.
3. Kalıcı aktivasyon için **Teknik Destek > Lisans Talebi** butonu üzerinden talebinizi iletebilirsiniz.

---

## 🛡️ 6. Güvenlik ve Yedekleme

*   **Otomatik Yedekleme:** Uygulama her kapandığında `backups/` klasörüne tarih-saat damgalı bir yedek alır.
*   **Veri Güvenliği:** `ayecpro.db` dosyasını düzenli olarak harici bir diske veya bulut depolama alanına yedeklemeniz önerilir.
*   **Uygulama Kilidi:** İzinsiz erişimi engellemek için **Ayarlar > Güvenlik** kısmından bir giriş şifresi belirleyebilirsiniz.

---

## 🆘 Destek ve İletişim

Herhangi bir kurulum sorunu yaşamanız durumunda:
- **E-posta:** gnnckrk@gmail.com
- **Destek Paneli:** Uygulama içindeki "Teknik Destek" sekmesi.

---
**AYEC Pro** - *Verimliliğin AYEC Pro.*

