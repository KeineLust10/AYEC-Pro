from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


def test_bank_reference_keeps_account_movements_linked_to_real_bank_ids():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function ayecBankUpdateLedger()")
    end = source.index("async function ayecLoadBankReference()", start)
    code = source[start:end]
    assert "row.bank_account_id&&ids.has(Number(row.bank_account_id))" in code
    assert "Number(row.bank_account_id)===selected" in code
    assert "financeTryValue(row)" in code
    assert 'loadAllDesktopTableData("bank_accounts")' in source


def test_offscreen_route_audit_covers_bank_account_creation_payload():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "result.bankAccountCreateWorkflow" in route_smoke
    assert 'workflow.bankName !== "QA New Bank"' in route_smoke
    assert 'workflow.currency !== "USD"' in route_smoke


def test_offscreen_route_audit_covers_bank_transfer_source_and_target():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.bankTransferWorkflow" in route_smoke
    assert 'transfer.path !== "/api/desktop/bank-transfer"' in route_smoke
    assert 'transfer.sourceId !== "8831"' in route_smoke
    assert 'transfer.targetId !== "8832"' in route_smoke


def test_actual_bank_and_loan_routes_honor_desktop_bank_context_setting():
    source = APP.read_text(encoding="utf-8")
    start = source.index("const ayecContextSettingByPage=")
    end = source.index(";", start)
    mapping = source[start:end]
    assert 'banks:"rc_bank"' in mapping
    assert 'loans:"rc_bank"' in mapping


def test_bank_summary_converts_mixed_account_currencies_to_try():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function ayecBankRenderData(rows)")
    end = source.index("function ayecBankUpdateLedger()", start)
    code = source[start:end]
    assert 'rateForCode(row.currency||"TRY")' in code
    assert "reduce((sum,row)=>sum+toTry(row),0)" in code


def test_bank_account_reference_has_responsive_treasury_composition():
    css = CSS.read_text(encoding="utf-8")
    assert 'body[data-page="banks"] .bank-ref-metrics' in css
    assert 'body[data-page="banks"] .bank-ref-columns' in css
    assert '@media(max-width:1100px){body[data-page="banks"]' in css
    assert '@media(max-width:700px){body[data-page="banks"]' in css
    assert '@media(max-width:420px){body[data-page="banks"]' in css
    assert '@media print{body[data-page="banks"]' in css


def test_bank_account_detail_exports_transactions_as_xlsx_and_pdf():
    source = APP.read_text(encoding="utf-8")
    assert 'button.dataset.bankTxExport=format' in source
    assert '/api/desktop/bank-accounts/${encodeURIComponent(account.id)}/transactions/export/${format}' in source
    assert 'format==="xlsx"?"Excel":"PDF"' in source
    assert 'search:txSearch?.value||""' in source
    assert 'filter_date:txDate?.checked===true' in source
    assert 'maximum:txMax?.value||""' in source
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "bankTransactionExportWorkflow" in route_smoke
    assert 'bank-accounts/7101/transactions/export/xlsx' in route_smoke


def test_bank_transfer_matches_desktop_source_balance_and_target_rules():
    source = APP.read_text(encoding="utf-8")
    start = source.index("async function ayecOpenBankTransfer(){")
    end = source.index("async function ayecPreviewBankStatement()", start)
    code = source[start:end]
    assert 'userAdminRole(currentAuthUser?.role)' in code
    assert 'loadAllDesktopTableData("bank_accounts")' in code
    assert 'Number(row.id)===sourceId?"selected":""' in code
    assert 'row.iban||row.account_number||""' in code
    assert 'Number(row.id)!==Number(source.id)' in code
    assert 'id="bankTransferSourceBalance"' in code
    assert 'amountInput.max=Number(source.current_balance)>0?String(Number(source.current_balance))' in code
    assert 'values.from_account_id===values.to_account_id' in code
    assert 'apiFetch("/api/desktop/bank-transfer"' in code
    assert 'if(action==="transfer-finance"){ayecOpenBankTransfer();return}' in source


