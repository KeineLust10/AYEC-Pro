from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_offers_list_matches_desktop_summary_and_column_order():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")

    assert '["offer_no","TEKLIF NO"]' in app
    assert '["created_at","TARIH"]' in app
    assert '["company_name","FIRMA"]' in app
    assert '["pdf_path","NOT / EVRAK"]' in app
    assert 'function ayecOfferStatusLabel' in app
    assert 'class="mini offer-open"' in app
    assert 'body[data-page="offers"] .offers-reference-metrics{grid-template-columns:repeat(5,minmax(0,1fr))' in styles
    assert 'grid-template-columns:minmax(0,2fr) minmax(420px,1fr)' in styles
    assert 'min-width:900px;table-layout:fixed' in styles
    assert 'white-space:normal!important;word-break:normal' in styles
    assert 'min-height:90px;height:auto' in styles
    assert 'width:170px;white-space:nowrap' in styles


def test_offer_reports_use_month_customer_and_staff_aggregates():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")

    assert "function renderOfferReports()" in app
    assert 'new Map()' in app[app.index("function renderOfferReports()"):]
    assert "Son 12 Ay Teklif Trendi" in app
    assert "En Cok Teklif Verilen" in app
    assert "En Cok Teklif Haz" in app
    assert "offer-report-total" in app
    assert 'grid-template-columns:repeat(4,minmax(0,1fr))' in styles
    assert 'body[data-page="offer-reports"] .offer-report-layout' in styles
    assert 'item.customers].slice(0,3)' in app
    assert 'table-layout:fixed' in styles
    assert '@media(max-width:430px){body[data-page="offer-reports"] .offer-report-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}' in styles
    assert 'body[data-page="offer-reports"] .offer-report-layout>.offer-report-panel:first-child table{min-width:640px}' in styles


def test_quote_builder_matches_reference_sections_and_responsive_cards():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'class="sales-reference-layout"' in app
    assert 'class="sales-reference-customer"' in app
    assert 'data-sales-category="${esc(id)}"' in app
    assert 'class="sales-cart-line"' in app
    assert 'data-sales-discount="${value}"' in app
    assert 'data-sales-currency="${code}"' in app
    assert "discount_percent:salesDiscountPercent" in app
    assert "data-sales-qty" in app
    assert "data-sales-focus-barcode" in app
    assert "data-sales-bulk-select" in app
    assert "data-sales-line-toggle" in app
    assert "salesLineComposerMarkup()" in app
    assert "salesLineDomainProducts()" in app
    assert "data-sales-line-add" in app
    assert 'id="salesDate" type="date"' in app
    assert "transaction_date:salesDraft.date" in app
    assert "let salesStockOnly=false" in app
    assert "(!salesStockOnly||Number(product.qty||0)>0)" in app
    assert "data-sales-filter aria-pressed=\"${salesStockOnly}\"" in app
    assert "F2 Toplu Se\u00e7im" in app
    assert "@media(max-width:760px){body[data-page=\"sales\"] .sales-line-fields" in styles
    assert "body[data-page=\"sales\"] .sales-reference-layout" in styles
    assert "@media(max-width:430px){body[data-page=\"sales\"] .sales-customer-actions" in styles
    assert "body[data-page=\"sales\"] .sales-line-fields" in styles
    assert "body[data-page=\"sales\"] .sales-reference-customer" in styles


def test_quote_builder_controls_have_bound_interactions():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'event.target.closest("[data-sales-category]")' in app
    assert 'salesStockOnly=!salesStockOnly;render();return' in app
    assert 'event.target.closest("[data-sales-discount]")' in app
    assert 'event.target.closest("[data-sales-currency]")' in app
    assert 'event.key==="F2"' in app
    assert '$("[data-sales-bulk-select]")' in app
    assert 'event.key==="F5"' in app
    assert 'event.key==="F8"' in app
    assert 'event.key==="F10"' in app
    assert 'event.key==="F12"' in app
    assert 'data-action="create-proforma">Proforma Olu\\u015ftur <kbd>F10</kbd>' in app
    assert 'data-action="pay-save">Do\\u011frudan Tahsilat Al &amp; Kaydet <kbd>F12</kbd>' in app
    assert 'event.key==="Enter"' in app


def test_offer_reference_list_uses_desktop_table_viewport():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="offers"] .offers-reference-list #genericHost .table-wrap { height: 310px; max-height: 310px; overflow: auto; }' in styles
    assert 'body[data-page="offers"] .offers-reference-list #genericHost .table-wrap { height: 360px; max-height: 360px; }' in styles


