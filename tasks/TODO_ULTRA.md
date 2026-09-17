# Todo Ultra

Bu belge, AYEC Pro içindeki ajan orkestrasyonu ve ultra seviye otomasyon katmanı için tek kaynak backlog dokümanıdır.
Mevcut `tasks/todo.md` içindeki genel ürün görevlerinden ayrıdır ve yalnızca eksik veya temel seviyede kalan ultra sistem parçalarını kapsar.

## P0 Kritik Canlılık

### 1. Gerçek Executor Entegrasyonu
- Durum: Eksik
- Neden Önemli: Orkestratör şu anda mock/input tabanlı çalışıyor; gerçek ajan yürütmesi olmadan tüm sistem kısmen simülasyon seviyesinde kalıyor.
- Hedef Çıktı: `executor.py` içinde gerçek Codex API, CLI veya IDE hook entegrasyonu; model seçimi, timeout, hata yakalama ve structured response desteği.
- Bağlı Dosya / Modül: `agent_orchestrator/executor.py`

### 2. Canlı GitHub PR / Check / Merge Akışı
- Durum: Temel Seviye
- Neden Önemli: PR açma ve merge deneme mantığı var, ancak gerçek GitHub check-suite, branch protection ve review state ile uçtan uca doğrulanmış değil.
- Hedef Çıktı: PR açıldıktan sonra check durumu bekleme, review state okuma, merge uygunluğu doğrulama ve güvenli merge kararı veren canlı akış.
- Bağlı Dosya / Modül: `agent_orchestrator/pr_manager.py`

### 3. Env Yükleme ve Secret Yönetimi
- Durum: Temel Seviye
- Neden Önemli: `.env.example` var ama otomatik env yükleme, secret doğrulama ve eksik ayar denetimi yok.
- Hedef Çıktı: Başlangıçta env dosyasını okuyan, zorunlu ayarları denetleyen ve eksik secret durumunda açık hata veren merkezi yükleme katmanı.
- Bağlı Dosya / Modül: `agent_orchestrator/config.py`, `.env.example`

## P1 Operasyonel Tamamlama

### 4. Neo4j Canlı Sync
- Durum: Temel Seviye
- Neden Önemli: Neo4j adapter mevcut ama gerçek bağlantı, hata yönetimi ve veri senkronizasyonu canlı ortamda doğrulanmadı.
- Hedef Çıktı: Neo4j bağlantı testi, node/edge sync doğrulaması, bağlantı hatası fallback’i ve gözlemlenebilir sync logları.
- Bağlı Dosya / Modül: `agent_orchestrator/neo4j_graph.py`, `agent_orchestrator/memory_graph.py`

### 5. Dashboard Pro Arayüzü
- Durum: Temel Seviye
- Neden Önemli: Dashboard artık HTML sunuyor ama auth, filtre, detay ekranı, durum drill-down ve güçlü görselleştirme eksik.
- Hedef Çıktı: Kimlik korumalı dashboard, event filtresi, risk filtresi, görev detay paneli, memory detay görünümü ve daha güçlü grafiksel özetler.
- Bağlı Dosya / Modül: `agent_orchestrator/dashboard.py`, `agent_orchestrator/monitoring.py`

### 6. Supervisor / Tek Komutla Servis Başlatma
- Durum: Eksik
- Neden Önemli: Webhook, dashboard, loop runner ve memory maintenance ayrı ayrı başlatılıyor; bu operasyonel kırılganlık yaratıyor.
- Hedef Çıktı: Tüm servisleri kontrollü başlatan tek bir supervisor script veya launcher; sağlık kontrolü ve kapanış yönetimi ile birlikte.
- Bağlı Dosya / Modül: `webhook_server.py`, `loop_runner.py`, `agent_orchestrator/run_dashboard.py`, `agent_orchestrator/memory_maintenance.py`

## P2 Ultra Seviye Yükseltmeler

