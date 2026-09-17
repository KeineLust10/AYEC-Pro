# Plan
- [x] Masaüstü kurulum paketi gereksinimlerini uygula
- [x] Derleme ve kurulum paketini üret
- [x] Kurulum sonrası doğrulama adımlarını kayda geçir

# Review
- [x] Kurulum tek paket halinde oluşturuldu (dist/AYECProDesktopSetup.exe)
- [x] DLL ve kısayol kopyalama kuralları kurulum scriptinde doğrulandı
- [x] Silent kurulum denemesinde hedef dizin oluşmadı (yönetici yetkisi gerekiyor)

# Plan
- [x] Mobil stok QR sayfasını hataya dayanıklı hale getir
- [x] Yeni iş kaydı sonrası müşteri listesi borcunu anlık yenile
- [x] Arayüz düzenle menüsüne eksik menüyü ekle
- [ ] Doğrulama komutlarını çalıştır

# Review
- [x] Mobil stok sayfası hatasız açılıyor
- [x] Müşteri listesi borçları anlık güncelleniyor
- [x] Arayüz düzenle menüsü yeni öğeleri gösteriyor
- [ ] Doğrulama komutları çalıştırıldı

# Plan
- [ ] Silinen kayıtlar için soft delete altyapısını genişlet
- [ ] Geri yükleme ekranını finans ve stok kayıtlarını kapsayacak şekilde güncelle
- [ ] Listeleme sorgularını silinen kayıtları gizleyecek şekilde düzenle
- [ ] Doğrulama komutlarını çalıştır

# Review
- [ ] Soft delete dönüşümü tamamlandı
- [ ] Geri yükleme ekranı tüm hedef kayıtları listeliyor
- [ ] Listeleme sorguları silinenleri gizliyor
- [ ] Doğrulama komutları çalıştırıldı

# Plan
- [ ] Stok hareketi yazım ve okuma akışını analiz et
- [ ] Stok hareketleri görünmeme sorununu düzelt
- [ ] Doğrulama komutlarını çalıştır

# Review
- [ ] Stok hareketi yazım ve okuma akışları netleşti
- [ ] Stok hareketleri eklenip listeleniyor
- [ ] Doğrulama komutları çalıştırıldı

# Plan
- [x] Servis modu sonrası cache temizliğini düzelt ve tek seferlik temizlik yap
- [x] Doğrulama komutlarını çalıştır
- [x] Düzeltme sonrası lessons notunu güncelle

# Review
- [x] Servis modu kullanıcı ekleme sonrası cache otomatik temizlenmiyor
- [x] Cache tek seferlik temizlendi
- [x] Doğrulama komutları çalıştırıldı
- [x] Lessons notu güncellendi

# Plan
- [x] SMTP ayarlarını ve uygulama mailini güncelle
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Mail ayarları güncellendi
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [x] Servis modu kullanıcı ekleme doğrulamasını düzelt ve görünürlüğü artır
- [x] Kullanıcı ekleme ile login ve ayarlar listelerini hizala
- [x] Veri kurtarma combobox renklerini düzelt
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Servis modu kullanıcı ekleme butonu aktifleşiyor
- [x] Yeni kullanıcı login ve kullanıcı yönetimi listelerinde görünüyor
- [x] Veri kurtarma combobox metni okunur
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [x] Stok hareketi kayıt uyumsuzluğunu düzelt
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Stok hareketleri kayıt sonrası görünüyor
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [x] Veri temizleme onay akışında master şifre doğrulaması ekle
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Veri temizleme akışı şifre doğrulamasıyla çalışıyor
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [x] Silinen kayıtlar ekranına kullanıcıları dahil et
- [x] Kullanıcı silme akışını geri alınabilir hale getir
- [x] Kullanıcı ekleme formu doğrulamasını düzelt
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Silinen kayıtlar ekranı kullanıcıları gösteriyor
- [x] Kullanıcı silme akışı geri yükleme ile uyumlu
- [x] Kullanıcı ekleme butonu gerekli alanlarla aktifleşiyor
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [x] Stok hareketi tablo uyumluluğunu garanti et
- [x] Envanter değerini maliyetle hizala
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Stok hareketleri listede görünür hale geldi
- [x] Envanter maliyeti finans ekranıyla uyumlandı
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [x] Masaüstü stok listeleme akışını analiz et
- [x] Parça tablosu şemasını masaüstünde garanti et
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Stok listeleme akışı doğrulandı
- [x] Parça tablosu şeması doğrulandı
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [x] Web arayüz stok veritabanı yolunu eşle
- [x] Parça tablosu şemasını web arayüzde garanti et
- [x] Doğrulama komutlarını çalıştır

