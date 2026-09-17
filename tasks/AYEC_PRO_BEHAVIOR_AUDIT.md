# AYEC Pro Davranis Audit Raporu

Tarih: 2026-03-30
Yontem: `static inspection + py_compile + unittest + secilmis runtime probe`

## Ozet

Bu rapor onceki stale audit dosyasinin yerine guncel durumu yansitir. Son onarim dalgalarindan sonra kritik guvenlik, dogrudan dialog kullanimi ve heuristik SQL f-string yuzeyi yeniden tarandi.

## Guncel Sonuc

- `src` agacinda `py_compile`: gecti
- `tests.test_update_logic`: gecti
- `tests.test_dialog_flows`: gecti
- `tests.test_input_validator_comprehensive`: gecti
- `src/ui` altinda dogrudan `QMessageBox.question|warning|critical|information`: `0`
- `src` altinda `except Exception: pass`: `0`
- `src` altinda `execute(f`, `query = f`, `sql = f`: `0`
- `Main.py --healthcheck`: destekleniyor
- `src\api src\utils src\workers src\bot` altinda `time.sleep(`: `0`

## Dogrulanan Davranislar

### Startup ve environment boot

- Davranis: uygulama venv icinde yeniden baslatilabiliyor ve startup probe calistirabiliyor.
- Beklenen calisma: tam GUI login akisini acmadan kisa bir saglik sinyali uretilmeli.
- Kontrol yontemi:
  - `Main.py` statik inceleme
  - `--healthcheck` modu eklenmesi
- Bulgular:
  - `Main.py` artik `--healthcheck` ve `--smoke` modlarini destekliyor
  - startup probe `venv`, `database`, `auth_manager`, `sector_manager`, `main_window` sinyallerini yaziyor
- Risk seviyesi: `Dogrulandi`
- Onerilen duzeltme: yok

### Logging

- Davranis: log dosyasi acilamazsa startup tamamen kirilmamali.
- Beklenen calisma: console-only fallback ile devam etmeli.
- Kontrol yontemi:
  - `Main.py` statik inceleme
- Bulgular:
  - `setup_logging()` artik `FileHandler` acilamazsa `StreamHandler` ile devam ediyor
- Risk seviyesi: `Dogrulandi`
- Onerilen duzeltme: yok

### Auth / auto-login

- Davranis: legacy backdoor token kabul edilmemeli.
- Beklenen calisma: legacy marker reject edilmeli.
- Kontrol yontemi:
  - `src/auth/auth_handler.py`
  - `tests/verify_auth.py`
- Bulgular:
  - legacy marker akisi kaldirildi
- Risk seviyesi: `Dogrulandi`
- Onerilen duzeltme: yok

### Dialog standardi

- Davranis: yeni UI yuzeyi merkezi dialog bridge kullanmali.
- Beklenen calisma: dogrudan `QMessageBox.question|warning|critical|information` cagri kalmamali.
- Kontrol yontemi:
  - `rg -n "QMessageBox\\.(question|warning|critical|information)" src\\ui`
- Bulgular:
  - eslesme yok
- Risk seviyesi: `Dogrulandi`
- Onerilen duzeltme: yok

### Assistant hata yonetimi

- Davranis: sessiz exception yutma olmamali.
- Beklenen calisma: loglu fallback kullanilmali.
- Kontrol yontemi:
  - `rg -n "except Exception: pass" src`
- Bulgular:
  - eslesme yok
- Risk seviyesi: `Dogrulandi`
- Onerilen duzeltme: yok

### SQL guvenligi

- Davranis: heuristik SQL f-string/query gürültüsü olmamali.
- Beklenen calisma: identifier sanitize + parametrik query/formatli sabit sablonlar kullanilmali.
- Kontrol yontemi:
  - `rg -n "execute\\(f|query\\s*=\\s*f|sql\\s*=\\s*f" src`
- Bulgular:
  - eslesme yok
- Risk seviyesi: `Dogrulandi`
- Onerilen duzeltme: yok

## Kalan Riskler

### P2 Orta

#### 1. Repo geneline yayilmis dusuk onemli encoding/comment hijyeni

- Davranis: kritik runtime yuzeyleri temizlenmis olsa da repo genelinde dusuk onemli yorum veya dekoratif metin kalintilari olabilir.
- Beklenen calisma: kalanlar kademeli refactor turlerinde temizlenmeli.
- Kontrol yontemi:
  - uzun kuyruk dosya taramalari
- Bulgular:
  - kritik UI ve startup yuzeyleri temizlendi
  - kalanlar esas olarak dusuk onemli hijyen seviyesi
  - guncel taramada urun kodunda tekil bir UI literal izi goruldu: `src/ui/dialogs/quick_sale_dialog.py`
- Risk seviyesi: `P2 Orta`
- Onerilen duzeltme:
  - yalniz gercek dosya icerigi bozuksa ve runtime degeri varsa temizle

#### 2. Entegre bot/test yardimci katmanlari

- Davranis: agir worker/integration `sleep` yuzeyi kapatildi; kalan alanlar artik daha cok yardimci test veya operator dogrulama seviyesinde.
- Beklenen calisma: runtime'i etkileyen bloklayici beklemeler kalmamali.
- Kontrol yontemi:
  - `rg -n "time\\.sleep\\(" src\\api src\\utils src\\workers src\\bot`
- Bulgular:
  - eslesme yok
- Risk seviyesi: `Dogrulandi`
- Onerilen duzeltme: yok

## Basarisiz Davranislar

- Bu turda secilen regresyon setinde basarisiz davranis yok.

## Bloklu / Ortam Eksikligi Nedeniyle Dogrulanamayanlar

- Tam GUI kullanici klik akisi burada manuel operator olmadan uctan uca dogrulanmadi.
- Qt warning azaltimi secili test yuzeyinde izlendi; ancak tum ekranlar icin gorsel operator dogrulamasi ayrica yapilabilir.
- `QMessageBox` taramasinda kalan eslesmelerin cogu dogrudan popup cagrisindan degil, enum karsilastirmasi veya import seviyesinden geliyor.

## Sonuc

Bu audit turunda daha once kritik gorunen uc ana baslik guncel olarak kapatildi:

- legacy auth bypass
- dogrudan `QMessageBox` yuzeyi
- heuristik SQL f-string/query yuzeyi

Aktif kalan isler artik agir guvenlik/regresyon kategorisinden cok, uzun kuyruk hijyen ve performans dalgasina giriyor.
