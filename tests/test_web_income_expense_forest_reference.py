from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_income_and_expense_views_use_forest_surface_tokens():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    for page in ("income", "expense"):
        scope = f'html[data-theme="forest"] body[data-page="{page}"]'
        assert f"{scope} .ie-page" in styles
        assert f"{scope} .ie-metrics article" in styles
        assert f"{scope} .ie-panel" in styles
        assert f"{scope} .ie-table-wrap" in styles
        assert "background: var(--surface);" in styles
        assert "background: var(--surface-2);" in styles
        assert "background: var(--input-bg, var(--surface));" in styles


def test_offscreen_route_audit_covers_income_creation_and_currency_conversion():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "result.incomeCreateWorkflow" in route_smoke
    assert "routes: results" in route_smoke
    assert 'workflow.currency !== "USD"' in route_smoke
    assert "workflow.tryEquivalent" in route_smoke
    assert 'workflow.toastText.includes("Gelir kaydedildi")' in route_smoke
    assert 'workflow.expenseType !== "Gider"' in route_smoke
    assert 'workflow.expenseToast.includes("Gider kaydedildi")' in route_smoke


def test_income_expense_tabs_have_roving_focus_and_linked_results_panel():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    for key in ("all", "expense", "income", "tax", "personnel"):
        assert f'id="ieTab-${{key}}"' in app
        assert 'aria-controls="ieTablePanel"' in app
    assert 'id="ieTablePanel" role="tabpanel"' in app
    assert 'aria-labelledby="ieTab-${ayecIncomeExpenseTab}"' in app
    assert 'button.tabIndex=selected?0:-1' in app
    assert 'event.key==="ArrowRight"' in app and 'event.key==="ArrowLeft"' in app
    assert 'event.key==="Home"' in app and 'event.key==="End"' in app
    assert "app.js?v=20261028-customer-layout-dialog-1" in index

