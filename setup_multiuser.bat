@echo off
echo ============================================================
echo Premium Bulut - Cok Kullanicili Giris Sistemi Kurulumu
echo ============================================================
echo.

echo [1/4] PyJWT kutuphanesi yukleniyor...
pip install PyJWT
if errorlevel 1 (
    echo HATA: PyJWT yuklenemedi!
    pause
    exit /b 1
)
echo [OK] PyJWT yuklendi
echo.

echo [2/4] Veritabani migration calistiriliyor...
python migrate_users_table.py
if errorlevel 1 (
    echo HATA: Migration basarisiz!
    pause
    exit /b 1
)
echo [OK] Migration tamamlandi
echo.

echo [3/4] Dosya izinleri kontrol ediliyor...
if not exist "src\ui\pages\settings_widgets\user_management.py" (
    echo HATA: user_management.py bulunamadi!
    pause
    exit /b 1
)
if not exist "src\ui\dialogs\login_dialog.py" (
    echo HATA: login_dialog.py bulunamadi!
    pause
    exit /b 1
)
echo [OK] Tum dosyalar mevcut
echo.

echo [4/4] Sistem kontrolu yapiliyor...
python -c "import jwt; print('[OK] PyJWT calisiyor')"
if errorlevel 1 (
    echo HATA: PyJWT import edilemiyor!
    pause
    exit /b 1
)
echo.

echo ============================================================
echo KURULUM TAMAMLANDI!
echo ============================================================
echo.
echo Sonraki adimlar:
echo 1. Server'i yeniden baslatin: python server_main.py
echo 2. Masaustu uygulamayi acin
echo 3. Ayarlar - Kullanici Yonetimi - Yeni kullanici olusturun
echo.
echo Detayli bilgi icin DEPLOYMENT_GUIDE.md dosyasina bakiniz.
echo.
pause