# Review
- [x] Stok veritabanı yolu doğrulandı
- [x] Parça tablosu şeması doğrulandı
- [x] Doğrulama komutları çalıştırıldı

# Plan
- [ ] Web menüleri ile sayfa eşlemesini envanterle
- [ ] Web API çağrılarında kimlik doğrulamayı düzelt
- [ ] Dialog butonlarının arka uç bağlantılarını düzelt
- [ ] CORS ve statik dosya sunumunu doğrula
- [ ] Doğrulama komutlarını çalıştır

# Review
- [ ] Web menü envanteri doğrulandı
- [ ] API kimlik doğrulama düzeltmesi doğrulandı
- [ ] Dialog butonları doğrulandı
- [ ] CORS ve statik sunum doğrulandı
- [ ] Doğrulama komutları çalıştırıldı

# Plan
- [x] Arayüz düzenleme menü listesini yeni menülerle senkronize et
- [x] Menü isimleri için düzenlenebilir etiketleri bağla
- [x] Doğrulama adımlarını çalıştır
- [ ] AI Asistan kestirmeler sekmesini modern tabloya taşı
- [ ] Sesli komut eğitimi görünümünü tam genişlik tabloya çevir
- [ ] Sistem ve güvenlik günlüğü kontrastını koyu tema için düzelt
- [ ] Kullanıcı yetkileri tablosunda inline düzenlemeyi etkinleştir
- [ ] Yeni kullanıcı ekleme dialogunu kurumsal tasarımda yenile
- [x] Master rolünü ve yetki davranışını ekle
- [x] Kurtarma akışını kullanıcı ayarları ve girişe bağla
- [x] Doğrulama adımlarını çalıştır
- [x] İşlem detayı hover stilini tespit et
- [x] Hover efektini kaldır
- [x] Doğrulama adımlarını çalıştır
- [x] Finans işlem detay hover stilini tespit et
- [x] Hover rengini maviye çevir
- [x] Doğrulama adımlarını çalıştır
- [x] Stok ekleme sonrası liste yenilemeyi incele
- [x] Kayıt ve liste yükleme tutarlılığını düzelt
- [x] Doğrulama adımlarını çalıştır
- [x] Galeri dialogunda görsele tıklayınca büyük önizleme aç
- [x] Teknisyen paneli galerisinde tıklama ile önizleme sağla
- [x] Finansal raporlar tablosunda çift tıkla detay penceresi aç
- [x] Finansal dashboard için yenile butonu ekle
- [x] Finans menüsünden Raporlar öğesini kaldır
- [x] Galeri önizleme pencerelerini daha büyük ölçülere çıkar
- [x] Blok/daire ekleme dialogunu yeni alanlarla yeniden tasarla
- [x] Otomatik blok/daire listesi ve fiyatlandırma araçlarını uygula
- [x] Daire satış dialogunu sekmeli ve validasyonlu hale getir
- [x] Ayarlar entegrasyon/api ve RBAC açılmama döngüsünü düzelt
- [x] Lisans talep et akışını düzelt
- [x] Blok/Daire ekle ekranında kaydırma ve boş alan davranışını düzelt
- [x] Lojistik & Garanti takip formunda boş alanı doldur
- [x] Doğrulama adımlarını çalıştır
- [x] Teknik servis panelini yeni frameless tasarımla güncelle
- [x] Teknik servis buton işlevleri ve canlı log akışını bağla
- [x] SecurityManager master modu ve gizli giriş akışını ekle
- [x] Doğrulama adımlarını çalıştır
- [x] Teknik servis paneline silinenleri kurtar akışını ekle
- [x] Menü şifre ayarını ve kullanım noktasını netleştir
- [x] Arayüz düzenlemede menü adı düzenleme erişimini aç
- [x] Doğrulama adımlarını çalıştır
- [x] RBAC ekranı açılma sorununu doğrula ve düzelt
- [x] Entegrasyon & API sekmesinde sesli özellikleri doğrula
- [x] Sesli komut kestirmeleri görünürlüğünü doğrula
- [x] Doğrulama adımlarını çalıştır
- [x] Cihaz kimliği kopyalama donmasını düzelt ve tam görünüm sağla
- [x] Entegrasyon sekmelerine AI Asistan Kestirmeler sekmesini ekle
- [x] Sesli Komut Eğitimi başlığını güncelle ve içerik taşımayı yap
- [x] Doğrulama adımlarını çalıştır
- [x] AI Asistan kestirmeler sayfasını yeniden tasarla ve görünürlüğü düzelt
- [x] Personel ve Ayarlar girişinde şifre istemeyi kaldır

