from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_pc_builder_is_loaded_after_shell_and_has_desktop_component_catalog():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")

    assert index.index('src="app.js?') < index.index('src="pc-builder-reference.js?')
    assert '["Anakart", "Anakart"' in script
    assert '["RAM (Bellek)", "RAM"' in script
    assert 'data-pc-preset="gaming"' in script
    assert 'data-pc-action="add-component"' in script
    assert 'function pcRefreshOfferCustomer()' in script
    assert 'pcRefreshOfferCustomer(); return;' in script
    assert 'const offerLabel = `Teklif No: ${pcOfferNo}' in script


def test_custom_component_empty_submission_matches_desktop_dialog_behavior():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "pc_builder_page.py").read_text(encoding="utf-8")

    assert 'if (!name) { toast("Bile\\u015fen ad\\u0131 bo\\u015f b\\u0131rak\\u0131lamaz.", "warning"); return true; } if (!category) return true;' in script
    assert '<input name="name">' in script
    assert '<input name="category">' in script
    assert 'elif not name:\n                self._warn("Bile\u015fen ad\u0131 bo\u015f b\u0131rak\u0131lamaz.")' in desktop


def test_pc_builder_quantity_input_matches_desktop_range_and_clamps_values():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "pc_builder_page.py").read_text(encoding="utf-8")

    assert "self.spn_qty.setRange(0, 99)" in desktop
    assert 'data-pc-qty type="number" min="0" max="99"' in script
    assert 'function pcSetQuantity(row, input)' in script
    assert 'Math.min(99, Math.max(0, Math.trunc(Number(input.value) || 0)))' in script


def test_pc_builder_quantity_and_price_controls_match_native_inline_steppers():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")
    css = (WEB / "pc-builder-reference.css").read_text(encoding="utf-8")
    page = (WEB / "index.html").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "pc_builder_page.py").read_text(encoding="utf-8")

    assert 'data-pc-stepper="qty"' in script
    assert 'data-pc-stepper="price"' in script
    assert 'data-pc-step="qty"' in script and 'data-pc-step="price"' in script
    assert 'data-pc-price type="text" inputmode="decimal" maxlength="9"' in script
    assert "function pcSetPrice(row, input)" in script
    assert "self.spn_price = InlineNumberStepper(value=0.0, decimals=2)" in desktop
    assert "self.spn_price.setRange(0, 999999)" in desktop
    assert ".pc-inline-stepper button{box-sizing:border-box;flex:0 0 28px" in css
    assert "body[data-page=\"pc-builder\"] .pc-inline-stepper[data-pc-stepper=\"qty\"]{height:34px;overflow:visible;border:0;border-radius:0;background:transparent}" in css
    assert "body[data-page=\"pc-builder\"] .pc-inline-stepper[data-pc-stepper=\"qty\"] button{flex:0 0 24px;width:24px;height:24px;align-self:center;border-radius:12px" in css
    assert "body[data-page=\"pc-builder\"] .pc-inline-stepper[data-pc-stepper=\"qty\"] input[data-pc-qty]{height:28px;align-self:center" in css
    assert 'body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"]{height:34px;overflow:visible;border:0;border-radius:0;background:transparent;gap:4px;align-items:center;justify-content:center}' in css
    assert '@media (min-width:1201px) and (max-width:1350px){body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"]{overflow:visible}body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"] button[data-pc-delta="1"]{position:relative;left:16px}}' in css
    assert 'body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"] button{flex:0 0 24px;width:24px;height:24px;min-height:24px!important;align-self:center;border-radius:12px' in css
    assert 'color:var(--text-muted,#94a3b8);font-family:"Segoe UI",Arial,sans-serif;font-size:16px;font-weight:800}' in css
    assert 'body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"] input[data-pc-price]{flex:0 0 62px;width:62px;min-width:62px;height:28px;min-height:28px!important;align-self:center' in css
    assert 'body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"] input[data-pc-price]{flex:0 0 62px;width:62px;min-width:62px;height:28px;min-height:28px!important;align-self:center;background:var(--surface-alt,#0d1829);border-radius:4px;font-size:13px;font-weight:800;font-family:"Segoe UI",Arial,sans-serif}' in css
    assert 'body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"] .pc-stepper-suffix{padding:0;color:var(--text-muted,#94a3b8);font-size:12px;font-weight:700}' in css
    assert 'pc-builder-reference.css?v=20261024-spec-no-chevron-1' in page


