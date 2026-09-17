# AYEC Pro Exception-Pass Denetim Raporu

Tarih: 2026-07-26

## 1. Amac

Bu rapor, test kodlari haric AYEC Pro kaynak agacindaki yalnizca `pass`
ile sonlanan `except` bloklarini inceler.

Raporun sorulari:

- Blok gercek bir hatayi gizliyor mu?
- Blok kaldirilirsa veya `pass` silinirse ne olur?
- Blok korunmali mi, daraltilmali mi, loglanmali mi?
- Veri, finans, guvenlik, senkronizasyon veya arayuz tutarliligi riski var mi?
- Temizlik hangi sirayla ve hangi test kapilariyla yapilmali?

Bu calismada uygulama kodu degistirilmemistir. Yalnizca statik denetim ve
etki analizi yapilmistir.

## 2. Kapsam ve Yontem

Taranan ana calisma alanlari:

- `Main.py`
- `server_main.py`
- `src/`
- `backend/`
- `Web_Arayuzu/`
- `Admin_Konsol/`
- `bulut_modules/`
- `core/`
- `interfaces/`
- `plugins/`
- `web_api/`

Haric tutulan alanlar:

- `tests/` ve `test/`
- `venv/` ve `.venv/`
- `build/` ve `dist/`
- yedek, release, setup ciktilari
- `node_modules/`
- uretilmis cache dosyalari

Yontem:

1. Python AST ile yalnizca `pass` iceren `except` govdeleri bulundu.
2. Genis yakalama ile belirli hata turu yakalama ayrildi.
3. Kritik akislardaki bloklar dosya ve islev baglaminda incelendi.
4. Silme etkisi ile guvenli temizlik etkisi ayri degerlendirildi.
5. Calisma zamaninda kullanilma olasiligi import ve giris noktalarina gore
   kontrol edildi.

## 3. Sayisal Ozet

| Olcum | Sonuc |
|---|---:|
| Incelenen Python dosyasi adayi | 1143 |
| AST ile basariyla ayrisan dosya | 871 |
| Ayrisma hatasi veren dosya | 272 |
| Yalnizca `pass` iceren `except` blogu | 464 |
| Genis yakalama (`Exception`, bare `except`, `BaseException`) | 432 |
| Belirli hata turu yakalayan blok | 32 |

Kok dizin dagilimi:

| Alan | Blok |
|---|---:|
| `src/` | 363 |
| `Web_Arayuzu/` | 49 |
| `bulut_modules/` | 42 |
| `server_main.py` | 3 |
| `backend/` | 3 |
| `Admin_Konsol/` | 3 |
| `Main.py` | 1 |

En yogun dosyalar:

| Dosya | Blok |
|---|---:|
| `bulut_modules/database.py` | 23 |
| `src/ui/widgets/side_menu.py` | 14 |
| `Web_Arayuzu/Main.py` | 10 |
| `src/utils/asistan_motoru.py` | 9 |
| `src/db/mixins/database_legacy_part4_mixin.py` | 9 |
| `src/db/mixins/finance_mixin.py` | 9 |
| `src/utils/_sip_ocr.py` | 8 |
| `src/ui/dialogs/customer_360_dialog.py` | 8 |
| `src/ui/dialogs/_tp_operations.py` | 8 |
| `src/ui/modern_login_window.py` | 7 |
| `src/db/mixins/database_legacy_part3_mixin.py` | 7 |
| `src/ui/mixins/_main_window_base_mixin.py` | 7 |
| `src/db/mixins/device_mixin.py` | 6 |
| `src/db/mixins/project_mixin.py` | 6 |

## 4. Yonetici Ozeti

Toplu olarak `except: pass` bloklarini silmek dogru degildir.

Uc ayri durum vardir:

1. Hata gizleyen kritik bloklar:
   Veri kaydi basarili gorunurken finans, bakiye, yedek, senkronizasyon veya
   yetki sonucu eksik kalabilir. Bunlar `pass` olarak kalmamalidir.

2. Kontrollu gerileme bloklari:
   Tema, TTS, OCR, pencere kapatma veya opsiyonel kutuphane gibi alanlarda
   ana uygulamanin calismaya devam etmesini saglar. Bunlar silinmemeli; hata
   turu daraltilmali ve uygun seviyede loglanmalidir.

3. Olu kod veya eski moduller:
   Bir kismi ayni adli ikinci metot tarafindan ezilmektedir ya da eski bir
   modul agacinda bulunmaktadir. Yalnizca import grafi ve regresyon testi ile
   kullanilmadigi kanitlandiktan sonra tum blok veya modul silinebilir.

En onemli sonuc:

- `pass` silmek yerine hata sozlesmesi kurulmalidir.
- Veri degistiren islemler atomik olmalidir.
- Basarili sonuc, alt mali veya senkronizasyon islemi basarisizsa
  kosulsuz donmemelidir.
- Arayuz yenileme hatasi veri kaydini geri almamali, fakat gorunur ve
  yeniden denenebilir olmalidir.

## 5. Kritik Bulgular

### K-01 - Guvenlik dogrulamasi hata halinde zayif parolaya dusuyor

Konum:

- `src/ui/dialogs/security_confirm_dialog.py:133`
- `src/ui/dialogs/security_confirm_dialog.py:141`
- `src/ui/dialogs/security_confirm_dialog.py:149`

Mevcut davranis:

- Normal yetki dogrulamasi hata verirse hata yutuluyor.
- Master anahtar dogrulamasi hata verirse hata yutuluyor.
- Ardindan `admin_pass` ayari okunuyor.
- Ayar yoksa varsayilan parola `admin123` kabul ediliyor.