# Plan
- [x] Terra/Sakura için Kanban tema renklerini dinamikleştir
- [x] Tema uyumsuz sabit renkleri tokenlara taşı
- [x] Tema görünümünü doğrula

# Review
- [x] Kanban renkleri tema değişiminde doğru güncelleniyor
- [x] Sabit renkler tema paletine uyumlu
- [x] Terra/Sakura görünümü doğrulandı
- [x] Müşteri borç ve kredi vade hatırlatma kestirmelerini ekle
- [x] Doğrulama adımlarını çalıştır
- [x] Sesli asistan aksiyon handlerlarını bul
- [x] Kestirme akışını doğrula
- [x] Entegrasyon sekme içerik-etiket eşleşmesini düzelt
- [x] SMS ve AI Asistan sekmelerini doğrula
- [x] Kestirme ekleme akışını netleştir
- [x] Sesli komut ayarları okunurluğunu artır
- [x] Kart yerleşimini boş alanları değerlendirecek şekilde düzenle
- [x] Kaydet butonunu en alta taşı
- [x] Sesli komut ayarları sayfasını premium tasarımla güncelle
- [x] Sesli komut ekranı bileşen stillerini sadeleştir
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Arayüz düzenleme menü listesi doğrulandı
- [x] Menü isimleri düzenlenebilirliği doğrulandı
- [x] Doğrulama adımları tamamlandı
- [ ] AI Asistan kestirmeler tablo düzeni doğrulandı
- [ ] Sesli komut eğitimi tablo düzeni doğrulandı
- [ ] Sistem günlüğü kontrast düzeltmesi doğrulandı
- [ ] Kullanıcı yetkileri inline düzenleme doğrulandı
- [ ] Yeni kullanıcı dialogu ve toast akışı doğrulandı
- [x] Master rolü doğrulandı
- [x] Kurtarma akışı doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] İşlem detayı hover efekti kaldırıldı
- [x] Hover kaldırma doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] Finans işlem detay hover rengi doğrulandı
- [x] Hover stil güncellemesi doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] Stok ekleme sonrası liste yenileme doğrulandı
- [x] Kayıt ve liste yükleme düzeltmesi doğrulandı

# Plan
- [ ] Tahsilat al dialogunu üç para birimi kartlı ve liste tabanlı tasarla
- [ ] Seçilen para birimine göre borç kalemlerini listele ve detayları aç/kapat göster
- [ ] Tahsilat kaydını borç düşümü ve finans gelir akışıyla bağla
- [ ] Doğrulama komutlarını çalıştır