def test_pc_builder_desktop_preset_bar_matches_native_geometry_and_label_size():
    css = (WEB / "pc-builder-reference.css").read_text(encoding="utf-8")

    assert "@media (min-width:1201px){.pc-preset-bar{border-radius:10px}.pc-preset-bar>span{font-size:12px}}" in css
    access = (WEB / "pc-builder-horizontal-access.css").read_text(encoding="utf-8")
    assert "@media(min-width:1001px) and (max-width:1350px){body[data-page=\"pc-builder\"] .pc-preset-bar button{padding:4px 12px;font-size:11px;font-weight:400}body[data-page=\"pc-builder\"] .pc-preset-bar button.success{padding:4px 14px;font-size:11px;font-weight:700}}" in access


def test_pc_builder_medium_desktop_keeps_non_table_controls_in_the_visible_content():
    access = (WEB / "pc-builder-horizontal-access.css").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "width:calc(100% - 40px);min-width:0;max-width:none;margin-left:20px" in access
    assert "height:auto;min-height:44px;flex-wrap:wrap" in access
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in access
    assert "toolbarActionVisible" in runner
    assert "nonTableSurfacesFit" in runner


def test_pc_builder_desktop_selects_hide_browser_only_arrows():
    css = (WEB / "pc-builder-reference.css").read_text(encoding="utf-8")

    assert '@media(min-width:1001px){body[data-page="pc-builder"] .pc-builder-page select{appearance:none;-webkit-appearance:none;background-image:linear-gradient(90deg,transparent calc(100% - 22px),var(--surface-2,#101a2b) calc(100% - 22px))}}' in css
    assert 'body[data-page="pc-builder"] .pc-component-row select[data-pc-spec]{box-sizing:border-box;height:34px;min-height:34px!important;padding:4px 30px 4px 10px;font-family:"Segoe UI",Arial,sans-serif!important;font-size:12px!important;text-overflow:ellipsis;border-radius:8px;background-image:linear-gradient(' in css
    assert 'background-repeat:no-repeat;background-position:0 0' in css
    assert 'background-size:auto' in css
    assert '@media(min-width:1201px) and (max-width:1350px){body[data-page="pc-builder"] .pc-component-row select[data-pc-spec]{position:relative;left:0;top:0}}' in css
    assert '@media(min-width:1201px) and (max-width:1350px){body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="price"]{position:relative;left:-8px;top:-1px}}' in css


