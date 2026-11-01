from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_contracts_reference_uses_desktop_controls_and_columns():
    source = (WEB / "contracts-reference.js").read_text(encoding="utf-8")
    page = (WEB / "index.html").read_text(encoding="utf-8")
    styles = (WEB / "contracts-reference.css").read_text(encoding="utf-8")
    layout_styles = (WEB / "typography-layout-fixes.css").read_text(encoding="utf-8")

    assert 'window.renderContractsReference = function' in source
    render_start = source.index('window.renderContractsReference = function')
    render_end = source.index('  function bindContractControls()', render_start)
    render = source[render_start:render_end]
    header = render.split('pageHead(', 1)[1].split(')}<div class="metric-grid', 1)[0]
    assert header.index('data-contract-plan') < header.index('data-contract-export') < header.index('data-generic-add') < header.index('data-contract-delete')
    assert 'data-generic-refresh' not in header
    filter_row = render.split('<div class="toolbar contracts-reference-filters">', 1)[1].split('</div>', 1)[0]
    assert 'data-generic-refresh' in filter_row
    assert 'contracts-reference-pager"><span class="muted" id="genericCount"' in render
    assert r'Listelenen: ${rows.length} / ${total} kay\u0131t' in source
    assert 'body:has(.contracts-reference-list) .page-head .actions{display:grid;grid-template-columns:repeat(2,max-content)' in styles
    assert 'body[data-page="contracts"] .contracts-reference-list' in layout_styles
    assert 'body[data-page="contracts"] .contracts-reference-metrics .metric' in layout_styles
    for control in (
        "data-contract-plan",
        "data-contract-export",
        "data-contract-delete",
        "data-generic-add",
        "data-contract-status",
        "contractType",
        "contractSla",
        "data-contract-page",
        "data-contract-calendar",
        "data-contract-renewal-view",
        "data-contract-footer-plans",
        "data-contract-footer-renewals",
    ):
        assert control in source
    for column in ("S\\u00d6ZLE\\u015eME NO", "M\\u00dc\\u015eTER\\u0130 / KURUM", "GE\\u00c7ERL\\u0130L\\u0130K", "KALAN S\\u00dcRE"):
        assert column in source
    assert '"contracts-reference.js?v=' in page
    assert 'openDialog("Eki Sil","SILME ONAYI"' in source
    assert 'dialogCancel").textContent="Hay\\u0131r"' in source
    assert 'dialogSubmit").classList.add("danger")' in source
    assert 'if (!confirm(' not in source
    assert 'const rowType = contractSearchKey(row.contract_type);' in source
    assert 'if (type !== "all" && !rowType.includes(contractSearchKey(type))) return false;' in source
    assert 'function updateContractFooter(source)' in source
    assert 'contractSearchKey(item.description || item.title || item.fault).includes("bak")' in source
    assert 'item.classList.toggle("is-selected", item === row)' in source
    assert 'item.setAttribute("aria-selected", String(item === row))' in source
    assert 'tr.is-selected{outline:2px solid var(--brand)' in styles
    assert 'function confirmContractDelete(meta,row)' in source
    assert 'S\\u0130LME ONAYI' in source
    assert 'row.id,_action:"delete"' in source


    assert 'function openContractCreateDialog(meta, customers)' in source
    assert '"Kiralama", "Servis", "Lisans", "Proje"' in source
    assert 'name="customer_id"' in source and 'name="start_date"' in source
    assert 'data-contract-file-select' in source and 'uploadContractFiles(result.id, files' in source
    assert 'event.target.closest(".contract-attachment-row")' in source
    assert 'openLink.click()' in source
    assert 'data-contract-attachment-select' in source
    assert 'data-contract-attachment-open' in source
    assert 'window.currentContractAttachmentSelection = attachmentId' in source
    assert '#appDialog.contract-create-dialog{width:min(650px' in styles
    assert 'height:min(752px' in styles and 'flex:1 1 auto' in styles


def test_contract_delete_offscreen_audit_covers_cancel_and_retry():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "contractDeleteCancelPreserved" in audit
    assert "contractDeleteFailureRetained" in audit
    assert "QA contract delete unavailable" in audit
    assert "contractDeleteAttempts !== 2" in audit