# Review
- [ ] Tahsilat al arayüzü yeni karta ve listeye taşındı
- [ ] Borç kalemleri ve detay görünümü doğru çalışıyor
- [ ] Tahsilat finansa gelir olarak yazılıyor
- [ ] Doğrulama komutları çalıştırıldı
- [x] Doğrulama adımları tamamlandı
- [x] Galeri görsel önizleme doğrulandı
- [x] Teknisyen paneli görsel önizleme doğrulandı
- [x] Finansal raporlar detay penceresi doğrulandı
- [x] Finansal dashboard yenile butonu doğrulandı
- [x] Finans menüsünde Raporlar kaldırma doğrulandı
- [x] Galeri önizleme boyutları doğrulandı
- [x] Blok/daire dialogu genişletme doğrulandı
- [x] Otomatik blok/daire listesi doğrulandı
- [x] Daire satış dialogu doğrulandı
- [x] Ayarlar entegrasyon/api ve RBAC doğrulandı
- [x] Lisans talep et doğrulandı
- [x] Blok/Daire ekle kaydırma davranışı doğrulandı
- [x] Lojistik & Garanti formu düzeni doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] Teknik servis panel tasarımı doğrulandı
- [x] Teknik servis işlevleri ve log akışı doğrulandı
- [x] SecurityManager master modu doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] Silinen kayıt kurtarma akışı doğrulandı
- [x] Menü şifre ayarı doğrulandı
- [x] Arayüz düzenleme menü adı düzenleme doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] RBAC ekranı doğrulandı
- [x] Entegrasyon & API sekmesi doğrulandı
- [x] Sesli komut kestirmeleri doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] Cihaz kimliği kopyalama düzeltmesi doğrulandı
- [x] AI Asistan Kestirmeler sekmesi doğrulandı
- [x] Sesli Komut Eğitimi başlık ve içerik taşıma doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] AI Asistan kestirmeler sayfası doğrulandı
- [x] Personel ve Ayarlar şifre isteme kaldırma doğrulandı
- [x] Borç ve kredi vade hatırlatma kestirmeleri doğrulandı
- [x] Doğrulama adımları tamamlandı
- [x] Sesli asistan aksiyon handlerları doğrulandı
- [x] Kestirme akışı doğrulandı
- [x] Entegrasyon sekme eşleşmesi doğrulandı
- [x] SMS ve AI Asistan sekmeleri doğrulandı
- [x] Kestirme ekleme yönlendirmesi doğrulandı
- [x] Sesli komut ayarları okunurluk düzeni doğrulandı
- [x] Kart yerleşimi ve boş alan kullanımı doğrulandı
- [x] Kaydet butonu konumu doğrulandı
- [x] Sesli komut ayarları tasarım güncellemesi doğrulandı
- [x] Sesli komut ekranı okunabilirlik iyileştirmesi doğrulandı
- [x] Doğrulama adımları tamamlandı

# Plan
- [ ] Banka hesapları görünümünü Mevcut Bakiye alanıyla güncelle
  - [ ] Banka tablosuna mevcut bakiye sütununu ekle ve tablo genişliklerini dengele
  - [ ] Hesap ekleme/güncelleme akışına başlangıç bakiyesi bağla
  - [ ] Banka detay penceresinde mevcut bakiyeyi göster
- [ ] Gelir/gider/transfer akışlarını banka hesabı seçimi ve bakiye güncellemesiyle bağla

# Plan
- [x] Firma ayarları dialogundan ilgili bölümleri çıkar
- [x] Firma ayarları menüsüne logo, konum ve numara bölümlerini taşı
- [x] Firma ayarları menüsünü derli toplu düzenle
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Firma ayarları dialogu sadeleştirildi
- [x] Logo, konum ve numara ayarları menüye taşındı
- [x] Firma ayarları menüsü düzenlendi
- [ ] Doğrulama adımları çalıştırıldı (sanity_audit: db dosyası açılamadı)
  - [x] Gelir/Gider dialoglarına banka hesabı seçimi ekle
  - [x] Transfer akışında kaynak/hedef hesap seçimi ve çift kayıt oluştur
  - [x] İşlem kaydında banka bakiyesi güncellemesini güvenli hale getir
- [ ] Transactions tablosu ve veri modelini banka hesaplarına bağlayacak şekilde güncelle
  - [ ] Muhasebe şemasına banka ilişki kolonlarını migrate et
  - [ ] Banka hareket kayıtlarını muhasebe raporuna dahil et
- [ ] Audit trail ve raporlamayı banka işlemleriyle genişlet
  - [ ] Banka hareketlerinde audit log kaydı oluştur
  - [ ] Finans raporu ekranında banka hareketi kaydını görünür yap
- [ ] Banka işlemleri yetkilendirme kontrollerini ve sağ tık menüsünü ekle
  - [ ] Banka işlemleri için RBAC izin kontrolü ekle
  - [ ] Banka listesinde sağ tık menüsüne hızlı işlem kısayolları ekle

# Review
- [ ] Banka hesapları görünüm güncellemesi doğrulandı
- [ ] Gelir/gider/transfer akışı banka hesabı bağlantısı doğrulandı
- [ ] Transactions tablo güncellemesi doğrulandı
- [ ] Audit trail ve raporlama genişletmesi doğrulandı
- [ ] Banka işlemleri yetkilendirme ve sağ tık menüsü doğrulandı

