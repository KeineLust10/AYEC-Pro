# Cross-Project Learning

Pattern'ler proje bazinda tag'lenir, 2+ projede tekrarlayan pattern'ler global'e promote edilir.

## Nasil Calisir

1. **passive-learner** her instinct'e `project` hash ve `projectName` ekler
2. **instinct-consolidator** session sonunda:
   - Legacy `mature-instincts.json` yazar (backward compat)
   - Proje-ozel `projects/{hash}/instincts/mature-instincts.json` yazar
   - 2+ projede, 5+ toplam tekrar → `global-instincts.json`'a promote eder
3. **instinct-loader** session basinda:
   - Proje-ozel pattern'leri inject eder (PROJECT PATTERNS)
   - Global pattern'leri inject eder (GLOBAL PATTERNS)
   - Proje dosyasi yoksa legacy fallback kullanir

## Dosya Yapisi

```
~/.claude/
  instincts.jsonl              # Ham (+ project, projectName)
  mature-instincts.json        # Legacy global
  global-instincts.json        # Cross-project promoted
  instinct-projects.json       # Proje registry
  projects/{hash}/instincts/
    mature-instincts.json      # Proje-ozel mature
```

## CLI

```bash
node ~/.claude/hooks/dist/instinct-cli.mjs portfolio      # Tum projeler
node ~/.claude/hooks/dist/instinct-cli.mjs global          # Global pattern'ler
node ~/.claude/hooks/dist/instinct-cli.mjs project <isim>  # Proje detay
node ~/.claude/hooks/dist/instinct-cli.mjs stats           # Istatistikler
```

## Promotion Kurallari

- 2+ projede gorulmus
- Toplam 5+ tekrar
- Ornek: `add-error-handling` 3x Proje A + 4x Proje B = 7 toplam → PROMOTE
