# 🛑 PREMIUM BULUT - AI KURALLARI (RULES)

Bu dosya, "Premium Bulut" projesi üzerinde çalışan yapay zeka ajanları (Cursor, Windsurf vb.) için **KESİN** kuralları içerir.

## 1. Kodlama Standartları
- **Dil**: Kod yorumları ve değişken isimlendirmeleri (mümkünse) İngilizce/Türkçe karma olabilir, ancak **Kullanıcı Arayüzü (UI) tamamen Türkçe** olmalıdır.
- **Yollar (Paths)**: ASLA göreceli yol (relative path) kullanma. Her zaman `src.utils.path_helper` modülündeki `PathHelper` sınıfını kullanarak mutlak yolları elde et.
  - ❌ `open("config.json")`
  - ✅ `open(os.path.join(PathHelper.get_app_data_dir(), "config.json"))`
- **Import Kontrolü**: Yeni bir kütüphane eklediğinde, her zaman `try-except ImportError` bloğu ile sarmala ve eksikse `None` ata veya kullanıcıya bildir.
  - Örnek: `BackupScheduler` veya `CloudBackupManager` importları.

## 2. UI/UX ve Tasarım (Premium Standartları)
- **Hedef**: Kullanıcı "WOW" demeli. Standart gri PyQt arayüzleri yasaktır.
- **Renkler**: `src.utils.design_system.py` dosyasındaki `DesignTokens` sınıfını kullan.
  - Ana Renkler değil, özel paletler kullan (Slate, Emerald, Indigo, Amber).
- **Animasyon**: Mümkün olan her yerde `QPropertyAnimation` ile yumuşak geçişler kullan.
- **İkonlar**: Emoji kullanımı serbesttir ancak profesyonel görünmeli. `QIcon` ile `assets/icons` klasörü tercih edilmeli.

## 3. Hata Yönetimi ve Loglama
- **Sessiz Hata Yok**: `except: pass` KESİNLİKLE YASAKTIR.
- **Bildirimler**: Kullanıcıya hata gösterirken `src.utils.toast_notification` kullan. Standart `QMessageBox` yerine modern, sağ alt köşeden çıkan bildirimleri tercih et.
- **Loglama**: Kritik işlemleri `AuditLogPage` için veritabanına kaydet.

## 4. Dosya ve Veritabanı Güvenliği
- **Yedekleme**: Veritabanı şeması üzerinde `ALTER TABLE` veya `DROP TABLE` gibi yıkıcı değişiklikler yapmadan önce MUTLAKA `backups` klasörüne yedek al.
- **Atomik İşlemler**: Çoklu tablo güncellemelerini `transaction` bloğu içinde yap.
