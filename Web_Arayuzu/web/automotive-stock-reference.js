(function () {
  let showingGuide = false;
  let lastPage = "";
  let purchasePricesVisible = false;
  const revealedPurchasePriceIds = new Set();
  const originalStockTable = stockTable;
  const originalStockTabs = stockTabs;

  function automotiveStockTable(rows, offset = 0) {
    const headers = ["ID", "Barkod", "\u00dcr\u00fcn Ad\u0131", "Marka", "Kategori", "OEM", "Muadil", "Ara\u00e7 Marka", "Ara\u00e7 Model", "Uyumlu Modeller", "Konum", "Tedarik\u00e7i", "Raf", "Stok", "Al\u0131\u015f \u25c9", "Sat\u0131\u015f", "PB", "Limit", "\u0130\u015flemler"];
    const cells = (item, index) => {
      const buy = Number(item.buy) || 0;
      const sell = Number(item.sell) || 0;
      const values = [
        String(item.id ?? index + offset + 1), item.barcode || "", item.name || "", item.brand || "", item.category || "",
        item.oem_code || "", item.equivalent_code || "", item.vehicle_brand || "", item.vehicle_model || "", item.compatible_models || "",
        item.position || "", item.supplier || "", item.shelf_number || item.shelf || "", `${Number(item.qty) || 0}`,
        money(buy, item.currency), money(sell, item.currency), item.currency || "TRY", String(Number(item.min) || 0),
        `<div class="row-actions"><button class="mini" data-action="edit-product" data-id="${esc(item.id)}">D\u00fczenle</button><button class="mini danger-outline" data-action="delete-product" data-id="${esc(item.id)}">Sil</button></div>`
      ];
      const priceVisible = purchasePricesVisible || revealedPurchasePriceIds.has(String(item.id));
      return `<tr data-kind="stock" data-id="${esc(item.id)}">${values.map((value, column) => `<td data-label="${headers[column]}">${column === 4 ? `<span class="badge">${esc(value)}</span>` : column === 13 ? `${statusBadge(Number(item.qty) <= Number(item.min) ? "Kritik" : "Stokta")} ${esc(value)}` : column === 14 ? `<button type="button" class="automotive-purchase-price" data-automotive-price-toggle data-id="${esc(item.id)}" data-purchase-price="${esc(value)}" aria-label="Al\u0131\u015f fiyat\u0131n\u0131 ${priceVisible ? "gizle" : "g\u00f6ster"}">${priceVisible ? esc(value) : "***"}</button>` : column === 18 ? value : esc(value)}</td>`).join("")}</tr>`;
    };
    return `<div class="table-wrap stock-reference-table-wrap automotive-stock-table-wrap"><table class="stock-reference-table automotive-stock-table"><thead><tr>${headers.map((header, index) => `<th>${index === 14 ? `<button type="button" data-automotive-price-all aria-label="Al\u0131\u015f fiyatlar\u0131n\u0131 ${purchasePricesVisible ? "gizle" : "g\u00f6ster"}" title="Al\u0131\u015f fiyatlar\u0131n\u0131 ${purchasePricesVisible ? "gizle" : "g\u00f6ster"}">${header}</button>` : header}</th>`).join("")}</tr></thead><tbody>${rows.map(cells).join("")}</tbody></table></div>`;
  }

  function guideMarkup() {
    return `<section class="automotive-stock-guide" hidden><h2>Yedek Par\u00e7a Y\u00f6netimi Kullan\u0131m K\u0131lavuzu</h2><p>Bu mod\u00fcl, otomotiv yedek par\u00e7alar\u0131n\u0131n stok takibini, OEM/muadil kodlar\u0131n\u0131, uyumlu ara\u00e7 bilgilerini ve tedarik\u00e7i kay\u0131tlar\u0131n\u0131 y\u00f6netir.</p><h3>1. Yedek Par\u00e7a Durumu Sekmesi</h3><ul><li><strong>Par\u00e7a Listesi:</strong> OEM kodu, muadil kodu, uyumlu ara\u00e7, raf/konum ve fiyat bilgisiyle t\u00fcm par\u00e7alar\u0131 listeler.</li><li><strong>Kritik Par\u00e7alar:</strong> Limitin alt\u0131na d\u00fc\u015fen par\u00e7alar\u0131 g\u00f6sterir.</li><li><strong>Yeni Par\u00e7a:</strong> Yeni yedek par\u00e7a kayd\u0131 olu\u015fturur.</li></ul><h3>2. Par\u00e7a Hareketleri Sekmesi</h3><ul><li><strong>Ge\u00e7mi\u015f:</strong> Giri\u015f ve \u00e7\u0131k\u0131\u015f i\u015flemlerini tarih s\u0131ras\u0131yla listeler.</li><li><strong>\u0130\u015flem T\u00fcr\u00fc:</strong> Sat\u0131n alma, servis t\u00fcketimi ve manuel d\u00fczeltmeleri izler.</li></ul><h3>3. \u0130pu\u00e7lar\u0131 ve K\u0131sayollar</h3><p>Par\u00e7a ad\u0131, OEM kodu veya stok koduyla aray\u0131n. Par\u00e7aya \u00e7ift t\u0131klayarak d\u00fczenleyin; sa\u011f t\u0131klayarak stok giri\u015f ve \u00e7\u0131k\u0131\u015f\u0131 yap\u0131n. Excel, CSV veya foto\u011fraftan toplu par\u00e7a aktar\u0131m\u0131 i\u00e7in Ak\u0131ll\u0131 \u0130\u00e7e Aktarma sayfas\u0131n\u0131 kullan\u0131n.</p></section>`;
  }

  stockTable = function (rows, offset = 0) {
    return currentSector === "otomotiv" && page === "automotive-stock" ? automotiveStockTable(rows, offset) : originalStockTable(rows, offset);
  };

  stockTabs = function (active) {
    if (currentSector !== "otomotiv" || !["automotive-stock", "movements"].includes(page)) return originalStockTabs(active);
    const guideEnabled = String(desktopInternalSettings.feature_usage_guides_active ?? "1") === "1";
    return `<div class="tabs automotive-stock-tabs"><button class="tab ${page === "automotive-stock" && !showingGuide ? "active" : ""}" data-page="automotive-stock">Yedek Par\u00e7a Durumu</button><button class="tab ${page === "movements" ? "active" : ""}" data-page="movements">Par\u00e7a Hareketleri</button><button class="tab" data-page="stock-locations">Depo Transferleri</button>${guideEnabled ? `<button class="tab ${showingGuide ? "active" : ""}" data-automotive-stock-guide>Nas\u0131l Kullan\u0131l\u0131r?</button>` : ""}</div>`;
  };

  const originalRender = render;
  document.addEventListener("click", event => {
    if (currentSector !== "otomotiv" || page !== "automotive-stock") return;
    const allButton = event.target.closest("[data-automotive-price-all]");
    const priceButton = event.target.closest("[data-automotive-price-toggle]");
    if (!allButton && !priceButton) return;
    event.preventDefault();
    event.stopPropagation();
    if (allButton) {
      purchasePricesVisible = !purchasePricesVisible;
      revealedPurchasePriceIds.clear();
    } else {
      const id = String(priceButton.dataset.id);
      if (revealedPurchasePriceIds.has(id)) revealedPurchasePriceIds.delete(id);
      else revealedPurchasePriceIds.add(id);
    }
    $$('[data-automotive-price-toggle]').forEach(button => {
      const shown = purchasePricesVisible || revealedPurchasePriceIds.has(String(button.dataset.id));
      button.textContent = shown ? button.dataset.purchasePrice : "***";
      button.setAttribute("aria-label", `Al\u0131\u015f fiyat\u0131n\u0131 ${shown ? "gizle" : "g\u00f6ster"}`);
    });
    const button = $('[data-automotive-price-all]');
    if (button) {
      const label = `Al\u0131\u015f fiyatlar\u0131n\u0131 ${purchasePricesVisible ? "gizle" : "g\u00f6ster"}`;
      button.setAttribute("aria-label", label);
      button.title = label;
    }
  }, true);
  render = function (...args) {
    if (lastPage !== page) showingGuide = false;
    lastPage = page;
    const result = originalRender(...args);
    if (currentSector !== "otomotiv" || !["automotive-stock", "movements"].includes(page)) return result;
    const heading = $("#content .page-head h2");
    const description = $("#content .page-head p");
    if (page === "automotive-stock") {
      if (heading) heading.textContent = "Yedek Par\u00e7a Y\u00f6netimi";
      if (description) description.textContent = "Otomotiv yedek par\u00e7a, stok hareketleri ve al\u0131m kay\u0131tlar\u0131n\u0131 bu alandan y\u00f6netin.";
      $("#content .page-head [data-action='add-product']")?.replaceChildren(document.createTextNode("Yeni Par\u00e7a Ekle"));
      const search = $("#stockSearch");
      if (search) search.placeholder = "Par\u00e7a ad\u0131, OEM kodu veya stok kodu ile ara...";
    } else if (heading) heading.textContent = "Par\u00e7a Hareketleri";
    const tabs = $("#content .automotive-stock-tabs");
    if (!tabs) return result;
    const updatePurchasePriceButtons = visible => {
      $$("[data-automotive-price-toggle]").forEach(button => {
        const shown = visible || revealedPurchasePriceIds.has(String(button.dataset.id));
        button.textContent = shown ? button.dataset.purchasePrice : "***";
        button.setAttribute("aria-label", `Al\u0131\u015f fiyat\u0131n\u0131 ${shown ? "gizle" : "g\u00f6ster"}`);
      });
      const allButton = $("[data-automotive-price-all]");
      if (allButton) {
        const label = `Al\u0131\u015f fiyatlar\u0131n\u0131 ${visible ? "gizle" : "g\u00f6ster"}`;
        allButton.setAttribute("aria-label", label);
        allButton.title = label;
      }
    };
    $("[data-automotive-price-all]")?.addEventListener("click", () => {
      purchasePricesVisible = !purchasePricesVisible;
      revealedPurchasePriceIds.clear();
      updatePurchasePriceButtons(purchasePricesVisible);
    });
    $$("[data-automotive-price-toggle]").forEach(button => button.addEventListener("click", () => {
      const id = String(button.dataset.id);
      if (revealedPurchasePriceIds.has(id)) revealedPurchasePriceIds.delete(id);
      else revealedPurchasePriceIds.add(id);
      updatePurchasePriceButtons(purchasePricesVisible);
    }));
    tabs.insertAdjacentHTML("afterend", guideMarkup());
    const guide = $(".automotive-stock-guide");
    const applyGuide = visible => {
      showingGuide = visible;
      guide.hidden = !showingGuide;
      $(".automotive-stock-tabs [data-automotive-stock-guide]")?.classList.toggle("active", showingGuide);
      $(".stock-category-strip")?.toggleAttribute("hidden", showingGuide);
      $$("#content .card").forEach(card => card.toggleAttribute("hidden", showingGuide));
    };
    $("[data-automotive-stock-guide]")?.addEventListener("click", () => applyGuide(!showingGuide));
    if (showingGuide) applyGuide(true);
    return result;
  };
})();