def test_pc_builder_preserves_desktop_pricing_calculation_and_existing_tenant_routes():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")

    assert "cost * pcMargin / 100" in script
    assert "vatBase * pcVat / 100" in script
    assert 'loadAllDesktopTableRows("parts")' in script
    assert 'loadAllDesktopTableRows("customers")' in script
    assert '$("#pcComponents") || $(".pc-builder-page") || $("#content")' in script
    assert 'apiFetch("/api/desktop/table/customer_notes"' in script
    assert 'if (action === "customer") { const customer = await pcSaveNote("Teklif"); if (customer) customer360(' in script
    assert 'return customer;' in script
    assert 'data-pc-action="customer-note"' not in script
    actions = script[script.index('<div class="pc-actions">'):script.index('</div></section>', script.index('<div class="pc-actions">'))]
    customer_bar = script[script.index('<div class="pc-customer-bar">'):script.index('<div class="pc-preset-bar">')]
    assert 'data-pc-action="customer"' not in customer_bar
    assert actions.index('data-pc-action="pdf"') < actions.index('data-pc-action="customer"') < actions.index('data-pc-action="stock"')
    assert 'apiFetch("/api/desktop/table/audit_logs"' in script
    assert 'async function pcSaveOffer()' in script
    assert 'if (customer) {' in script
    assert 'toast(`Teklif kaydedilemedi: ${error?.message || error}`, "error");' in script
    assert 'toast(`M\\u00fc\\u015fteri kayd\\u0131 eklenemedi: ${error?.message || error}`, "error");' in script
    assert 'toast(`Stoktan d\\u00fc\\u015f\\u00fclemedi: ${error?.message || error}`, "error");' in script
    assert 'toast(`Finans kayd\\u0131 eklenemedi: ${error?.message || error}`, "error");' in script
    assert 'if (action === "save") await pcSaveOffer();' in script
    assert r'content: [22, "Yarat\u0131c\u0131 i\u00e7erik \u00fcretimi \u0026 video d\u00fczenleme' in script
    assert r'workstation: [18, "Profesyonel i\u015f istasyonu. ECC RAM \u0026 i\u015f y\u00fck\u00fc optimizasyonu."]' in script
    assert 'name="spec" value="Standart"' in script
    assert 'const spec = String(form.get("spec") || "").trim() || "Tip"' in script
    assert 'pcNewRow(name, category, spec, ["Standart"])' in script
    assert 'function pcBrandOptions(parts, category)' in script
    assert 'function pcBrandMatches(brand, text)' in script
    assert 'function pcSelectedPartMatches(row)' in script
    assert 'if (!pcSelectedPartMatches(row)) { row.partId = ""; row.price = 0; row.stock = null; }' in script
    assert 'if (priceInput) priceInput.value = row.price.toFixed(2);' in script
    assert 'stockLabel.classList.toggle("good", Number(row.stock) > 3)' in script
    assert 'pcBrandOptions(categoryParts, row.category)' in script
    assert 'const pcNativeNumber = (value) =>' in script
    assert r'\u2022 ${row.component}: ${row.product}  x${row.qty}' in script


def test_pc_builder_uses_the_tenant_vat_default_and_keeps_zero_tax():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "pcVat = ayecNormalizeVatPercent(desktopSettings?.default_vat_percent)" in script
    assert "function ayecNormalizeVatPercent(value)" in app
    assert r'Teklif Toplam\u0131: ${pcNativeNumber(totals.grand)}' in script
    assert 'pcNativeDateTime(new Date())' in script
    assert 'apiFetch("/api/desktop/pc-builder/deduct-stock"' in script
    assert 'const insufficient = groups.filter((group) => group.quantity > group.stock)' in script
    assert 'const available = groups.filter((group) => group.quantity <= group.stock)' in script
    assert 'row.stock = Number(selected.qty) || 0' in script
    assert 'items: available.map((group) => ({ part_id: group.part_id, quantity: group.quantity }))' in script
    assert 'apiFetch("/api/desktop/table/accounting"' in script
    assert 'const componentSummary = rows.slice(0, 3).map((row) => row.component).join(", ");' in script
    assert 'rows.length > 3 ? "..." : ""' in script
    assert 'data-pc-action="pdf"' in script
    assert 'function pcOpenProformaDialog()' in script
    assert 'fetch("/api/desktop/pc-builder/proforma.pdf"' in script
    assert 'name="template"' in script
    assert 'name="currency"' in script
    assert 'if (String(pcSettings().proforma_editor_html || "").trim())' in script
    assert 'value="editor_template"' in script


def test_pc_builder_customer_search_keeps_selection_across_filter_reset_and_preset():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")

    assert 'id="pcCustomerSearch"' in script
    assert '<option value="">\\u2014 M\\u00fc\\u015fteri Se\\u00e7 \\u2014</option>' in script
    assert 'toLocaleLowerCase("tr-TR")' in script
    assert 'const selectedId = select?.value || pcCustomerId' in script
    assert 'pcCustomerId = selectedId' in script
    assert 'select.value = pcCustomerId' in script
    assert 'String(customer.id) === String(pcCustomerId) ? "selected" : ""' in script
    assert 'pcCustomerSearch = ""; pcMargin = 20' in script


