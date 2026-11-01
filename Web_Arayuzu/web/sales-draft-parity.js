(() => {
  let suppressSave = false;
  let restoring = false;
  const tenantId = () => String(typeof currentAuthUser !== "undefined" ? currentAuthUser?.tenant_id || "" : "").trim();
  let activeTenantId = tenantId();
  const resetSalesState = () => {
    salesCart = [];
    salesCustomer = "";
    salesCurrency = "TRY";
    salesManualRates = {};
    salesDiscountPercent = 5;
    salesDraft = { template: "modern", project: "", vat: 0, discountPercent: 5, date: today(), includeApproval: true };
  };
  const ensureTenantContext = () => {
    const nextTenantId = tenantId();
    if (nextTenantId === activeTenantId) return false;
    activeTenantId = nextTenantId;
    resetSalesState();
    document.querySelector("#appDialog")?.close("tenant-changed");
    return true;
  };
  const draftKey = () => {
    const id = tenantId();
    return id ? "ayec.sales_draft.v1." + encodeURIComponent(id) : "";
  };
  const removeDraft = key => {
    if (!key) return;
    try { localStorage.removeItem(key); } catch (_) {}
  };
  const readDraft = () => {
    const key = draftKey();
    if (!key) return null;
    try {
      const value = JSON.parse(localStorage.getItem(key) || "null");
      return value?.version === 1 && String(value.tenant_id || "") === String(currentAuthUser?.tenant_id || "") && Array.isArray(value.cart_items) && value.cart_items.length ? value : null;
    } catch (_) {
      return null;
    }
  };
  const saveDraft = () => {
    if (ensureTenantContext()) return;
    const key = draftKey();
    if (!key || suppressSave || restoring || page !== "sales") return;
    if (!Array.isArray(salesCart) || !salesCart.length) {
      removeDraft(key);
      return;
    }
    const draft = {
      version: 1,
      tenant_id: String(currentAuthUser?.tenant_id || ""),
      customer_id: String(salesCustomer || ""),
      cart_items: salesCart,
      currency: salesCurrency,
      manual_rates: salesManualRates,
      discount_percent: salesDiscountPercent,
      settings: salesDraft,
    };
    try { localStorage.setItem(key, JSON.stringify(draft)); } catch (_) {}
  };
  const restoreDraft = draft => {
    const key = draftKey();
    const validLines = draft.cart_items.filter(line => {
      const qty = Number(line?.qty);
      if (!Number.isFinite(qty) || qty <= 0) return false;
      if (line?.type === "service") return String(line.name || "").trim().length > 0;
      return db.stock.some(product => String(product.id) === String(line?.productId));
    });
    if (!validLines.length) {
      removeDraft(key);
      return;
    }
    const removedCount = draft.cart_items.length - validLines.length;
    openDialog("Kaydedilmemis Satis Taslagi", "SATIS HUB", `<p>Onceki oturumdan ${validLines.length} kalemlik tamamlanmamis bir satis bulundu. Geri yuklensin mi?${removedCount ? ` ${removedCount} gecersiz kalem atlandi.` : ""}</p>`, () => {
      restoring = true;
      salesCart = validLines;
      salesCustomer = db.customers.some(customer => String(customer.id) === String(draft.customer_id || "")) ? String(draft.customer_id) : "";
      salesCurrency = ["TRY", "USD", "EUR"].includes(String(draft.currency || "")) ? draft.currency : "TRY";
      salesManualRates = Object.fromEntries(Object.entries(draft.manual_rates || {}).filter(([code, value]) => ["TRY", "USD", "EUR"].includes(code) && Number(value) > 0));
      salesDiscountPercent = Math.max(0, Math.min(100, Number(draft.discount_percent) || 0));
      const settings = draft.settings && typeof draft.settings === "object" ? draft.settings : {};
      salesDraft = {
        template: ["modern", "corporate", "minimal"].includes(settings.template) ? settings.template : "modern",
        project: String(settings.project || "").slice(0, 240),
        vat: Math.max(0, Math.min(100, Number(settings.vat) || 0)),
        discountPercent: salesDiscountPercent,
        date: /^\d{4}-\d{2}-\d{2}$/.test(String(settings.date || "")) ? settings.date : today(),
        includeApproval: settings.includeApproval !== false,
      };
      render();
      restoring = false;
      saveDraft();
      return true;
    }, "Geri Yukle");
    const dialog = document.querySelector("#appDialog");
    const cancel = document.querySelector("#dialogCancel");
    if (cancel) cancel.textContent = "Taslagi Sil";
    dialog?.addEventListener("close", () => {
      if (dialog.returnValue !== "ok" && dialog.returnValue !== "tenant-changed") removeDraft(key);
    }, { once: true });
  };
  const showRestorePrompt = () => {
    if (page !== "sales" || salesCart.length) return;
    const draft = readDraft();
    if (draft) restoreDraft(draft);
    else saveDraft();
  };
  const baseRender = render;
  render = function () {
    ensureTenantContext();
    const result = baseRender.apply(this, arguments);
    if (!suppressSave && page === "sales") setTimeout(saveDraft, 0);
    return result;
  };
  const baseNavigate = navigate;
  navigate = function (next) {
    ensureTenantContext();
    if (page === "sales" && next !== "sales") saveDraft();
    suppressSave = true;
    try { return baseNavigate.apply(this, arguments); }
    finally {
      suppressSave = false;
      if (next === "sales") showRestorePrompt();
    }
  };
  const scheduleSave = event => {
    if (page !== "sales" || restoring || suppressSave) return;
    const target = event.target;
    if (!(target instanceof Element) || (!target.closest("#content") && !target.closest("#appDialog"))) return;
    setTimeout(saveDraft, 0);
  };
  document.addEventListener("click", scheduleSave);
  document.addEventListener("change", scheduleSave);
  document.addEventListener("input", scheduleSave);
  window.addEventListener("beforeunload", saveDraft);
})();