Risk:

- Kritik islemler kimlik dogrulama altyapisi bozukken statik bir parola ile
  acilabilir.
- Hata, denetim kaydina dusmez.
- Guvenli tarafta kapanma yerine guvensiz tarafta acilma olusur.

`pass` silinirse:

- Ilk dogrulama hatasinda diyalog kapanabilir veya uygulama hata verebilir.
- Guvenlik acigi azalabilir, fakat kullaniciya kontrollu hata gosterilmez.
- Yalnizca `pass` silmek yeterli ve temiz bir cozum degildir.

Guvenli temizlik:

- Varsayilan `admin123` destegini kaldir.
- Dogrulama altyapisi hata verirse islemi reddet.
- Hata turlerini daralt.
- Guvenlik audit kaydi olustur.
- Kurtarma icin tek kullanimlik, sureli ve hash saklanan sifre mekanizmasi
  kullan.

Oncelik: P0

### K-02 - Canli veritabani geri yukleme basarisizken basarili donuyor

Konum:

- `server_main.py:873`
- `server_main.py:878`
- `server_main.py:886`
- `server_main.py:888`

Mevcut davranis:

- Eski `-wal` ve `-shm` dosyalari silinemezse hata yutuluyor.
- Canli DB kopyalama basarisiz olsa bile API `success: true` donebiliyor.

Risk:

- Kullanici geri yuklemenin tamamlandigini sanir.
- Eski WAL yeni DB uzerinde tekrar oynatilarak veri bozulmasi yaratabilir.
- Kilitli veya yari degismis canli DB durumu olusabilir.

`pass` silinirse:

- Dosya silme hatasi yukariya cikar ve geri yukleme durur.
- Bu, yanlis basari donmekten daha guvenlidir; ancak acik baglantilar
  kapatilmadan yapildigi icin tek basina yeterli degildir.

Guvenli temizlik:

- Yazma trafigini durdur.
- Tum SQLite baglantilarini kapat.
- `wal_checkpoint` sonucunu dogrula.
- Eski DB icin atomik yedek al.
- Gecici dosyaya kopyala, `integrity_check` calistir, atomik degistir.
- WAL/SHM temizlenemiyorsa islemi basarisiz say.
- Canli DB degismediyse `success: false` don.

Oncelik: P0

### K-03 - Yedek indirme checkpoint hatasini gizliyor

Konum:

- `server_main.py:899`
- `server_main.py:905`

Mevcut davranis:

- WAL checkpoint basarisiz olsa da ana DB dosyasi indiriliyor.

Risk:

- Son islemler yalnizca WAL icinde kalmissa indirilen yedek eksik olur.
- Dosya acilabilir gorundugu icin sessiz veri kaybi fark edilmeyebilir.

`pass` silinirse:

- Checkpoint hatasi indirmeyi durdurur.
- Eksik yedek indirmekten daha dogru davranistir.

Guvenli temizlik:

- SQLite backup API ile tutarli snapshot al.
- Snapshot `quick_check` veya `integrity_check` sonrasinda indirilsin.
- Checkpoint/snapshot basarisizsa HTTP hata donsun.

Oncelik: P0

### K-04 - Servis borcu kaydi sonrasi bakiye esitleme hatalari yutuluyor

Konum:

- `src/db/mixins/device_mixin.py:295`
- `src/db/mixins/device_mixin.py:301`
- `src/db/mixins/device_mixin.py:305`
- `src/db/mixins/device_mixin.py:374`
- `src/db/mixins/device_mixin.py:383`
- `src/db/mixins/device_mixin.py:388`

Mevcut davranis:

- Servis borcu kaydedilebiliyor.
- Otomatik odeme dagitimi ve tum musteri bakiyelerini yeniden hesaplama
  basarisiz olsa da metot basarili donebiliyor.

Risk:

- Musteri 360, finans ve servis teslim ekranlari farkli bakiye gosterebilir.
- Uygulama yeniden baslayinca duzeliyor gorunen anlik tutarsizliklar olusur.
- Odeme kaydi borcla eslesmeyebilir.

`pass` silinirse:

- Yardimci hesaplama hatasi ana servis kaydini da kesebilir.
- Transaction siniri yoksa yarim kayit olusmaya devam edebilir.

Guvenli temizlik:

- Borc, odeme dagitimi ve bakiye hesaplamasini tek transaction yap.
- Ya tamamini commit et ya tamamini rollback et.
- Geriye uyumluluk gerekiyorsa `partial_success` durumu ve onarim kuyrugu
  olustur.
- UI yenileme sinyalini commit sonrasinda ayri calistir.

Oncelik: P0

### K-05 - Proje urunu stoktan dusuyor, maliyeti sifir kalabiliyor

Konum:

- `src/db/mixins/project_mixin.py:875`
- `src/db/mixins/project_mixin.py:885`
- `src/db/mixins/project_mixin.py:927`

Mevcut davranis:

- Urun proje dairesine ekleniyor ve stoktan dusuyor.
- Alis fiyati veya para birimi sorgusu hata verirse `unit_cost=0` kalir.
- Bu durumda proje malzeme gideri yazilmayabilir.

Risk:

- Proje kar raporu gercekten yuksek gorunur.
- Stok miktari azalirken maliyet ve finans hareketi eksik kalir.
- Dovizli stoklarda fark daha buyuk olabilir.

`pass` silinirse:

