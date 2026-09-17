AYEC PRO - KURULUM HAZIRLAMA KILAVUZU
=====================================
Version: 68.1.0
Tarih: 2026-02-14

GEREKSİNİMLER
-------------
1. Python 3.8 veya üzeri
2. PyInstaller (pip install pyinstaller)
3. Inno Setup 6 (https://jrsoftware.org/isdl.php)
4. Tüm Python bağımlılıkları (requirements.txt)

HIZLI BAŞLANGIÇ
---------------
1. PowerShell'de proje klasörüne gidin
2. Şu komutu çalıştırın:
   .\BuildSetup.ps1

VEYA

1. build_setup.bat dosyasını çift tıklayın

KURULUM ADIMLARI
----------------
BuildSetup.ps1 scripti otomatik olarak şunları yapar:

1. Gereksinimleri kontrol eder (Python, PyInstaller, Inno Setup)
2. Önceki derlemeleri temizler (build, dist, Setup_Output)
3. Gerekli dosyaları kontrol eder
4. Python bağımlılıklarını kontrol eder
5. Masaüstü uygulamasını derler (AYECPro_App.exe)
6. Sunucu uygulamasını derler (AYECPro_Server.exe)
7. Kurulum paketini oluşturur (AYECPro_Setup_v68.1.0.exe)

ÇIKTI
-----
Kurulum dosyası şu konumda oluşturulur:
Setup_Output\AYECPro_Setup_v68.1.0.exe

PARAMETRELER
------------
BuildSetup.ps1 aşağıdaki parametreleri destekler:

-SkipBuild      : Masaüstü uygulamasını derleme
-SkipServer     : Sunucu uygulamasını derleme
-CleanOnly      : Sadece temizleme yap (derleme yapma)

Örnek:
.\BuildSetup.ps1 -SkipServer
.\BuildSetup.ps1 -CleanOnly

SORUN GİDERME
-------------
1. "Python bulunamadı" hatası:
   - Python'u PATH'e ekleyin veya tam yolunu belirtin

2. "PyInstaller bulunamadı" hatası:
   - Script otomatik yüklemeye çalışır, manuel: pip install pyinstaller

3. "Inno Setup bulunamadı" hatası:
   - Inno Setup 6'yı kurun: https://jrsoftware.org/isdl.php
   - Varsayılan konum: C:\Program Files (x86)\Inno Setup 6\

4. Derleme hataları:
   - build.log dosyasını kontrol edin
   - requirements.txt'deki tüm paketlerin yüklü olduğundan emin olun

5. Kurulum paketi oluşturulamıyor:
   - setup.iss dosyasının mevcut olduğundan emin olun
   - Inno Setup'ın doğru kurulduğunu kontrol edin

DOSYA YAPISI
------------
Proje kök dizini:
├── Main.py                    # Ana giriş noktası
├── ModernDesktopApp.py        # Masaüstü uygulaması
├── server_main.py             # Sunucu uygulaması
├── AYECPro_App.spec           # PyInstaller spec (Masaüstü)
├── AYECPro_Server.spec        # PyInstaller spec (Sunucu)
├── setup.iss                  # Inno Setup scripti
├── BuildSetup.ps1             # Otomatik build scripti
├── build_setup.bat            # Batch wrapper
├── requirements.txt           # Python bağımlılıkları
├── assets\                    # Varlıklar (ikonlar, vb.)
├── src\                       # Kaynak kod
├── backend\                   # Backend API
├── web_interface\             # Web arayüzü
└── Setup_Output\             # Çıktı klasörü (oluşturulur)

VERSİYON BİLGİSİ
----------------
Versiyon bilgisi version.txt dosyasından okunur.
setup.iss içinde #define AppVersion ile de tanımlanabilir.

LİSANS
------
Bu proje için lisans bilgileri LICENSE.txt dosyasında bulunmaktadır.

DESTEK
------
Sorularınız için: ayecpro@gmail.com
Web: https://www.bulutteknoloji.com.tr