def test_bank_transfer_dialog_stacks_fields_like_desktop_form():
    css = (ROOT / "Web_Arayuzu" / "web" / "finance-dialog-parity.css").read_text(encoding="utf-8")
    index = (ROOT / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")
    assert ".bank-transfer-form{grid-template-columns:minmax(0,1fr)!important}" in css
    assert 'finance-dialog-parity.css?v=' in index


def test_statement_preview_exports_every_parsed_row_and_can_remain_open():
    source = APP.read_text(encoding="utf-8")
    start = source.index("async function ayecPreviewBankStatement()")
    end = source.index("function ayecBindBankActions()", start)
    code = source[start:end]
    assert 'esc(file.name)' in code
    assert 'download("banka_ekstresi.csv"' in code
    assert 'rows.map(row=>({Date:row.date,Amount:row.amount,Reference:row.ref||"",Description:row.description||""}))' in code
    assert 'return false},"CSV D\\u0131\\u015fa Aktar")' in code
    assert 'document.querySelector("#dialogCancel").textContent="Kapat"' in code
    assert '!/^\\d{8}$/.test(date)' in code
    assert 'text.split(/\\r?\\n/)' in code
    assert 'line.match(/^:61:(\\d{6})(?:\\d{4})?([CD])([A-Z])?([0-9,]+)/)' in code


def test_bank_management_controls_require_admin_role():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function ayecBankShell(){")
    end = source.index("function ayecBankClass(row)", start)
    shell = source[start:end]
    actions_start = source.index("function ayecBindBankActions()")
    actions_end = source.index("ayecBindBankActions();", actions_start)
    actions = source[actions_start:actions_end]
    assert "const canManageBank=userAdminRole(currentAuthUser?.role)" in shell
    assert 'data-bank-action="transfer" ${canManageBank?"":"disabled' in shell
    assert 'data-bank-action="add" ${canManageBank?"":"disabled' in shell
    assert '["transfer","add"].includes(action)&&!userAdminRole(currentAuthUser?.role)' in actions


def test_bank_cards_support_desktop_account_context_and_detail_history():
    source = APP.read_text(encoding="utf-8")
    start = source.index("const ayecShowContextBeforeBankCards=showContext;")
    end = source.index("const ayecRenderBeforeBankReference=render;", start)
    code = source[start:end]
    assert 'card.dataset.kind="bank-account"' in source
    assert "bindInteractiveRow(card)" in source
    assert '["Detay G\\u00f6r","bank-detail",false]' in code
    assert '["D\\u00fczenle","bank-edit",!manager],["Transfer Yap","bank-transfer",!manager]' in code
    assert '["separator","separator",true]' in code
    assert 'disabled?" disabled":""' in code
    assert 'const accountTransactions=(db.finance||[]).filter(item=>(Number(item.bank_account_id)===Number(account.id)||Number(item.related_account_id)===Number(account.id))' in code
    assert 'data-bank-tx-search' in code and 'data-bank-tx-size' in code
    assert 'data-bank-tx-prev' in code and 'data-bank-tx-next' in code
    assert 'document.querySelector("#dialogCancel").hidden=true' in code


def test_bank_account_details_mirror_desktop_tabs_and_scoped_workflows():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function ayecOpenBankAccountDetail(account){")
    end = source.index("const ayecRenderBeforeBankReference=render;", start)
    code = source[start:end]
    for tab in ("general", "loans", "transactions", "analytics", "extra"):
        assert f'data-bank-tab="{tab}"' in code
        assert f'data-bank-panel="{tab}"' in code
        assert f'id="bank-detail-tab-{tab}"' in code
        assert f'id="bank-detail-panel-{tab}"' in code
        assert f'aria-labelledby="bank-detail-tab-{tab}"' in code
    assert 'tabindex="0" data-bank-tab="general"' in code
    assert 'tabindex="-1" data-bank-tab="loans"' in code
    assert 'tab.tabIndex=selected?0:-1' in code
    assert 'event.key==="ArrowRight"' in code and 'event.key==="ArrowLeft"' in code
    assert 'event.key==="Home"' in code and 'event.key==="End"' in code
    for control in ("data-bank-tx-search", "data-bank-tx-type", "data-bank-tx-date", "data-bank-tx-from", "data-bank-tx-to", "data-bank-tx-min", "data-bank-tx-max", "data-bank-tx-size", "data-bank-tx-prev", "data-bank-tx-next", "data-bank-tx-reset"):
        assert control in code
    assert 'ayecFetchAllDesktopTableRows("loans")' in code
    assert 'ayecFetchAllDesktopTableRows("loan_installments")' in code
    assert 'ayecFetchAllDesktopTableRows("accounting")' in code
    assert "data-bank-analytics-content" in code and "Kategorilere G\\u00f6re Harcama Da\\u011f\\u0131l\\u0131m\\u0131" in code
    assert "window.ayecSetBankTransactions" in code
    helper_start = source.index("async function ayecFetchAllDesktopTableRows(")
    helper_end = source.index("function ayecOpenBankAccountDetail(", helper_start)
    helper = source[helper_start:helper_end]
    assert '"?limit=1000&offset="+offset' in helper and "data.count" in helper


def test_bank_context_menu_supports_selection_bulk_actions_and_status_reactivation():
    source = APP.read_text(encoding="utf-8")
    menu_css = (ROOT / "Web_Arayuzu" / "web" / "styles.css").read_text(encoding="utf-8")
    assert "let ayecBankSelectedIds=new Set()" in source
    assert "event.shiftKey" in source and "event.ctrlKey||event.metaKey" in source
    assert '["\\u00c7oklu Pasifle\\u015ftir/Aktifle\\u015ftir","bank-bulk-toggle",!manager]' in source
    assert 'action==="bank-toggle"||action==="bank-bulk-toggle"' in source
    assert 'action==="bank-bulk-toggle"&&ayecBankSelectedIds.size' in source
    assert '["\\u00c7oklu Sil","bank-bulk-delete",!manager]' in source
    assert 'action==="bank-bulk-delete"&&ayecBankSelectedIds.size' in source
    assert 'is_active:isActive?0:1' in source
    assert 'Promise.allSettled(ids.map(accountId=>' in source
    assert ".context-menu button{height:24px;min-height:24px;" in menu_css
    assert "#contextMenu hr.context-menu-separator{height:2px;margin:0;" in menu_css
    assert 'html[data-theme="midnight"] .context-menu{background:#0F1428!important;' in menu_css


def test_bank_bulk_delete_retains_failed_accounts_for_retry():
    source = APP.read_text(encoding="utf-8")
    start = source.index('if(action==="bank-delete"||action==="bank-bulk-delete"){')
    end = source.index("function ayecFetchAllDesktopTableRows", start)
    block = source[start:end]

    assert 'failedIds=results.flatMap((result,index)=>result.status==="rejected"?[String(ids[index])]:[])' in block
    assert "ayecBankSelectedIds=new Set(failedIds)" in block
    assert 'failed?"error":"warning"' in block


def test_offscreen_audit_covers_bank_context_permission_and_confirmation_workflow():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.bankAccountContextWorkflow" in route_smoke
    assert 'bankContext.editPayload._action !== "update"' in route_smoke
    assert 'bankContext.editPayload.bank_name !== "QA Updated Bank"' in route_smoke
    assert 'bankContext.togglePayload._action !== "update"' in route_smoke
    assert 'bankContext.deletePayload._action !== "delete"' in route_smoke
    assert 'bankContext.confirmText.includes("QA Updated Bank")' in route_smoke
    assert 'bankContext.managerActions["bank-detail"].disabled' in route_smoke
    assert '["bank-edit","bank-transfer","bank-toggle","bank-delete"].some(action =>' in route_smoke
    assert "bankContext.bulkTogglePayloads.length !== 2" in route_smoke
    assert 'bankContext.bulkTogglePayloads.map(payload => String(payload.id)).sort().join(",") !== "8841,8842"' in route_smoke
    assert "bankDelete.deleteCancelPreserved" in route_smoke
    assert "bankContext.bulkDeletePayloads.length !== 2" in route_smoke
    assert "!bankContext.bulkDeleted" in route_smoke
    assert 'bankContext.partialDeleteSelected.join(",") !== "8841"' in route_smoke
    assert 'partialDeleteToast.includes("1 hesap silindi, 1 hesap silinemedi")' in route_smoke


def test_bank_bulk_delete_reports_partial_failures():
    source = APP.read_text(encoding="utf-8")

    assert 'failedIds=results.flatMap((result,index)=>result.status==="rejected"?[String(ids[index])]:[])' in source
    assert 'count=results.length-failedIds.length,failed=failedIds.length' in source
    assert 'toast(failed?`${count} hesap silindi, ${failed} hesap silinemedi.`:`${count} hesap silindi`,failed?"error":"warning")' in source
    assert "ayecBankSelectedIds=new Set(failedIds)" in source