- Hata yukariya cikar; ancak stok daha once dusurulduyse rollback olmadan
  tutarsizlik devam edebilir.

Guvenli temizlik:

- Stok dusumu, urun kurulumu ve proje giderini tek transaction yap.
- Maliyet bulunamazsa islemi reddet veya "fiyatlandirilmamis malzeme"
  kaydi olustur.
- Doviz kuru bulunamazsa sifir maliyet kabul etme.

Oncelik: P0

### K-06 - Satis kaydi COGS olmadan tamamlanabiliyor

Konum:

- `src/ui/pages/transaction_page_behaviors.py:939`
- `src/ui/pages/transaction_page_behaviors.py:959`

Mevcut davranis:

- Stok dusumu yapiliyor.
- Alis fiyati sorgusu hata verirse hata yutuluyor.
- Satis veya servis tamamlanirken satilan malin maliyeti gideri eksik
  kalabiliyor.

Risk:

- Net kar ve gider raporlari yanlis olur.
- Birden fazla urunde hatali satir fark edilmez.

`pass` silinirse:

- Satis akisi hata ile kesilebilir.
- Stok daha once dusuruldugu icin transaction yoksa yarim islem kalabilir.

Guvenli temizlik:

- COGS hesaplama ve stok dusumunu servis katmanina tasi.
- Tum satirlari onceden dogrula.
- Tek transaction kullan.
- Eksik maliyetli urun varsa acik hata veya onayli uzlasma kaydi olustur.

Oncelik: P0

### K-07 - Odeme kaydediliyor, borca dagitim tablosu olusmayabiliyor

Konum:

- `src/ui/pages/transaction_page_behaviors.py:999`
- `src/ui/pages/transaction_page_behaviors.py:1005`
- `src/ui/pages/transaction_page_behaviors.py:1008`
- `src/ui/dialogs/customer_360_dialog.py:1453`
- `src/ui/dialogs/customer_360_dialog.py:1462`

Mevcut davranis:

- Tahsilat kaydi olusabilir.
- Esleme tablosu olusturma hatasi yutulur.
- Borca dagitim ayri bir blokta denenir.

Risk:

- Kasa geliri vardir ama hangi borcu kapattigi belirsizdir.
- Musteri alacakli veya borclu yanlis gorunebilir.
- Yeniden hesaplama sonucu ekrana gore degisebilir.

`pass` silinirse:

- Tablo olusturma hatasi akisi keser; daha once yazilan tahsilat commit
  edildiyse yarim islem kalir.

Guvenli temizlik:

- Sema migrasyonunu odeme aninda yapma; uygulama acilisinda dogrula.
- Tahsilat ve borc dagitimini tek transaction yap.
- Esleme basarisizsa tahsilati da rollback et veya acik uzlasma kaydi yaz.

Oncelik: P0

### K-08 - Senkronizasyon durum dosyasi bozuksa sessizce sifirlaniyor

Konum:

- `src/utils/web_sync_client.py:234`
- `src/utils/web_sync_client.py:238`

Mevcut davranis:

- JSON durum dosyasi okunamazsa yeni `machine_id`, bos zaman damgalari ve
  bos satir hash listesi ile devam edilir.

Risk:

- Ayni kayitlar tekrar gonderilebilir veya tekrar cekilebilir.
- Cakisma tabani kaybolur.
- Eski degisiklikler yeni degisiklik gibi yorumlanabilir.

`pass` silinirse:

- Senkronizasyon durur ve kullanici hata gorur.
- Veri cakismasi yaratmaktan daha guvenlidir, ancak otomatik kurtarma
  sunulmaz.

Guvenli temizlik:

- Bozuk dosyayi zaman damgali adla karantinaya al.
- Hatayi logla ve kullaniciya bildir.
- Guvenli tam uzlasma modu calistir.
- Yeni state yalnizca sunucu ve yerel veri karsilastirildiktan sonra yazilsin.

Oncelik: P0

### K-09 - Web tenant sema migrasyonu basarisizligi gizleniyor

Konum:

- `Web_Arayuzu/Main.py:430`
- `Web_Arayuzu/Main.py:443`
- `Web_Arayuzu/Main.py:489`
- `Web_Arayuzu/Main.py:547`
- `Web_Arayuzu/Main.py:549`

Mevcut davranis:

- Sektor ve lisans kolonlari eklenemezse sunucu calismaya devam eder.
- Otomatik kolon ekleme hatalari da yutulur.
- Sema hazir kabul edilip path cache'e alinabilir.

Risk:

- Sektor uygulama, lisans ve admin islemleri daha sonra belirsiz hata verir.
- Firma semalari birbirinden farkli kalir.
- Uygulama saglikli gorunurken temel kolonlar eksik olabilir.

`pass` silinirse:

- Web sunucusu baslangicta durabilir.
- Bu, bozuk sema ile hizmet vermekten daha guvenli olabilir; fakat planli
  migration ve saglik endpoint'i olmadan operasyonu zorlastirir.

Guvenli temizlik:

- Surumlu migration tablosu kullan.
- Her migration atomik ve tekrar calistirilabilir olsun.
- Basarisiz migration hizmet sagligini `unhealthy` yapsin.
- Sema dogrulanmadan `_SCHEMA_READY_PATHS` listesine ekleme.

Oncelik: P0

## 6. Yuksek ve Orta Riskli Bulgular

### Y-01 - Silinmis finans kayitlari tekrar gorunebilir

Konum:

