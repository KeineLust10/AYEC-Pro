from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_web_date_only_defaults_and_download_names_use_local_calendar_keys():
    expected_sources = {
        "app.js": [
            'proforma_${today().replaceAll("-","")}.pdf',
            'const month=today().slice(0,7)',
            'link.download=`ayec-audit-${today()}.csv`',
        ],
        "customer-context-parity.js": ['musteri_listesi_${today().replaceAll("-", "")}.pdf'],
        "brand-export-parity.js": ['markalar-${today()}.${extension}'],
        "product-groups-export-parity.js": ['urun_gruplari-${today()}.${extension}'],
        "service-list-reference.js": ['const date = today().replaceAll("-", "");'],
        "external-tracking-reference.js": ['row.sent_date || today()'],
        "smart-home-sales-reference.js": ["date: localToday()"],
        "partners-reference.js": ['document.execCommand("insertText", false, today())'],
    }

    for filename, snippets in expected_sources.items():
        source = (WEB / filename).read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in source, f"{filename} is missing local-date behavior: {snippet}"

    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'localDate:today()' in route_smoke
    assert 'exportAudit.download?.name!=="servis_listesi_"+exportAudit.localDate.replaceAll("-","")+".pdf"' in route_smoke
