(() => {
  const previousLoad = window.loadGenericModule;
  const previousShowContext = window.showContext;
  window.loadGenericModule = async function(meta, query = "") {
    const result = await previousLoad.call(this, meta, query);
    if (meta?.table !== "personnel" || document.body.dataset.page !== "personnel") return result;
    document.querySelectorAll("#personnelRows [data-personnel-id]").forEach(row => {
      if (row.dataset.personnelContextBound) return;
      row.dataset.personnelContextBound = "1";
      row.addEventListener("contextmenu", event => window.showContext(event, "personnel", row.dataset.personnelId));
    });
    return result;
  };
  window.showContext = function(event, kind, id) {
    if (kind !== "personnel") return previousShowContext.call(this, event, kind, id);
    if (!window.ayecContextMenuEnabled()) return;
    event.preventDefault();
    const menu = document.querySelector("#contextMenu");
    const items = [["&#x1F4DD; D\u00fczenle", "edit"], ["&#x1F5D1;&#xFE0F; Personel \u00c7\u0131kar", "remove"]];
    menu.innerHTML = items.map(([label, action]) => `${action === "remove" ? '<hr class="context-menu-separator" role="separator">' : ""}<button data-personnel-context="${action}">${label}</button>`).join("");
    menu.style.left = `${Math.max(8, Math.min(event.clientX, innerWidth - 210))}px`;
    menu.style.top = `${Math.max(8, Math.min(event.clientY, innerHeight - items.length * 40 - 20))}px`;
    menu.classList.add("open");
    menu.querySelectorAll("[data-personnel-context]").forEach(button => {
      button.onclick = () => {
        menu.classList.remove("open");
        const row = (window.currentGenericData?.rows || []).find(item => String(item.id) === String(id));
        if (!row) return;
        if (button.dataset.personnelContext === "edit") {
          window.openGenericDialog(window.currentGenericMeta, row, window.currentGenericData.columns);
          return;
        }
        openDialog("Onay", "PERSONEL \u00c7IKAR", `<p>${esc(row.name || "-")} kayd\u0131n\u0131 silmek i\u00e7in yönetici parolas\u0131n\u0131 girin.</p><label class="field">Yönetici Parolas\u0131<input name="admin_password" type="password" autocomplete="current-password" required></label>`, async form => {
          try {
            await apiFetch("/api/desktop/personnel/delete", {method: "POST", body: JSON.stringify({id, admin_password: form.get("admin_password")})});
            toast("Personel silindi.");
            await window.loadGenericModule(window.currentGenericMeta, document.querySelector("#genericSearch")?.value || "");
            return true;
          } catch (error) {
            toast(error.message || "Personel silinemedi.", "error");
            return false;
          }
        }, "Personeli \u00c7\u0131kar");
      };
    });
  };
})();
