(function () {
  "use strict";

  var pageState = { page: 1, pages: 1, total: 0, search: "", type: "", dateFormat: "" };
  var pageRows = [];
  var searchTimer = 0;
  var baseRender = render;
  var baseContextAction = contextAction;

  function pageMarkup() {
    return pageHead(
      "Stok Hareketleri",
      "Giri\u015f, \u00e7\u0131k\u0131\u015f, sat\u0131\u015f ve servis kullan\u0131m kay\u0131tlar\u0131.",
      '<button class="primary" data-action="add-movement">\uff0b Hareket Ekle</button>'
    ) + stockTabs("movements") +
      '<section class="card"><div class="toolbar"><input class="control search" id="movementSearch" placeholder="\u00dcr\u00fcn veya referans ara" aria-label="Hareket ara">' +
      '<select class="control" id="movementType" aria-label="Hareket t\u00fcr\u00fc"><option value="">T\u00fcm\u00fc</option><option value="Giri\u015f">Giri\u015f</option><option value="\u00c7\u0131k\u0131\u015f">\u00c7\u0131k\u0131\u015f</option></select></div>' +
      '<div id="movementTable" aria-live="polite"></div><div class="pagination" id="movementPager"></div></section>';
  }

  function dateLabel(value) {
    var text = String(value || "");
    var parsed = new Date(text.includes("T") ? text : text.replace(" ", "T"));
    if (Number.isNaN(parsed.getTime())) return text;
    var format = pageState.dateFormat || String((window.desktopSettings || {}).date_format || "");
    var year = parsed.getFullYear();
    var month = String(parsed.getMonth() + 1).padStart(2, "0");
    var day = String(parsed.getDate()).padStart(2, "0");
    var date = format.includes("YYYY-AA-GG") ? year + "-" + month + "-" + day
      : format.includes("AA/GG/YYYY") ? month + "/" + day + "/" + year
      : format.includes("Uzun Tarih") || format.includes("Mart")
        ? parsed.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })
        : day + "." + month + "." + year;
    return date + " " + String(parsed.getHours()).padStart(2, "0") + ":" + String(parsed.getMinutes()).padStart(2, "0");
  }

  function currencySymbol(code) {
    return ({ USD: "$", EUR: "\u20ac" })[code] || "\u20ba";
  }

  function tableMarkup(rows) {
    if (!rows.length) return '<div class="empty-state">Kay\u0131t bulunamad\u0131.</div>';
    var body = rows.map(function (item) {
      var currency = String(item.currency || "TRY").toUpperCase();
      var cost = Number(item.unit_cost || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      return '<tr data-kind="movement" data-id="' + esc(item.id) + '">' +
        '<td>' + esc(item.id) + '</td><td>' + esc(item.part_name || "-") + '</td>' +
        '<td>' + esc(item.movement_type || "-") + '</td><td>' + esc(item.amount ?? 0) + '</td>' +
        '<td>' + esc(currency) + '</td><td>' + esc(cost + " " + currencySymbol(currency)) + '</td>' +
        '<td>' + esc(item.description || "") + '</td><td>' + esc(dateLabel(item.created_at)) + '</td></tr>';
    }).join("");
    return '<div class="table-wrap"><table><thead><tr><th>ID</th><th>Par\u00e7a</th><th>\u0130\u015flem</th><th>Miktar</th><th>PB</th><th>Birim Maliyet</th><th>A\u00e7\u0131klama</th><th>Tarih</th></tr></thead><tbody>' + body + '</tbody></table></div>';
  }

  function openMovementDetail(item) {
    var currency = String(item.currency || "TRY").toUpperCase();
    var cost = Number(item.unit_cost || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    var fields = [
      ["Hareket ID", item.id ?? "-"], ["Urun", item.part_name || "-"],
      ["Islem", item.movement_type || "-"], ["Miktar", item.amount ?? 0],
      ["Para Birimi", item.currency || "TRY"], ["Birim Maliyet", cost + " " + currencySymbol(currency)],
      ["Aciklama", item.description || "-"], ["Tarih", dateLabel(item.created_at) || "-"]
    ];
    var body = '<div class="movement-detail-grid">' + fields.map(function (field) {
      return '<div class="movement-detail-row"><strong>' + esc(field[0]) + '</strong><span>' + esc(field[1]) + '</span></div>';
    }).join("") + '</div>';
    openDialog("Stok Hareketi Detayi", "STOK HAREKETI DETAYI", body, function () { return true; }, "Kapat");
    var dialog = document.getElementById("appDialog");
    var cancel = document.getElementById("dialogCancel");
    dialog.classList.add("movement-history-detail");
    if (cancel) cancel.hidden = true;
    dialog.addEventListener("close", function () {
      dialog.classList.remove("movement-history-detail");
      if (cancel) cancel.hidden = false;
    }, { once: true });
  }

  function ensureDetailStyle() {
    if (document.getElementById("movementDetailStyle")) return;
    var style = document.createElement("style");
    style.id = "movementDetailStyle";
    style.textContent = "#appDialog.movement-history-detail{width:min(620px,calc(100vw - 32px));max-width:620px;height:min(430px,calc(100dvh - 32px));max-height:calc(100dvh - 32px)}.movement-history-detail #dialogBody{overflow:auto}.movement-detail-grid{display:grid;grid-template-columns:1fr;gap:0;padding:8px 18px}.movement-detail-row{display:grid;grid-template-columns:minmax(130px,170px) minmax(0,1fr);gap:14px;padding:10px 0;border-bottom:1px solid var(--line)}.movement-detail-row strong{color:var(--muted);font-weight:600}.movement-detail-row span{white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:520px){.movement-detail-grid{padding:4px 8px}.movement-detail-row{grid-template-columns:minmax(100px,125px) minmax(0,1fr);gap:8px}}";
    document.head.appendChild(style);
  }

  async function loadPage() {
    var host = document.getElementById("movementTable");
    if (!host || page !== "movements") return;
    host.innerHTML = '<div class="empty-state">Y\u00fckleniyor...</div>';
    var params = new URLSearchParams({ page: String(pageState.page), search: pageState.search, type: pageState.type });
    try {
      var data = await apiFetch("/api/desktop/stock/movements/history?" + params.toString());
      pageRows = Array.isArray(data.rows) ? data.rows : [];
      pageState.dateFormat = String(data.date_format || "");
      pageState.pages = Math.max(1, Number(data.pages) || 1);
      pageState.total = Number(data.total) || 0;
      pageState.page = Math.min(pageState.page, pageState.pages);
      host.innerHTML = tableMarkup(pageRows);
      ensureDetailStyle();
      host.querySelectorAll('tr[data-kind="movement"]').forEach(function (row, index) {
        row.addEventListener("dblclick", function () { openMovementDetail(pageRows[index]); });
      });
      var pager = document.getElementById("movementPager");
      if (pager) pager.innerHTML = '<span>' + (pageState.total ? ((pageState.page - 1) * 100 + 1) + " - " + Math.min(pageState.page * 100, pageState.total) : "0") + ' / ' + pageState.total + ' kay\u0131t</span>' +
        '<button type="button" class="secondary" id="movementPrev"' + (pageState.page <= 1 ? " disabled" : "") + '>\u00d6nceki</button>' +
        '<span>' + pageState.page + ' / ' + pageState.pages + '</span>' +
        '<button type="button" class="secondary" id="movementNext"' + (pageState.page >= pageState.pages ? " disabled" : "") + '>Sonraki</button>';
      document.getElementById("movementPrev")?.addEventListener("click", function () { pageState.page--; loadPage(); });
      document.getElementById("movementNext")?.addEventListener("click", function () { pageState.page++; loadPage(); });
    } catch (error) {
      host.innerHTML = '<div class="empty-state">Hareket ge\u00e7mi\u015fi y\u00fcklenemedi.</div>';
      toast(error.message || "Hareket ge\u00e7mi\u015fi y\u00fcklenemedi.", "error");
    }
  }

  function bindPage() {
    if (page !== "movements") return;
    var search = document.getElementById("movementSearch");
    var type = document.getElementById("movementType");
    if (search) {
      search.value = pageState.search;
      search.addEventListener("input", function () {
        pageState.search = search.value;
        pageState.page = 1;
        clearTimeout(searchTimer);
        searchTimer = setTimeout(loadPage, 220);
      });
    }
    if (type) {
      type.value = pageState.type;
      type.addEventListener("change", function () { pageState.type = type.value; pageState.page = 1; loadPage(); });
    }
    loadPage();
  }

  renderMovements = pageMarkup;
  render = function () {
    var result = baseRender.apply(this, arguments);
    bindPage();
    return result;
  };

  contextAction = function (kind, id, action, row) {
    if (kind === "movement" && action === "movement-print") {
      window.print();
      return;
    }
    if (kind === "movement" && action === "movement-pdf") {
      var pdfParams = new URLSearchParams({ page: String(pageState.page), search: pageState.search, type: pageState.type });
      fetch("/api/desktop/stock/movements/export/pdf?" + pdfParams.toString(), { credentials: "same-origin" })
        .then(async function (response) {
          if (!response.ok) {
            var body = {};
            try { body = await response.json(); } catch (_) {}
            if (response.status === 401 && window.handleUnauthorized) window.handleUnauthorized();
            throw new Error(body.error || "PDF export failed.");
          }
          return response.blob();
        })
        .then(function (blob) {
          var url = URL.createObjectURL(blob);
          var link = document.createElement("a");
          link.href = url;
          link.download = "stok_hareketleri_" + today().replace(/-/g, "") + ".pdf";
          link.click();
          URL.revokeObjectURL(url);
          toast("Stok hareketleri PDF olarak indirildi.", "success");
        })
        .catch(function (error) { toast(error.message, "error"); });
      return;
    }
    if (kind === "movement" && action === "movement-export") {
      var params = new URLSearchParams({ page: String(pageState.page), search: pageState.search, type: pageState.type });
      fetch("/api/desktop/stock/movements/export/xlsx?" + params.toString(), { credentials: "same-origin" })
        .then(async function (response) {
          if (!response.ok) {
            var body = {};
            try { body = await response.json(); } catch (_) {}
            if (response.status === 401 && window.handleUnauthorized) window.handleUnauthorized();
            throw new Error(body.error || "Excel aktar\u0131m\u0131 tamamlanamad\u0131.");
          }
          return response.blob();
        })
        .then(function (blob) {
          var url = URL.createObjectURL(blob);
          var link = document.createElement("a");
          link.href = url;
          link.download = "stok_hareketleri_" + today().replace(/-/g, "") + ".xlsx";
          link.click();
          URL.revokeObjectURL(url);
          toast("Stok hareketleri Excel olarak indirildi.", "success");
        })
        .catch(function (error) { toast(error.message, "error"); });
      return;
    }
    if (kind === "movement" && action === "movement-delete") {
      var originalRows = db.movements;
      var known = new Map((originalRows || []).map(function (item) { return [String(item.id), item]; }));
      pageRows.forEach(function (item) { known.set(String(item.id), item); });
      db.movements = Array.from(known.values());
      try { return baseContextAction(kind, id, action, row); }
      finally { db.movements = originalRows; }
    }
    return baseContextAction(kind, id, action, row);
  };

  document.addEventListener("contextmenu", function (event) {
    if (page !== "movements" || !ayecContextMenuEnabled("stock")) return;
    var row = event.target.closest('#movementTable tr[data-kind="movement"]');
    if (!row) return;
    event.preventDefault();
    var id = String(row.dataset.id || "");
    if (!id) return;
    var menu = document.getElementById("contextMenu");
    if (!menu) return;
    var items = [
      ["&#x1F4CA; Excel'e Aktar", "movement-export"],
      ["&#x1F4C4; PDF Olarak Kaydet", "movement-pdf"],
      ["&#x1F5A8;&#xFE0F; Yazd\u0131r", "movement-print"],
      ["", "separator"],
      ["&#x1F5D1;&#xFE0F; Bu Hareket Kayd\u0131n\u0131 Ge\u00e7mi\u015ften Sil", "movement-delete"]
    ];
    menu.innerHTML = items.map(function (item) {
      if (item[1] === "separator") return '<hr class="context-menu-separator">';
      return '<button type="button" role="menuitem" data-stock-movement-context="' + item[1] + '">' + item[0] + '</button>';
    }).join("");
    menu.setAttribute("role", "menu");
    menu.classList.add("open");
    menu.style.left = Math.max(8, Math.min(event.clientX, innerWidth - menu.offsetWidth - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(event.clientY, innerHeight - menu.offsetHeight - 8)) + "px";
    var closeMenu = function (outsideEvent) {
      if (outsideEvent && menu.contains(outsideEvent.target)) return;
      menu.classList.remove("open");
      document.removeEventListener("pointerdown", closeMenu, true);
      document.removeEventListener("keydown", closeOnEscape, true);
    };
    var closeOnEscape = function (keyEvent) {
      if (keyEvent.key !== "Escape") return;
      keyEvent.preventDefault();
      closeMenu();
    };
    menu.querySelectorAll("[data-stock-movement-context]").forEach(function (button) {
      button.onclick = function () {
        var action = button.dataset.stockMovementContext;
        closeMenu();
        contextAction("movement", id, action, row);
      };
    });
    setTimeout(function () {
      document.addEventListener("pointerdown", closeMenu, true);
      document.addEventListener("keydown", closeOnEscape, true);
    }, 0);
  }, true);
}());