# Plan
- [x] Gemini ayar ekranını sadeleştir ve yerleşimi modernleştir
  - [x] Üst banner ve kart görsel dilini nötr ve premium yap
  - [x] Kart/panel aralıklarını ve hizalamayı tutarlı hale getir
  - [x] Birincil aksiyon butonlarını sade ve net bir stile çek
- [x] Vergi analizi diyalogunda butonları aktif ve tıklanabilir yap
  - [x] Butonların enable ve görsel durumunu düzelt
  - [x] Yenile/kaydet aksiyonlarını güvenli bağla
- [x] Banka bakiyesi güncellemesini sağlamlaştır
  - [x] Banka tablosu şemasını güncelleme öncesi garanti et
  - [x] Bakiye güncelleme sorgularını uyumlu kolonla çalıştır

# Review
- [x] Gemini ayar ekranı sade tasarım doğrulandı
- [x] Vergi analizi butonları doğrulandı
- [x] Banka bakiyesi güncellemesi doğrulandı

# Plan
- [x] Finans dashboard gelir/gider dialoglarına banka hesabı alanı ekle
- [x] Gelir/gider işlemlerini banka bakiyesiyle senkronize et
- [x] Doğrulama ve lint adımlarını çalıştır

# Review
- [ ] Banka hesabı alanı doğrulandı
- [ ] Bakiye güncellemesi doğrulandı
- [x] Doğrulama ve lint adımları doğrulandı

# Plan
- [x] Doğrulama komutlarını belirle
- [x] Sanity ve test scriptlerini çalıştır
- [x] Lint ve typecheck adımlarını çalıştır

# Review
- [x] Doğrulama komutları belirlendi
- [ ] Sanity ve test scriptleri doğrulandı
- [x] Lint ve typecheck doğrulandı

# Plan
- [x] Uygulama donma sebebini loglar ve izlerle analiz et
- [x] UI thread blokajına neden olan akışları tespit et

# Plan
- [x] Müşteri 360 servis listesini müşteri adı eşleşmesiyle düzelt
- [x] Servis Modu menüsünü ve giriş ekranı konumunu görünür hale getir
- [x] Silinenleri Kurtar listesini servis silme akışıyla uyumlu yap
- [x] Lisans yönetimi 404 hatasını gider
- [ ] Doğrulama ve lint adımlarını çalıştır

# Review
- [ ] Müşteri 360 servis listesi doğrulandı
- [ ] Servis Modu görünürlüğü doğrulandı
- [ ] Silinenleri Kurtar listesi doğrulandı
- [ ] Lisans yönetimi doğrulandı
- [ ] Doğrulama ve lint adımları doğrulandı

# Plan
- [x] Kredi kayıtlarını banka hesabı ile eşleştir
- [x] Kredi kartı kayıtlarını banka hesabına bağla
- [x] Otomatik ödeme talimatı düzenleme akışını ekle
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Kredi-banka hesabı eşleşmesi doğrulandı
- [x] Kredi kartı akışı doğrulandı
- [x] Otomatik ödeme düzenleme akışı doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Sesli asistan senaryolarını varsayılanlara ekle ve mevcut ayarlara taşı
- [x] Zam komutunda yüzde parametresini çözüp aksiyona aktar

# Review
- [x] Sesli asistan senaryoları ve ayar taşıma doğrulandı
- [x] Zam komutu yüzde parametresi doğrulandı
- [x] Donma riskini azaltacak düzeltmeyi uygula

# Review
- [x] Donma analizi doğrulandı

# Plan
- [x] Stok kullanımında borç kaydı akışını ekle
- [x] Servis ekranlarında borç kaydı çağrılarını bağla
- [x] Borç hesaplamasında parça kayıtlarında mükerrerliği engelle
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Stok kullanımında borç kaydı akışı doğrulandı
- [x] Servis ekranı borç kayıtları doğrulandı
- [x] Borç hesaplama mükerrerlik düzeltmesi doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] UI donmasına yol açan thread UI çağrılarını tespit et ve düzelt
- [x] Lisans sorgusu hata akışında UI güncellemelerini güvenli hale getir
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Thread UI çağrıları düzeltmesi doğrulandı
- [x] Lisans hata akışı güncellemeleri doğrulandı
- [x] Doğrulama adımları doğrulandı
- [x] UI thread blokajı düzeltmesi doğrulandı
- [x] Regresyon kontrolü doğrulandı

