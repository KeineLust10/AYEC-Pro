# AYEC Pro Devam Notu

Bu dosya, AYEC Pro Admin Konsol ve Teknik Servis gelistirme senaryosunun
22.09.2026 tarihindeki durumunu ve sonraki devam adimlarini kaydeder.

## Ana hedef

Admin Konsol uygulamasini Super Admin yetkileri olan profesyonel bir merkez
haline getirmek. Firma ve musteri bilgileri, lisanslar, cihazlar, yedekler,
hata kayitlari, guncellemeler, e-posta islemleri, konumlar ve destek islemleri
tek merkezden yonetilecek.

Teknik Servis tarafinda merkezi lisans, yedekleme, guncelleme, otomatik
guncelleme kontrolu, lisans suresi kilidi, konum bildirimi ve Google kayit
akisi birlikte calisacak.

## Gecici parola davranisi

Admin Konsol icindeki "E-posta ile Gecici Parola" islemi:

1. Her talepte rastgele yeni bir gecici parola uretir.
2. Parolayi veritabanina duz metin olarak kaydetmez; hash olarak saklar.
3. Parolayi musterinin kayitli e-posta adresine gonderir.
4. Musteri ilk giriste yeni kalici parola belirlemek zorundadir.
5. E-posta gonderilemezse eski parola korunur ve gecici parola islemi uygulanmaz.
6. Gecici parola Admin Konsol ekraninda ve API cevabinda gosterilmez.

Bu nedenle tek bir ortak veya sabit "gecici parola" yoktur. Parola, islem
aninda e-posta ile olusturulur.

## Yapilan islemler

- Admin customer 360 endpoint ve Admin Konsol customer 360 ekrani eklendi.
- Firma, kullanici, lisans, yedek, hata, audit ve canli durum ozeti baglandi.
- Gecici parola e-posta akisi ve zorunlu ilk parola degistirme eklendi.
- SMTP basarisizliginda transaction rollback ve eski parola korumasi eklendi.
- Guncelleme indirildikten sonra kalici hazir durumu eklendi.
- Guncelleme hazir dialogunda "Simdi guncelle" ve "Daha sonra guncelle"
  secenekleri eklendi.
- Daha sonra secilirse sonraki program acilislarinda uyari tekrarlanir.
- Lisans kilidi, firma bazli yedek izolasyonu ve mevcut Super Admin akisinin
  testleri yapildi.
- Google nonce, kayit ve subject login testleri yapildi.
- Super Admin yetki siniri ve guncelleme dagitim kuyrugu icin regresyon testi
  eklendi; vendor kimligi platform kapsaminda, musteri yoneticisi kapsam disinda
  dogrulandi.
- Web sunucu paketi, mobil paket, Teknik Servis Setup ve Admin Konsol build'i
  olusturuldu.
- Son test verisi aktif masaustu veritabaninda kontrol edildi.

## Paketler

- `Setup_Output/AYECPro_Admin_Console.exe`
- `Setup_Output/AYECPro_Setup_v2.0.4_Final.exe`
- `Setup_Output/AYECPro_Web_Server_20260922_124041.zip`
- `Setup_Output/AYECPro_Mobile_20260922_124041.zip`
- `Setup_Output/AYECPro_Release_Manifest_20260922_124041.json`

## Aktif test verisi

Aktif masaustu veritabani:

`C:\Users\yedek\AppData\Local\AYEC Pro\Data\ayecpro.db`

Kontrol edilen kayitlar:

- 25 customer
- 90 parts
- 5 personnel
- 15 devices
- 30 used_parts
- 10 offers
- 8 appointments
- 8 projects
- 3 bank_accounts
- 6 checks_notes
- 10 stock_movements
- SQLite integrity_check: ok

Kurulum yeni kullanici verisini ezmez. Uygulama ilk acilista kullaniciya ait
AppData veritabanini kullanir ve mevcut veriyi korur.

## Test sonucu

- Admin ve lisans/yedek akis testleri: 32 passed
- Vendor management center testleri: 15 passed
- Gercek yerel HTTP route smoke testi: 1 passed; Admin login, Customer 360,
  backup listeleme, restore kuyrugu ve update dagitimi birlikte dogrulandi.
- Masaustu senkron istemci testi: `deploy_update` komutunun tuketilip update
  kontrolune iletildigi ve komutun basarili olarak tamamlandigi dogrulandi.
- Ilk senkron konum testi: yerel kurulumdaki adres/enlem/boylam bilgilerinin
  otomatik provisioning payload icine alindigi dogrulandi.
- Update ve secure update testleri: 8 passed
- Auth mail testi: setup 2/2, registration 2/2, integrity ok
- Google auth testi: nonce ok, registration ok, subject login ok
- Son kapsamli regresyon seti: 45 passed
- ASCII diff guard: ok
- Mojibake guard: ok
- Web JavaScript syntax check: ok

## Canli ortamda kalan dogrulamalar

### 22.09.2026 devam kaniti

- Salt-okunur canli resilience probe basarili: `https://lisans.ayecpro.com`
  TLS 1.3, `lisans.ayecpro.com` sertifikasi ve 14.12.2026 sertifika bitisi
  dogrulandi.
- Canli lisans katalogu HTTP 200 dondu; aylik, 6 aylik, 1, 2 ve 3 yillik
  planlar okundu.
- Mutasyonlu canli akis kimlik bilgileri bulunmadigi icin calistirilmadi;
  probe gerekli degiskenleri yazdirmadan raporladi.
- Windows gecici SQLite dosyasi temizleme testi duzeltildi; resilience probe
  guvenlik testleri 3/3 gecti.
- Gecici parola akisi 30 dakikalik son kullanma zamaniyla tamamlandi; sure
  veritabaninda saklaniyor, suresi dolan parola reddediliyor ve kalici parola
  belirlendiginde alan temizleniyor. Ilgili merkezi regresyon seti 44 test
  olarak gecti.
- Mojibake guard ve ASCII diff guard basarili.

Asagidaki maddeler yetkili canli ortam erisimi ile tamamlanmalidir:

1. Gercek SMTP ile gecici parola e-postasinin teslimi.
2. Gercek lisans aktivasyonu ve suresi dolmus lisansin kilitlenmesi.
3. Admin Konsol ile canli firma yedegi listeleme, indirme ve restore.
4. Gercek istemcide guncelleme indirme ve kullanici onayiyla kurulum.
5. Ilk kurulum konum bilgisinin canli haritada gorunmesi.
6. Google OAuth'un production client bilgileriyle gercek hesap testi.

## Devam sirasi

1. Bu dosyayi ve `docs/AYEC_ECOSYSTEM_RULES.md` dosyasini oku.
2. `git status --short` ile mevcut degisiklikleri koru; reset veya toplu silme
   yapma.
3. Canli sunucu erisimini ve kimlik bilgilerini kontrol et; gizli degerleri
   loglama.
4. Yukaridaki canli dogrulamalari sirayla yap.
5. Her canli adimdan sonra ilgili test ve log kanitini bu dosyaya ekle.
6. Tum canli kanitlar tamamlanmadan hedefi tamamlandi olarak isaretleme.

## Onemli dosyalar

- `Web_Arayuzu/Main.py`
- `Web_Arayuzu/web/app.js`
- `Admin_Konsol/api_client.py`
- `Admin_Konsol/main_window.py`
- `Admin_Konsol/pages/companies.py`
- `Admin_Konsol/pages/customer_360.py`
- `src/utils/update_manager.py`
- `src/utils/secure_update.py`
- `tests/test_admin_temporary_password.py`
