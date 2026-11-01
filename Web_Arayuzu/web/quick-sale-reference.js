(() => {
  let active = false;
  let cart = [];
  let selectedCartIndex = -1;
  let searchText = "";
  let discount = 0;
  let paymentMethod = "Nakit";
  let bankAccountId = "";
  let bankAccounts = [];
  let selectedCustomerId = "";
  let customers = [];
  let activeTenantId = "";

  const currentTenantId = () => String(typeof currentAuthUser !== "undefined" ? currentAuthUser?.tenant_id || "" : "").trim();
  const draftStorageKey = (tenantId = currentTenantId()) => {
    const id = String(tenantId || "").trim();
    return id ? "ayec.quick_sale_draft.v1." + encodeURIComponent(id) : "";
  };
  function clearDraft(tenantId = activeTenantId || currentTenantId()) {
    const key = draftStorageKey(tenantId);
    if (!key) return;
    try { localStorage.removeItem(key); } catch (_) {}
  }
  function ensureActiveTenant() {
    if (!active || activeTenantId === currentTenantId()) return true;
    active = false;
    cart = [];
    searchText = "";
    discount = 0;
    paymentMethod = "Nakit";
    bankAccountId = "";
    bankAccounts = [];
    selectedCustomerId = "";
    customers = [];
    document.querySelector("#appDialog")?.close("tenant-changed");
    return false;
  }
  function removeDraftKey(key) {
    try { localStorage.removeItem(key); } catch (_) {}
  }
  function saveDraft() {
    if (!ensureActiveTenant()) return;
    const key = draftStorageKey(activeTenantId);
    if (!key || !cart.length) {
      if (key) clearDraft();
      return;
    }
    try {
      localStorage.setItem(key, JSON.stringify({
        version: 1,
        tenant_id: activeTenantId,
        cart_items: cart,
        discount,
        payment_method: paymentMethod,
        bank_account_id: bankAccountId,
        customer_id: selectedCustomerId,
      }));
    } catch (_) {}
  }
  function restoreDraftPrompt() {
    if (!ensureActiveTenant()) return;
    const key = draftStorageKey(activeTenantId);
    if (!key) return;
    let draft;
    try { draft = JSON.parse(localStorage.getItem(key) || "null"); } catch (_) { draft = null; }
    if (draft?.version !== 1 || String(draft.tenant_id || "") !== String(currentAuthUser?.tenant_id || "") || !Array.isArray(draft.cart_items)) {
      if (draft) removeDraftKey(key);
      return;
    }
    const restored = [];
    let currency = "";
    for (const line of draft.cart_items) {
      const product = db.stock.find(item => String(item.id) === String(line.productId));
      if (!product || Number(product.qty || 0) <= 0) continue;
      const productCurrency = currencyOf(product);
      if (currency && productCurrency !== currency) continue;
      currency = productCurrency;
      const qty = Math.floor(Number(line.qty) || 0);
      if (qty > 0) restored.push({ productId: product.id, qty: Math.min(qty, Number(product.qty || 0)) });
    }
    if (!restored.length) {
      removeDraftKey(key);
      return;
    }
    openDialog("Kaydedilmemis Satis Taslagi", "HIZLI SATIS", '<p>' + restored.length + ' kalemlik tamamlanmamis bir satis bulundu. Taslagi geri yuklemek ister misiniz?</p>', () => {
      cart = restored;
      discount = Math.max(0, Math.min(Number(draft.discount) || 0, subtotal()));
      paymentMethod = ["Nakit", "Kredi Kart\u0131", "Havale/EFT"].includes(String(draft.payment_method || "")) ? draft.payment_method : "Nakit";
      bankAccountId = bankAccounts.some(item => String(item.id) === String(draft.bank_account_id || "")) ? String(draft.bank_account_id) : "";
      selectedCustomerId = customers.some(item => String(item.id) === String(draft.customer_id || "")) ? String(draft.customer_id) : "";
      saveDraft();
      render();
      return true;
    }, "Geri Yukle");
    const dialog = document.querySelector("#appDialog");
    const cancel = document.querySelector("#dialogCancel");
    if (cancel) cancel.textContent = "Taslagi Sil";
    const handleDraftPromptClose = () => {
      if (dialog?.open) return;
      dialog?.removeEventListener("close", handleDraftPromptClose);
      if (dialog.returnValue !== "ok" && dialog.returnValue !== "tenant-changed") {
        removeDraftKey(key);
        cart = [];
        discount = 0;
        paymentMethod = "Nakit";
        bankAccountId = "";
      }
    };
    dialog?.addEventListener("close", handleDraftPromptClose);
  }

  const currencyOf = item => String(item && item.currency || "TRY").toUpperCase();
  const cartCurrency = () => currencyOf(cart.length ? db.stock.find(row => String(row.id) === String(cart[0].productId)) : null);
  const subtotal = () => cart.reduce((sum, line) => {
    const item = db.stock.find(row => String(row.id) === String(line.productId));
    return sum + (item ? Number(item.sell || 0) * Number(line.qty || 0) : 0);
  }, 0);
  const total = () => Math.max(0, subtotal() - discount);
  const formatMoney = amount => money(amount, cartCurrency());
  const matches = item => {
    const query = searchText.trim().toLocaleLowerCase("tr-TR");
    if (!query) return Number(item.qty || 0) > 0;
    return [item.name, item.code, item.barcode, item.id]
      .some(value => String(value || "").toLocaleLowerCase("tr-TR").includes(query))
      && Number(item.qty || 0) > 0;
  };

  function renderProducts() {
    const rows = db.stock.filter(matches).map(item =>
      '<button type="button" class="quick-sale-product" data-qpos-add="' + esc(item.id) + '"><span><strong>' +
      esc(item.name) + '</strong><small>' + esc(item.code || item.barcode || '') + ' | Stok: ' + esc(item.qty) +
      '</small></span><b>' + money(item.sell, currencyOf(item)) + '</b></button>'
    ).join("");
    return rows || '<p class="muted">E\u015fle\u015fen stok \u00fcr\u00fcn\u00fc bulunamad\u0131.</p>';
  }

  function renderCart() {
    if (!cart.length) return '<p class="muted">Sepet bos. Urun arayin veya barkod okutun.</p>';
    return cart.map((line, index) => {
      const item = db.stock.find(row => String(row.id) === String(line.productId));
      if (!item) return "";
      return '<div class="quick-sale-cart-row' + (index === selectedCartIndex ? ' is-selected' : '') + '" data-qpos-row="' + index + '"><strong>' + esc(item.name) +
        '</strong><input class="control" type="number" min="1" max="' + esc(item.qty) +
        '" step="1" value="' + esc(line.qty) + '" data-qpos-qty="' + index +
        '" aria-label="Adet"><span>' + money(Number(item.sell || 0) * line.qty, currencyOf(item)) +
        '</span><button type="button" class="mini" data-qpos-remove="' + index +
        '" aria-label="Sepetten kald\u0131r">&times;</button></div>';
    }).join("");
  }

  function renderQuickSale() {
    const bankOptions = bankAccounts.map(item => {
      const id = item.id;
      const name = item.bank_name || item.account_name || item.name || ("Hesap " + id);
      return '<option value="' + esc(id) + '"' + (String(id) === String(bankAccountId) ? " selected" : "") +
        '>' + esc(name) + '</option>';
    }).join("");
    const customerOptions = customers.map(item => {
      const name = item.name || item.customer_name || ("M\u00fc\u015fteri " + item.id);
      return '<option value="' + esc(item.id) + '"' + (String(item.id) === String(selectedCustomerId) ? " selected" : "") +
        '>' + esc(name) + '</option>';
    }).join("");
    const currency = cartCurrency();
    return '<section class="quick-sale-workspace"><header class="quick-sale-heading"><div>' +
      '<p class="eyebrow">STOK VE TAHS\u0130LAT</p><h1>H\u0131zl\u0131 Sat\u0131\u015f</h1>' +
      '<p class="muted">Barkod okutun veya stok \u00fcr\u00fcn\u00fcn\u00fc aray\u0131p sepete ekleyin.</p></div>' +
      '<button type="button" class="secondary" data-qpos-close>Sales Hub ekran\u0131na d\u00f6n</button></header>' +
      '<div class="quick-sale-layout"><section class="card quick-sale-picker"><div class="card-head"><h2>\u00dcr\u00fcn Listesi</h2><span class="badge">Canl\u0131 stok</span></div>' +
      '<input class="control search" id="quickSaleSearch" type="search" value="' + esc(searchText) +
      '" placeholder="\u00dcr\u00fcn, kod veya barkod ara"><div class="quick-sale-products" id="quickSaleProducts">' + renderProducts() +
      '</div></section><aside class="card quick-sale-checkout"><div class="card-head"><h2>Sepet</h2><span class="badge">' +
      cart.length + ' kalem</span></div><div class="quick-sale-cart" id="quickSaleCart">' + renderCart() +
      '</div><div class="quick-sale-customer"><label for="quickSaleCustomer">M\u00fc\u015fteri</label><select class="control" id="quickSaleCustomer"><option value="">M\u00fc\u015fteri se\u00e7in (iste\u011fe ba\u011fl\u0131)</option>' + customerOptions +
      '</select><button type="button" class="secondary" data-qpos-customer-picker>M\u00fc\u015fteri i\u015flemleri</button></div><div class="quick-sale-totals"><div><span>Ara toplam</span><strong id="quickSaleSubtotal">' +
      formatMoney(subtotal()) + '</strong></div><label for="quickSaleDiscount">\u0130skonto (' + currency +
      ')</label><input class="control" id="quickSaleDiscount" type="number" min="0" max="' + subtotal() +
      '" step="1" value="' + esc(discount) + '"><div class="quick-sale-grand"><span>Genel toplam</span><strong id="quickSaleTotal">' +
      formatMoney(total()) + '</strong></div></div><div class="quick-sale-payment"><label>\u00d6deme y\u00f6ntemi<select class="control" id="quickSalePayment">' +
      '<option' + (paymentMethod === "Nakit" ? " selected" : "") + '>Nakit</option><option' +
      (paymentMethod === "Kredi Kart\u0131" ? " selected" : "") + '>Kredi Kart\u0131</option><option' +
      (paymentMethod === "Havale/EFT" ? " selected" : "") + '>Havale/EFT</option></select></label>' +
      '<label>Kasa / banka<select class="control" id="quickSaleBank"><option value="">Se\u00e7iniz...</option>' +
      bankOptions + '</select></label></div><div class="actions"><button type="button" class="primary" data-qpos-checkout' +
      (cart.length ? "" : " disabled") + '>Sat\u0131\u015f\u0131 tamamla</button><button type="button" class="secondary" data-qpos-clear' +
      (cart.length ? "" : " disabled") + '>Sepeti temizle</button></div></aside></div></section>';
  }

  function render() {
    const host = document.querySelector("#content");
    if (active && !ensureActiveTenant()) {
      if (host && typeof baseRenderSales === "function") host.innerHTML = baseRenderSales();
      return;
    }
    if (host) host.innerHTML = active ? renderQuickSale() : (typeof baseRenderSales === "function" ? baseRenderSales() : "");
  }

  function addProduct(product) {
    if (!ensureActiveTenant()) return render();
    if (!product || Number(product.qty || 0) <= 0) return toast("Bu \u00fcr\u00fcn stokta yok.", "warning");
    if (cart.length && currencyOf(product) !== cartCurrency()) {
      return toast("Farkl\u0131 para birimleri ayn\u0131 sepette sat\u0131lamaz.", "warning");
    }
    const line = cart.find(item => String(item.productId) === String(product.id));
    if (line) {
      if (line.qty >= Number(product.qty || 0)) return toast("Stoktaki maksimum adede ula\u015f\u0131ld\u0131.", "warning");
      line.qty += 1;
      selectedCartIndex = cart.indexOf(line);
    } else {
      cart.push({ productId: product.id, qty: 1 });
      selectedCartIndex = cart.length - 1;
    }
    saveDraft();
    render();
  }

  function removeCartItem(index) {
    if (!Number.isInteger(index) || index < 0 || index >= cart.length) return;
    cart.splice(index, 1);
    selectedCartIndex = cart.length ? Math.min(index, cart.length - 1) : -1;
    saveDraft();
    render();
  }

  function updateTotals() {
    const subtotalNode = document.querySelector("#quickSaleSubtotal");
    const totalNode = document.querySelector("#quickSaleTotal");
    const discountInput = document.querySelector("#quickSaleDiscount");
    if (subtotalNode) subtotalNode.textContent = formatMoney(subtotal());
    if (totalNode) totalNode.textContent = formatMoney(total());
    if (discountInput) discountInput.max = String(subtotal());
  }

  async function loadBanks() {
    const requestTenantId = activeTenantId;
    try {
      const result = await loadAllDesktopTableData("bank_accounts");
      if (!active || requestTenantId !== currentTenantId()) {
        ensureActiveTenant();
        return;
      }
      bankAccounts = result.rows || [];
      render();
    } catch (_) {
      bankAccounts = [];
    }
  }

  async function loadCustomers() {
    const requestTenantId = activeTenantId;
    try {
      const result = await loadAllDesktopTableData("customers");
      if (!active || requestTenantId !== currentTenantId()) {
        ensureActiveTenant();
        return;
      }
      const nextCustomers = result.rows || [];
      if (selectedCustomerId && !nextCustomers.some(item => String(item.id) === String(selectedCustomerId))) {
        selectedCustomerId = "";
        saveDraft();
      }
      customers = nextCustomers;
      render();
    } catch (_) {
      customers = [];
    }
  }

  function confirmCheckout() {
    if (!ensureActiveTenant()) return render();
    if (!cart.length) return;
    if (discount > subtotal()) {
      discount = subtotal();
      render();
      return toast("\u0130skonto ara toplamdan b\u00fcy\u00fck olamaz.", "warning");
    }
    openDialog("Sat\u0131\u015f Onay\u0131", "HIZLI SATI\u015e",
      '<p>Toplam <strong>' + formatMoney(total()) + '</strong> tutar\u0131ndaki sat\u0131\u015f\u0131 onayl\u0131yor musunuz?</p>' +
      '<p>\u00d6deme: ' + esc(paymentMethod) + ' | Para birimi: ' + esc(cartCurrency()) + '</p>',
      async () => {
        if (!ensureActiveTenant()) {
          render();
          return false;
        }
        const checkoutTenantId = activeTenantId;
        try {
          const result = await apiFetch("/api/desktop/sales/quick-commit", {
            method: "POST",
            body: JSON.stringify({
              lines: cart.map(line => ({ product_id: line.productId, qty: line.qty })),
              discount,
              payment_method: paymentMethod,
              bank_account_id: bankAccountId || null,
              customer_id: selectedCustomerId || null,
            }),
          });
          clearDraft(checkoutTenantId);
          if (currentTenantId() !== checkoutTenantId) {
            active = false;
            cart = [];
            searchText = "";
            discount = 0;
            paymentMethod = "Nakit";
            bankAccountId = "";
            bankAccounts = [];
            selectedCustomerId = "";
            customers = [];
            document.querySelector("#appDialog")?.close("tenant-changed");
            render();
            return true;
          }
          await hydrateDesktop();
          if (currentTenantId() !== checkoutTenantId) {
            ensureActiveTenant();
            render();
            return true;
          }
          active = false;
          cart = [];
          searchText = "";
          discount = 0;
          selectedCustomerId = "";
          render();
          toast("Sat\u0131\u015f tamamland\u0131: " + money(result.total, result.currency), "success");
          return true;
        } catch (error) {
          toast(error.message || "Sat\u0131\u015f tamamlanamad\u0131.", "error");
          return false;
        }
      },
      "Sat\u0131\u015f\u0131 onayla",
    );
  }

  const baseRenderSales = window.renderSales;
  if (typeof baseRenderSales === "function") {
    window.renderSales = function () {
      return active && ensureActiveTenant() ? renderQuickSale() : baseRenderSales.apply(this, arguments);
    };
  }

  window.ayecOpenQuickSale = async () => {
    activeTenantId = currentTenantId();
    active = true;
    cart = [];
    searchText = "";
    discount = 0;
    paymentMethod = "Nakit";
    bankAccountId = "";
    selectedCustomerId = "";
    if (page === "sales") render();
    else navigate("sales");
    await Promise.all([loadBanks(), loadCustomers()]);
    restoreDraftPrompt();
    requestAnimationFrame(() => document.querySelector("#quickSaleSearch")?.focus());
  };

  document.addEventListener("click", event => {
    if (!active) return;
    if (!ensureActiveTenant()) { render(); return; }
    const cartRow = event.target.closest("[data-qpos-row]");
    if (cartRow) {
      selectedCartIndex = Number(cartRow.dataset.qposRow);
      document.querySelectorAll("[data-qpos-row]").forEach(row => row.classList.toggle("is-selected", Number(row.dataset.qposRow) === selectedCartIndex));
    }
    if (event.target.closest("[data-qpos-customer-picker]")) {
      customerSelect(customer => {
        selectedCustomerId = String(customer.id);
        saveDraft();
        loadCustomers();
      }, "Hizli Satis - Musteri Secimi", result => {
        if (result !== "ok") loadCustomers();
      });
      return;
    }
    if (event.target.closest("[data-qpos-close]")) {
      active = false;
      render();
      return;
    }
    if (event.target.closest("#nav")) {
      active = false;
      return;
    }
    const add = event.target.closest("[data-qpos-add]");
    if (add) {
      addProduct(db.stock.find(item => String(item.id) === String(add.dataset.qposAdd)));
      return;
    }
    const remove = event.target.closest("[data-qpos-remove]");
    if (remove) {
      removeCartItem(Number(remove.dataset.qposRemove));
      return;
    }
    if (event.target.closest("[data-qpos-clear]")) {
      cart = [];
      discount = 0;
      selectedCustomerId = "";
      clearDraft();
      render();
      return;
    }
    if (event.target.closest("[data-qpos-checkout]")) confirmCheckout();
  }, true);

  document.addEventListener("input", event => {
    if (!active) return;
    if (!ensureActiveTenant()) { render(); return; }
    if (event.target.id === "quickSaleSearch") {
      searchText = event.target.value;
      const list = document.querySelector("#quickSaleProducts");
      if (list) list.innerHTML = renderProducts();
    }
    if (event.target.id === "quickSaleDiscount") {
      discount = Math.max(0, Number(event.target.value) || 0);
      saveDraft();
      updateTotals();
    }
  }, true);

  document.addEventListener("change", event => {
    if (!active) return;
    if (!ensureActiveTenant()) { render(); return; }
    if (event.target.id === "quickSalePayment") { paymentMethod = event.target.value; saveDraft(); }
    if (event.target.id === "quickSaleBank") { bankAccountId = event.target.value; saveDraft(); }
    if (event.target.id === "quickSaleCustomer") { selectedCustomerId = event.target.value; saveDraft(); }
    if (event.target.matches("[data-qpos-qty]")) {
      const line = cart[Number(event.target.dataset.qposQty)];
      const product = db.stock.find(item => line && String(item.id) === String(line.productId));
      if (line && product) {
        const quantity = Math.floor(Number(event.target.value) || 1);
        line.qty = Math.max(1, Math.min(quantity, Number(product.qty || 1)));
      }
      saveDraft();
      render();
    }
  }, true);

  document.addEventListener("keydown", event => {
    if (!active || event.target.id !== "quickSaleSearch" || event.key !== "Enter") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const query = searchText.trim().toLocaleLowerCase("tr-TR");
    const exact = db.stock.find(item => Number(item.qty || 0) > 0 &&
      [item.id, item.code, item.barcode].some(value =>
        String(value || "").toLocaleLowerCase("tr-TR") === query));
    const filtered = db.stock.filter(matches);
    const product = exact || (filtered.length === 1 ? filtered[0] : null);
    if (!product) return toast("Barkod veya \u00fcr\u00fcn i\u00e7in tek bir e\u015fle\u015fme bulunamad\u0131.", "warning");
    addProduct(product);
    searchText = "";
    render();
    requestAnimationFrame(() => document.querySelector("#quickSaleSearch")?.focus());
  }, true);

  document.addEventListener("keydown", event => {
    if (!active || document.querySelector("#appDialog")?.open) return;
    if (event.key === "F1" || event.key === "F2") {
      if (!cart.length) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      paymentMethod = event.key === "F1" ? "Nakit" : "Kredi Kart\u0131";
      const payment = document.querySelector("#quickSalePayment");
      if (payment) payment.value = paymentMethod;
      saveDraft();
      confirmCheckout();
      return;
    }
    if (event.key !== "Delete" || event.target?.closest?.("input,textarea,select,[contenteditable=true]")) return;
    const row = event.target?.closest?.("[data-qpos-row]");
    const index = row ? Number(row.dataset.qposRow) : selectedCartIndex;
    if (!Number.isInteger(index) || index < 0 || index >= cart.length) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    removeCartItem(index);
  }, true);
})();
