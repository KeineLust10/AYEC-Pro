# Safety & Quality

## Git Kurallari

### Commit Format
```
<type>: <description>
```
Types: feat, fix, refactor, docs, test, chore, perf, ci

### Onay Gerektiren Komutlar (MUTLAKA SOR)
git checkout, git reset, git clean, git stash, git rebase, git merge, git push, git commit

### Guvenli Komutlar (sormadan calistir)
git status, git log, git diff, git branch (list), git show, git blame

### PR Workflow
1. Tum commit history'yi analiz et
2. `git diff [base-branch]...HEAD` ile degisiklikleri gor
3. Kapsamli PR ozeti yaz, test plani ekle

## Silme Kurallari (MUTLAKA SOR)

rm, rm -rf, rmdir, unlink → kullaniciya sor, onay bekle.
"Archive" denirse silme, tasI (mv X archive/).

## Security

### Commit Oncesi Kontrol
- [ ] Hardcoded secret yok (API key, password, token)
- [ ] User input valide edilmis
- [ ] SQL injection onlenmis (parameterized query)
- [ ] XSS onlenmis
- [ ] Hata mesajlari hassas veri sizdirmiyor

### Secret Yonetimi
```typescript
// YANLIS
const apiKey = "sk-proj-xxxxx"

// DOGRU
const apiKey = process.env.OPENAI_API_KEY
if (!apiKey) throw new Error('OPENAI_API_KEY not configured')
```

Security sorunu bulunursa: DURDUR → security-reviewer cagir → CRITICAL duzelt → rotate secrets

## Testing

### TDD Zorunlu
1. Test yaz (RED)
2. Test FAIL etmeli
3. Minimal implementasyon (GREEN)
4. Test PASS etmeli
5. Refactor (IMPROVE)
6. Coverage %80+

### Test Tipleri
- Unit: fonksiyonlar, utility'ler
- Integration: API endpoint, DB
- E2E: kritik kullanici akislari (Playwright)

Agent'lar: tdd-guide (yeni feature), e2e-runner (Playwright)