# Plan
- [x] Gemini ayar ekranını yeni yerleşimle yeniden düzenle
- [x] Özet kartları ve model yönetimi akışını entegre et
- [x] Doğrulama ve lint/typecheck adımlarını çalıştır

# Review
- [x] Yeni Gemini ayar yerleşimi doğrulandı
- [x] Özet kartları ve model yönetimi doğrulandı
- [x] Doğrulama ve lint/typecheck doğrulandı

# Plan
- [ ] Banka hesapları mevcut durum ve pazar araştırmasını derle
- [ ] Banka hesapları sayfasını yeni premium yerleşimle yeniden tasarla
- [ ] Arama/filtre/özet ve tablo etkileşimlerini iyileştir
- [ ] Doğrulama ve kalite kontrollerini çalıştır

# Review
- [ ] Araştırma ve gereksinimler doğrulandı
- [ ] Yeni banka hesapları yerleşimi doğrulandı
- [ ] Etkileşim ve tablo iyileştirmeleri doğrulandı
- [ ] Doğrulama ve kalite kontrolleri doğrulandı

# Plan
- [x] Kilit ekranı HWID kopyala butonu ekle
- [x] Takılı ekranı kapatmak için süreci sonlandır
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] HWID kopyalama butonu doğrulandı
- [x] Takılı ekran kapatma doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Lisans kilit ekranına lisans anahtarı girişi ekle
- [x] Yönetici ile iletişime geç butonunu aktif hale getir
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Lisans anahtarı girişi doğrulandı
- [x] İletişim butonu aktifliği doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Lisans kontrolü UI callback çağrısını thread güvenli hale getir
- [x] QMetaObject invokeMethod hatasını düzelt
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Lisans callback thread güvenliği doğrulandı
- [x] QMetaObject invokeMethod düzeltmesi doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Banka hesap dialogunu tek sayfaya dönüştür ve yerleşimi genişlet
- [x] Banka hesap detay penceresini sekmeli kapsamlı görünümle yenile
- [x] Hareketler tablosuna filtre, sayfalama ve dışa aktarma ekle
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Banka hesap dialogu tek sayfada doğrulandı

# Plan
- [x] Servis Modu panelini dashboard şablonuna entegre et
- [x] Lisans yönetimi ve giriş takibi verilerini tamamla
- [x] Grafikler, uyarılar ve responsive düzeni finalize et
- [x] Doğrulama ve kalite kontrollerini çalıştır

# Review
- [x] Servis Modu panel entegrasyonu doğrulandı
- [x] Lisans yönetimi ve giriş takibi doğrulandı
- [x] Grafikler, uyarılar ve responsive düzen doğrulandı
- [x] Doğrulama ve kalite kontrolleri doğrulandı
- [x] Banka hesap detay penceresi doğrulandı
- [x] Hareketler filtre ve dışa aktarma doğrulandı
- [x] Doğrulama adımları tamamlandı

# Plan
- [ ] Finansal dashboard gelir/gider tabloları ve kaynak akışlarını denetle
- [ ] Arayüz düzenleme yetki ve şifre akışını Bulut için düzelt
- [ ] Arayüz düzenleme menüsünün kapanma hatasını düzelt
- [ ] Doğrulama ve kalite kontrollerini çalıştır

# Review
- [ ] Finansal dashboard gelir/gider akışı doğrulandı
- [ ] Arayüz düzenleme yetki akışı doğrulandı
- [ ] Arayüz düzenleme menüsü kapanma hatası doğrulandı
- [ ] Doğrulama ve kalite kontrolleri doğrulandı

# Plan
- [ ] Finansal özet aksiyonunu ve veri kaynağını netleştir
- [ ] Sesli yanıtta sayı-okunuşu ve para birimi biçimini uygula
- [ ] Dinleme akışında 5 dakika sonra durma nedenini düzelt
- [ ] Doğrulama ve kalite kontrollerini çalıştır