### 7. Multi-Round Debate Judge
- Durum: Temel Seviye
- Neden Önemli: Judge katmanı mevcut ama tek turlu ve tek prompt ile karar veriyor; daha güçlü karşılaştırmalı muhakeme yapılmıyor.
- Hedef Çıktı: Ajan sonuçlarını birkaç tur değerlendiren, güçlü/zayıf yanları karşılaştıran ve gerekirse ikinci seçim turu yapan judge akışı.
- Bağlı Dosya / Modül: `agent_orchestrator/debate_judge.py`, `agent_orchestrator/debate_system.py`

### 8. Confidence Calibration
- Durum: Temel Seviye
- Neden Önemli: Confidence skoru şu an heuristik; geçmiş başarı oranları ve gerçek operasyonel sonuçlarla kalibre edilmiyor.
- Hedef Çıktı: Confidence hesaplamasını geçmiş sonuçlar, debate skoru, validation başarısı ve memory isabetine göre daha sağlam normalize eden sistem.
- Bağlı Dosya / Modül: `agent_orchestrator/confidence_engine.py`, `agent_orchestrator/main.py`

### 9. Check-Suite Aware Auto-Merge
- Durum: Temel Seviye
- Neden Önemli: Auto-merge mantığı mergeable/draft/state kontrol ediyor ama GitHub check-suite ve branch protection kurallarını tam yorumlamıyor.
- Hedef Çıktı: Check suite, required status checks ve protection state okuyan, yalnız uygun PR’larda merge kararı veren tam güvenlik kapısı.
- Bağlı Dosya / Modül: `agent_orchestrator/pr_manager.py`

### 10. Offline / Local Embedding Fallback
- Durum: Temel Seviye
- Neden Önemli: `OPENAI_API_KEY` yoksa semantic memory gücü düşüyor; sistem yalnız zayıf fallback ile kalıyor.
- Hedef Çıktı: Yerel embedding modeli veya offline similarity fallback’i ile semantic memory’nin dış servise bağımlılığını azaltmak.
- Bağlı Dosya / Modül: `agent_orchestrator/vector_memory.py`

## P3 Kalite ve Bakım

### 11. Metrics Rotation / Archive
- Durum: Eksik
- Neden Önemli: Metrics dosyası büyüdükçe dashboard ve analiz maliyeti artar; arşivleme olmadan bakım zorlaşır.
- Hedef Çıktı: Boyut veya tarih bazlı metrics rotation, arşiv klasörü ve eski kayıtları özetleyen bakım akışı.
- Bağlı Dosya / Modül: `agent_orchestrator/metrics.py`, `.agents/metrics/agent_stats.json`

### 12. Memory Cleanup Servisleşmesi
- Durum: Temel Seviye
- Neden Önemli: Memory cleanup mantığı var ama sürekli servis veya worker düzenine tam bağlı değil.
- Hedef Çıktı: Memory optimization işini periyodik, gözlemlenebilir ve hataya dayanıklı servis görevine dönüştürmek.
- Bağlı Dosya / Modül: `agent_orchestrator/memory_optimizer.py`, `agent_orchestrator/memory_maintenance.py`

### 13. Memory Rewrite Approval Gate
- Durum: Temel Seviye
- Neden Önemli: Memory rewrite mevcut ama yeniden yazılan çözüm kalitesini onaylayan ayrı güvenlik katmanı yok.
- Hedef Çıktı: Rewrite edilen çözüm için confidence, validation veya human approval tabanlı kabul mekanizması.
- Bağlı Dosya / Modül: `agent_orchestrator/memory_rewriter.py`

### 14. Validator Intelligence ve Test Profilleri
- Durum: Temel Seviye
- Neden Önemli: Validator temel komutlarla çalışıyor; proje tipine göre dinamik test planı ve akıllı doğrulama profili üretmiyor.
- Hedef Çıktı: Hata tipine, agent tipine ve proje bileşenine göre doğru test/build/check kombinasyonunu seçen akıllı validator.
- Bağlı Dosya / Modül: `agent_orchestrator/validator.py`

## Bağımlılık Sırası

`executor -> github canlı akış -> neo4j -> dashboard pro -> validator intelligence -> memory evolution`
