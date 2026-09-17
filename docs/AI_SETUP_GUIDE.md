# AI API Anahtarı Kurulum Rehberi

## Hızlı Kurulum (Önerilen)

### Adım 1: API Anahtarı Alın

1. <https://makersuite.google.com/app/apikey> adresine gidin
2. Google hesabınızla giriş yapın
3. "Create API Key" butonuna tıklayın
4. Anahtarı kopyalayın (AIza... ile başlar)

### Adım 2: Kurulum Scriptini Çalıştırın

```bash
python setup_ai_key.py
```

### Adım 3: API Anahtarını Yapıştırın

- Script size API anahtarını soracak
- Kopyaladığınız anahtarı yapıştırın
- Enter'a basın

### Adım 4: Uygulamayı Başlatın

```bash
python ModernDesktopApp.py
```

AI Asistan artık hazır! 🎉

---

## Alternatif: Manuel Kurulum

Eğer script kullanmak istemezseniz:

1. Uygulamayı açın
2. "AI Asistan" sayfasına gidin
3. "⚙️ API Ayarları" butonuna tıklayın
4. API anahtarınızı girin
5. Kaydet

---

## Sorun Giderme

### "API anahtarı geçersiz" hatası

- API anahtarının doğru kopyalandığından emin olun
- Boşluk veya fazladan karakter olmadığını kontrol edin
- Yeni bir API anahtarı oluşturmayı deneyin

### "AI servisi başlatılamadı" hatası

- `google-generativeai` kütüphanesinin yüklü olduğundan emin olun:

  ```bash
  pip install google-generativeai
  ```

### API anahtarını değiştirmek

- `setup_ai_key.py` scriptini tekrar çalıştırın
- Veya uygulama içinden "⚙️ API Ayarları" ile güncelleyin

---

## Güvenlik Notları

- API anahtarınızı kimseyle paylaşmayın
- Anahtarı public repository'lere yüklemeyin
- Düzenli olarak anahtarınızı yenileyin
- Şüpheli aktivite görürseniz anahtarı iptal edin

---

## Maliyet

Google Gemini Pro:

- **Ücretsiz** (rate limit var)
- Günlük 60 istek/dakika
- Aylık limitsiz kullanım

Daha fazla bilgi: <https://ai.google.dev/pricing>
