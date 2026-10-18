from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_external_tracking_row_typography_matches_desktop_item_roles():
    script = (WEB / "external-tracking-reference.js").read_text(encoding="utf-8")
    styles = (WEB / "external-tracking-reference.css").read_text(encoding="utf-8")

    assert '<span class="external-tracking-primary">' in script
    assert "external-tracking-primary{display:block;font-weight:400}" in styles
    assert 'td:nth-child(1) strong{font-family:"JetBrains Mono"' in styles
    assert 'td:nth-child(4){font-family:"JetBrains Mono"' in styles
    assert 'td:nth-child(5) small{font-size:12px;line-height:16px}' in styles
    assert 'td:nth-child(7){font-family:"JetBrains Mono"' in styles


def test_external_tracking_pending_metric_detail_matches_desktop():
    script = (WEB / "external-tracking-reference.js").read_text(encoding="utf-8")

    assert "<footer>Fiyat / Onay</footer>" in script
    assert "Bekleyen i\\u015Flemler</footer>" not in script


def test_external_tracking_report_export_label_matches_desktop():
    script = (WEB / "external-tracking-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "external_tracking_page.py").read_text(encoding="utf-8")

    assert 'data-external-export>Excel / Rapor</button>' in script
    assert 'QPushButton("Excel / Rapor")' in desktop


def test_external_tracking_header_casing_and_wrapping_match_desktop():
    script = (WEB / "external-tracking-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "external_tracking_page.py").read_text(encoding="utf-8")

    assert '"Takip No /<br>Servis No"' in script
    assert '"M\\u00FC\\u015Fteri & \\u00DCr\\u00FCn"' in script
    assert '"D\\u0131\\u015F Servis / Yer"' in script
    assert '"G\\u00F6nderim<br>Tarihi"' in script
    assert '"Garanti<br>Kapsam\\u0131"' in script
    assert '"Maliyet /<br>Tutar"' in script
    assert '"Durum", "\\u0130\\u015Flemler"' in script
    assert '"Takip No /\\nServis No"' in desktop
    assert '"G\\u00f6nderim\\nTarihi"' in desktop


def test_external_tracking_row_actions_match_desktop_button_geometry():
    styles = (WEB / "external-tracking-reference.css").read_text(encoding="utf-8")

    assert "td:last-child button[data-external-edit]{width:74px;min-width:74px}" in styles
    assert "td:last-child button[data-external-delete]{width:36px;min-width:36px}" in styles
    assert "td:last-child button{box-sizing:border-box;height:30px;min-height:0" in styles
    assert "button[data-external-edit]{border:1px solid #26354b;border-radius:4px" in styles
    assert "button[data-external-delete]{border:1px solid #ef4444;border-radius:4px" in styles


def test_hidden_external_tracking_audit_asserts_desktop_action_geometry():
    audit = (ROOT / "tools" / "quality" / "external_tracking_double_click_offscreen.cjs").read_text(encoding="utf-8")

    assert "pageResult.rowActions" in audit
    assert 'width: 74, height: 30' in audit
    assert 'width: 36, height: 30' in audit
    assert 'pendingMetricLabel).startsWith("Fiyat / Onay")' in audit