- `src/db/mixins/finance_mixin.py:600`
- `src/db/mixins/finance_mixin.py:611`
- `src/db/mixins/finance_mixin.py:743`
- `src/db/mixins/finance_mixin.py:754`
- `src/db/mixins/finance_mixin.py:860`
- `src/db/mixins/finance_mixin.py:872`
- `src/db/mixins/finance_mixin.py:894`
- `src/db/mixins/finance_mixin.py:908`
- `src/db/mixins/finance_mixin.py:924`

Mevcut davranis:

- Soft-delete kolonu tespit edilemezse sorgu filtresiz devam eder.
- Arsivlenmis banka karti, taksit, cek veya senet tekrar listelenebilir.
- Toplam borca silinmis kalem dahil olabilir.

`pass` silinirse:

- Listeleme islemi tamamen hata verir.

Guvenli temizlik:

- Sema bilgisini uygulama baslangicinda bir kez dogrula.
- Bilinmeyen semada "fail closed" davran.
- Yalnizca `sqlite3.Error` yakala.
- Arsiv filtresi olmadan finans sorgusu calistirma.

Oncelik: P1

### Y-02 - Stok fiyat degisikligi audit kaydi olmadan tamamlanabilir

Konum:

- `src/db/mixins/stock_mixin.py:98`
- `src/db/mixins/stock_mixin.py:110`

Mevcut davranis:

- Fiyat artisi uygulanir.
- Audit kaydi yazilamazsa hata yutulur.

Risk:

- Kim, ne zaman, ne oranda fiyat degistirdi bilgisi eksik kalir.
- Finans ve yetki incelemesinde iz surulemez.

`pass` silinirse:

- Audit hatasi fiyat guncellemesini de kesebilir; transaction sinirina
  bagli olarak yari durum olusabilir.

Guvenli temizlik:

- Audit zorunluysa ayni transaction icinde tut.
- Zorunlu degilse kullaniciya "kayit yapildi, audit yazilamadi" uyarisi ver
  ve merkezi hata kaydi olustur.

Oncelik: P1

### Y-03 - Teknisyen kaydi sonrasi ekranlar yenilenmeyebilir

Konum:

- `src/ui/dialogs/_tp_operations.py:697`
- `src/ui/dialogs/_tp_operations.py:701`
- `src/ui/dialogs/_tp_operations.py:706`
- `src/ui/dialogs/add_stock_dialog.py:1186`
- `src/ui/dialogs/add_stock_dialog.py:1195`

Mevcut davranis:

- Veri kaydi tamamlanir.
- Sayfa yenileme veya `financial_data_changed` sinyali hata verirse hata
  yutulur.

Risk:

- Kullanici eski bakiye, stok veya finans ozetini gorur.
- Uygulama yeniden acilinca duzeliyor algisi olusur.

`pass` silinirse:

- Basarili veri kaydindan sonra UI hata penceresi veya kapanma olabilir.
- Veri aslinda kayitli oldugu icin kullanici tekrar kaydedip cift kayit
  olusturabilir.

Guvenli temizlik:

- Veri sonucu ile UI yenileme sonucunu ayri raporla.
- Merkezi bir refresh event bus kullan.
- Basarisiz yenilemeyi kuyrukla ve bir kez tekrar dene.
- "Kayit basarili, ekran yenilenemedi" mesaji goster.

Oncelik: P1

### Y-04 - Eski yedek silme hatasi depolama birikmesine yol acar

Konum:

- `src/db/mixins/_db_legacy_maintenance_mixin.py:90`
- `src/db/mixins/_db_legacy_maintenance_mixin.py:95`

Mevcut davranis:

- Retention sirasinda eski dosya silinemezse devam edilir.

Risk:

- Disk zamanla dolar.
- Yedek alma daha sonra tamamen basarisiz olabilir.

`pass` silinirse:

- Tek bir kilitli eski dosya yeni yedek islemini basarisiz gosterebilir.

Guvenli temizlik:

- Yalnizca `OSError` yakala.
- Dosya yolunu ve hata kodunu logla.
- Retention saglik metrigi ve tekrar deneme kuyrugu ekle.

Oncelik: P1

### Y-05 - Wipe rollback/foreign-key geri acma hatasi gizleniyor

Konum:

- `src/db/mixins/_db_legacy_maintenance_mixin.py:72`
- `src/db/mixins/_db_legacy_maintenance_mixin.py:77`

Mevcut davranis:

- Wipe hatasi loglanir.
- Rollback veya foreign key geri acma hatasi tekrar yutulur.

Risk:

- Baglanti bilinmeyen transaction durumunda kalabilir.
- `foreign_keys` kapali kalabilir.

`pass` silinirse:

- Temizlik hatasi asil wipe hatasini maskeleyebilir.

Guvenli temizlik:

- Asil hata ile cleanup hatasini ayri logla.
- Baglantiyi kapatip temiz baglanti ac.
- `PRAGMA foreign_keys` durumunu islem sonunda dogrula.

Oncelik: P1

### Y-06 - Bulut modulu migrationlari sistematik olarak hata yutuyor

Konum:

- `bulut_modules/database.py:42`
- `bulut_modules/database.py:61`
- `bulut_modules/database.py:85`
- `bulut_modules/database.py:124`
- `bulut_modules/database.py:130`
- `bulut_modules/database.py:249`
- `bulut_modules/database.py:303`

Mevcut davranis:

- Tek bir `init_db` icinde cok sayida `ALTER TABLE` ve index olusturma
  deneniyor.
- 23 genis veya bare `except-pass` blogu migration hatalarini gizliyor.

Risk:

