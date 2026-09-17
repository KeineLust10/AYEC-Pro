# PRD: Kod Kalitesi ve Mod?ler Refactor Program?

## Ama?
- Kod taban?n? s?rd?r?lebilir hale getirmek.
- Dosya ba??na 1000 sat?r limitini zorunlu kural yapmak.
- Exception y?netimini g?venli ve izlenebilir hale getirmek.
- Test kapsam?n? otomatik + manuel do?rulama ile standartla?t?rmak.

## Kapsam
- `src/` alt?ndaki t?m Python mod?lleri.
- ?ncelik: `database.py`, `settings_page.py`, `modern_login_window.py`, `bank_page.py`, `accounting_page.py`, `theme_manager.py`.

## Zorunlu M?hendislik Kurallar?
1. Dosya sat?r limiti: `<=1000`.
2. Geni? `except` yasa??: `except Exception` sadece s?n?r katmanda ve log + context + fallback ile.
3. `except: pass` yasa??.
4. Refactor sonras? test zorunlu: unit + integration + UI smoke.
5. PR merge ?ncesi otomatik kalite raporu.

## Fonksiyonel Gereksinimler
- FR-1: Sat?r limiti ihlal raporu otomatik ?retilmeli.
- FR-2: Exception anti-pattern raporu otomatik ?retilmeli.
- FR-3: Her refactor dalgas?nda hedef dosyada ihlal say?s? d??meli.
- FR-4: UI kritik ak??lar? manuel checklist ile do?rulanmal?.

## Teknik Tasar?m
### A?ama 1: Denetim ve Envanter
- `docs/QUALITY_RULES_AUDIT_2026-02-23.md` referans al?n?r.
- P0/P1/P2 ?nceliklendirme ile backlog a??l?r.

### A?ama 2: Mod?ler Par?alama
- B?y?k dosyalar i?in mod?l ?emas?:
  - `database.py` -> `src/db/services/*`
  - `settings_page.py` -> `src/ui/pages/settings_sections/*`
  - `modern_login_window.py` -> `src/ui/login/*`
- Her par?alama ad?m?nda davran?? uyumlulu?u korunur.

### A?ama 3: Exception Refactor
- Pattern d?n???mleri:
  - `except: pass` -> spesifik exception + warning log
  - `except Exception` -> `ValueError`, `TypeError`, `sqlite3.Error`, `KeyError` vb.
- Sessiz fallbackler sadece bilin?li degrade senaryosunda kal?r ve yorumlan?r.

### A?ama 4: Test Zinciri
- Unit: veri d?n??t?r?c?ler, parser, yard?mc? fonksiyonlar.
- Integration: DB CRUD ve i? ak??? tetiklemeleri.
- UI smoke: Randevu, Gelir/Gider, Yeni Servis, Ayarlar, Banka Hesaplar?.
- Manuel: tema ge?i?i + dialog okunabilirlik + combobox davran??lar?.

## Ba?ar? Kriterleri
- SK-1: 1000+ sat?r dosya say?s? her sprintte azal?r.
- SK-2: `except: pass` kullan?m say?s? 0.
- SK-3: Geni? `except` say?s? hedef dosyalarda %70+ d??er.
- SK-4: Kritik ak??larda regresyon yok.

## Riskler
- B?y?k dosya b?lmelerinde import d?ng?s?.
- UI sinyal ba?lant?lar?n?n k?r?lmas?.
- DB katman?nda geri uyumluluk sorunlar?.

## Risk Azaltma
- Her mod?ler ta??ma sonras? py_compile + smoke test.
- Ge?i?te adapt?r katman? kullan?m?.
- Fonksiyon imza uyumlulu?u korunmas?.

## Teslim Plan?
1. Dalg?-1 (P0): `database.py` exception daraltma ve alt mod?llere ay?rma ba?lang?c?.
2. Dalg?-2 (P0): `settings_page.py` ve `modern_login_window.py` par?alama.
3. Dalg?-3 (P1): `bank_page.py`, `accounting_page.py`, `theme_manager.py` temizli?i.
4. Dalg?-4 (P2): kalan dialog/panel refactor.

## Manuel Test Checklist (?zet)
- [ ] Banka Hesaplar?: yeni/d?zenle/pasifle?tir/sil/?oklu i?lem.
- [ ] Gelir/Gider: banka bakiyesi tetikleme.
- [ ] Randevu ve Servis Formu dialog okunabilirli?i (AYEC/Bulut/Forest/Nord).
- [ ] Ayarlar sayfalar?: b?l?m ge?i?i, men? metinleri, tema renkleri.

## Kabul Kriterleri
- T?m kalite raporlar? g?ncel.
- Kritik hatalar kapal?.
- Test raporu ve manuel kontrol kay?tlar? mevcut.