def test_pc_builder_topbar_uses_native_page_title_while_sidebar_label_stays_configured():
    app_script = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'target==="pc-builder"?"PC Yap\\u0131land\\u0131r\\u0131c\\u0131"' in app_script


def test_pc_builder_resolves_desktop_palette_tokens_in_midnight_theme():
    styles = (WEB / "pc-builder-reference.css").read_text(encoding="utf-8")

    assert "--surface-alt:var(--surface-2" in styles
    assert "--border:var(--line" in styles
    assert "--text:var(--ink" in styles
    assert "--window:var(--input-bg" in styles
    assert 'html[data-theme="midnight"] .pc-builder-page{--window:var(--bg,#080e1a)}' in styles
    assert "--accent:var(--brand" in styles
    assert ".pc-builder-header h2{display:flex;align-items:center;font-size:26.67px;position:relative;top:-8px}" in styles
    assert ".pc-builder-title-icon{display:inline-flex;flex:0 0 52px" in styles
    assert ".pc-builder-title-icon{margin-left:-5px;flex-basis:58px}" in styles
    assert ".pc-component-name,.pc-row-total{font-size:13.33px}" in styles
    assert ".pc-row-total{text-align:right;font-size:11px;color:#2563eb;white-space:nowrap}" in styles
    assert "@media (min-width:1201px) and (max-width:1350px)" in styles
    assert "width:calc(100% + 36px)" in styles
    assert ".pc-builder-page>:not(.pc-builder-header){width:1172px;min-width:1172px;max-width:none}" in styles
    assert ".pc-component-head{display:grid;grid-template-columns:160px 150px 135px minmax(0,1fr) 56px 110px 105px 55px 28px" in styles
    assert "padding-inline:12px;align-items:center" in styles
    assert ".pc-component-head>span:nth-child(-n+4){text-align:left}" in styles
    assert ".pc-component-head>span:nth-child(6),.pc-component-head>span:nth-child(7){text-align:right}" in styles
    assert ".pc-component-row{box-sizing:border-box;height:56px;min-height:56px;grid-template-columns:160px 150px 135px minmax(189px,1fr) 112px 148px 105px 55px 28px" in styles
    assert ".pc-components{gap:4px;margin-top:0}.pc-component-name{font-size:12px;font-weight:400}" in styles
    assert '@media(min-width:1351px){body[data-page="pc-builder"] .pc-components{padding-top:14px}}' in styles
    assert '@media(min-width:1351px){body[data-page="pc-builder"] .pc-inline-stepper[data-pc-stepper="qty"]{height:34px;overflow:visible;border:0;border-radius:0;background:transparent;gap:4px;align-items:center;justify-content:center}' in styles
    assert "@media (min-width:1201px) and (max-width:1350px){body[data-page=\"pc-builder\"] .pc-components{gap:8px}body[data-page=\"pc-builder\"] .pc-component-row{height:52px;min-height:52px}" in styles
    assert "grid-template-columns:350px 335px 274px" in styles
    assert 'body[data-page="pc-builder"] #content{overflow-x:auto}' in styles
    assert ".pc-customer-bar{box-sizing:border-box;height:44px" in styles


