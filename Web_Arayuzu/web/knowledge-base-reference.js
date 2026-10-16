(function () {
  "use strict";

  var shellBeforeKnowledge = genericShell;
  var loadBeforeKnowledge = loadGenericModule;
  var selectedArticleId = null;

  genericShell = function (meta) {
    if (page !== "knowledge" || meta.table !== "kb_articles") return shellBeforeKnowledge(meta);
    var automotiveResources = currentSector === "otomotiv" ? '<section class="card kb-resource-card"><header><div><h2>Otomotiv \u0130\u00e7in \u00d6nerilen D\u0131\u015f Kaynak</h2><p>Otomotiv se\u00e7iliyken bilgi bankas\u0131 i\u00e7inde kullanabilece\u011finiz sabit referans kaynaklar\u0131.</p></div></header><div class="kb-resource-grid"><article><div><strong>CarCareKiosk</strong><p>Araca ozel bakim, parca ve kullanim videolari.</p></div><a href="https://www.carcarekiosk.com/" target="_blank" rel="noopener noreferrer">Ac</a></article><article><div><strong>NHTSA Recall Lookup</strong><p>Geri \u00e7a\u011f\u0131rma ve g\u00fcvenlik kontrolleri i\u00e7in resmi kaynak.</p></div><a href="https://www.nhtsa.gov/recalls" target="_blank" rel="noopener noreferrer">Ac</a></article><article><div><strong>AutoZone Repair Help</strong><p>Onar\u0131m rehberleri, ar\u0131za \u00e7\u00f6z\u00fcmleri ve bak\u0131m i\u00e7erikleri.</p></div><a href="https://www.autozone.com/lp/repair-help/" target="_blank" rel="noopener noreferrer">Ac</a></article></div></section>' : "";
    return pageHead("TEKN\u0130K B\u0130LG\u0130 BANKASI", "KURUMSAL \u00c7\u00d6Z\u00dcM REHBER\u0130 VE PROTOKOLLER", '<button class="danger" type="button" data-kb-delete disabled>Sil</button><button class="primary" type="button" data-kb-add>Yeni \u00c7\u00f6z\u00fcm Ekle</button>')
      + '<div class="kb-search"><input class="control search" id="genericSearch" placeholder="Ar\u0131za, Model veya Anahtar Kelime Ara..." aria-label="Bilgi bankas\u0131nda ara"><button type="button" class="secondary" data-generic-refresh>Yenile</button></div>'
      + automotiveResources
      + '<section class="knowledge-base-layout"><aside class="card kb-article-list"><header><h2>Makaleler</h2><span class="badge" id="kbArticleCount">0</span></header><div id="genericHost"></div></aside><article class="card kb-article-detail" id="kbArticleDetail"></article></section>';
  };

  function renderArticles(meta, data) {
    var rows = data.rows || [];
    var selected = rows.find(function (row) { return String(row.id) === String(selectedArticleId); }) || rows[0] || null;
    selectedArticleId = selected ? String(selected.id) : null;
    var host = document.querySelector("#genericHost");
    var detail = document.querySelector("#kbArticleDetail");
    var count = document.querySelector("#kbArticleCount");
    if (!host || !detail || !count) return;
    count.textContent = String(data.count || rows.length);
    host.innerHTML = rows.length ? '<ul class="kb-article-items">' + rows.map(function (row) {
      return '<li><button type="button" class="kb-article-item ' + (selected && String(selected.id) === String(row.id) ? "active" : "") + '" data-kb-article="' + esc(row.id) + '"><strong>' + esc(row.title || "") + '</strong><small>' + esc(row.tags || "") + '</small></button></li>';
    }).join("") + '</ul>' : '<div class="kb-empty-state"><span aria-hidden="true">&#128218;</span><h2>Hen\u00fcz makale yok</h2><p>Bilgi bankas\u0131na teknik \u00e7\u00f6z\u00fcmler ekleyerek ba\u015flay\u0131n.</p><button type="button" class="primary" data-kb-empty-add>Yeni Makale Ekle</button></div>';
    detail.innerHTML = selected ? '<header><div><h2>' + esc(selected.title || "") + '</h2><small>' + esc(selected.tags || "") + '</small></div><div class="kb-detail-actions"><button type="button" class="secondary" data-kb-copy>\u0130\u00e7eri\u011fi Kopyala</button><button type="button" class="danger" data-kb-delete>Sil</button></div></header><div class="kb-article-content">' + esc(selected.content || "") + '</div>' : '<div class="kb-empty-detail"><h2>Makale se\u00e7in</h2><p>Detaylar\u0131n\u0131 g\u00f6rmek i\u00e7in listeden bir makale se\u00e7in.</p></div>';
    host.querySelectorAll("[data-kb-article]").forEach(function (button) {
      button.onclick = function () { selectedArticleId = button.dataset.kbArticle; renderArticles(meta, data); };
      button.oncontextmenu = function (event) {
        event.preventDefault();
        var targetArticle = rows.find(function (row) { return String(row.id) === String(button.dataset.kbArticle); });
        if (!targetArticle) return;
        selectedArticleId = String(targetArticle.id);
        renderArticles(meta, data);
        var menu = document.createElement("div");
        menu.className = "kb-context-menu";
        menu.style.left = Math.max(8, Math.min(event.clientX, window.innerWidth - 190)) + "px";
        menu.style.top = Math.max(8, Math.min(event.clientY, window.innerHeight - 100)) + "px";
        menu.innerHTML = '<button type="button" data-kb-menu-delete>\u274c Sil</button><button type="button" data-kb-menu-copy>\uD83D\uDCCB \u0130\u00e7eri\u011fi Kopyala</button>';
        document.body.append(menu);
        var closeMenu = function (outsideEvent) { if (!menu.contains(outsideEvent.target)) { menu.remove(); document.removeEventListener("pointerdown", closeMenu); } };
        menu.querySelector("[data-kb-menu-copy]").onclick = function () { copyArticle(targetArticle); menu.remove(); document.removeEventListener("pointerdown", closeMenu); };
        menu.querySelector("[data-kb-menu-delete]").onclick = function () { deleteArticle(meta, targetArticle); menu.remove(); document.removeEventListener("pointerdown", closeMenu); };
        setTimeout(function () { document.addEventListener("pointerdown", closeMenu); }, 0);
      };
    });
    document.querySelectorAll("[data-kb-delete]").forEach(function (deleteButton) {
      deleteButton.disabled = !selected;
      deleteButton.onclick = function () { if (selected) deleteArticle(meta, selected); };
    });
    var copyButton = document.querySelector("[data-kb-copy]");
    if (copyButton) copyButton.onclick = function () { copyArticle(selected); };
    var emptyAdd = document.querySelector("[data-kb-empty-add]");
    if (emptyAdd) emptyAdd.onclick = openArticleDialog.bind(null, meta);
  }

  async function copyArticle(article) {
    if (!article) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(String(article.content || ""));
      else {
        var field = document.createElement("textarea");
        field.value = String(article.content || "");
        field.style.position = "fixed"; field.style.opacity = "0";
        document.body.append(field); field.select();
        try { if (!document.execCommand("copy")) throw new Error("Clipboard access is unavailable"); }
        finally { field.remove(); }
      }
      toast("Makale i\u00e7eri\u011fi panoya kopyaland\u0131.", "success");
    } catch (error) { toast("\u0130\u00e7erik kopyalanamad\u0131: " + error.message, "error"); }
  }

  function deleteArticle(meta, article) {
    if (!article) return;
    openDialog("Onay", "BILGI BANKASI", "<p>Bu makaleyi silmek istedi\u011finize emin misiniz</p>", async function () {
      await apiFetch("/api/desktop/table/kb_articles", {method:"POST", body:JSON.stringify({id:article.id,_action:"delete"})});
      selectedArticleId = null;
      toast("Bilgi bankas\u0131 makalesi silindi.", "success");
      await loadGenericModule(meta, document.querySelector("#genericSearch")?.value || "");
      return true;
    }, "Evet");
    var dialog = document.getElementById("appDialog");
    var cancel = document.getElementById("dialogCancel");
    var submit = document.getElementById("dialogSubmit");
    dialog.classList.add("kb-confirm-dialog");
    if (cancel) cancel.textContent = "Hay\u0131r";
    if (submit) { submit.classList.remove("primary"); submit.classList.add("danger"); }
    dialog.addEventListener("close", function () { dialog.classList.remove("kb-confirm-dialog"); }, { once: true });
  }

  function openArticleDialog(meta) {
    var form = '<div class="kb-editor"><div class="field"><label for="kbArticleTitle">Ba\u015fl\u0131k *</label><input id="kbArticleTitle" name="title" required placeholder="Makale ba\u015fl\u0131\u011f\u0131n\u0131 giriniz..."></div><div class="field"><label for="kbArticleTags">Etiketler</label><input id="kbArticleTags" name="tags" placeholder="anahtar, kelimeler, virg\u00fclle, ay\u0131r\u0131n"></div><div class="field"><label for="kbArticleContent">\u00c7\u00f6z\u00fcm/\u0130\u00e7erik *</label><textarea id="kbArticleContent" name="content" required rows="12"></textarea></div></div>';
    openDialog("Yeni Bilgi Bankas\u0131 Makalesi", "BILGI BANKASI", form, async function (formData) {
      var article = Object.fromEntries(formData);
      article.title = String(article.title || "").trim();
      article.content = String(article.content || "").trim();
      article.tags = String(article.tags || "").trim();
      if (!article.title || !article.content) { toast("Ba\u015fl\u0131k ve i\u00e7erik zorunludur.", "error"); return false; }
      await apiFetch("/api/desktop/table/kb_articles", {method:"POST", body:JSON.stringify(article)});
      selectedArticleId = null;
      toast("Bilgi bankas\u0131 makalesi eklendi.", "success");
      await loadGenericModule(meta, document.querySelector("#genericSearch")?.value || "");
      return true;
    }, "Kaydet");
  }

  loadGenericModule = async function (meta, query) {
    if (page !== "knowledge" || meta.table !== "kb_articles") return loadBeforeKnowledge(meta, query);
    var effectiveQuery = String(query || "").trim().length > 2 ? query : "";
    await loadBeforeKnowledge(meta, effectiveQuery);
    renderArticles(meta, window.currentGenericData || {rows:[], count:0});
    var addButton = document.querySelector("[data-kb-add]");
    if (addButton) addButton.onclick = openArticleDialog.bind(null, meta);
  };

  var tableBeforeKnowledge = genericTable;
  genericTable = function (meta, data) {
    if (page === "knowledge" && meta.table === "kb_articles") return '<div class="kb-placeholder" aria-hidden="true"></div>';
    return tableBeforeKnowledge(meta, data);
  };
}());