- Ayni surumde farkli kullanicilar farkli semalara sahip olabilir.
- Bir sonraki sorgu beklenen kolonu bulamaz.
- Baslangic basarili gorunur, hata daha sonra alakasiz ekranda ortaya cikar.

`pass` silinirse:

- Ilk tekrar eden kolon veya uyumsuz semada modul acilmaz.

Guvenli temizlik:

- Modul aktifse migrationlari surumlu dosyalara ayir.
- `PRAGMA table_info` ile on kosul dogrula.
- Her migration sonucu log ve migration tablosuna yazilsin.
- Modul kullanilmiyorsa import grafi testi sonrasi tum eski modul kaldirilabilir.

Oncelik: P1

### Y-07 - Bcrypt kutuphanesi hatasi sessizce legacy SHA-256 denemesine dusuyor

Konum:

- `Web_Arayuzu/Main.py:2200`
- `Web_Arayuzu/Main.py:2205`

Mevcut davranis:

- Bcrypt hash algilanir.
- Bcrypt import veya kontrol hatasi yutulur.
- Kod ayni bcrypt metnini legacy SHA-256 hash gibi karsilastirmaya gider.

Risk:

- Dogru parola "yanlis" gorunur.
- Kutuphane eksikligi kimlik hatasi gibi raporlanir.
- Operasyon ekibi gercek nedeni goremez.

`pass` silinirse:

- Login 500 hatasi verebilir.

Guvenli temizlik:

- `ImportError` ile bcrypt dogrulama hatasini ayir.
- Desteklenmeyen hash algoritmasi icin acik ve guvenli hata don.
- Parola migrationini basarili giris sonrasi kontrollu yap.

Oncelik: P1

## 7. Dusuk Riskli veya Korunmasi Gereken Bloklar

Bu bloklarin amaci genellikle ana uygulamayi ikincil bir UI veya opsiyonel
entegrasyon hatasindan korumaktir.

### D-01 - UI obje kapatma ve `deleteLater`

Ornekler:

- `src/ui/modern_login_window.py:883`
- `src/ui/modern_login_window.py:928`
- `src/ui/widgets/side_menu.py`
- `src/ui/mixins/_main_window_base_mixin.py`

Silme etkisi:

- Qt nesnesi daha once silinmisse `RuntimeError` ana pencereyi kapatabilir.
- Pencere kapanisi veya tema gecisi kirilgan olur.

Temizlik:

- `Exception` yerine `(RuntimeError, AttributeError)` yakala.
- Debug seviyesinde tek satir logla.
- Ayni cleanup yardimcisini merkezilestir.

### D-02 - Opsiyonel medya, TTS ve OCR gerilemesi

Ornekler:

- `src/utils/asistan_motoru.py`
- `src/utils/_sip_ocr.py`
- `src/ui/dialogs/_sipd_logic_mixin.py`

Silme etkisi:

- Ses motoru, codec, OCR veya harici arac yoksa tum ozellik ya da uygulama
  acilisi hata verebilir.

Temizlik:

- Opsiyonel bagimlilikta `ImportError` yakala.
- Calisma zamani hatalarinda belirli medya/OCR hata turlerini yakala.
- Ozellik saglik durumunu UI icinde goster.
- Gecici dosya temizleme hatasini `OSError` olarak logla.

### D-03 - TCMB gecici erisim hatasi

Konum:

- `Web_Arayuzu/Main.py:3085`
- `Web_Arayuzu/Main.py:3106`

Mevcut davranis:

- TCMB erisilemezse son basarili kur kullaniliyor.

Silme etkisi:

- Gecici internet hatasi tum doviz ekranini hata durumuna sokar.

Temizlik:

- Blok korunmali.
- Timeout, HTTP, XML ve veri hatalari ayri yakalanmali.
- Kullanilan kurun zamani ve "stale" durumu ekranda gorunmeli.
- Eski kur ile mali islem yapiliyorsa kullanici onayi veya yas siniri
  uygulanmali.

### D-04 - Uygulama kapatma `KeyboardInterrupt`

Konum:

- `Web_Arayuzu/Main.py:5172`
- `Web_Arayuzu/Main.py:5174`

Degerlendirme:

- Bu blok kontrollu terminal kapatmasi icin normaldir.
- Silinmesi traceback goruntusune yol acar; islevsel kazanc saglamaz.
- Oldugu gibi kalabilir.

### D-05 - Admin konsolu logout best-effort

Konum:

- `Admin_Konsol/api_client.py:62`
- `Admin_Konsol/api_client.py:66`

Mevcut davranis:

- Sunucu logout istegi basarisiz olsa da yerel token temizleniyor.

Silme etkisi:

- Ag kesintisinda kullanici konsoldan cikamayabilir.

Temizlik:

- Blok korunmali.
- `requests.RequestException` yakalanmali.
- Sunucu oturumu kisa omurlu veya iptal listeli olmali.

## 8. Dogrudan Silinebilecek Adaylar

### S-01 - Ezilen ayni isimli metot

Konum:

- `src/db/mixins/project_mixin.py:970`
- `src/db/mixins/project_mixin.py:992`

Durum:

- `update_unit_product_note` iki kez tanimli.
- Ikinci tanim birinci tanimi sinif olusurken ezer.
- Ilk metottaki `except-pass` calisma zamaninda ulasilabilir degildir.

Silme etkisi:

- Birinci tanim tamamen silinirse mevcut Python davranisi degismez.
- Ikinci tanim calismaya devam eder.

Kosul:

