from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_external_tracking_delete_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    start = source.index("const removeRow = async id => {")
    end = source.index("const exportWorkbook", start)
    block = source[start:end]

    assert "window.confirm" not in block and "!confirm(" not in block
    assert 'openDialog("Harici Takip Kayd\\u0131n\\u0131 Sil"' in block
    assert '"Evet, Sil"' in block
    assert 'textContent = "Hay\\u0131r"' in block
    assert 'body: JSON.stringify({ id: row.id, _action: "delete" })' in block


def test_external_tracking_context_menu_respects_preference_and_keeps_multiselection():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    start = source.index('document.addEventListener("contextmenu", event => {')
    end = source.index('document.addEventListener("click", event => {', start)
    block = source[start:end]

    assert 'view !== "external" || !ayecContextMenuEnabled()' in block
    assert 'if (!multiselect) { selectedIds.clear(); selectedIds.add(id); }' in block
    assert 'else if (!selectedIds.size) selectedIds.add(id);' in block


def test_external_tracking_context_menu_supports_keyboard_focus():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    start = source.index('document.addEventListener("keydown", event => {')
    end = source.index('document.addEventListener("click", event => {', start)
    block = source[start:end]

    assert 'event.key !== "ContextMenu"' in block
    assert 'event.shiftKey && event.key === "F10"' in block
    assert 'row.dispatchEvent(new MouseEvent("contextmenu"' in block
    assert 'menu.querySelector("[data-external-context]")?.focus()' in block


def test_external_tracking_context_menu_supports_touch_long_press():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    start = source.index('document.addEventListener("pointerdown", event => {')
    end = source.index('document.addEventListener("keydown", event => {', start)
    block = source[start:end]

    assert 'event.pointerType === "mouse"' in block
    assert 'event.pointerType === "mouse" || !ayecContextMenuEnabled()' in block
    assert '}, 550);' in block
    assert 'Math.hypot(event.clientX - externalContextPressOrigin.x, event.clientY - externalContextPressOrigin.y) <= 10' in block
    assert 'document.addEventListener("pointerup", cancelExternalContextPress);' in block
    assert 'document.addEventListener("pointercancel", cancelExternalContextPress);' in block


def test_external_tracking_double_click_uses_its_own_desktop_preference():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    start = source.index('document.addEventListener("dblclick", event => {')
    end = source.index('document.addEventListener("contextmenu", event => {', start)
    block = source[start:end]

    assert 'view !== "external" || !db.settings.doubleClick' in block
    assert "ayecContextMenuEnabled()" not in block
    assert "editRow(row)" in block


def test_external_tracking_cargo_labels_match_desktop_accents():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    assert "Gidi\\u015f:" in source
    assert "D\\u00f6n\\u00fc\\u015f:" in source


def test_external_tracking_summary_counts_match_desktop_status_buckets():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    assert 'replace(/\\u0131/g, "i").normalize("NFKD")' in source
    assert 'new Set(["kargoya verildi", "servise ulasti", "onarimda", "dis serviste"])' in source
    assert 'new Set(["onay bekliyor", "iade bekliyor"])' in source
    assert 'new Set(["geri geldi", "teslim alindi", "musteriye hazir"])' in source
    assert '<strong id="externalTrackingTotal">0</strong>' in source
    assert 'node.textContent = String(count)' in source
    assert 'node.textContent = count + " Kay\\u0131t"' not in source
    assert "/bekliyor|haz" not in source


def test_external_tracking_page_uses_desktop_column_order_and_month_combo():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    assert '"KARGO TAK\\u0130P", "GARANT\\u0130 KAPSAMI", "MAL\\u0130YET / TUTAR", "DURUM", "\\u0130\\u015eLEMLER"' in source
    assert '<select class="control" id="externalTrackingMonth"' in source
    assert 'const months = [...new Set(rows.map(row => monthOf(row.sent_date)).filter(Boolean))].sort().reverse()' in source
    assert "G\\u00F6sterilen ' + shown.length" in source


def test_external_tracking_status_tones_match_desktop_palette():
    source = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.css").read_text(encoding="utf-8")
    assert '"onarimda": "warn"' in source
    assert '"onay bekliyor": "info"' in source
    assert '"hazirlaniyor": "neutral"' in source
    assert '"hazir": "success"' in source
    assert '"dis serviste": "danger"' in source
    assert '.badge.info{background:#101a2b;color:#2563eb}' in stylesheet
    assert '.badge.neutral{background:#101a2b;color:#94a3b8}' in stylesheet
    assert '.badge.warn{background:#6b3f08;color:#fbbf24}' in stylesheet
    assert '.badge.danger{background:#7f1d1d;color:#c084fc}' in stylesheet
    assert '.badge.success{background:#073034;color:#4edea3}' in stylesheet


def test_external_tracking_pager_matches_desktop_page_label_width():
    stylesheet = (ROOT / "Web_Arayuzu" / "web" / "external-tracking-reference.css").read_text(encoding="utf-8")
    assert ".external-tracking-filters .search{box-sizing:border-box;flex:1 1 518px;min-width:200px;height:38px;min-height:38px}" in stylesheet
    assert ".external-tracking-filters select,.external-tracking-filters input[type=month]{flex:0 0 208px;width:208px;min-width:208px;height:48px}" in stylesheet
    assert "#externalTrackingPagination.external-tracking-page-footer>div b{min-width:52px}" in stylesheet
    assert "min-height:28px;margin:12px 16px 0;padding:0 0 0 4px" in stylesheet
    assert "box-sizing:border-box;width:34px;height:28px;min-height:28px!important" in stylesheet
