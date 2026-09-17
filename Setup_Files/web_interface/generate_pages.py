# -*- coding: utf-8 -*-
"""
Generate all remaining page components
"""

pages = {
    'service-status': {
        'title': 'Durum Ekranı',
        'desc': 'Müşteri görüntüleme ekranı için durum panosu',
        'api': '/api/services',
        'icon': 'monitor'
    },
    'technician': {
        'title': 'Teknisyen Paneli',
        'desc': 'Teknisyen görev ve iş takip paneli',
        'api': '/api/services',
        'icon': 'tool'
    },
    'external-tracking': {
        'title': 'Lojistik & Garanti',
        'desc': 'Dış servis ve garanti takip sistemi',
        'api': '/api/external-tracking',
        'icon': 'truck'
    },
    'field-service': {
        'title': 'Saha Haritası',
        'desc': 'Saha servisi harita ve rota planlama',
        'api': '/api/field-service',
        'icon': 'map-pin'
    },
    'new-transaction': {
        'title': 'Yeni İşlem',
        'desc': 'Yeni servis kaydı oluşturma sihirbazı',
        'api': '/api/services',
        'icon': 'plus-circle'
    },
    'contracts': {
        'title': 'Sözleşmeler',
        'desc': 'Müşteri sözleşmeleri ve yenileme takibi',
        'api': '/api/contracts',
        'icon': 'file-text'
    },
    'reminders': {
        'title': 'Hatırlatıcılar',
        'desc': 'Otomatik hatırlatıcı ve bildirim sistemi',
        'api': '/api/reminders',
        'icon': 'bell'
    },
    'announcements': {
        'title': 'Duyurular',
        'desc': 'Toplu duyuru ve SMS/Email gönderimi',
        'api': '/api/announcements',
        'icon': 'megaphone'
    },
    'pos': {
        'title': 'Hızlı Satış (POS)',
        'desc': 'Hızlı satış ve kasa sistemi',
        'api': '/api/pos',
        'icon': 'shopping-cart'
    },
    'service-definitions': {
        'title': 'Hizmet Tanımları',
        'desc': 'Hizmet tanımları ve fiyatlandırma',
        'api': '/api/service-definitions',
        'icon': 'tag'
    },
    'reports': {
        'title': 'Raporlar',
        'desc': 'Detaylı raporlar ve analizler',
        'api': '/api/reports',
        'icon': 'bar-chart-2'
    },
    'ai-assistant': {
        'title': 'AI Asistan',
        'desc': 'Yapay zeka destekli asistan (Jarvis)',
        'api': '/api/ai',
        'icon': 'bot'
    },
    'knowledge-base': {
        'title': 'Bilgi Bankası',
        'desc': 'Teknik bilgi bankası ve dokümantasyon',
        'api': '/api/kb',
        'icon': 'book-open'
    },
    'settings': {
        'title': 'Ayarlar',
        'desc': 'Sistem ayarları ve konfigürasyon',
        'api': '/api/settings',
        'icon': 'settings'
    },
    'audit-log': {
        'title': 'Log Kayıtları',
        'desc': 'Sistem log kayıtları ve denetim',
        'api': '/api/audit-log',
        'icon': 'file-search'
    },
    'support': {
        'title': 'Destek',
        'desc': 'Destek ve yardım merkezi',
        'api': '/api/support',
        'icon': 'help-circle'
    }
}

print("Total pages to generate:", len(pages))
for page_id, info in pages.items():
    print(f"  - {page_id}: {info['title']}")

