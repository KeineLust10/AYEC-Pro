# AI Asistan Online Entegrasyon Rehberi

## Genel Bakış

AI Asistan'ı online hale getirmek için harici AI API entegrasyonu gerekiyor.

## Seçenek 1: OpenAI API (ChatGPT)

### 1. API Key Alma

1. <https://platform.openai.com> adresine git
2. Hesap oluştur
3. API Keys bölümünden yeni key oluştur
4. Key'i güvenli bir yerde sakla

### 2. Kütüphane Kurulumu

```bash
pip install openai
```

### 3. Kod Entegrasyonu

`src/ui/pages/ai_assistant_page.py` dosyasına ekle:

```python
import openai

class AIAssistantPage(QWidget):
    def __init__(self, db):
        super().__init__(db)
        # OpenAI API key (güvenli şekilde saklanmalı)
        openai.api_key = "sk-your-api-key-here"
    
    def search_question(self):
        question = self.search_input.text()
        
        if not question:
            return
        
        try:
            # OpenAI API çağrısı
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sen bir teknik servis asistanısın. Türkçe cevap ver."},
                    {"role": "user", "content": question}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            self.answer_area.setMarkdown(answer)
            
        except Exception as e:
            self.answer_area.setMarkdown(f"❌ **Hata**: {str(e)}")
```

---

## Seçenek 2: Google Gemini API

### 1. API Key Alma

1. <https://makersuite.google.com/app/apikey> adresine git
2. Google hesabıyla giriş yap
3. "Create API Key" tıkla
4. Key'i kopyala

### 2. Kütüphane Kurulumu

```bash
pip install google-generativeai
```

### 3. Kod Entegrasyonu

```python
import google.generativeai as genai

class AIAssistantPage(QWidget):
    def __init__(self, db):
        super().__init__(db)
        # Gemini API key
        genai.configure(api_key="your-api-key-here")
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def search_question(self):
        question = self.search_input.text()
        
        if not question:
            return
        
        try:
            # Gemini API çağrısı
            prompt = f"Sen bir teknik servis asistanısın. Türkçe cevap ver.\n\nSoru: {question}"
            response = self.model.generate_content(prompt)
            
            answer = response.text
            self.answer_area.setMarkdown(answer)
            
        except Exception as e:
            self.answer_area.setMarkdown(f"❌ **Hata**: {str(e)}")
```

---

## Güvenlik Önerileri

### API Key Yönetimi

1. **Asla kodda hardcode etme**
2. **Ortam değişkeni kullan**:

```python
import os
api_key = os.getenv('OPENAI_API_KEY')
```

1. **Veya ayarlar dosyasında sakla**:

```python
# settings.json
{
    "ai_api_key": "your-key-here",
    "ai_provider": "openai"  # or "gemini"
}
```

---

## Maliyet Kontrolü

### OpenAI Fiyatlandırma

- GPT-3.5-turbo: ~$0.002 / 1K tokens
- GPT-4: ~$0.03 / 1K tokens

### Gemini Fiyatlandırma

- Gemini Pro: Ücretsiz (rate limit var)
- Gemini Pro Vision: Ücretsiz

### Öneri

Başlangıç için **Gemini Pro** kullan (ücretsiz)

---

## Uygulama Adımları

1. ✅ API key al (OpenAI veya Gemini)
2. ✅ Kütüphaneyi kur (`pip install`)
3. ✅ `ai_assistant_page.py` dosyasını güncelle
4. ✅ API key'i güvenli şekilde sakla
5. ✅ Test et
6. ✅ Hata yönetimi ekle
7. ✅ Rate limiting ekle (çok fazla istek önleme)

---

## Örnek Tam Kod

```python
import os
import google.generativeai as genai
from PyQt5.QtWidgets import QMessageBox

class AIAssistantPage(QWidget):
    def __init__(self, db):
        super().__init__(db)
        self.db = db
        self.setup_ui()
        
        # Gemini API kurulumu
        try:
            api_key = os.getenv('GEMINI_API_KEY') or self.db.get_setting('gemini_api_key', '')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.ai_enabled = True
            else:
                self.ai_enabled = False
        except Exception as e:
            self.ai_enabled = False
            print(f"AI initialization error: {e}")
    
    def search_question(self):
        question = self.search_input.text().lower()
        
        if not question:
            return
        
        # Önce local FAQ'de ara
        for key, answer in self.faq.items():
            if key in question:
                self.answer_area.setMarkdown(answer)
                return
        
        # Sonra bilgi bankasında ara
        articles = self.db.get_kb_articles(question)
        if articles:
            result = f"**Bilgi Bankasında Bulunan Makaleler:**\n\n"
            for art in articles[:3]:
                result += f"📄 **{art[1]}**\n{art[2][:200]}...\n\n"
            self.answer_area.setMarkdown(result)
            return
        
        # En son AI'ya sor (eğer aktifse)
        if self.ai_enabled:
            try:
                self.answer_area.setMarkdown("🤖 **AI düşünüyor...**")
                QApplication.processEvents()  # UI güncelle
                
                prompt = f"""Sen bir teknik servis asistanısın. 
                Türkçe, kısa ve net cevap ver.
                
                Soru: {question}"""
                
                response = self.model.generate_content(prompt)
                answer = f"🤖 **AI Asistan:**\n\n{response.text}"
                self.answer_area.setMarkdown(answer)
                
            except Exception as e:
                self.answer_area.setMarkdown(
                    f"❌ **AI Hatası**: {str(e)}\n\n"
                    "Lütfen daha sonra tekrar deneyin."
                )
        else:
            self.answer_area.setMarkdown(
                "❌ **Sonuç bulunamadı**\n\n"
                "AI asistan aktif değil. Ayarlardan API key ekleyin."
            )
```

---

## Test

1. API key'i ayarla
2. Uygulamayı başlat
3. AI Asistan'ı aç
4. Bir soru sor
5. AI cevabını gör

**Başarılı! 🎉**
