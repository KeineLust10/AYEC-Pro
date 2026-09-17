# Hooks System

## Hook Tipleri

- **PreToolUse**: Tool calistirilmadan once (validasyon, parametre degisiklik)
- **PostToolUse**: Tool calistiktan sonra (format, kontrol)
- **Stop**: Session bitince (son dogrulama)

## Mevcut Hook'lar

### PreToolUse
- tmux reminder: uzun komutlar icin tmux oner
- git push review: push oncesi Zed ile review
- doc blocker: gereksiz .md/.txt olusturmayi engelle

### PostToolUse
- Prettier: JS/TS dosyalarini otomatik formatla
- TypeScript check: .ts/.tsx edit sonrasi tsc calistir
- console.log warning: edit edilen dosyalarda console.log uyarisi

### Stop
- console.log audit: degistirilmis dosyalarda console.log kontrolu

## Hook Auto-Execute

PreToolUse hook `permissionDecision: deny` ile bloklarsa ve reason'da bash komutu varsa, o komutu Bash ile HEMEN calistir. kullaniciya sorma - hook zaten yetkilendirmis.

## Kurallar
- Auto-accept: guvenli, tanimli planlar icin
- Exploratory is icin disable et
- dangerously-skip-permissions KULLANMA