def test_sales_cart_context_menu_edits_and_manages_lines():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src/ui/pages/transaction_page_behaviors.py").read_text(encoding="utf-8")

    assert 'db.stock.find(x=>String(x.id)===String(line.productId))' in app
    assert 'db.stock.find(x=>String(x.id)===String(l.productId))' in app
    assert 'db.customers.find(x=>String(x.id)===String(salesCustomer))' in app
    assert 'data-kind="sales-cart" data-id="${index}"' in app
    assert 'if(kind==="sales-cart")items=[[' in app
    for action in (
        "sales-cart-quantity", "sales-cart-price", "sales-cart-description",
        "sales-cart-copy", "sales-cart-remove",
    ):
        assert action in app
    assert "unit_price:salesCart[index]?.unitPriceTry" in app
    assert "description:salesCart[index]?.description" in app
    assert 'isService=line?.type==="service"' in app
    assert 'if(!line||(!isService&&!product))return' in app
    assert 'type="text" inputmode="decimal" value="${esc(line.qty)}"' in app
    assert 'step="${service?"any":"1"}"' in app
    assert 'line.priceTry=line.unitPriceTry' in app
    assert 'max="999999999" step="1"' in app
    bulk_sales = (WEB / "bulk-sales-selection.js").read_text(encoding="utf-8")
    assert 'loadAllDesktopTableRows("services")' in bulk_sales
    assert 'apiFetch("/api/desktop/table/services?limit=1000")' not in bulk_sales
    service_catalog = app.split("async function loadSalesServiceCatalog()", 1)[1].split("\n}", 1)[0]
    assert 'loadAllDesktopTableRows("services")' in service_catalog
    assert 'services?limit=1000' not in service_catalog
    assert 'type="text" inputmode="decimal" value="${esc(line.qty)}"' in bulk_sales
    assert 'step="${service?"any":"1"}"' in bulk_sales
    assert 'line.priceTry=value' in bulk_sales
    assert '<textarea name="description">' in bulk_sales
    assert 'String(form.get("description")||"")' in bulk_sales
    assert '.trim().slice(0,500)' not in bulk_sales
    start = desktop.index("def show_cart_context_menu")
    end = desktop.index("\n    def ", start + 1)
    assert desktop[start:end].count("menu.addSeparator()") == 2
    assert '["Hizmeti Kopyala","sales-cart-copy"],["","sales-cart-separator"],["Sepetten \\u00c7\\u0131kar","sales-cart-remove"]' in app




def test_offscreen_route_audit_covers_numeric_stock_id_resolution():
    route_smoke = (ROOT / "tools/quality/web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.salesCartIdentifierWorkflow" in route_smoke
    assert "result.salesPaymentWorkflow" in route_smoke
    assert 'workflow.total) !== 120' in route_smoke
    assert 'workflow.cartShowsProduct' in route_smoke
    assert 'payment.path !== "/api/desktop/sales/commit"' in route_smoke
    assert 'Number(payment.paymentAmount) !== 100' in route_smoke
    assert 'payment.paymentMethod !== "Banka"' in route_smoke


def test_bulk_selection_enter_key_accepts_selected_rows():
    source = (WEB / "bulk-sales-selection.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "event.key!==\"Enter\"" in source
    assert "dialog.querySelector(\"#dialogForm\")?.requestSubmit()" in source
    assert "bulk-sales-selection.js?v=20261027-offer-edit-unit-price-parity-1" in index
    assert "result.bulkStockKeyboardWorkflow" in route_smoke


def test_mixed_offer_edit_preserves_service_lines_and_custom_part_prices():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    bulk = (WEB / "bulk-sales-selection.js").read_text(encoding="utf-8")
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    offer_edit = app.split("function beginOfferEdit(offer){", 1)[1].split("\n}", 1)[0]

    assert 'item.item_type||item.line_type||item.type' in offer_edit
    assert 'if(itemType==="service")' in offer_edit
    assert 'serviceId:item.item_id??item.serviceId??undefined' in offer_edit
    assert 'qty,unitPriceTry,priceTry:unitPriceTry' in offer_edit
    assert 'storedDiscountTry=Number(offer.discount_try)' in offer_edit
    assert 'discountPercent:Math.max(0,Math.min(100,discountPercent))' in offer_edit
    assert 'Number(line.unitPriceTry??line.priceTry??' in bulk
    assert "result.salesOfferMixedLineEditWorkflow" in route_smoke
    assert 'mixedOfferEdit.discountPercent !== 10' in route_smoke
    assert 'approvalExists:!!approval,approvalMarkup:document.querySelector("#content")?.innerHTML.includes("salesIncludeApproval")' in route_smoke
    assert 'mixedOfferEdit.approvalExists !== true' in route_smoke
