# -*- coding: utf-8 -*-

PAGE_CONTEXT_KEYS = {
    40: "rc_dashboard",
    21: "rc_customers",
    50: "rc_stock",
    101: "rc_accounting",
    140: "rc_services",
    30: "rc_appointments",
    120: "rc_announcements",
    160: "rc_knowledge_base",
    10: "rc_personnel",
    25: "rc_contracts",
    201: "rc_job_service",
    200: "rc_projects",
    202: "rc_projects",
    65: "rc_logistics",
    66: "rc_loaner",
    105: "rc_bank",
}


def is_context_menu_enabled(db, page_id=None, explicit_key=None):
    if not db:
        return True
    if str(db.get_setting("enable_right_click", "1")) != "1":
        return False
    key = explicit_key or PAGE_CONTEXT_KEYS.get(page_id)
    if not key:
        return True
    return str(db.get_setting(key, "1")) == "1"
