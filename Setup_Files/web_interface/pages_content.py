# -*- coding: utf-8 -*-

"""
Complete Web System - All Pages Content Generator
This will create all 27 pages with full functionality
"""

# Page content mapping based on desktop app
PAGES_CONTENT = {
    'dashboard': {
        'title': 'Genel Bakış',
        'description': 'Dashboard with stats, charts, and quick actions',
        'features': ['Stats cards', 'Recent activities', 'Quick actions', 'Charts']
    },
    'kanban': {
        'title': 'İş Emirleri (Pano)',
        'description': 'Kanban board for service management',
        'features': ['Drag & drop', 'Status columns', 'Service cards', 'Filters']
    },
    'service-status': {
        'title': 'Durum Ekranı',
        'description': 'Service status display screen',
        'features': ['Real-time updates', 'Status grid', 'Customer display']
    },
    'technician': {
        'title': 'Teknisyen Paneli',
        'description': 'Technician work panel',
        'features': ['Assigned tasks', 'Work log', 'Parts usage', 'Time tracking']
    },
    'external-tracking': {
        'title': 'Lojistik & Garanti',
        'description': 'External warranty tracking',
        'features': ['Warranty list', 'Shipping status', 'External services']
    },
    'field-service': {
        'title': 'Saha Haritası',
        'description': 'Field service map',
        'features': ['Google Maps', 'Service locations', 'Route planning']
    },
    'appointments': {
        'title': 'Randevular',
        'description': 'Appointment calendar',
        'features': ['Calendar view', 'Appointment list', 'Create/Edit', 'Reminders']
    },
    'new-transaction': {
        'title': 'Yeni İşlem',
        'description': 'New service transaction wizard',
        'features': ['3-step wizard', 'Customer selection', 'Device info', 'Confirmation']
    },
    'customers': {
        'title': 'Müşteri Listesi',
        'description': 'Customer management',
        'features': ['Customer list', 'Search/Filter', 'CRUD operations', 'Service history']
    },
    'contracts': {
        'title': 'Sözleşmeler',
        'description': 'Contract management',
        'features': ['Contract list', 'Create/Edit', 'Renewal tracking', 'PDF export']
    },
    'reminders': {
        'title': 'Hatırlatıcılar',
        'description': 'Reminder system',
        'features': ['Reminder list', 'Create/Edit', 'Notifications', 'Calendar integration']
    },
    'announcements': {
        'title': 'Duyurular',
        'description': 'Announcements and notifications',
        'features': ['Announcement list', 'Create/Edit', 'SMS/Email', 'Templates']
    },
    'stock': {
        'title': 'Stok Yönetimi',
        'description': 'Stock management',
        'features': ['Part list', 'Stock levels', 'Low stock alerts', 'CRUD operations']
    },
    'pos': {
        'title': 'Hızlı Satış (POS)',
        'description': 'Point of sale system',
        'features': ['Product selection', 'Cart', 'Payment', 'Receipt printing']
    },
    'service-definitions': {
        'title': 'Hizmet Tanımları',
        'description': 'Service definitions and pricing',
        'features': ['Service list', 'Pricing', 'Categories', 'CRUD operations']
    },
    'accounting': {
        'title': 'Gelir / Gider',
        'description': 'Income and expense tracking',
        'features': ['Transaction list', 'Income/Expense', 'Categories', 'Reports']
    },
    'reports': {
        'title': 'Raporlar',
        'description': 'Reports and analytics',
        'features': ['Report types', 'Date filters', 'Charts', 'PDF/Excel export']
    },
    'ai-assistant': {
        'title': 'AI Asistan',
        'description': 'AI assistant (Jarvis)',
        'features': ['Chat interface', 'Voice input', 'Technical notes', 'Settings']
    },
    'knowledge-base': {
        'title': 'Bilgi Bankası',
        'description': 'Knowledge base',
        'features': ['Article list', 'Search', 'Categories', 'Create/Edit']
    },
    'settings': {
        'title': 'Ayarlar',
        'description': 'System settings',
        'features': ['General', 'Company info', 'Users', 'Integrations', 'Backup']
    },
    'audit-log': {
        'title': 'Log Kayıtları',
        'description': 'Audit log',
        'features': ['Log list', 'Filters', 'User actions', 'Export']
    },
    'support': {
        'title': 'Destek',
        'description': 'Support and help',
        'features': ['Help articles', 'Contact', 'Ticket system', 'FAQ']
    },
    'personnel': {
        'title': 'Personel',
        'description': 'Personnel management',
        'features': ['Employee list', 'Roles', 'Permissions', 'CRUD operations']
    }
}

print("Total pages:", len(PAGES_CONTENT))
for page_id, content in PAGES_CONTENT.items():
    print(f"- {page_id}: {content['title']}")

