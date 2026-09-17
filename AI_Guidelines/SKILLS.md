# 🛠️ YETENEKLER & BECERİLER (SKILLS)

Bu proje için özel olarak tanımlanmış iş akışları ve teknik yöntemler.

## 📦 SKILL: Uygulamayı Derleme (Build EXE)
1. **Temizlik**: Önce `build` ve `dist` klasörlerini temizle (`rd /s /q build`).
2. **Build**: `pyinstaller PremiumBulut_Final.spec --noconfirm` komutunu çalıştır.
3. **Kontrol**: `dist` klasöründe `PremiumBulut.exe` oluştuğunu teyit et.
4. **Setup**: Inno Setup Compiler (`ISCC.exe`) ile `Setup_Files\PremiumBulut_Setup.iss` dosyasını derle.
   - Sürüm numarasını (`AppVersion`) ve Çıktı ismini (`OutputBaseFilename`) güncelle.

## 🗄️ SKILL: Veritabanı Yönetimi & Migration
- Veritabanı dosyası: `bulut_tech.db`
- **Tablo Ekleme**: `src/database.py` dosyasındaki `create_tables` metodunu kontrol et.
- **Sütun Ekleme**: Mevcut tabloda sütun yoksa (`PRAGMA table_info`), `ALTER TABLE` komutu ile ekle.
- **Veri Düzeltme**: Karakter sorunları için `text_factory = str` ayarını kullan.

## ☁️ SKILL: Uzak Sunucu & Yedekleme
- **Modül**: `src.utils.cloud_backup`
- **Konfigürasyon**: IP adresi veritabanında `backup_server_ip` anahtarı ile tutulur.
- **Yöntem**: `requests.post` ile sunucu API'sine (`/upload` veya `/api/upload`) multipart/form-data olarak gönderilir.
- **Zamanlayıcı**: `BackupScheduler` thread tabanlıdır (`QThread`). GUI'yi dondurmamalıdır.

## 🧭 SKILL: Navigasyon ve Sayfa Yönetimi
- **Stack**: `MainWindow` içinde `QStackedWidget` kullanılır.
- **Erişim**: Sayfalara erişirken ASLA sabit index (Örn: `15`) kullanma.
  - ✅ `idx = self.stack.indexOf(self.page_backup)`
  - ✅ `self.stack.setCurrentIndex(idx)`
- **Yeni Sayfa Ekleme**:
  1. Sayfayı `src/ui/pages/` altına oluştur.
  2. `MainWindow.__init__` içinde import et ve instantiate et.
  3. `self.stack.addWidget(page)` ile ekle.
  4. `SideMenu` ve `SettingsPage` (gerekirse) içinden erişim ver.
