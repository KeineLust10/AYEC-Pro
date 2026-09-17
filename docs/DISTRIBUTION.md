# AYEC Pro Dağıtım ve Güncelleme Rehberi

Bu belge, AYEC Pro uygulamasının yeni sürümlerini oluşturmak, paketlemek ve dağıtmak için gereken adımları içerir.

## 1. Versiyonlama ve Build (Sürüm Oluşturma)

Yeni bir versiyon yayınlamak için `scripts/release_manager.py` aracı kullanılır. Bu araç otomatik olarak:
1.  `version.txt` dosyasındaki versiyon numarasını günceller.
2.  `AYECPro_Modern_Setup.iss` dosyasındaki versiyonu günceller.
3.  `BuildAYECPro.ps1` betiğini çalıştırarak projeyi derler.
4.  `Releases/vX.Y.Z` klasörüne kurulum dosyasını ve `version.json` manifestosunu oluşturur.

### Kullanım

Terminali açın ve proje ana dizininde şu komutu çalıştırın:

```powershell
# Yama (Patch) Güncellemesi (örn: 1.0.0 -> 1.0.1)
python scripts/release_manager.py patch "Küçük hata düzeltmeleri"

# Minör Güncelleme (örn: 1.0.0 -> 1.1.0)
python scripts/release_manager.py minor "Yeni özellikler eklendi"

# Major Güncelleme (örn: 1.0.0 -> 2.0.0)
python scripts/release_manager.py major "Büyük sistem değişikliği"
```

## 2. Sunucuya Yükleme

Build işlemi tamamlandıktan sonra, `Releases/vX.Y.Z/` klasöründeki dosyaları sunucuya yüklemeniz gerekir.

**Sunucu Bilgileri:**
- **URL**: `http://85.117.239.60:8000`
- **Hedef Klasör**: `/update` (veya `Releases` klasör yapısına uygun sanal dizin)

**Yüklenmesi Gereken Dosyalar:**
1.  `setup.exe` (İndirilecek asıl dosya)
2.  `version.json` (Uygulamanın kontrol ettiği manifest dosyası)

> [!IMPORTANT]
> `version.json` dosyasındaki `url` alanının, `setup.exe` dosyasının sunucudaki *gerçek* erişim adresiyle eşleştiğinden emin olun. Standart olarak `http://85.117.239.60:8000/Releases/vX.Y.Z/setup.exe` veya sabit bir `/update/setup.exe` adresi kullanabilirsiniz.

## 3. Güncelleme Mekanizması Nasıl Çalışır?

1.  Uygulama açılışta `src/utils/startup_updater.py` çalışır.
2.  Sunucudaki `version.json` dosyasını kontrol eder.
3.  Eğer sunucudaki versiyon, yerel versiyondan (version.txt) yüksekse:
    -   Kullanıcıya "Yeni Sürüm Bulundu" ekranı gösterilir (Release notları ile).
    -   Kullanıcı onaylamasa bile (Splash ekranı) indirme başlar.
4.  İndirme tamamlanınca uygulama kapanır ve `Bulut_Update.exe` (yeni kurulum) başlatılır.

## 4. Sorun Giderme

-   **Güncelleme Görünmüyor:**
    -   Sunucudaki `version.json` dosyasının erişilebilir olduğunu tarayıcıdan kontrol edin.
    -   Yerel `version.txt` dosyasının sunucudakinden daha düşük olduğundan emin olun.
-   **İndirme Başarısız:**
    -   `version.json` içindeki `url` adresinin doğru olduğunu teyit edin.
    -   Windows güvenlik duvarının engelleyip engellemediğini kontrol edin.

## 5. Manuel Build (Opsiyonel)

Eğer `release_manager.py` kullanmadan manuel build almak isterseniz:

1.  `AYECPro_App.spec` ile PyInstaller çalıştırın.
2.  Inno Setup ile `.iss` dosyasını derleyin.
3.  `version.txt` dosyasını manuel güncelleyin.
