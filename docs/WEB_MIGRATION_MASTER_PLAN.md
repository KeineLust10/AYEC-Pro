# AYEC Pro Web Dönüşüm Master Planı

## 1) Hedef Mimari
- Frontend: `React + TypeScript + Vite` (`frontend/`)
- Backend: `FastAPI` (`backend/`)
- Veritabanı: Geçiş aşamasında SQLite, üretimde PostgreSQL hedefi
- Kimlik doğrulama: JWT access/refresh + role-based authorization
- Dağıtım: Docker + reverse proxy (Nginx) + CI/CD pipeline

## 2) Masaüstü → Web Eşleme Kapsamı
- Menü ve modül envanteri: `docs/DESKTOP_TECHNICAL_INVENTORY.md`
- Şema analizi: `docs/DB_SCHEMA_ANALYSIS.md`
- Navigasyon API: `GET /api/v2/navigation/menu`
- Sayfa map API: `GET /api/v2/navigation/page-map`

## 3) Fazlar
### Faz A - Analiz ve Dokümantasyon
- Desktop modül envanteri ve kullanım senaryoları çıkarıldı.
- DB tablo/index envanteri çıkarıldı.
- Menü/alt menü web route map belirlendi.

### Faz B - Backend RESTful Refactor
- v1 endpoint’leri korunacak, v2 katmanı kademeli eklenecek.
- Domain bazlı servis ayrımı:
  - `auth`, `customers`, `devices`, `service-workflow`, `stock`, `finance`, `reports`, `settings`, `notifications`
- Standard response contract:
  - `data`, `meta`, `errors`, `trace_id`
- Pagination/sorting/filtering standardı:
  - `page`, `size`, `sort`, `q`, `filters`

### Faz C - Frontend Web Uygulaması
- Sidebar artık masaüstü menü ağacına göre section/group/item modelinde.
- Eksik modüller için route placeholder’ları oluşturuldu.
- Modül bazlı dönüşüm sırası:
  1. Dashboard + müşteri + servis formu
  2. Stok + finans
  3. Proje + dış takip + bilgi bankası
  4. Ayarlar + audit + yedekleme

### Faz D - PWA ve Mobil Uyum
- Manifest + service worker başlangıcı eklendi.
- Sonraki adımlar:
  - Offline veri katmanı (IndexedDB)
  - Sync queue (background sync)
  - Push notifications (Web Push)
  - Kamera/GPS erişimi (izin akışıyla)

## 4) Güvenlik Standartları
- JWT kısa ömürlü access + rotate edilen refresh token
- CSRF/CORS policy sıkılaştırma
- Rate limiting + brute-force koruması
- Audit log ve admin aksiyon kayıtları
- Şifreleme: PBKDF2/bcrypt + secret rotation

## 5) Test Stratejisi
- Unit: domain service katmanı
- API integration: endpoint contract + auth matrix
- E2E: kritik iş akışları (müşteri ekle → servis aç → ödeme al → raporla)
- Cross-browser: Chrome, Edge, Firefox, Safari
- Performance:
  - Lighthouse
  - API p95 latency
  - bundle size budget

## 6) UAT Senaryoları (Özet)
- Yönetici: kullanıcı/rol/ayar yönetimi
- Operasyon: servis akışı ve durum güncelleme
- Finans: gelir-gider, banka, çek/senet
- Müşteri: kayıt, not, sözleşme, geçmiş
- Raporlama: günlük/haftalık/özel filtreli rapor

## 7) Tamamlanan Başlangıç İşleri
- Menü/alt menü teknik envanter üretimi
- DB şema analizi raporu
- Backend v2 navigasyon endpointleri
- Frontend’te tam menü ağacı ve route iskeleti
- PWA başlangıç dosyaları (`manifest`, `sw`)

## 8) Sonraki Sprint Çıktıları
1. DTO ve service layer standardizasyonu (backend v2)
2. Form doğrulama standardı (Zod + RHF) ve shared validation
3. Dashboard/Service Board canlı veri entegrasyonu
4. Offline-first müşteri + servis taslak akışı

