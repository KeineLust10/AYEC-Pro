# AYEC Pro Web — 85.117.239.60 Windows Server kurulumu

## Mobil kamera notu

Mobil kameradan barkod okuma için HTTPS zorunludur. Tarayıcılar kamera iznini
yalnızca güvenli bağlamda (HTTPS veya localhost) verir; `http://85.117.239.60`
adresinde barkod dialogu kamera yerine elle barkod girişi sunar.

AYEC arka ucu yalnızca `127.0.0.1:8501` üzerinde çalışır. IIS 10, dışarıdan gelen
port 80 isteklerini bu arka uca yönlendirir:

```text
http://85.117.239.60
```

## Taşınacak tek dosya

Geliştirme bilgisayarında proje klasöründe çalıştırın:

```powershell
Copy the complete `Web_Arayuzu` directory to the server.
```

Komut varsayılan olarak kullanıcı hesaplarını ve kullanıcı tarafından girilmiş
müşteri, stok, finans, servis, randevu ve teklif verilerini temizler; masaüstü
şemasını ve fabrika kataloglarını korur. Üretilen paket:

```text
C:\Users\yedek\Desktop\Masaustu\AYEC-Pro-Web-Server-85.117.239.60.zip
```

ZIP içindeki `Web_Arayuzu` klasörünü sunucuda örneğin
`C:\AYEC-Pro\Web_Arayuzu` konumuna çıkarın. Pakette şunlar bulunur:

- İlk açılış sihirbazını gösterecek temiz `data\ayecpro.db`
- Web arayüzü, masaüstü ortak motoru ve üç proforma şablonu
- Python bağımlılık listeleri ve tek komutluk kurulum betikleri
- EasyOCR ve PaddleOCR modelleri (`ocr-models`); ilk OCR'da tekrar indirme gerekmez

Canlı veriyi bilinçli olarak taşımak gerekirse:

```powershell
Keep the existing `data` and tenant data directories when migrating live data.
```

## One-click setup

Extract the ZIP and double-click `AYEC_PRO_TEK_TIK_BASLAT.cmd`. On a new server it
requests administrator permission and runs the Python/IIS installation, scheduled
task and port 80 proxy configuration automatically. On later runs it starts the
backend with the server environment, starts IIS when available, and opens
`http://85.117.239.60`.

## Tek komutla IIS kurulumu

Sunucuya Uzak Masaüstü ile bağlanın, PowerShell'i **Yönetici olarak** açın:

```powershell
cd C:\AYEC-Pro\Web_Arayuzu
Set-ExecutionPolicy -Scope Process Bypass
.\server-windows-install.ps1
```

Kurulumdan önce mevcut SQLite dosyası `tools/repair_database.py` ile kontrol edilir.
Eksik masaüstü tabloları (örneğin `customers`) veriler silinmeden tamamlanır ve
`backups/pre-schema-repair-*.db` altında otomatik yedek alınır.

Betik:

- Gerekirse Python 3.12.10'u resmi Python adresinden sessizce kurar.
- IIS URL Rewrite 2 ve Application Request Routing 3 modüllerini kurar.
- PDF, Excel/DOCX, EasyOCR ve masaüstüyle aynı PaddleOCR 2.x ortamını `.venv` içine kurar.
- AYEC'i Windows açılışında başlayan `AYEC Pro Web` görevi olarak çalıştırır.
- IIS port 80 kök adresini `127.0.0.1:8501` arka ucuna yönlendirir.
- Güvenlik duvarında yalnızca HTTP port 80 kuralını ekler.
- IIS anonim geçişini açar; gerçek erişimi AYEC kurulum ve giriş ekranı korur.

İlk ziyarette dört adımlı kurulum sihirbazı açılır. Firma, sektör, yönetici ve SMTP
bilgileri tamamlandıktan sonra giriş ekranına dönülür. Kayıt e-postaları hem üyeye
hem yönetici bildirim adresine ayrı ayrı gönderilir.

Python önceden özel bir konumda kuruluysa:

```powershell
.\server-windows-install.ps1 -Python "C:\Python312\python.exe"
```

## Sunucu gereksinimleri

- Windows Server 2019/2022 veya uyumlu sürüm
- Yönetici yetkisi ve kurulum sırasında internet erişimi
- En az 8 GB boş disk
- İsteğe bağlı Tesseract yedeği için Windows Tesseract ve Türkçe dil paketi

EasyOCR/PaddleOCR model dosyaları pakettedir. Tesseract ayrı bir Windows programıdır; gerekirse
`TESSERACT_CMD` ortam değişkeni tam `tesseract.exe` yolu olarak tanımlanmalıdır.

## Kontrol

Sunucunun PowerShell penceresinde:

```powershell
Invoke-RestMethod http://127.0.0.1:8501/api/desktop/health
Get-ScheduledTask -TaskName "AYEC Pro Web"
Get-Content .\logs\server.error.log -Tail 100
```

Başka bir bilgisayarda `http://85.117.239.60` adresini açın.

## Veriler ve yedekler