- Mixin kaynak metnini runtime patch veya AST araci ile okuyan harici bir
  arac olmadigi dogrulanmali.
- Proje teknik not guncelleme testi calistirilmali.

Karar:

- Guvenli silme adayi.

### S-02 - Kullanilmayan eski modul agaci

Konum:

- `bulut_modules/`

Durum:

- Eski veya ayri bir calisma alanina benziyor.
- Ana masaustu girisi dogrudan bu modulu import etmiyor gorunuyor.

Silme etkisi:

- Gercekten kullanilmiyorsa 42 `pass` blogu ve eski sema kodu birlikte
  kaldirilabilir.
- Ayri bir launcher, paketleme dosyasi veya musteri kurulumu kullaniyorsa
  ilgili urun parcasi tamamen bozulur.

Kosul:

- PyInstaller spec, setup script, kisayol hedefi ve tum import grafi
  dogrulanmadan silinmemeli.

Karar:

- Kanit gerektiren silme adayi; hemen silinmemeli.

## 9. Toplu Silme Yapilirsa Ne Olur?

`except ...: pass` satirlarinda yalnizca `pass` ifadesini silmek Python
sozdizimini bozar; `except` govdesi bos kalamaz.

Bloklarin tamamini silmek de ayni anlama gelmez:

1. `try` govdesi korunup `except` silinirse hata yukariya yayilir.
2. UI cleanup hatalari uygulamayi veya pencere kapanisini kesebilir.
3. Opsiyonel TTS/OCR kutuphanesi eksikligi uygulama acilisini etkileyebilir.
4. Kritik veri hatalari artik gorunur olur; bu olumlu olsa da transaction
   yoksa yari kayit sorununu tek basina cozmez.
5. Migration bloklari ilk mevcut kolon veya eski semada baslangici durdurur.
6. Kullanici "kayit basarisiz" gorup tekrar deneyebilir; onceki kismi commit
   edilmisse cift kayit olusabilir.
7. Yedek ve geri yukleme akislari daha guvenli bicimde durabilir, ancak
   atomik dosya degistirme kurulmadan operasyon eksik kalir.

Sonuc:

- Toplu silme yapilmamali.
- `pass` sayisini sifira indirmek hedef olmamali.
- Sessiz ve belirsiz basarisizligi sifira indirmek hedef olmali.

## 10. Guvenli Temizlik Siniflari

### Sinif A - Hata yukariya yayilmali

Kullanim:

- Guvenlik dogrulamasi
- DB geri yukleme
- Tutarli yedek olusturma
- Zorunlu sema migrationi

Uygulama:

- Belirli hata turunu yakala.
- Logla.
- Kullaniciya acik hata don.
- Islem basarisiz sayilsin.

### Sinif B - Transaction icinde geri alinmali

Kullanim:

- Servis borcu ve tahsilat
- Borc dagitimi
- Stok dusumu ve COGS
- Proje urunu ve malzeme gideri
- Teklif kabul ve cari hesaba isleme

Uygulama:

- Tek servis katmani.
- Tek DB transaction.
- Commit sonrasi UI sinyali.
- Hata halinde tam rollback.

### Sinif C - Kontrollu gerileme ve gorunur durum

Kullanim:

- TTS
- OCR
- TCMB
- Tema ve gorsel efekt
- Harici program acma

Uygulama:

- Ana islem devam edebilir.
- Ozellik "kullanilamiyor" durumu gosterir.
- Hata debug/warning olarak kaydedilir.
- Surekli tekrar eden loglar oran sinirli olur.

### Sinif D - Cleanup best-effort

Kullanim:

- Gecici dosya silme
- Qt `deleteLater`
- Pencere kapanisinda thread bekleme
- Logout istegi

Uygulama:

- Dar hata turu yakalanir.
- Asil hata maskelenmez.
- Kaynak sizintisi olasiligi loglanir.

### Sinif E - Olu kod veya modul silme

Kullanim:

- Ayni adli ikinci tanim tarafindan ezilen metot
- Import edilmeyen eski modul
- Paketlemeye girmeyen yedek kaynak

Uygulama:

- Import grafi
- Paket manifesti
- Calisma zamani smoke testi
- Silme sonrasi kaynak ve paket fark testi

## 11. Onerilen Uygulama Sirasi

### Faz 0 - Koruma

1. Mevcut DB ve WAL ile tutarli yedek al.
2. Kritik finans ve senkronizasyon senaryolari icin regresyon verisi olustur.
3. Loglarda `operation_id`, `customer_id`, `tracking_no` ve `tenant_id`
   alanlarini standartlastir.

### Faz 1 - P0 guvenlik ve veri butunlugu

1. `security_confirm_dialog.py` fail-closed yap.
2. `server_main.py` backup/restore akisini atomik yap.
3. Servis borcu, tahsilat ve borc dagitimini transaction yap.
4. Stok/COGS ve proje maliyetini transaction yap.
5. Senkronizasyon state bozulmasini karantina ve uzlasma akimina bagla.
6. Web migration basarisizligini saglik durumuna bagla.

### Faz 2 - P1 finans ve audit

1. Soft-delete filtrelerinin sema bagimliligini kaldir.
2. Stok fiyat audit kaydini zorunlu veya acik partial-success yap.
3. Wipe cleanup ve backup retention hatalarini gorunur yap.
4. Bcrypt algoritma destegini acik hata sozlesmesi ile yonet.

### Faz 3 - UI ve opsiyonel ozellikler

