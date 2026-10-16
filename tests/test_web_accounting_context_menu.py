from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_accounting_context_menus_match_desktop_actions():
    desktop = (ROOT / "src" / "ui" / "pages" / "_accounting_table_mixin.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("const ayecFinanceShowContextBase=showContext")
    end = app.index("const ayecFinanceContextActionBase=contextAction", start)
    menus = app[start:end]
    expected = ["finance-detail", "finance-export", "finance-pdf", "finance-print"]
    positions = []
    cursor = 0
    for action in expected:
        position = menus.index(f'"{action}"', cursor)
        positions.append(position)
        cursor = position + len(action) + 2

    desktop_start = desktop.index("def show_table_context_menu")
    desktop_menu = desktop[desktop_start:]
    assert positions == sorted(positions)
    assert "page_id=101" in desktop_menu
    assert 'entry.get("kind") == "date_group"' in desktop_menu
    assert "_toggle_ledger_date_group" in desktop_menu
    assert "on_table_double_click" in desktop_menu
    assert "export_to_excel" in desktop_menu
    assert "export_to_pdf" in desktop_menu
    assert "print_ledger" in desktop_menu
    assert 'kind==="finance-date-group"' in menus
    assert 'action="finance-date-toggle"' in menus
    assert 'ayecToggleLedgerDate(id)' in app
    assert "!ayecContextMenuEnabled()" in menus
    assert 'if(action==="finance-detail"&&item)financeDetailDialog(item)' in app
    assert '["","maintenance-separator"]' in menus
    assert 'menu.classList.add("open");menu.style.top=`${Math.max(8,Math.min(event.clientY,innerHeight-menu.offsetHeight-8))}px`' in menus
