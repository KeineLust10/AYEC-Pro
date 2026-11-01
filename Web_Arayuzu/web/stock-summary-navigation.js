(function () {
  if (typeof renderStock !== "function" || typeof ayecStockSummaryCards !== "function") return;

  const renderStockBeforeSummaryNavigation = renderStock;
  const renderSummaryCardsBeforeNavigation = ayecStockSummaryCards;
  const stockTabsBeforeNavigation = stockTabs;

  stockTabs = function (active) {
    if (page !== "stock") return stockTabsBeforeNavigation.apply(this, arguments);
    return `<div class="tabs"><button class="tab ${active === "stock" ? "active" : ""}" data-page="stock">Stok Durumu</button><button class="tab ${active === "movements" ? "active" : ""}" data-page="movements">Stok Hareketleri</button><button class="tab" type="button" data-page="stock-locations" data-stock-transfer-tab>Depo Transferleri</button></div>`;
  };

  ayecStockSummaryCards = function () {
    const links = [
      ["stock-locations", "Son Fiziksel Depo Say\u0131m\u0131", "Say\u0131m detaylar\u0131n\u0131 a\u00e7"],
      ["loaners", "\u015eantiye / Servis Konsinye \u00c7\u0131k\u0131\u015f\u0131", "Konsinye i\u015flemlerini a\u00e7"],
      ["income", "Muhasebe Entegrasyonu", "Entegrasyon durumunu a\u00e7"],
    ];
    return `<div class="stock-reference-summary">${links.map(([page, title, description]) => `<article><button type="button" class="stock-reference-summary-action" data-page="${esc(page)}"><strong>${esc(title)}</strong><small>${esc(description)}</small></button></article>`).join("")}</div>`;
  };

  renderStock = function () {
    const view = renderStockBeforeSummaryNavigation.apply(this, arguments);
    return view + ayecStockSummaryCards();
  };

  window.ayecRestoreStockSummaryNavigation = function () {
    renderStock = renderStockBeforeSummaryNavigation;
    ayecStockSummaryCards = renderSummaryCardsBeforeNavigation;
    stockTabs = stockTabsBeforeNavigation;
    delete window.ayecRestoreStockSummaryNavigation;
  };
})();