- `data\ayecpro.db`: firma kayıt defteri ve eski tekil kurulumun geri dönüş kopyasıdır; işlem kayıtları burada tutulmaz.
- `Kullanıcılar\<Firma Adı>.db`: müşteriler, stok, servis, finans, ayarlar ve firma içi kullanıcı/yetkilerin gerçek çalışma veritabanıdır.
- `web\uploads`: firma logosu ve yüklemeler
- `backups`: Wipe All ve manuel yedekler

İlk eski veritabanı erişiminde `data\ayecpro.db` silinmeden `Kullanıcılar\<Firma Adı>.db` dosyasına taşınır.
Bu iki klasörü ve `backups` klasörünü günlük yedekleyin. Çalışan SQLite dosyasını düz kopyalamak yerine
`tools\backup_database.py` kullanın.

## HTTPS notu

Ham IP üzerinde giriş, oturum ve uygulama içi toast uyarıları çalışır. Üretim için
bir alan adını bu IP'ye yönlendirip IIS'e geçerli TLS sertifikası bağlamak önerilir.
HTTPS etkinleştirildiğinde oturum çerezi otomatik olarak `Secure` işaretlenir ve
tarayıcının işletim sistemi bildirim API'si de kullanılabilir.

## Firma veritabanları ve masaüstü senkronizasyonu

- `AYEC_TENANT_DIR` (Windows başlatıcısında varsayılan: `Kullanıcılar`) altında her firma için
  `Firma Adı.db` oluşturulur. `data\ayecpro.db` firma kayıtlarının merkez kayıt defteri ve eski
  kurulum için geri dönüş yedeğidir; ilk istek geldiğinde eski veri otomatik kopyalanır.
- Oturum çerezi firma kimliğini taşır; stok, servis, müşteri, finans ve ayarlar her firmada yalnızca
  kendi SQLite dosyasından okunur. Firma içi kullanıcılar aynı dosyadaki `users` tablosuna eklenir.
- Masaüstü istemcisi `src\utils\web_sync_client.py` içindeki `WebSyncClient` ile giriş yapıp
  `/api/sync/manifest`, `/api/sync/pull` ve `/api/sync/push` uçlarını kullanabilir. Hazır komut:
  `python tools\desktop_sync.py --url http://85.117.239.60 --db C:\AYEC\ayecpro.db --user kullanici`.
- Çakışmalarda `updated_at` daha yeni olan kayıt korunur; gönderimler `sync_events` ile idempotent
  tutulur. Sunucudaki `Kullanıcılar`, `data`, `backups` ve `web\uploads` klasörleri birlikte yedeklenmelidir.

### Masaüstü istemcisinde çalışma akışı

Masaüstü uygulaması açılışta (ve istersen kapanıştan önce) aşağıdaki yardımcıyı çağırabilir. İlk çağrıda
sunucudan firma verileri alınır; sonraki çağrılarda yalnızca değişen satırlar gönderilir/alınır.

Güncel masaüstü paketinde açılış senkronizasyonu isteğe bağlı olarak hazırdır. Masaüstünde
manuel girişten sonra (otomatik yerel giriş değil) şu ortam değişkenini tanımlayın:

```powershell
$env:AYEC_WEB_SYNC_URL = "https://firma-adresi"
```

Uygulama arka planda giriş yapıp aynı yerel SQLite dosyasını senkronize eder. İnternet yoksa
masaüstü açılışı durmaz; hata günlük dosyasına yazılır ve sonraki açılışta yeniden denenir.

```python
from src.utils.web_sync_client import WebSyncClient

client = WebSyncClient("https://firma-adresi", verify_tls=True)
client.login(kullanici_adi, parola, remember=True)
client.sync_sqlite("C:/AYEC/ayecpro.db")
```

Ham IP ile geçici testte `http://85.117.239.60` kullanılabilir; üretimde parola ve oturum
verisi için HTTPS zorunlu tutulmalıdır. Masaüstü uygulamasına henüz otomatik giriş bilgisi
eklenmemişse hazır CLI ile tek çevrim test edilebilir:

```powershell
python tools\desktop_sync.py --url http://85.117.239.60 --db C:\AYEC\ayecpro.db --user kullanici
```

İsim aynı olan firmalarda `/api/auth/status` çıktısındaki `tenant_id` değerini ayrıca
`--tenant <tenant_id>` olarak verin.

## Desktop installer download link

The purple A mark on the web login screen downloads the desktop installer from:

`/downloads/AYECPro_Setup_v2.0.4_Final.exe`

On the server, create a `downloads` directory next to the web static directory and copy
`AYECPro_Setup_v2.0.4_Final.exe` into it. The web server must expose that directory at the
`/downloads` URL without requiring an authenticated session. For the bundled Python server,
the expected layout is:

```text
Web_Arayuzu/
  web/
  downloads/
    AYECPro_Setup_v2.0.4_Final.exe
```

After copying the file, open `/downloads/AYECPro_Setup_v2.0.4_Final.exe` in a browser to
verify that the download starts before publishing the web ZIP.

Additional program cards use these exact server file names:

```text
downloads/AnyDesk.exe
downloads/AYECPro_Setup_v2.0.4_Final.exe
downloads/SmartPSS.exe
downloads/ConfigTools.exe
```

If a program is not ready yet, keep its card file in the same path or replace the card URL
in `web/app.js` inside the `authPrograms` list.
