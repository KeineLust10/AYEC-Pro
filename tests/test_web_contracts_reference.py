from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_contracts_reference_uses_desktop_controls_and_columns():
    source = (WEB / "contracts-reference.js").read_text(encoding="utf-8")
    page = (WEB / "index.html").read_text(encoding="utf-8")
    styles = (WEB / "contracts-reference.css").read_text(encoding="utf-8")

    assert 'window.renderContractsReference = function' in source
    for control in (
        "data-contract-plan",
        "data-contract-export",
        "data-contract-delete",
        "data-generic-add",
        "data-contract-status",
        "contractType",
        "contractSla",
        "data-contract-page",
    ):
        assert control in source
    for column in ("S\\u00d6ZLE\\u015eME NO", "M\\u00dc\\u015eTER\\u0130 / KURUM", "GE\\u00c7ERL\\u0130L\\u0130K", "KALAN S\\u00dcRE"):
        assert column in source
    assert '"contracts-reference.js?v=' in page
    assert 'openDialog("Eki Sil","SILME ONAYI"' in source
    assert 'dialogCancel").textContent="Hay\\u0131r"' in source
    assert 'dialogSubmit").classList.add("danger")' in source
    assert 'if (!confirm(' not in source
    assert 'function confirmContractDelete(meta,row)' in source
    assert 'S\\u0130LME ONAYI' in source
    assert 'row.id,_action:"delete"' in source
    assert 'function openContractCreateDialog(meta, customers)' in source
    assert '"Kiralama", "Servis", "Lisans", "Proje"' in source
    assert 'name="customer_id"' in source and 'name="start_date"' in source
    assert 'data-contract-file-select' in source and 'uploadContractFiles(result.id, files' in source
    assert 'event.target.closest(".contract-attachment-row")' in source
    assert 'openLink.click()' in source
    assert '#appDialog.contract-create-dialog{width:min(650px' in styles
    assert 'height:min(752px' in styles and 'flex:1 1 auto' in styles


def test_contracts_reference_layout_is_full_width_and_mobile_adaptive():
    styles = (WEB / "contracts-reference.css").read_text(encoding="utf-8")

    assert ".contracts-reference-table{width:100%" in styles
    assert ".contracts-reference-table{min-width:0" in styles
    assert "@media(max-width:760px)" in styles
    assert "grid-template-columns:minmax(0,1fr)" in styles
