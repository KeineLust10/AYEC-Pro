from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_appointment_views_normalize_iso_and_localized_dates():
    app = (WEB / "appointments-reference.js").read_text(encoding="utf-8")

    assert "function apDateKey(value)" in app
    assert "a.date===today" not in app
    assert "a.date>=today" not in app
    assert "apDateKey(a.date)===today" in app
    assert "apDate(d)===apDateKey(a.date)" in app
    assert "apDateKey(a.date)===apDate(d)" in app
    assert 'a.technician_name)===name&&apDateKey(a.date)>=today' in app
