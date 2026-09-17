# AYEC Pro - Saha Takip APK Oluşturma Rehberi

Bu rehber, saha personelinin kullanacağı mobil uygulamanın APK haline getirilmesi ve sunucuya dağıtımı için gerekli adımları içerir.

## 1. APK Oluşturma (Build)

Uygulama **React Native (Expo)** ile hazırlanmıştır. APK almak için iki ana yöntem vardır:

### A. Bulut Üzerinden (En Kolay)
Expo'nun (EAS) bulut sistemini kullanarak bilgisayarınıza Android SDK kurmadan APK alabilirsiniz:
1. `npm install -g eas-cli`
2. `eas login`
3. `eas build -p android --profile preview`
4. İşlem bittiğinde size verilecek olan `.apk` linkini indirin.

### B. Yerel Bilgisayarda (Android Studio Gerektirir)
1. `npx expo run:android` komutu ile yerel test yapabilirsiniz.
2. `cd android && ./gradlew assembleRelease` (Android klasörü oluşturulduktan sonra)

---

## 2. API Dağıtımı (Domain / Host)

Uygulamanın çalışması için merkezi API sunucusunun internete açık olması gerekir.

### Adımlar:
1. **Dosyaları Yükleyin**: `api_server.py`, `ayecpro.db` ve `requirements.txt` dosyalarını sunucunuza (VPS/Dedicated) yükleyin.
2. **Bağımlılıkları Kurun**: `pip install -r requirements.txt` (Sunucu üzerinde)
3. **Servisi Başlatın**: 
   - `python api_server.py`
   - *Tavsiye*: `gunicorn` veya `pm2` gibi bir proses yöneticisi ile başlatın:
     `pm2 start api_server.py --interpreter python3`
4. **Proxy Yapılandırması (Nginx)**: Domain adresinizi (örn: `api.siteniz.com`) 5000 portuna yönlendirin.

### ⚠️ ÖNEMLİ: Mobil Uygulama Bağlantısı
Uygulamanın sunucuya bağlanabilmesi için `src/api/client.js` dosyasındaki `API_URL` değişkenini kendi domain adresinizle güncelleyip APK'yı öyle oluşturmalısınız:

```javascript
const API_URL = 'https://saha-api.deneme.com/api/v1';
```

---

## 3. İlk Kurulum ve Kullanım
1. APK'yı personelin telefonuna kurun.
2. Masaüstü uygulamasından **Personel Yönetimi** kısmına gidin.
3. Personel için bir e-posta ve şifre belirleyin.
4. Personel telefonundan bu bilgilerle giriş yaptığında harita üzerinde anlık takibi başlayacaktır.

