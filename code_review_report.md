# AYEC Pro - Kod Inceleme Raporu (Aktif Dosyalar)

## Dosya Kullanim Haritasi

Oncelikle hangi dosyanin gercekte kullanildigini netlestirdim:

| Dosya | Durum | Aciklama |
|-------|-------|----------|
| `Main.py` | **AKTIF** | Desktop uygulamanin giris noktasi (PyQt6) |
| `src/desktop_runtime.py` | **AKTIF** | Backend sunucuyu baslatir, DB init yapar |
| `src/utils/server_main.py` | **AKTIF** | Desktop icinden calisan lokal API (port 8000) |
| `src/database.py` | **AKTIF** | Ana veritabani sinifi (Desktop) |
| `server_main.py` (kok) | **AKTIF** | Bulut sunucu (bagimsiz uvicorn) |
| `backend/` | **KULLANILMIYOR** | Import basarisiz (`ModuleNotFoundError` log'da mevcut) |
| `web_api/` | **KULLANILMIYOR** | Hicbir yerden import edilmiyor |

> [!NOTE]
> `backend/` ve `web_api/` klasorleri incelemeden cikarildi. Asagidaki tum bulgular aktif dosyalara aittir.

---

## KRITIK - Uygulama Crash'ine Sebep Olan Sorunlar

### 1. `stdout/stderr` Buffer Detach - Surekli Tekrarlayan Hata
> [!CAUTION]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L6-L9)
> **Ayni sorun:** [server_main.py (kok)](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/server_main.py#L22-L24)

```python
# src/utils/server_main.py satir 6-9:
if sys.stdout is not None and sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
if sys.stderr is not None and sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
```

**Sorun:** `detach()` cagrisi orijinal buffer'i kalici olarak ayirir. Python'un `logging` modulu veya herhangi bir kutuphane `sys.__stdout__` / `sys.__stderr__` uzerinden yazmaya calisinca:
```
ValueError: underlying buffer has been detached
```
Bu hata `app_launch.err.log` dosyasinda **onlarca kez** tekrarlaniyor. TTS motoru, veritabani, update manager - loglama yapan her sey bu hatayi tetikliyor.

**Cozum:**
```python
import io
if sys.stdout is not None and sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr is not None and sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

---

### 2. `conn.close()` finally Blogu Olmadan - Connection Leak
> [!WARNING]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L291)

```python
# get_customer_balance - satir 291
balance = (total_debt + total_sales) - total_paid
conn.close()       # <-- finally blogu yok
return {"balance": balance}
```

Ayni sorun [get_customer_history_api satir 381](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L381)'de de var.

Herhangi bir satirda exception olursa `conn.close()` cagrilmaz ve SQLite baglantisi acik kalir. Yeterince birikince veritabani kilitlenir.

**Cozum:** `finally: conn.close()` blogu eklenmeli.

---

## YUKSEK - Veri Butunlugu Riskleri

### 3. Tracking Number Race Condition (Cift Kayit)
> [!IMPORTANT]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L408-L411)

```python
cur.execute("SELECT MAX(id) as max_id FROM devices")
row = cur.fetchone()
max_id = row[0] if row and row[0] else 0
tracking_no = f"SRV{max_id + 1:05d}"
```

`MAX(id)` okunduktan sonra `INSERT` yapilmadan once baska bir istek gelirse **ayni tracking_no** iki farkli kayda atanir. Desktop uygulamada bu daha az olasilik, ama web API aciksa risk yuksek.

**Cozum:** `INSERT` sonrasi `lastrowid` kullanarak tracking number olusturulmali:
```python
cur.execute("INSERT INTO devices (...) VALUES (...)")
tracking_no = f"SRV{cur.lastrowid:05d}"
cur.execute("UPDATE devices SET tracking_no=? WHERE id=?", (tracking_no, cur.lastrowid))
```

---

### 4. Stok Negatife Dusebilir (Kontrol Yok)
> [!IMPORTANT]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L442-L446)

Process wizard'da used_parts ekleniyor ama **stok guncellenmeden** birakiliyor. Kok `server_main.py`'de stok dusme kodu var ama negatif kontrol yok:

```python
# server_main.py (kok) satir 756:
cur.execute("UPDATE parts SET stock = stock - ? WHERE id = ?", (item.qty, item.id))
```

Ne `src/utils/server_main.py`'de stok dusme var ne de negatif kontrol.

---

## ORTA - Aktif Bug'lar

### 5. Cift `@app.post` Dekoratoru (Personel Endpoint)
> [!WARNING]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L555-L556)

```python
@app.post("/api/personnel")
@app.post("/api/personnel")    # <-- CIFT dekorator!
def create_personnel(p: PersonnelModel):
```

Ayni route iki kez tanimlanmis. FastAPI bunu kabul eder ama OpenAPI dokumaninda cakisma olusturur ve bazi HTTP istemcilerde beklenmedik davranis gosterebilir.

**Cozum:** Fazla dekoratoru silin.

---

### 6. `customer_balance` - Hata Durumunda `conn` Kapatilmiyor
> [!NOTE]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L226-L296)

```python
def get_customer_balance(cid: int):
    try:
        conn = DB.get_conn()
        ...
        conn.close()       # sadece basarili path'te kapaniyor
        return {"balance": balance}
    except Exception as e:
        logger.error(...)
        return {"balance": 0.0}
        # conn BURADA KAPATILMIYOR!
```

**Cozum:** `finally: conn.close()` eklenmeli.

---

### 7. `customer_history` - Cursor Yeniden Kullanimi (Tehlikeli)
> [!NOTE]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py#L324-L327)

```python
for row in cursor.fetchall():
    cursor.execute("SELECT SUM(...) FROM used_parts WHERE tracking_no = ?", (row['tracking_no'],))
    part_cost = cursor.fetchone()[0] or 0.0
```

Dis dongu icinde **ayni cursor** ile ic sorgu yapiliyor. `fetchall()` kullanildigi icin sorun olmuyor (tum sonuclar belleye aliniyor), ancak biri bunu `for row in cursor:` olarak degistirirse sonuclar kesilir. Riskli bir kalip.

---

### 8. Tum Lokal API Endpoint'leri Auth'suz
> [!WARNING]
> **Dosya:** [src/utils/server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/server_main.py)

**Hicbir endpoint'te** kimlik dogrulamasi yok. Lokal API `0.0.0.0:8000` uzerinde aciliyor, yani ayni agdaki herhangi bir cihaz erisebilir. Bu demek ki:
- Musteri verileri okunabilir
- Yeni kayitlar eklenebilir/silinebilir
- Muhasebe verilerine erisilebilir
- Backup yuklenebilir

Kok `server_main.py`'de JWT token sistemi var ama `src/utils/server_main.py`'de hic yok.

**Not:** Eger `local_api_host()` fonksiyonu `127.0.0.1` donduruyorsa sorun azalir (sadece lokal erisim). Ama `0.0.0.0` ise agdaki herkes erisebilir.

---

## ORTA - Kok server_main.py (Bulut Sunucu) Sorunlari

### 9. Hardcoded Legacy Token Bypass
> [!CAUTION]
> **Dosya:** [server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/server_main.py#L302-L303)

```python
if token == "Bearer premium_bulut_secure_token_v3":
    return {"user_id": 0, "username": "legacy_user", "role": "Admin"}
```

Bu sabit token ile JWT olmadan tam Admin yetkisi alinir. Sunucu internete aciksa ciddi guvenlik acigi.

---

### 10. Setup Endpoint Tekrar Calistirma Korunmasi Yok
> [!WARNING]
> **Dosya:** [server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/server_main.py#L1035-L1093)

`POST /api/setup/complete`:
- Auth yok
- `setup_completed == true` kontrolu yok
- Herkes yeni admin olusturabilir

---

### 11. 13 Bulut Endpoint Auth'suz
> [!WARNING]
> **Dosya:** [server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/server_main.py)

`change-password`, `accounting`, `parts`, `personnel`, `reminders`, `announcements`, `logistics`, `customer_history` endpoint'lerinde `Depends(verify_token)` yok.

---

### 12. SHA-256 Sifre Hash (Salt'siz, Zayif)
> [!NOTE]
> **Dosya:** [server_main.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/server_main.py#L243)

```python
hashed_pw = hashlib.sha256(data.password.encode()).hexdigest()
```

Salt'siz SHA-256 GPU ile kolayca kirilamaz. bcrypt'e gecilmeli.

---

## DUSUK - Performans ve Kod Kalitesi

### 13. N+1 Sorgu Performans Sorunu (Her Iki server_main'de)

Musteri listesi ve bakiye hesaplamalarinda her musteri icin **5+ SQL sorgusu** calistiriliyor. 100 musteri = 500+ sorgu. Tek JOIN ile cozulebilir.

---

### 14. Bare `except:` Bloklari (Hata Yutma)

Asagidaki **aktif** dosyalarda `except:` (tip belirtmeden) kullaniyor - `KeyboardInterrupt` ve `SystemExit` dahil tum hatalari yakalar:

| Dosya | Satir |
|-------|-------|
| [customer_360_dialog.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/ui/dialogs/customer_360_dialog.py#L253) | 253 |
| [_accounting_func_mixin.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/ui/pages/_accounting_func_mixin.py#L49) | 49, 55, 58 |
| [_dashboard_data_mixin.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/ui/pages/_dashboard_data_mixin.py#L326) | 326 |
| [_dashboard_dialog_mixin.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/ui/pages/_dashboard_dialog_mixin.py#L103) | 103, 110 |
| [_dashboard_func_mixin.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/ui/pages/_dashboard_func_mixin.py#L438) | 438, 459 |
| [accounting_page.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/ui/pages/accounting_page.py#L283) | 283 |
| [_pdf_invoice_mixin.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/_pdf_invoice_mixin.py#L283) | 283 |
| [_pdf_service_mixin.py](file:///c:/Users/yedek/Desktop/yapay%20zeka/AYEC%20Pro/src/utils/_pdf_service_mixin.py#L101) | 101, 103 |

---

## Ozet

| # | Sorun | Dosya | Onem |
|---|-------|-------|------|
| 1 | `stdout` buffer detach - surekli log hatasi | `src/utils/server_main.py:6-9` | **KRITIK** |
| 2 | `conn.close()` finally blogu yok (leak) | `src/utils/server_main.py:291,381` | **KRITIK** |
| 3 | Tracking number race condition | `src/utils/server_main.py:408-411` | YUKSEK |
| 4 | Stok negatif kontrol yok | `src/utils/server_main.py` | YUKSEK |
| 5 | Cift `@app.post` dekoratoru | `src/utils/server_main.py:555-556` | ORTA |
| 6 | Balance - hata durumunda conn acik | `src/utils/server_main.py:226-296` | ORTA |
| 7 | Cursor yeniden kullanimi | `src/utils/server_main.py:324-327` | DUSUK |
| 8 | Tum lokal API auth'suz | `src/utils/server_main.py` | ORTA |
| 9 | Hardcoded legacy token | `server_main.py:302` | YUKSEK |
| 10 | Setup tekrar calistirma korunmasi yok | `server_main.py:1035` | YUKSEK |
| 11 | 13 bulut endpoint auth'suz | `server_main.py` | ORTA |
| 12 | SHA-256 salt'siz hash | `server_main.py:243` | ORTA |
| 13 | N+1 sorgu performans | her iki server_main | DUSUK |
| 14 | Bare `except:` bloklari | src/ui/* , src/utils/* | DUSUK |

> [!TIP]
> **En acil 3 duzeltme:**
> 1. Buffer detach hatasini duzelt (surekli log hatasini durdurur)
> 2. `finally: conn.close()` ekle (connection leak'i onler)
> 3. Cift dekoratoru sil (temiz bir duzeltme)
