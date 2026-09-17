# Proactive Agent Delegation

Main context'i temiz tut, agent'lara delege et.

## Pattern Tespiti

| Pattern | Sinyal | Aksiyon |
|---------|--------|--------|
| Birden fazla is | "X ve Y", "ayrica" | Paralel agent'lar oner |
| Arastirma lazim | "nasil", "ne", "bul" | scout/oracle spawn et |
| Implementasyon | "ekle", "implement et" | /build workflow'una yonlendir |
| Bug/sorun | "fix", "bozuk", "calismiyor" | /fix workflow'una yonlendir |
| Kesfet | "anla", "incele" | scout cagir |

## Agent Secimi

| Gorev | Kullan | Kullanma |
|-------|--------|----------|
| Codebase kesfetme | scout | Explore (Haiku, yanlis sonuc verir) |
| Dis arastirma | oracle | Explore |
| Pattern bulma | scout | Explore |
| Dokumantasyon | claude-code-guide | Explore |

Opus'taysan ve yuksek dogruluk lazimsa, agent yerine direkt Grep/Glob/Read kullan.

## Main Context = Sadece Koordinasyon

**Agent'lara ver:** 3+ dosya okuma, dis arastirma, implementasyon, test calistirma, debug
**Main'de tut:** Kullanici niyetini anlama, workflow secimi, agent koordinasyonu, ozet sunma

## Workflow Zincirleme

| Biten | Oner |
|-------|------|
| /explore | "/build brownfield?" |
| /plan | "/premortem?" |
| /fix | "/commit?" |

## Delegasyon ZORUNLU Durumlar

Bu durumlarda MUTLAKA agent spawn et, main context'te YAPMA:

| Durum | Agent | Neden |
|-------|-------|-------|
| 5+ dosya okuma/analiz | scout | Main context kirlenmesin |
| Bug investigation | sleuth | Izole debug context |
| 3+ dosya edit | kraken veya spark | Paralel calisma |
| Test yazma/calistirma | tdd-guide + arbiter | Test context ayri |
| Security audit | security-reviewer | Uzman goz |
| Build hatasi | build-error-resolver | Hizli fix |
| Code review | code-reviewer | Objektif review |
| Dependency analiz | migrator | CVE + impact analiz |
| Tech debt tarama | janitor | Codebase health |

## Main Context Limitleri

Main context SADECE bunlari yapsin:
- Kullanici niyetini anla
- Uygun workflow/agent sec
- Agent sonuclarini ozetle
- Kullaniciya sun

Main context BUNLARI YAPMASIN:
- 3'ten fazla dosya okuma (scout'a ver)
- Uzun debug session'lari (sleuth'a ver)
- Multi-file edit (kraken/spark'a ver)
- Test yazma/calistirma (tdd-guide'a ver)
- Detayli code review (code-reviewer'a ver)

## Asiri Delege Etme

Delege etme: tek basit soru, 1-2 dosya okuma, kullanici direkt cevap istiyorsa, hiz onemliyse.

**ONEMLI:** "Delegasyon ZORUNLU Durumlar" tablosu her zaman onceliklidir. Hiz istense bile security audit, dependency CVE, veya 5+ dosya analizi durumlarinda MUTLAKA delege et.
