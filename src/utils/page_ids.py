# -*- coding: utf-8 -*-

"""
Merkezi Sayfa ID Kaydı
Tüm switch_page() çağrılarında bu sabitleri kullanın — magic number yazmayın.
"""


class PageIds:
    # ── Ana Sayfa ──────────────────────────────────────────────────────────
    DASHBOARD = 40

    # ── Operasyon ──────────────────────────────────────────────────────────
    PC_BUILDER        = 300
    NEW_SERVICE       = 150
    SERVICE_BOARD     = 41   # Service board / Kanban
    SERVICE_LIST      = 42   # Service list
    SERVICE_STATUS    = 43   # Service status panel
    TECHNICIAN_PANEL  = 62
    AUTOMOTIVE_STOCK  = 60
    FIELD_MAP         = 61
    AI_ASSISTANT      = 170
    APPOINTMENTS      = 30
    STOCK             = 50
    DEVICE_BRANDS     = 145
    PRODUCT_GROUPS    = 146
    REPORT_TEMPLATES  = 147
    LOGISTICS         = 65
    JOB_TRACKING      = 201
    VEHICLE_MAINTENANCE = 210

    # ── Müşteri & Finans ───────────────────────────────────────────────────
    CUSTOMER_LIST     = 21
    ADD_CUSTOMER      = 22
    INCOME_EXPENSE    = 101
    BANK_ACCOUNTS     = 105
    CHECK_BOND        = 106
    INVOICE           = 115
    CONSIGNMENT       = 66

    # ── Yönetim ───────────────────────────────────────────────────────────
    REPORTS           = 111
    OP_REPORTS        = 260
    PERSONNEL         = 10
    SERVICE_SETTINGS  = 140

    # ── Sistem ────────────────────────────────────────────────────────────
    BACKUP            = 180
    KNOWLEDGE_BASE    = 160
    SUPPORT           = 70
    SETTINGS          = 130
    USER_MANUAL       = 261

    # ── Diğer ─────────────────────────────────────────────────────────────
    PROJECTS          = 200
    PROJECT_ARCHIVE   = 202
    LOGOUT            = -1