def test_contract_date_classifier_rejects_calendar_rollover_dates():
    source = (WEB / "contracts-reference.js").read_text(encoding="utf-8")
    start = source.index("function contractDaysUntil(")
    end = source.index("function contractTodayKey(", start)
    classifier = source[start:end]

    assert "target.getFullYear() !== Number(match[1])" in classifier
    assert "target.getMonth() !== Number(match[2]) - 1" in classifier
    assert "target.getDate() !== Number(match[3])" in classifier


def test_offscreen_route_audit_covers_contract_creation_payload_and_refresh():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "auditContractCreation" in audit
    assert 'contract.payload.title !== "Audit Annual SLA"' in audit
    assert 'contract.payload.contract_type !== "Bak\\u0131m"' in audit
    assert "contract.rowCount !== 5" in audit
    assert "!contract.createdVisible" in audit
    assert 'contract.attachmentCalls[0].filename !== "audit-sla.pdf"' in audit
    assert 'contract.previewUrl.endsWith("/api/desktop/contracts/attachments/940053/preview")' in audit
    assert "!contract.attachmentRemoved" in audit
    assert "attachmentDeleteFailureRetained" in audit
    assert "attachmentDeleteAttempts !== 2" in audit
    assert "contract.activeRows !== 3" in audit
    assert "contract.renewalRows !== 1" in audit
    assert "contract.expiredRows !== 1" in audit
    assert "contract.draftRows !== 1" in audit
    assert "contract.restoredRows !== 4" in audit
    assert "contractInvalidDateAudit" in audit
    assert "Invalid contract dates were not excluded" in audit
    assert "contract.detailRows !== 3" in audit
    assert "contract.updatePayload._action !== \"update\"" in audit
    assert "Number(contract.updatePayload.price) !== 19500" in audit
    assert "contract.contractDeletePayload._action !== \"delete\"" in audit
    assert "contract.contractDeleteRowGone" in audit
    assert 'mobileResult.contractDeleteFailureWorkflow = contractDeleteFailureWorkflow' in audit
    assert "contractDeleteFailureWorkflow.canceledWithoutWrite" in audit
    assert "contractDeleteFailureWorkflow.retainedAfterFailure" in audit
    assert "contractDeleteFailureWorkflow.retrySucceeded" in audit
    assert "contractRefreshFailureWorkflow.selectionCleared" in audit
    assert "contractRefreshFailureWorkflow.staleDeleteBlocked" in audit
    assert "exportBlobTextPromise=blob.text()" in audit
    assert 'contract.exportCsvText.includes("Audit Contract")' in audit


def test_contracts_reference_layout_is_full_width_and_mobile_adaptive():
    styles = (WEB / "contracts-reference.css").read_text(encoding="utf-8")
    viewport_styles = (WEB / "typography-layout-fixes.css").read_text(encoding="utf-8")

    assert ".contracts-reference-table{width:100%" in styles
    assert ".contracts-reference-table{min-width:0" in styles
    assert "@media(max-width:760px)" in styles
    assert ".contracts-reference-footer{display:grid" in styles
    assert "grid-template-columns:minmax(0,1fr)" in styles
    assert 'body[data-page="contracts"] .contracts-reference-list .contracts-reference-table-wrap' in viewport_styles
    assert "max-height: none;" in viewport_styles
    assert 'body[data-page="contracts"] .contracts-reference-metrics .metric' in viewport_styles
    assert "height: 82px;" in viewport_styles


def test_contract_metrics_keep_unmeasured_sla_response_time_as_placeholder():
    source = (WEB / "contracts-reference.js").read_text(encoding="utf-8")
    start = source.index("function contractTable(")
    end = source.index("window.renderContractsReference", start)
    contract_table = source[start:end]
    desktop = (ROOT / "src" / "ui" / "pages" / "contracts_page.py").read_text(encoding="utf-8")
    assert '"ORTALAMA SLA YANIT S\\u00dcRES\\u0130", "-"' in desktop
    assert "metricValues[0].textContent" in contract_table
    assert "metricValues[1].textContent" in contract_table
    assert "metricValues[2].textContent" in contract_table
    assert "metricValues[3].textContent" not in contract_table


def test_contracts_page_ctrl_k_focuses_and_selects_search():
    source = (WEB / "contracts-reference.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "window.ayecContractSearchShortcutBound" in source
    assert "event.key.toLowerCase() !== \"k\"" in source
    assert "search.focus();\n        search.select();" in source
    assert "contracts-reference.js?v=20261026-contract-search-shortcut-1" in index
