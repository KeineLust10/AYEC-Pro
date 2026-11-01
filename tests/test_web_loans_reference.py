from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
LOANS = (ROOT / "Web_Arayuzu" / "web" / "loans.js").read_text(encoding="utf-8")
PARITY = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")
STYLES = (ROOT / "Web_Arayuzu" / "web" / "styles.css").read_text(encoding="utf-8")

def test_loans_route_remains_available_without_a_desktop_menu_item():
    for section in ("ayecSectorMenuModels.teknik_servis=[", "ayecSectorMenuModels.otomotiv=["):
        start = APP.index(section)
        end = APP.index("];", start)
        assert 'id:"loans",label:"Krediler & Taksitler"' not in APP[start:end]
    assert '"banks","loans","checks"' in APP
    assert 'if(sectorPages[sector]?.has(pageId))' in APP
    assert 'loans:{group:"Finans",title:"Krediler & Taksitler",table:"loans"' in APP

def test_loans_view_preserves_contract_and_installment_behaviors():
    for endpoint in ("/api/desktop/table/${table}?limit=${limit}&offset=0", "/api/desktop/loan-installments/${item.id}/status"):
        assert endpoint in LOANS
    assert "/api/desktop/loans/create" in APP
    assert 'async function loadAllLoanTableRows(table)' in LOANS
    assert 'offset<Number(first.count||0)' in LOANS
    assert 'loadAllLoanTableRows("loans")' in LOANS
    assert 'loadAllLoanTableRows("loan_installments")' in LOANS
    assert 'async function loadAllDesktopTableRows(table)' in APP
    assert 'loadAllDesktopTableRows("loan_installments")' in APP
    for control in ("loanCreate", "loanSearch", "loanSelect", "loanCurrency", "loanExport", "loanPrint", "loanPrev", "loanNext", "loanMarkPending"):
        assert control in LOANS
    assert 'if(page!=="loans")return previousRender()' in LOANS

def test_new_loan_action_uses_desktop_parity_wizard():
    assert 'document.getElementById("loanCreate").onclick=openAdvancedLoanWizardManifestDialog' in LOANS
    wizard = APP[APP.index("function openAdvancedLoanWizardManifestDialog"):APP.index("function openCustomerSMSManifestDialog")]
    for field in ("loan_title", "loan_type", "principal", "interest_period", "term_months", "start_date", "kkdf_rate", "bsmv_rate", "attachments"):
        assert field in wizard
    for section in ("Genel Bilgiler", "Finansal Detaylar", r"Y\u00fckleme", r"\u00d6zet ve Onay"):
        assert section in wizard
    assert 'document_upload_enabled!==false' in wizard
    assert "return progress+body" in wizard
    assert "maxAttachments=20,maxTotalBytes=25*1024*1024" in wizard

def test_early_close_uses_atomic_tenant_api_from_active_app_workflow():
    assert '/api/desktop/loans/${encodeURIComponent(loan.id)}/early-close' in APP
    assert '()=>payRows(unpaid,true)' not in APP
    assert 'try{await apiFetch(`/api/desktop/loans/${encodeURIComponent(loan.id)}/early-close`' in APP

def test_loan_view_uses_normalized_paid_status_aliases_consistently():
    assert '["odendi","paid","dendi"]' in APP
    assert 'function installmentIsPaid(item)' in LOANS
    assert 'return ["odendi","paid","dendi"].includes(status)' in LOANS
    assert 'items.filter(installmentIsPaid)' in LOANS
    assert 'items.filter(row=>!installmentIsPaid(row))' in LOANS
    assert 'item.status==="\\u00d6dendi"' not in LOANS

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
        '/early-close',
    ):
        assert value in LOANS


def test_offscreen_route_audit_covers_bulk_loan_installment_payment():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.loanInstallmentPaymentWorkflow" in route_smoke
    assert "result.loanEarlyClosureWorkflow" in route_smoke
    assert "workflow.installmentIds.join(\",\") !== \"8811,8812\"" in route_smoke
    assert r'workflow.statuses.some(status => status !== "\u00d6dendi")' in route_smoke
    assert 'early.adjustedSummary.includes("74,00")' in route_smoke
    assert r'early.loanStatus !== "Erken Kapat\u0131ld\u0131"' in route_smoke
    assert "workflow.loanListReloaded" in route_smoke



def test_loan_search_matches_desktop_search_fields():
    desktop = (ROOT / "src" / "ui" / "pages" / "finance" / "bank_loans_widget.py").read_text(encoding="utf-8")
    assert 'for key in ("bank_name", "description", "loan_title", "id")' in desktop
    assert 'searchable=[row.bank_name,row.description,row.loan_title,row.id]' in LOANS

def test_offscreen_route_audit_exercises_the_complete_loan_create_wizard():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    for value in ("loanCreateWizardWorkflow", "QA Bank (QAB)", "interest_rate!==24", "data_base64!==\"aGVsbG8=\"", "attachmentCount!==20", "summaryVisible"):
        assert value in route_smoke

def test_offscreen_route_audit_checks_loan_wizard_on_narrow_mobile_viewports():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "loanWizardMobileWorkflow" in route_smoke
    assert "for(const width of [390,320])" in route_smoke
    assert "financial?.interestOverflow" in route_smoke
    assert "summary?.bodyScrollWidth" in route_smoke
    assert ".loan-interest-field{flex-wrap:wrap;min-width:0}" in STYLES
    assert ".loan-interest-field>input[type=number]{box-sizing:border-box;width:100%;max-width:100%;min-width:0;flex:1 1 100%}" in STYLES
    assert 'placeholder="Banka ad\\u0131, kredi no veya kullan\\u0131m yeri ara..."' in LOANS
    assert 'String(row.status||"").toLocaleLowerCase("tr-TR")==="aktif"' in LOANS



def test_loan_currency_formatting_matches_desktop_precision_and_fallback():
    start = LOANS.index("const loanMoney=")
    end = LOANS.index("};", start)
    formatter = LOANS[start:end]
    assert 'exchangeRateState?.[code]?.selling' in formatter
    assert 'salesManualRates' not in formatter
    assert 'desktopSettings.currency_precision' in formatter
    assert 'minimumFractionDigits:precision,maximumFractionDigits:precision' in formatter
    assert 'displayCode=code!=="TRY"&&rate<=0?"TRY":code' in formatter
    desktop = (ROOT / "src" / "ui" / "pages" / "finance" / "bank_loans_widget.py").read_text(encoding="utf-8")
    assert 'except ValueError:' in desktop[desktop.index("def _format_reference_money"):desktop.index("def _reference_filtered_loans")]


def test_loan_export_matches_desktop_display_currency_and_receipt_fields():
    assert 'amount:loanMoney(item.amount??item.total_amount)' in LOANS
    assert 'receipt:item.receipt_number||""' in LOANS


def test_loan_print_uses_filtered_desktop_style_payment_schedule():
    assert 'function printLoanSchedule()' in LOANS
    assert 'document.getElementById("loanPrint").onclick=printLoanSchedule' in LOANS
    assert 'id="loanPrintDocument"' in LOANS
    assert 'body.loan-print-mode>*:not(#loanPrintDocument)' in PARITY
    for column in ('<th>Banka</th>', '<th>Taksit</th>', '<th>Vade</th>', '<th>Tutar</th>', '<th>Durum</th>', r'<th>\u00d6deme tarihi</th>'):
        assert column in LOANS
    assert 'filteredLoans().flatMap(loan=>installmentRows.filter' in LOANS
