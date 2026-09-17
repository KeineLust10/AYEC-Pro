# Dev-QA Loop - Surekli Kalite Dongusu

Her task implement edildikten sonra QA dogrulamasi ZORUNLU.
Agency-agents NEXUS framework'unden adapte edildi.

## Core Mekanik

```
HER task ICIN:
  1. ASSIGN → Uygun developer agent'a ver (assignment-matrix'e bak)
  2. IMPLEMENT → Agent task'i implement eder
  3. QA → @code-reviewer + @verifier kontrol eder
  4. KARAR:
     PASS → Task tamamlandi, sonraki task'a gec
     FAIL (deneme < 3) → QA feedback'i developer'a gonder, tekrar dene
     FAIL (deneme >= 3) → ESCALATE (reassign, parcala, ertele)
  5. STATUS → Pipeline durumunu guncelle
```

## QA Kontrol Listesi

Her task icin su kontroller yapilir:

| # | Kontrol | Agent |
|---|---------|-------|
| 1 | Kod kalitesi, pattern uyumu | @code-reviewer |
| 2 | Build basarili | @verifier (build) |
| 3 | Testler geciyor | @verifier (test) |
| 4 | Security check | @security-reviewer (auth/data isleri) |
| 5 | Type check | @verifier (tsc/pyright) |

## Retry Logic

### Deneme 1 basarisiz:
- QA feedback'ini developer agent'a gonder (handoff-templates #3)
- Agent SADECE belirtilen sorunlari duzeltir
- Yeni ozellik EKLEMEZ
- Tekrar QA'ye gonder

### Deneme 2 basarisiz:
- Birikimli feedback gonder
- Agent dogru secim mi? Farkli agent daha uygun olabilir
- Daha fazla context ekle
- Tekrar QA

### Deneme 3 basarisiz → ESCALATION:
- Escalation mesaji gonder (handoff-templates #4)
- Secenekler:
  a) **Reassign** → Farkli agent'a ver (kraken → spark, veya tersi)
  b) **Decompose** → Task'i daha kucuk parcalara bol
  c) **Revise** → Yaklasimi/mimariyi degistir
  d) **Defer** → Sonraki sprint'e ertele
  e) **Accept** → Mevcut durumu kabul et, bilinen sinirlamalari dokumante et

## Paralel Task Yonetimi

```
BAGIMSIZ task'lar varsa:
  → Farkli agent'lara AYNI ANDA ver
  → Her biri bagimsiz QA dongusu calistirir
  → Tamamlananlar dependency sirasina gore merge edilir

BAGIMLI task varsa:
  → Dependency QA'den gecene kadar BEKLE
  → Sonra bagimli task'i ata
  → Handoff'a dependency context'ini ekle
```

## Quality Gate (Phase Gecisi)

Bir phase'den digerine gecmek icin TUM kriterler saglanmali:

| # | Kriter | Kanit |
|---|--------|-------|
| 1 | Tum task'lar QA'den gecti | code-reviewer + verifier raporlari |
| 2 | Critical/high bug yok | Bug listesi temiz |
| 3 | Build basarili | verifier PASS |
| 4 | Test coverage yeterli | Coverage raporu |
| 5 | Security audit temiz | security-reviewer raporu |

## Maestro Entegrasyonu

Maestro `/swarm` calistirdiginda bu donguyu otomatik uygular:
- Phase 2 (Gelistirme) sirasinda her task icin Dev-QA loop calisir
- Phase 3 (Review) tum task'lar QA'den gectikten sonra baslar
- Phase gecislerinde quality gate kontrol edilir

## Metrikler (Comms Uzerinden Takip)

- Task first-pass QA orani (ilk denemede gecen)
- Ortalama retry sayisi per task
- Escalation sayisi
- Phase tamamlanma suresi
