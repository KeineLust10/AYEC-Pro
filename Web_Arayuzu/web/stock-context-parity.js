(function() {
  const baseContextAction = contextAction;

  function openStockPhoto(item) {
    const name = String(item.name || item.code || "Stok");
    openDialog("Foto\u011fraf - " + name, "STOK KARTI", '<div class="stock-photo-preview"><img id="stockPhotoPreview" alt="' + esc(name) + '"><p id="stockPhotoMessage">Foto\u011fraf y\u00fckleniyor...</p></div>', () => true, "Kapat");
    const image = document.querySelector("#stockPhotoPreview");
    const message = document.querySelector("#stockPhotoMessage");
    image.onload = () => { message.hidden = true; };
    image.onerror = () => {
      image.hidden = true;
      message.textContent = "Bu stok kart\u0131 i\u00e7in eri\u015filebilir bir foto\u011fraf bulunamad\u0131.";
    };
    image.src = "/api/desktop/stock/photo/" + encodeURIComponent(item.id);
  }

  function printStockList() {
    const previousTitle = document.title;
    document.title = "stok_listesi_" + today();
    window.print();
    document.title = previousTitle;
  }

  async function exportStockPdf() {
    const response = await fetch("/api/desktop/stock/export/pdf", { credentials: "same-origin" });
    if (!response.ok) {
      let result = {};
      try { result = await response.json(); } catch (_) {}
      if (response.status === 401 && window.handleUnauthorized) window.handleUnauthorized();
      throw new Error(result.error || "PDF export failed.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "stok_listesi_" + today().replaceAll("-", "") + ".pdf";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  }

  async function exportStockExcel() {
    const response = await fetch("/api/desktop/stock/export/xlsx", { credentials: "same-origin" });
    if (!response.ok) {
      let result = {};
      try { result = await response.json(); } catch (_) {}
      if (response.status === 401 && window.handleUnauthorized) window.handleUnauthorized();
      throw new Error(result.error || "Excel aktar\u0131m\u0131 tamamlanamad\u0131.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "stok_listesi_" + today() + ".xlsx";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  }

  function confirmStockDelete(item) {
    openDialog("Stok Silme Onay\u0131", "STOK KARTI", '<p><strong>' + esc(item.name || item.code || "Stok") + '</strong> kayd\u0131n\u0131 silmek i\u00e7in giri\u015f parolan\u0131z\u0131 do\u011frulay\u0131n.</p><div class="field"><label for="stockDeletePassword">Giri\u015f Parolas\u0131</label><input id="stockDeletePassword" name="password" type="password" autocomplete="current-password" required></div>', async form => {
      const password = String(form.get("password") || "").trim();
      if (!password) throw new Error("Giri\u015f parolas\u0131n\u0131z\u0131 girin.");
      const response = await fetch("/api/desktop/stock/delete", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: item.id, password })
      });
      let result = {};
      try { result = await response.json(); } catch (_) {}
      if (!response.ok) {
        if (response.status === 401 && window.handleUnauthorized) window.handleUnauthorized();
        throw new Error(result.error || "Stok kart\u0131 silinemedi.");
      }
      db.stock = (db.stock || []).filter(row => String(row.id) !== String(item.id));
      save();
      render();
      toast("Stok kart\u0131 silindi.", "success");
      return true;
    }, "Stoku Sil");
  }

  contextAction = function(kind, id, action, row) {
    if (kind === "stock" && action === "stock-photo") {
      const item = (db.stock || []).find(value => String(value.id) === String(id)) ||
        (window.currentGenericData?.rows || []).find(value => String(value.id) === String(id));
      if (item) openStockPhoto(item);
      else toast("Stok kart\u0131 bulunamad\u0131.", "error");
      return;
    }
    if (kind === "stock" && action === "delete-product") {
      const item = (db.stock || []).find(value => String(value.id) === String(id));
      if (item) confirmStockDelete(item);
      else toast("Stok kart\u0131 bulunamad\u0131.", "error");
      return;
    }
    if (kind === "stock" && action === "stock-pdf") {
      exportStockPdf().then(() => toast("Stok listesi PDF olarak indirildi.", "success"))
        .catch(error => toast(error.message, "error"));
      return;
    }
    if (kind === "stock" && action === "stock-print") {
      printStockList();
      return;
    }
    if (kind === "stock" && action === "stock-excel") {
      exportStockExcel().then(() => toast("Stok listesi Excel olarak indirildi.", "success"))
        .catch(error => toast(error.message, "error"));
      return;
    }
    return baseContextAction(kind, id, action, row);
  };

  const baseShowContext = showContext;
  showContext = function(event, kind, id) {
    if (kind !== "stock") return baseShowContext(event, kind, id);
    if (!ayecContextMenuEnabled()) return;
    event.preventDefault();
    const menu = document.querySelector("#contextMenu");
    const items = [
      ["\uD83D\uDCE6 Stok Ekle/\u00c7\u0131kar", "movement"],
      ["\u270F\uFE0F D\u00fczenle", "edit-product"],
      ["\uD83D\uDCF7 Foto\u011fraf\u0131 G\u00f6r\u00fcnt\u00fcle", "stock-photo"],
      ["", "maintenance-separator"],
      ["\uD83D\uDCC4 PDF Olarak Kaydet", "stock-pdf"],
      ["\uD83D\uDDA8\uFE0F Yazd\u0131r", "stock-print"],
      ["\uD83D\uDCCA Excel'e Aktar", "stock-excel"],
      ["", "maintenance-separator"],
      ["\uD83D\uDDD1\uFE0F Sil", "delete-product"]
    ];
    menu.innerHTML = items.map(([label, action]) => action === "maintenance-separator"
      ? '<hr class="context-menu-separator">'
      : '<button type="button" role="menuitem" data-context-action="' + action + '">' + label + "</button>").join("");
    menu.classList.add("open");
    menu.style.left = Math.max(8, Math.min(event.clientX, innerWidth - menu.offsetWidth - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(event.clientY, innerHeight - menu.offsetHeight - 8)) + "px";
    menu.querySelectorAll("[data-context-action]").forEach(button => {
      button.onclick = () => {
        menu.classList.remove("open");
        contextAction(kind, id, button.dataset.contextAction);
      };
    });
  };
})();
