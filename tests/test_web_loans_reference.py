from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
LOANS = (ROOT / "Web_Arayuzu" / "web" / "loans.js").read_text(encoding="utf-8")
PARITY = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")

def test_loans_route_is_available_in_both_sector_menus():
    for section in ("ayecSectorMenuModels.teknik_servis=[", "ayecSectorMenuModels.otomotiv=["):
        start = APP.index(section)
        end = APP.index("];", start)
        assert 'id:"loans",label:"Krediler & Taksitler"' in APP[start:end]
    assert '"banks","loans","checks"' in APP
    assert 'loans:{group:"Finans",title:"Krediler & Taksitler",table:"loans"' in APP

def test_loans_view_preserves_contract_and_installment_behaviors():
    for endpoint in ("/api/desktop/table/loans?limit=500", "/api/desktop/table/loan_installments?limit=1000", "/api/desktop/loans/create", "/api/desktop/loan-installments/${item.id}/status"):
        assert endpoint in LOANS
    for control in ("loanCreate", "loanSearch", "loanSelect", "loanCurrency", "loanExport", "loanPrint", "loanPrev", "loanNext", "loanMarkPending"):
        assert control in LOANS
    assert 'if(page!=="loans")return previousRender()' in LOANS

def test_loans_filter_select_stays_within_mobile_form_width():
    assert 'body[data-page="loans"] .loan-toolbar #loanSelect' in PARITY
    assert 'width: 100%;\n    min-width: 0;\n    max-width: 100%;\n    flex: 1 1 100%;' in PARITY
