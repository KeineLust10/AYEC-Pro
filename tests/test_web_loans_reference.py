from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
LOANS = (ROOT / "Web_Arayuzu" / "web" / "loans.js").read_text(encoding="utf-8")
PARITY = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")

def test_loans_route_remains_available_without_a_desktop_menu_item():
    for section in ("ayecSectorMenuModels.teknik_servis=[", "ayecSectorMenuModels.otomotiv=["):
        start = APP.index(section)
        end = APP.index("];", start)
        assert 'id:"loans",label:"Krediler & Taksitler"' not in APP[start:end]
    assert '"banks","loans","checks"' in APP
    assert 'if(sectorPages[sector]?.has(pageId))' in APP
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


def test_loan_context_menus_match_desktop_loan_and_installment_actions():
    desktop = (ROOT / "src" / "ui" / "pages" / "finance" / "bank_loans_widget.py").read_text(encoding="utf-8")
    start = desktop.index("def _open_installment_context_menu(self, position):")
    end = desktop.index("def _change_installment_page", start)
    desktop_menu = desktop[start:end]
    for value in ('data-loan-context-row', 'data-installment-row', 'data-loan-context-action="edit"', 'data-loan-context-action="bulk"', 'data-loan-context-action="details"', 'data-loan-context-action="cancel"', 'data-loan-context-action="delete"'):
        assert value in LOANS
    assert 'data-loan-context-action="pay"' in LOANS
    assert 'data-loan-context-action="unpay"' in LOANS
    assert '\\u00d6deme Durumunu Geri Al' in LOANS
    assert 'Taksiti \\u00d6dendi Olarak \\u0130\\u015faretle' in LOANS
    assert 'data-loan-context-action="details">Detaylar</button>' in LOANS
    assert 'data-loan-context-action="details">Kredi Detaylar\\u0131</button>' in LOANS
    assert 'menu.addAction("\\u00d6deme Durumunu Geri Al"' in desktop_menu
    assert 'menu.addAction("Taksiti \\u00d6dendi Olarak \\u0130\\u015faretle"' in desktop_menu
    assert 'menu.addAction("Kredi Detaylar\\u0131"' in desktop_menu
    assert 'function openBulkLoanPayment(loan)' in LOANS
    assert 'loanPayAll' in LOANS
    for value in (
        'id="loanSelectAll"',
        'id="loanPaymentSummary"',
        'id="loanEarlyClose"',
        'function openEarlyLoanClosure(loan,unpaid)',
        'id="loanEarlyPenalty" type="number" min="0" max="5"',
        'id="loanEarlyComparison"',
        'status:"Erken Kapat\\u0131ld\\u0131"',
    ):
        assert value in LOANS
