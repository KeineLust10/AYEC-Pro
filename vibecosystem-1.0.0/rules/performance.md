# Performance & Model Selection

## Model Kuralları

- Agent spawn'larken `model` parametresini OMIT ET (parent'tan inherit eder)
- Haiku KULLANMA. Hicbir agent'ta haiku kullanma
- Opus: karmasik mimari kararlar, arastirma, analiz
- Sonnet: ana gelistirme, orchestration

## Context Window

Son %20'ye girme:
- Buyuk refactoring, multi-file feature, karmasik debug
- Bu tarz isleri agent'lara delege et

## Ultrathink + Plan Mode

Karmasik islerde:
1. Plan Mode ac
2. Split role sub-agent'lar kullan
3. Birden fazla tur kritik yap

## Build Hatasi

1. **build-error-resolver** agent cagir
2. Hata mesajlarini analiz et
3. Parcali duzelt, her fix sonrasi verify et
