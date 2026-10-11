from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_service_board_today_filter_accepts_localized_desktop_dates():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert "ayecFinanceDateKey(item.date||item.entry)!==ayecLocalDateKey(new Date())" in app
    assert 'match(/^(\\d{2})\\.(\\d{2})\\.(\\d{4})$/)' in app
    assert '"bekliyor","BEK\\u0130YOR"' in app
    assert '"teslim","TESL\\u0130M"' in app
    assert "@media(max-width:760px){.service-board-toolbar" in styles