1. Qt bloklarini dar hata turlerine indir.
2. Refresh event bus ve retry mekanizmasi ekle.
3. TTS/OCR/TCMB icin saglik gostergesi ekle.
4. Tekrarlanan cleanup kodlarini yardimci fonksiyona tasi.

### Faz 4 - Olu kod ve eski modul temizligi

1. Ezilen `update_unit_product_note` tanimini sil.
2. `bulut_modules` kullanimini kanitla veya kaldir.
3. Gecersiz `Web_Arayuzu/src` ayna agacini runtime import yolundan cikar.

## 12. Web_Arayuzu/src Ayrisma Sorunu

AST taramasinda 272 dosya ayrisma hatasi verdi. Buyuk cogunlugu
`Web_Arayuzu/src` altindadir.

Ornekler:

- `Web_Arayuzu/src/database.py`
- `Web_Arayuzu/src/ui/pages/accounting_page.py`
- `Web_Arayuzu/src/ui/widgets/side_menu.py`

Bu dosyalar Python kodu yerine kod aciklamasi niteliginde duz Ingilizce
metinle baslamaktadir. Bu nedenle Python olarak import edilemezler.

Risk:

- `Web_Arayuzu/Main.py`, calisma dizinine gore `src` paketini bu ayna
  agacindan cozmeye calisabilir.
- Bazi dosyalar gecerli, bazilari gecersiz oldugu icin ortam bagimli import
  sonucu olusabilir.
- Bu 272 dosyadaki `except-pass` davranislari AST ile tam siniflandirilamadi.

Silme etkisi:

- Ayna agaci runtime tarafindan kullanilmiyorsa silmek veya paket disina
  almak riski azaltir.
- Web tarafinda uc yardimci import bu `src` adini kullandigi icin dogrudan
  toplu silme importlari bozabilir.

Guvenli temizlik:

1. Web icin tek ve acik bir paket kok dizini belirle.
2. `sys.path` degisikliklerini kaldir veya paket adini benzersiz yap.
3. Gerekli yardimcilari gecerli bir ortak pakete tasi.
4. Tum `Web_Arayuzu/src` dosyalarini `compileall` ile kapila.
5. Paketleme testinde import kaynagini logla.

Oncelik: P0 depo ve runtime hijyeni.

## 13. Dogrulama Kapilari

Her temizlik fazindan sonra asagidaki testler calismalidir.

### Veritabani

- `PRAGMA foreign_key_check`
- `PRAGMA integrity_check`
- WAL acik/kapali yedek snapshot testi
- Eski semadan yeni semaya migration testi
- Migration ikinci kez calistirildiginda degisiklik olmama testi

### Finans

- USD/EUR/TRY stoktan satis ve servis
- Stok dusumu ile COGS esitligi
- Proje malzeme gideri ve stok hareketi esitligi
- Kismi tahsilat ve borc dagitimi
- Silinmis/arsivlenmis finans kaydinin toplamlara girmemesi
- Uygulama yeniden baslatmadan ekranlarin ayni bakiyeyi gostermesi

### Senkronizasyon

- Bozuk state JSON
- Ayni kaydin iki cihazda degismesi
- Offline kayit, yeniden baglanma ve tekrar senkronizasyon
- Silme ve geri yukleme
- State dosyasi kaybi sonrasi tam uzlasma

### Guvenlik

- Auth servisi hata verirken kritik islemin reddedilmesi
- Varsayilan parola bulunmamasi
- Bcrypt kutuphanesi eksikligi
- Sureli sifre sifirlama
- Audit kaydi olusmasi

### UI

- Kayit basarili, refresh basarisiz senaryosu
- Dialog kapatma ve thread temizligi
- Tema degisimi
- TTS/OCR bagimliligi yokken ana uygulama
- Menu ve alt menu gecisleri

### Kod Kalitesi

- `python -m compileall` aktif runtime paketleri
- `python tools/mojibake_guard.py`
- `python tools/ascii_diff_guard.py`
- Yeni bare `except` eklenmesini engelleyen CI kontrolu
- `except Exception: pass` icin izin listesi ve gerekce kontrolu

## 14. CI Kurali Onerisi

Yeni kod icin asagidaki politika uygulanmalidir:

1. Bare `except` yasak.
2. `except Exception: pass` varsayilan olarak yasak.
3. Izin verilen blokta tek satir gerekce yorumu ve hata sinifi zorunlu.
4. Veri degistiren fonksiyonda sessiz `pass` kesinlikle yasak.
5. Guvenlik, yedek, senkronizasyon ve finans akiminda hata sonucu acik
   bir return/exception sozlesmesine sahip olmali.
6. UI cleanup istisnalari sadece belirli Qt veya OS hata turlerini
   yakalamali.

Ornek kabul edilebilir desen:

```python
try:
    temporary_path.unlink()
except FileNotFoundError:
    pass
except OSError as exc:
    logger.warning("Temporary file cleanup failed: %s", exc)
```

Ornek kabul edilemez desen:

```python
try:
    apply_payment_to_debts(...)
except Exception:
    pass
```

## 15. Nihai Karar

- 464 blogun toplu silinmesi onerilmez.
- P0 grubundaki bloklar mevcut haliyle birakilmamalidir.
- En tehlikeli alanlar guvenlik fallback'i, WAL/yedek, servis-tahsilat
  dagitimi, stok/COGS, proje maliyeti, web migration ve sync state'tir.
- UI ve opsiyonel entegrasyon bloklari kaldirilmak yerine daraltilmali ve
  loglanmalidir.