def test_pc_builder_remove_button_matches_desktop_toolbutton():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")
    styles = (WEB / "pc-builder-reference.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "pc_builder_page.py").read_text(encoding="utf-8")

    assert f'btn_del.setText("{chr(0x2715)}")' in desktop
    assert 'btn_del.setFixedSize(28, 28)' in desktop
    assert '>&#x2715;</button>' in script
    assert 'body[data-page="pc-builder"] .pc-component-row .pc-remove{box-sizing:border-box;min-width:28px;min-height:28px;width:28px;height:28px;padding:0!important;border:0;border-radius:6px;background:transparent;color:var(--text-muted,#94a3b8);font:13px "Segoe UI",Arial,sans-serif;line-height:1;box-shadow:none}' in styles


def test_pc_builder_medium_desktop_rows_match_rendered_reference_geometry():
    styles = (WEB / "pc-builder-reference.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "pc_builder_page.py").read_text(encoding="utf-8")

    assert "self.setFixedHeight(56)" in desktop
    assert "self.rows_layout.setSpacing(4)" in desktop
    assert "self.cmb_brand.setFixedHeight(34)" in desktop
    assert "body[data-page=\"pc-builder\"] .pc-components{gap:8px}body[data-page=\"pc-builder\"] .pc-component-row{height:52px;min-height:52px}" in styles
    assert "body[data-page=\"pc-builder\"] .pc-component-row select,body[data-page=\"pc-builder\"] .pc-component-row input{height:34px;min-height:34px!important}" in styles
    access = (WEB / "pc-builder-horizontal-access.css").read_text(encoding="utf-8")
    assert "@media(min-width:1001px) and (max-width:1350px){body[data-page=\"pc-builder\"] .pc-components{gap:8px;margin-top:14px}body[data-page=\"pc-builder\"] .pc-component-row{height:52px;min-height:52px}}" in access


def test_proforma_template_editor_is_a_saved_settings_section_with_token_insertion():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "proforma-template-editor.js").read_text(encoding="utf-8")
    pc_builder = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert index.rindex('src="proforma-template-editor.js?') > index.index('src="app.js?')
    assert 'settingsGroups.push(["TASARIM", [["proforma-template"' in script
    assert 'data-setting-key="proforma_editor_html"' in script
    assert 'data-setting-key="proforma_use_custom_editor"' in script
    assert 'data-proforma-pdf-file' in script
    assert '"/api/desktop/pc-builder/proforma-template"' in script
    assert 'value="custom_template"' in pc_builder
    assert 'insertEditorNode(wrapper)' in script
    assert 'id="proformaTemplateCanvas" class="proforma-template-canvas" contenteditable="true"' in script
    assert 'function sanitizeTemplateHtml(markup)' in script
    assert 'data-proforma-format="bold"' in script
    assert 'data-proforma-color' in script
    assert '[8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28]' in script
    assert '<option value="Segoe UI">Segoe UI</option>' in script
    assert 'const formats = { b: "bold", i: "italic", u: "underline" }' in script
    assert 'await apiFetch("/api/desktop/table/settings"' in script
    assert "const preview = await requestTemplatePdf()" in script
    assert 'const previousSettings = (await apiFetch("/api/desktop/bootstrap")).settings || {}' in script
    assert 'String(previousSettings.proforma_editor_html ?? desktopSettings.proforma_editor_html ?? "")' in script
    assert 'await persist("proforma_editor_html", previousHtml)' in script
    assert 'desktopSettings.proforma_use_custom_editor = "0"' in script
    assert 'if (toggle) toggle.checked = ["1", "true", "True"].includes(String(desktopSettings.proforma_use_custom_editor || "0"))' in script
    assert ".proforma-template-source" in styles
    assert ".proforma-template-canvas" in styles


def test_proforma_editor_surfaces_legacy_local_images_for_safe_replacement():
    script = (WEB / "proforma-template-editor.js").read_text(encoding="utf-8")
    styles = (WEB / "settings-theme-reference.css").read_text(encoding="utf-8")

    assert "function localImageName(source)" in script
    assert 'placeholder.className = "proforma-legacy-image"' in script
    assert 'data-proforma-legacy-image' in script
    assert 'activeLegacyImagePlaceholder.replaceWith(embedded)' in script
    assert "unresolvedLegacyImageCount()" in script
    assert "Eski masa\\u00fcst\\u00fc g\\u00f6rsellerini kaydetmeden \\u00f6nce de\\u011fi\\u015ftirin veya kald\\u0131r\\u0131n." in script
    assert ".proforma-legacy-image:focus-visible" in styles

def test_pc_builder_visual_fixture_uses_native_reference_date():
    audit = (ROOT / "tools" / "quality" / "pc_builder_offscreen_capture.cjs").read_text(encoding="utf-8")
    native = (ROOT / "artifacts" / "desktop_shell_reference" / "20261018_001800_152029" / "koyu_mavi_route_300_1600x1128.png")
    assert native.is_file()
    assert "textContent = 'Tarih: 24.10.2026'" in audit
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'result.pcBuilderVisualDate === "Tarih: 24.10.2026"' in route_smoke
    assert "dateNode.textContent='Tarih: 24.10.2026'" in route_smoke
    styles = (WEB / "pc-builder-reference.css").read_text(encoding="utf-8")
    assert ".pc-offer-meta span{position:relative;left:9px;top:-2px}" in styles
    assert ".pc-offer-meta strong{position:relative;left:15px;top:2px;display:flex;box-sizing:border-box;width:136px;height:32px;align-items:center;justify-content:center;padding:0}" in styles
    assert "@media (min-width:1351px) and (max-width:1597px){body[data-page=\"pc-builder\"] .pc-offer-meta strong" in styles
    capture_audit = (ROOT / "tools" / "quality" / "pc_builder_offscreen_capture.cjs").read_text(encoding="utf-8")
    assert "for (const width of [1201, 1280, 1350, 1440, 1597, 1598])" in capture_audit
    assert "const expectsHorizontalScroll = width <= 1350" in capture_audit
    assert "const offerMetadataFits = probe.offerBadge[2] === 136 && probe.offerBadge[3] === 32" in capture_audit
    assert "offerDateRight: Math.round(offerDate.right)" in capture_audit


def test_pc_builder_offscreen_audit_checks_desktop_margin_and_vat_totals():
    capture_audit = (ROOT / "tools" / "quality" / "pc_builder_offscreen_capture.cjs").read_text(encoding="utf-8")

    assert "const pricingCalculation = await evaluate" in capture_audit
    assert 'quantity.value = index === 0 ? "2" : "0"' in capture_audit
    assert 'price.value = index === 0 ? "100.00" : "0.00"' in capture_audit
    assert 'margin.value = "12.5"' in capture_audit
    assert 'vat.value = "18"' in capture_audit
    assert 'pricingCalculation.grandTotal !== "265.50 \\u20ba"' in capture_audit


def test_pc_builder_offscreen_audit_checks_customer_offer_note_write():
    capture_audit = (ROOT / "tools" / "quality" / "pc_builder_offscreen_capture.cjs").read_text(encoding="utf-8")

    assert "const customerSave = await evaluate" in capture_audit
    assert 'customer.dispatchEvent(new Event("change", { bubbles: true }))' in capture_audit
    assert 'item.endpoint === "/api/desktop/table/audit_logs"' in capture_audit
    assert 'item.endpoint === "/api/desktop/table/customer_notes"' in capture_audit
    assert 'customerSave.note?.body?.note_type !== "PC Teklif"' in capture_audit
    assert 'customerSave.note?.body?.type !== "PC Teklif"' in capture_audit
    assert 'customerSave.messages.some(message => message.includes("kaydedildi"))' in capture_audit


def test_pc_builder_offscreen_audit_checks_finance_income_payload():
    capture_audit = (ROOT / "tools" / "quality" / "pc_builder_offscreen_capture.cjs").read_text(encoding="utf-8")

    assert "const financeSave = await evaluate" in capture_audit
    assert 'financeSave.request?.endpoint !== "/api/desktop/table/accounting"' in capture_audit
    assert 'financeBody.type !== "Gelir"' in capture_audit
    assert 'financeBody.category !== "Sat\\u0131\\u015f"' in capture_audit
    assert "Number(financeBody.amount) !== 17280" in capture_audit
    assert 'financeBody.payment_method !== "Nakit"' in capture_audit
    assert 'financeBody.currency !== "TRY"' in capture_audit