# Plan
- [x] Finansal dashboard işlem detayında stok ürünlerini görünür yap
- [x] Stok açıklamasından ürün satırlarını üret
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Stok işlem detayları doğrulandı
- [x] Ürün satırları doğrulandı
- [x] Doğrulama adımları doğrulandı

# Review
- [ ] Finansal özet sesli okuma doğrulandı
- [ ] Dinleme sürekliliği doğrulandı
- [ ] Doğrulama ve kalite kontrolleri doğrulandı

# Plan
- [x] Vergi analizi penceresini büyüt
- [x] Vergi dilimi detayı yazı taşmasını düzelt
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Vergi analizi penceresi boyutları doğrulandı
- [x] Vergi dilimi detayı okunabilirliği doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Yeni banka hesabı diyalogunda banka seçim combobox akışını düzelt
- [x] Banka seçimi için aşağı ok zorunluluğunu kaldır
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Banka hesabı seçim combobox düzeltmesi doğrulandı
- [x] Aşağı ok zorunluluğu kaldırma doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] code_inspector.py hata ve risklerini analiz et
- [x] Güvenli düzeltmeleri uygula ve ölü kodu temizle
- [x] Test çalıştır ve sonuçları doğrula
- [x] Düzeltme raporunu hazırla

# Review
- [x] Hata ve risk düzeltmeleri doğrulandı

# Plan
- [x] Hızlı bağlantı indirme linkleri için sunucu indirme uçlarını ekle
- [x] Kurulum ve AnyDesk dosyası indirme akışını doğrula

# Review
- [x] İndirme uçları doğrulandı
- [x] Dosya indirme akışı doğrulandı

# Plan
- [x] Muhasebe ekranında toplu faturalandırma seçimi ve modal akışını ekle
- [x] Toplu fatura kesme API çağrısını ve seçim özetini bağla
- [x] Doğrulama ve kalite kontrollerini çalıştır

# Review
- [x] Toplu faturalandırma akışı doğrulandı
- [x] API çağrısı ve seçim özeti doğrulandı
- [x] Doğrulama ve kalite kontrolleri doğrulandı
- [x] Ölü kod temizliği doğrulandı
- [x] Test sonuçları doğrulandı
- [x] Raporlama tamamlandı

# Plan
- [x] Banka hesabı ekleme bildirimini toast ile göster
- [x] Lisans keygen penceresini ekle ve boyutu iyileştir
- [x] Lisans kilit ekranı penceresini büyüt
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Banka hesabı toast bildirimi doğrulandı
- [x] Keygen penceresi ve boyut iyileştirmeleri doğrulandı
- [x] Lisans kilit ekranı boyutu doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Vergi dilimleri detayında yazı taşmasını düzelt
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Vergi dilimleri detayı okunabilirliği doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Giriş ekranlarında admin kullanıcıyı gizle
- [x] Kredi bilgileri sekmesinde erken ödeme bölümünü kaldır ve taksit planını alta al
- [x] Lisans cihaz kimliği üretimini tekilleştir
- [x] Doğrulama adımlarını çalıştır

# Review
- [x] Admin kullanıcı gizleme doğrulandı
- [x] Kredi bilgileri düzeni doğrulandı
- [x] HWID tekilleştirme doğrulandı
- [x] Doğrulama adımları doğrulandı

# Plan
- [x] Teknik servis modunu web dashboard şablonuna entegre et
- [x] Lisans yönetimi, cihaz giriş takibi ve uyarı sistemini ekle
- [x] Grafiksel raporları ve responsive düzeni tamamla
- [x] Doğrulama ve kalite kontrollerini çalıştır

# Review
- [x] Teknik servis mod entegrasyonu doğrulandı
- [x] Lisans ve cihaz panelleri doğrulandı
- [x] Grafikler ve responsive düzen doğrulandı
- [x] Doğrulama komutları çalıştırıldı, testler bulunamadı

# Plan
- [x] Stok görünmeme için soft delete etkisini analiz et
- [x] Silinmiş stok kayıtlarını geri yükle
- [x] Stok görünürlüğünü doğrula

# Review
- [x] Stok görünmeme analiz edildi, kullanılan DB konumu kontrol edildi
- [x] Silinmiş kayıtlar için geri yükleme güncellendi
- [x] Stok tablosu sayıları doğrulandı