- Bir adet kesin olu metot tanimi silme adayi olarak belirlenmistir.
- `bulut_modules` ve `Web_Arayuzu/src` icin import/paketleme kaniti
  olmadan toplu silme yapilmamalidir.

Onerilen hedef "pass sayisini azaltmak" degil, "sessiz basarisizligi,
yarim commit'i ve yanlis basari sonucunu ortadan kaldirmak" olmalidir.

## 16. Uygulama Sonucu

Bu rapordaki oncelikli onarimlar 26.07.2026 tarihinde kaynak yedegi
alindiktan sonra uygulandi.

### Kaynak yedegi

- Klasor:
  `C:\Users\yedek\Desktop\yapay zeka\AYEC_Pro_Source_Backups\AYEC_Pro_Source_20260726_162125`
- Arsiv:
  `C:\Users\yedek\Desktop\yapay zeka\AYEC_Pro_Source_Backups\AYEC_Pro_Source_20260726_162125.zip`
- Dosya sayisi: 2109
- ZIP SHA-256:
  `012eb5c19ee434a36baf9749577839b30f20505e750eff90957c80e740f73e40`
- Veritabani, log, derleme ciktisi, sanal ortam, kullanici verisi ve gizli
  ortam dosyalari arsive alinmadi.
- Arsiv manifesti 2109 dosyanin SHA-256 ozetini icerir.

### P0 bulgu durumu

- K-01 tamamlandi. Guvenlik dogrulamasi hata halinde kapali duruma geciyor.
  Zayif varsayilan parola kaldirildi.
- K-02 tamamlandi. Geri yukleme once gecici dosyaya aliniyor, SQLite basligi
  ve butunlugu dogrulaniyor, sonra atomik olarak canli dosyanin yerini aliyor.
- K-03 tamamlandi. Yedekler SQLite backup API ile uretiliyor. Checkpoint,
  butunluk ve gecici dosya temizligi gorunur hata sozlesmesine sahip.
- K-04 tamamlandi. Servis borcu, muhasebe, stok ve odeme dagitimi tek
  transaction icinde tamamlanmadan basarili sayilmiyor.
- K-05 tamamlandi. Proje urunlerinde stok, kur ve maliyet on kontrolu
  yapiliyor. Finans kaydi basarisizsa stok ve proje satiri geri aliniyor.
- K-06 tamamlandi. Satis kaydi ile stok dusumu ayni transaction icinde.
  Kur veya stok hatasinda COGS olmadan satis tamamlanmiyor.
- K-07 tamamlandi. Odeme-borc baglanti semasi zorunlu. Dagitim tekrar
  calistirilsa bile ayni borctan ikinci kez dusmuyor.
- K-08 tamamlandi. Bozuk senkronizasyon state dosyasi karantinaya aliniyor,
  kayip state icin uzlasma yapiliyor ve yeni state atomik yaziliyor.
- K-09 tamamlandi. Web sema migrasyonu hatalari toplanip yukariya
  aktariliyor. Sema dogrulanmadan hazir isareti verilmiyor.

### P1 bulgu durumu

- Y-01, Y-02, Y-03, Y-04, Y-05 ve Y-07 icin hata yutma davranislari
  kaldirildi veya loglanan, geri alinan ve sonuc donduren akislara cevrildi.
- Y-06 icin toplu silme yapilmadi. `bulut_modules` import kaniti olmadan
  kaldirilmasi yuksek regresyon riski tasiyor.
- UI cleanup ve opsiyonel entegrasyon bloklari topluca silinmedi. Kritik
  teknisyen paneli yenileme ve sinyal hatalari loglanir hale getirildi.

### Ilave runtime duzeltmesi

`Web_Arayuzu/Main.py` icindeki kaynak yolu hazirlama fonksiyonu global
`sys.path` onceligini degistiriyordu. Bu davranis masaustu `src` paketi
yerine Web kopyasinin yuklenmesine ve paketleme/menu importlarinin
bozulmasina neden olabiliyordu. Web kok dizini artik yalnizca eksikse yolun
sonuna ekleniyor; mevcut paket onceligi degismiyor.

### Finans ve stok transaction kapsami

- Yeni stok karti ve stok alis muhasebe kaydi atomik hale getirildi.
- Stok miktari/fiyati guncellemesi ve buna bagli finans kaydi atomik hale
  getirildi.
- Banka bakiyesi ile muhasebe satiri ayni transaction icinde tutuluyor.
- Servis kaydi, kullanilan parcalar, musteri borcu, tahsilat ve dagitim ayni
  transaction icinde tutuluyor.
- Eksik USD/EUR kuru artik 1.0 kabul edilmiyor. Finansal kayit reddediliyor.
- Sifir bakiyeli kullanilmayan dovizler kur gerektirmiyor. Gercek bakiyesi
  olan bir dovizin kuru eksikse Musteri 360 ekrani bunu acikca gosteriyor.

### Dogrulama sonucu

- Tam test paketi: `150 passed`
- Python derleme kontrolu:
  `src`, `core`, `Admin_Konsol`, `Web_Arayuzu/Main.py`, `server_main.py`
- Mojibake korumasi: basarili
- ASCII eklenen satir korumasi: basarili
- Onarilan kritik dosyalarda `git diff --check`: basarili

Sonuc: Kritik akislarda sessiz `pass` yerine fail-closed, transaction
rollback, atomik dosya degisimi, acik hata sonucu ve loglama uygulanmistir.
Kalan dusuk riskli bloklar toplu olarak silinmemeli; ilgili modul degisirken
dar hata siniflariyla kademeli temizlenmelidir.
