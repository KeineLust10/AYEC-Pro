/* Desktop external service and warranty tracking workflow. */
(() => {
  const statuses = ["Haz\u0131rlan\u0131yor", "Kargoya Verildi", "Servise Ula\u015Ft\u0131", "Onar\u0131mda", "\u0130ade Bekleniyor", "Geri Geldi", "M\u00FC\u015Fteriye Teslim Edildi"];
  let rows = [];
  let pageIndex = 0;
  let selectedIds = new Set();
  let multiselect = false;
  let view = "external";
  const table = "external_warranty_tracking";
  const safe = value => esc(value == null ? "" : String(value));
  const normalizeStatus = value => String(value || "").toLocaleLowerCase("tr-TR").replace(/\u0131/g, "i").normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
  const url = "/api/desktop/table/" + table;
  const monthOf = value => {
    const text = String(value || "");
    const iso = text.match(/^(\d{4})-(\d{2})/);
    if (iso) return iso[1] + "-" + iso[2];
    const local = text.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})/);
    return local ? local[3] + "-" + local[2].padStart(2, "0") : "";
  };
  const filtered = () => {
    const query = String($("#externalTrackingSearch")?.value || "").trim().toLocaleLowerCase("tr-TR");
    const status = $("#externalTrackingStatus")?.value || "";
    const service = $("#externalTrackingService")?.value || "";
    const month = $("#externalTrackingMonth")?.value || "";
    return rows.filter(row => {
      const haystack = [row.internal_tracking_no, row.customer_name, row.product_name, row.external_service_name, row.external_service_no, row.outbound_cargo_no, row.inbound_cargo_no, row.status].join(" ").toLocaleLowerCase("tr-TR");
      return (!query || haystack.includes(query)) && (!status || String(row.status || "") === status) && (!service || String(row.external_service_name || "") === service) && (!month || monthOf(row.sent_date) === month);
    });
  };
  const refresh = async () => {
    try {
      const data = await apiFetch(url + "?limit=500");
      rows = data.rows || [];
      const serviceSelect = $("#externalTrackingService");
      if (serviceSelect) {
        const selected = serviceSelect.value;
        const services = [...new Set(rows.map(row => row.external_service_name).filter(Boolean))].sort();
        serviceSelect.innerHTML = '<option value="">Yetkili Servis: T\u00fcm\u00fc</option>' + services.map(name => '<option>' + safe(name) + '</option>').join("");
        serviceSelect.value = services.includes(selected) ? selected : "";
      }
      const monthSelect = $("#externalTrackingMonth");
      if (monthSelect) {
        const selected = monthSelect.value;
        const months = [...new Set(rows.map(row => monthOf(row.sent_date)).filter(Boolean))].sort().reverse();
        monthSelect.innerHTML = '<option value="">T\u00FCm Aylar</option>' + months.map(month => '<option value="' + safe(month) + '">' + safe(month) + '</option>').join("");
        monthSelect.value = months.includes(selected) ? selected : "";
      }
      renderRows();
    } catch (error) {
      const host = $("#externalTrackingHost");
      if (host) host.innerHTML = empty("Kay\u0131tlar y\u00FCklenemedi", safe(error.message));
    }
  };
  const renderRows = () => {
    const host = $("#externalTrackingHost");
    if (!host) return;
    const matches = filtered();
    const pageSize = 4;
    const pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
    pageIndex = Math.min(pageIndex, pageCount - 1);
    const shown = matches.slice(pageIndex * pageSize, (pageIndex + 1) * pageSize);
    const columns = [
      "Takip No /<br>Servis No", "M\u00FC\u015Fteri & \u00DCr\u00FCn", "D\u0131\u015F Servis / Yer",
      "G\u00F6nderim<br>Tarihi", "Kargo Takip", "Garanti<br>Kapsam\u0131", "Maliyet /<br>Tutar", "Durum", "\u0130\u015Flemler"
    ];
    const dateLabel = value => {
      const text = String(value || "");
      if (!text) return "-";
      const date = new Date(text.slice(0, 10) + "T00:00:00");
      return Number.isNaN(date.getTime()) ? text : new Intl.DateTimeFormat("tr-TR").format(date);
    };
    const statusCell = value => {
      const status = String(value || "-");
      const tones = {
        "onarimda": "warn",
        "iade bekleniyor": "info",
        "onay bekliyor": "info",
        "dis serviste": "danger",
        "hazir": "success",
        "geri geldi": "success",
        "teslim alindi": "success",
        "musteriye hazir": "success",
        "kargoya verildi": "danger",
        "servise ulasti": "info",
        "musteriye teslim edildi": "success",
        "hazirlaniyor": "neutral"
      };
      const tone = tones[normalizeStatus(status)] || "";
      return '<span class="badge ' + tone + '">' + safe(status) + '</span>';
    };
    const rowCells = row => [
      '<strong>' + safe(row.internal_tracking_no || "-") + '</strong><small>Servis: ' + safe(row.external_service_no || "-") + '</small>',
      '<span class="external-tracking-primary">' + safe(row.customer_name || "-") + '</span><small>' + safe(row.product_name || "-") + '</small>',
      '<span class="external-tracking-primary">' + safe(row.external_service_name || "-") + '</span><small>No: ' + safe(row.external_service_no || "-") + '</small>',
      safe(dateLabel(row.sent_date)),
      '<small>Gidi\u015f: ' + safe(row.outbound_cargo_no || "-") + '</small><small>D\u00f6n\u00fc\u015f: ' + safe(row.inbound_cargo_no || "-") + '</small>',
      safe(row.warranty_coverage || "-"),
      safe(row.repair_cost == null ? "-" : row.repair_cost),
      statusCell(row.status),
      '<button type="button" class="mini" data-external-edit="' + safe(row.id) + '">D\u00FCzenle</button> <button type="button" class="mini" data-external-delete="' + safe(row.id) + '">Sil</button>'
    ];
    host.innerHTML = shown.length ? '<div class="table-wrap"><table><thead><tr>' + (multiselect ? '<th>SE\u00c7</th>' : "") + columns.map(label => '<th>' + label + '</th>').join("") + '</tr></thead><tbody>' + shown.map(row => '<tr tabindex="0" data-external-row="' + safe(row.id) + '" class="' + (selectedIds.has(String(row.id)) ? "selected" : "") + '">' + (multiselect ? '<td><input type="checkbox" aria-label="Kayd\u0131 se\u00e7" data-external-select="' + safe(row.id) + '" ' + (selectedIds.has(String(row.id)) ? "checked" : "") + '></td>' : "") + rowCells(row).map(cell => '<td>' + cell + '</td>').join("") + '</tr>').join("") + '</tbody></table></div>' : empty("Harici servis kayd\u0131 bulunamad\u0131", "Arama ve filtreleri de\u011Fi\u015Ftirin veya yeni bir takip kayd\u0131 ekleyin.");
    const pager = $("#externalTrackingPagination");
    if (pager) pager.innerHTML = '<span>G\u00F6sterilen ' + shown.length + " / " + matches.length + ' kay\u0131t</span><div><button type="button" data-external-page="-1" aria-label="\u00D6nceki sayfa" ' + (pageIndex === 0 ? "disabled" : "") + '>\u00D6nceki</button><b>' + (pageIndex + 1) + " / " + pageCount + '</b><button type="button" data-external-page="1" aria-label="Sonraki sayfa" ' + (pageIndex >= pageCount - 1 ? "disabled" : "") + '>Sonraki</button></div>';
    const total = rows.length;
    const normalizedStatuses = rows.map(row => normalizeStatus(row.status));
    const countStatuses = values => normalizedStatuses.filter(status => values.has(status)).length;
    const active = countStatuses(new Set(["kargoya verildi", "servise ulasti", "onarimda", "dis serviste"]));
    const pending = countStatuses(new Set(["onay bekliyor", "iade bekliyor"]));
    const received = countStatuses(new Set(["geri geldi", "teslim alindi", "musteriye hazir"]));
    [["externalTrackingTotal", total], ["externalTrackingActive", active], ["externalTrackingPending", pending], ["externalTrackingReceived", received]].forEach(([id, count]) => { const node = $("#" + id); if (node) node.textContent = String(count); });
    const footerSummaries = [["externalTrackingTotal", total, "Kay\u0131t"], ["externalTrackingActive", active, "A\u00e7\u0131k \u0130rsaliye"], ["externalTrackingPending", pending, "Bekleyen Kay\u0131t"], ["externalTrackingReceived", received, "Teslim Al\u0131nd\u0131"]];
    footerSummaries.forEach(([id, count, suffix]) => {
      const card = $("#" + id)?.closest("article");
      const footer = card?.querySelector("footer");
      if (!footer) return;
      let label = footer.querySelector("span");
      if (!label) { label = document.createElement("span"); label.textContent = footer.textContent; footer.replaceChildren(label); }
      let detail = footer.querySelector("b");
      if (!detail) { detail = document.createElement("b"); footer.append(detail); }
      detail.textContent = count + " " + suffix;
    });
  };
  const formBody = row => '<div class="external-tracking-form"><label>M\u00FC\u015Fteri Emanet No<input name="internal_tracking_no" required value="' + safe(row.internal_tracking_no) + '" placeholder="\u00D6rn: M.NO 1025 / Cihaz Takip No"></label><label>M\u00FC\u015Fteri Bilgisi<input name="customer_name" value="' + safe(row.customer_name) + '" placeholder="M\u00FC\u015Fteri se\u00E7in veya yaz\u0131n"></label><label>\u00DCr\u00FCn / Par\u00E7a<input name="product_name" value="' + safe(row.product_name) + '" placeholder="Marka / Model / Par\u00E7a Ad\u0131"></label><label>G\u00F6nderilen Yer<input name="external_service_name" value="' + safe(row.external_service_name) + '" placeholder="Asus Servis, Penta, vb."></label><label>Servis Kay\u0131t No<input name="external_service_no" value="' + safe(row.external_service_no) + '" placeholder="Kar\u015F\u0131 taraf\u0131n verdi\u011Fi servis no"></label><label>G\u00F6nderim Tarihi<input name="sent_date" type="date" value="' + safe(String(row.sent_date || new Date().toISOString().slice(0, 10)).slice(0, 10)) + '"></label><label>G\u00FCncel Durum<select name="status">' + statuses.map(status => '<option' + (String(row.status || statuses[0]) === status ? " selected" : "") + '>' + status + '</option>').join("") + '</select></label><fieldset><legend>Kargo Bilgileri</legend><label>Gidi\u015F Kargo No<input name="outbound_cargo_no" value="' + safe(row.outbound_cargo_no) + '"></label><label>D\u00F6n\u00FC\u015F Kargo No<input name="inbound_cargo_no" value="' + safe(row.inbound_cargo_no) + '"></label></fieldset><label class="external-tracking-notes">Notlar<textarea name="notes" rows="3">' + safe(row.notes) + '</textarea></label><div class="external-tracking-photo-note">Foto\u011Fraf galerisi masa\u00FCst\u00FC dosya yollar\u0131na ba\u011Fl\u0131 oldu\u011Fundan taray\u0131c\u0131ya aktar\u0131lam\u0131yor.</div></div>';
  const galleryFormBody = row => formBody(row).replace(/<div class="external-tracking-photo-note">[\s\S]*?<\/div>/, '<section class="external-tracking-gallery"><div><strong>Foto\u011Fraf Galerisi</strong><button type="button" class="secondary" data-external-photo-pick>Foto\u011Fraf Ekle</button><input type="file" accept=".jpg,.jpeg,.png,.bmp,image/jpeg,image/png,image/bmp" multiple data-external-photo-input hidden></div><p data-external-photo-status>Kayda ba\u011Fl\u0131 foto\u011Fraflar</p><div data-external-photo-list></div></section>');
  const galleryUpload = async file => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Foto\u011Fraf okunamad\u0131"));
    reader.onload = async () => {
      try {
        const data = String(reader.result || "").split(",")[1] || "";
        await apiFetch("/api/desktop/external-tracking/photos", { method: "POST", body: JSON.stringify({ tracking_no: $("#dialogBody [name=internal_tracking_no]")?.value || "", label: file.name, data }) });
        resolve();
      } catch (error) { reject(error); }
    };
    reader.readAsDataURL(file);
  });
  const loadGallery = async trackingNo => {
    const host = $("#dialogBody [data-external-photo-list]");
    const status = $("#dialogBody [data-external-photo-status]");
    if (!host || !status) return;
    if (!trackingNo.trim()) { host.innerHTML = ""; status.textContent = "Foto\u011Fraf eklemek i\u00E7in emanet numaras\u0131n\u0131 girin."; return; }
    try {
      const data = await apiFetch("/api/desktop/external-tracking/photos?tracking_no=" + encodeURIComponent(trackingNo));
      const photos = (data.rows || []).filter(photo => photo.available);
      status.textContent = photos.length ? photos.length + " foto\u011Fraf" : "Bu kay\u0131t i\u00E7in foto\u011Fraf bulunamad\u0131.";
      host.innerHTML = photos.map(photo => '<figure><img src="' + safe(photo.url) + '" alt="' + safe(photo.photo_label || "Garanti s\u00FCreci foto\u011Fraf\u0131") + '"><figcaption>' + safe(photo.photo_label || "Foto\u011Fraf") + '<button type="button" class="mini" data-external-photo-delete="' + safe(photo.id) + '">Sil</button></figcaption></figure>').join("");
    } catch (error) { status.textContent = error.message; }
  };
  const bindGallery = () => {
    const picker = $("#dialogBody [data-external-photo-pick]"), input = $("#dialogBody [data-external-photo-input]");
    const tracking = $("#dialogBody [name=internal_tracking_no]");
    if (!picker || !input || !tracking) return;
    picker.onclick = () => input.click();
    tracking.addEventListener("change", () => loadGallery(tracking.value));
    input.onchange = async () => {
      const files = [...input.files];
      try {
        for (const file of files) {
          if (file.size > 8 * 1024 * 1024) throw new Error("Her foto\u011Fraf en fazla 8 MB olabilir");
          await galleryUpload(file);
        }
        await loadGallery(tracking.value);
        toast(files.length + " foto\u011Fraf eklendi");
      } catch (error) { toast(error.message, "error"); }
      input.value = "";
    };
    loadGallery(tracking.value);
  };
  const editRow = row => {
    openDialog(row.id ? "Harici Servis Kayd\u0131n\u0131 D\u00FCzenle" : "Lojistik & Garanti Takip Ekle", "DI\u015E SERV\u0130S / GARANT\u0130", galleryFormBody(row), async form => {
      const payload = Object.fromEntries(form.entries());
      if (row.id) { payload.id = row.id; payload._action = "update"; }
      await apiFetch(url, { method: "POST", body: JSON.stringify(payload) });
      await refresh();
      toast(row.id ? "Harici servis kayd\u0131 g\u00FCncellendi" : "Harici servis kayd\u0131 eklendi");
    });
    bindGallery();
  };
  const openGallery = row => {
    const body = '<input type="hidden" name="internal_tracking_no" value="' + safe(row.internal_tracking_no) + '"><section class="external-tracking-gallery"><div><strong>Foto\u011Fraf Galerisi</strong><button type="button" class="secondary" data-external-photo-pick>Foto\u011Fraf Ekle</button><input type="file" accept=".jpg,.jpeg,.png,.bmp,image/jpeg,image/png,image/bmp" multiple data-external-photo-input hidden></div><p data-external-photo-status>Kayda ba\u011Fl\u0131 foto\u011Fraflar</p><div data-external-photo-list></div></section>';
    openDialog("Foto\u011Fraf Galerisi", "DI\u015E SERV\u0130S / GARANT\u0130", body, () => true, "Tamam");
    bindGallery();
  };
  const removeRow = async id => {
    const row = rows.find(item => String(item.id) === String(id));
    if (!row) return;
    const label = row.tracking_no || row.internal_tracking_no || row.id;
    openDialog("Harici Takip Kayd\u0131n\u0131 Sil", "DI\u015e SERV\u0130S / GARANT\u0130", `<p><strong>${safe(label)}</strong> harici servis takip kayd\u0131 silinsin mi?</p>`, async () => {
      try {
        await apiFetch(url, { method: "POST", body: JSON.stringify({ id: row.id, _action: "delete" }) });
        selectedIds.delete(String(row.id));
        await refresh();
        toast("Harici servis kayd\u0131 silindi");
        return true;
      } catch (error) {
        toast(error.message || "Harici servis kayd\u0131 silinemedi.", "error");
        return false;
      }
    }, "Evet, Sil");
    document.querySelector("#dialogCancel").textContent = "Hay\u0131r";
    document.querySelector("#dialogSubmit").classList.remove("primary");
    document.querySelector("#dialogSubmit").classList.add("danger");
  };
  const exportWorkbook = async () => {
    const records = selectedIds.size ? rows.filter(row => selectedIds.has(String(row.id))) : filtered();
    if (!records.length) { toast("D\u0131\u015Fa aktar\u0131lacak kay\u0131t bulunamad\u0131.", "warning"); return; }
    try {
      const ids = records.map(row => row.id).join(",");
      const response = await fetch("/api/desktop/external-tracking/export?ids=" + encodeURIComponent(ids), { credentials: "same-origin", headers: ayecFiscalArchiveHeaders() });
      if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error || "Excel dosyas\u0131 olu\u015Fturulamad\u0131"); }
      const anchor = document.createElement("a");
      anchor.href = URL.createObjectURL(await response.blob());
      anchor.download = "Dis_Takip_Listesi_" + today() + ".xlsx";
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
    } catch (error) { toast(error.message, "error"); }
  };
  const importWorkbook = async file => {
    if (!file) return;
    if (file.size > 12 * 1024 * 1024) { toast("Dosya 12 MB sin\u0131r\u0131n\u0131 a\u015F\u0131yor", "error"); return; }
    const allowed = /\.(xlsx|xls|csv)$/i.test(file.name);
    if (!allowed) { toast("XLSX, XLS veya CSV dosyas\u0131 se\u00E7in", "error"); return; }
    try {
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error("Dosya okunamad\u0131"));
        reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
        reader.readAsDataURL(file);
      });
      const result = await apiFetch("/api/desktop/external-tracking/import", { method: "POST", body: JSON.stringify({ filename: file.name, data: dataUrl }) });
      toast("\u0130\u00E7e aktarma tamamland\u0131. Ba\u015Far\u0131l\u0131: " + result.success + " \u00B7 Hatal\u0131: " + result.failures);
      await refresh();
    } catch (error) { toast(error.message, "error"); }
  };
  const showDocumentsCenter = async () => {
    let documents = [];
    let selectedKey = "";
    const draw = host => {
      host.innerHTML = documents.length ? '<div class="table-wrap"><table><thead><tr><th>Kaynak</th><th>Ba\u015Fl\u0131k</th><th>Kategori</th><th>Sevk / Kay\u0131t</th><th>Durum</th><th>Tarih</th></tr></thead><tbody>' + documents.map(item => '<tr tabindex="0" data-document-key="' + safe(item.key) + '" class="' + (item.key === selectedKey ? "selected" : "") + '"><td>' + safe(item.source) + '</td><td>' + safe(item.title) + '</td><td>' + safe(item.category) + '</td><td>' + safe(item.shipment) + '</td><td>' + (item.available ? "Web eri\u015Fimi var" : "Yerel dosya eri\u015Fimi yok") + '</td><td>' + safe(item.date) + '</td></tr>').join("") + '</tbody></table></div>' : empty("Belge bulunamad\u0131", "Kirac\u0131 veritaban\u0131nda listelenecek dosya yok.");
    };
    const load = async host => {
      try { documents = (await apiFetch("/api/desktop/documents/center")).rows || []; selectedKey = ""; draw(host); }
      catch (error) { host.innerHTML = empty("Belge merkezi y\u00FCklenemedi", safe(error.message)); }
    };
    const body = '<section class="external-documents-center"><p>Partner, lojistik, stok ve s\u00F6zle\u015Fme belgeleri kirac\u0131 veritaban\u0131ndan listelenir. Yerel dosyalar taray\u0131c\u0131da a\u00E7\u0131lmaz.</p><button type="button" class="secondary" data-document-refresh>Yenile</button><div id="externalDocumentsHost">Y\u00FCkleniyor...</div></section>';
    openDialog("Belge Merkezi", "DOSYALAR / BELGELER", body, async () => {
      const item = documents.find(document => document.key === selectedKey);
      if (!item) { toast("A\u00E7mak i\u00E7in bir belge se\u00E7in.", "warning"); return false; }
      if (!item.available || !item.url) { toast("Bu dosya masa\u00FCst\u00FC yerel yolunda; web eri\u015Fimi yok.", "warning"); return false; }
      window.open(item.url, "_blank", "noopener,noreferrer");
      return false;
    }, "A\u00E7");
    const host = $("#externalDocumentsHost");
    if (host) { await load(host); host.addEventListener("click", event => { const row = event.target.closest("[data-document-key]"); if (!row) return; selectedKey = row.dataset.documentKey; draw(host); }); }
    const refreshButton = $("#dialogBody [data-document-refresh]");
    if (refreshButton && host) refreshButton.onclick = () => load(host);
  };
  window.openDesktopDocumentsCenter = showDocumentsCenter;
  const showCargoManifest = () => {
    const records = selectedIds.size ? rows.filter(row => selectedIds.has(String(row.id))) : filtered();
    if (!records.length) { toast("Kargo fi\u015Fi i\u00E7in kay\u0131t se\u00E7in veya filtreleri de\u011Fi\u015Ftirin.", "warning"); return; }
    const headings = ["Takip No", "M\u00FC\u015Fteri / Cihaz", "Yetkili Servis", "G\u00F6nderim", "Gidi\u015F Kargo", "D\u00F6n\u00FC\u015F Kargo", "Durum"];
    const body = records.map(row => '<tr><td>' + safe(row.internal_tracking_no || "-") + '</td><td>' + safe((row.customer_name || "-") + " / " + (row.product_name || "-")) + '</td><td>' + safe(row.external_service_name || "-") + '</td><td>' + safe(row.sent_date || "-") + '</td><td>' + safe(row.outbound_cargo_no || "-") + '</td><td>' + safe(row.inbound_cargo_no || "-") + '</td><td>' + safe(row.status || "-") + '</td></tr>').join("");
    const html = '<section class="external-cargo-manifest"><h2>Lojistik / Toplu Kargo Fi\u015Fi</h2><p>' + records.length + ' kay\u0131t</p><div class="table-wrap"><table><thead><tr>' + headings.map(heading => '<th>' + heading + '</th>').join("") + '</tr></thead><tbody>' + body + '</tbody></table></div></section>';
    document.body.dataset.externalManifestPrint = "true";
    const dialog = $("#appDialog");
    if (dialog) dialog.addEventListener("close", () => { delete document.body.dataset.externalManifestPrint; }, { once: true });
    openDialog("Toplu Kargo Fi\u015Fi", "KARGO / \u0130RSAL\u0130YE", html, async () => { window.print(); return false; }, "Yazd\u0131r");
  };
  const originalShell = genericShell;
  genericShell = function(meta) {
    const html = originalShell(meta);
    if (page !== "logistics" || meta?.table !== "logistics") return html;
    return '<nav class="external-tracking-tabs" aria-label="Lojistik g\u00F6r\u00FCn\u00FCmleri"><button type="button" data-external-view="external" class="' + (view === "external" ? "active" : "") + '">Garanti / D\u0131\u015F Servis</button><button type="button" data-external-view="cargo" class="' + (view === "cargo" ? "active" : "") + '">Kargo Takip</button></nav><section id="externalTrackingPanel"' + (view === "cargo" ? ' hidden' : '') + '><div class="page-head"><div><h2>Lojistik &amp; Garanti Y\u00F6netimi</h2><p>Anla\u015Fmal\u0131 servisler ve garanti s\u00FCre\u00E7lerinin merkezi takip sistemi</p></div><div class="actions"><button type="button" class="secondary" data-external-refresh>Yenile</button><button type="button" class="secondary" data-external-export>Excel / Rapor</button><button type="button" class="primary" data-external-add>+ Yeni Takip Ba\u015Flat</button></div></div><section class="metric-grid external-tracking-metrics"><article><small>Toplam Kay\u0131t</small><strong id="externalTrackingTotal">0</strong><footer>Garanti Havuzu</footer></article><article><small>D\u0131\u015F Serviste (Aktif)</small><strong id="externalTrackingActive">0</strong><footer>Kargoda / Serviste</footer></article><article><small>Onay Bekleyen</small><strong id="externalTrackingPending">0</strong><footer>Fiyat / Onay</footer></article><article><small>Teslim Al\u0131nan</small><strong id="externalTrackingReceived">0</strong><footer>Depo kabul</footer></article></section><section class="card external-tracking-filters"><input class="control search" id="externalTrackingSearch" type="search" placeholder="Kargo takip no, emanet no, m\u00FC\u015Fteri veya yetkili servis ara..."><select class="control" id="externalTrackingStatus"><option value="">Durum: T\u00FCm\u00FC</option>' + statuses.map(status => '<option>' + status + '</option>').join("") + '</select><select class="control" id="externalTrackingService"><option value="">Yetkili Servis: T\u00FCm\u00FC</option></select><select class="control" id="externalTrackingMonth" aria-label="G\u00F6nderim ay\u0131"><option value="">T\u00FCm Aylar</option></select></section><section class="card external-tracking-table"><div id="externalTrackingHost"></div><footer id="externalTrackingPagination"></footer></section></section><section id="logisticsCargoPanel"' + (view === "external" ? ' hidden' : '') + '>' + html + '</section>';
  };
  const originalRender = render;
  render = function() {
    originalRender();
    if (page !== "logistics") return;
    const actions = $("#externalTrackingPanel .actions");
    if (actions && !actions.querySelector("[data-external-cargo-sync]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.dataset.externalCargoSync = "";
      button.textContent = "Kargo API Sync";
      button.title = "Kargo saglayici API baglantisi bu modulde henuz mevcut degil.";
      button.disabled = true;
      actions.insertBefore(button, actions.querySelector("[data-external-export]"));
    }
    if (actions && !actions.querySelector("[data-external-multiselect]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.dataset.externalMultiselect = "";
      button.textContent = "\u00c7oklu Se\u00e7im";
      actions.insertBefore(button, actions.querySelector("[data-external-export]"));
    }
    if (actions && !actions.querySelector("[data-external-manifest]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.dataset.externalManifest = "";
      button.textContent = "Toplu Kargo Fi\u015Fi";
      actions.insertBefore(button, actions.querySelector("[data-external-export]"));
    }
    if (actions && !actions.querySelector("[data-external-import]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.dataset.externalImport = "";
      button.textContent = "\u0130\u00E7e Aktar";
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".xlsx,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv";
      input.hidden = true;
      input.dataset.externalImportFile = "";
      input.onchange = () => { importWorkbook(input.files?.[0]); input.value = ""; };
      button.onclick = () => input.click();
      actions.insertBefore(button, actions.querySelector("[data-external-manifest]"));
      actions.append(input);
    }
    if (actions && !actions.querySelector("[data-external-documents]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.dataset.externalDocuments = "";
      button.textContent = "Belgeler";
      actions.insertBefore(button, actions.querySelector("[data-external-export]"));
    }
    const panel = $("#externalTrackingPanel");
    const tableCard = panel?.querySelector(".external-tracking-table");
    const pagination = panel?.querySelector("#externalTrackingPagination");
    if (tableCard && pagination && pagination.parentElement === tableCard) {
      tableCard.after(pagination);
      pagination.classList.add("external-tracking-page-footer");
    }
    const heading = panel?.querySelector(".page-head > div:first-child");
    if (heading && !heading.querySelector(".external-tracking-title-row")) {
      const title = heading.querySelector("h2");
      const titleRow = document.createElement("div");
      titleRow.className = "external-tracking-title-row";
      const icon = document.createElement("span");
      icon.className = "external-tracking-title-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.innerHTML = '<svg viewBox="0 0 32 32"><path d="M3 8h17v15H3zM20 13h5l5 5v5H20zM8 23a3 3 0 1 0 6 0m9 0a3 3 0 1 0 6 0"/></svg>';
      const badge = document.createElement("span");
      badge.className = "external-tracking-sla-badge";
      badge.textContent = "V2.5 SLA SYNC";
      titleRow.append(icon);
      if (title) titleRow.append(title);
      titleRow.append(badge);
      heading.prepend(titleRow);
    }
    const filters = panel?.querySelector(".external-tracking-filters");
    const actionsReady = actions && !actions.querySelector(".external-tracking-command-row");
    if (actionsReady && filters) {
      const rowOne = document.createElement("div");
      rowOne.className = "external-tracking-command-row external-tracking-command-row-primary";
      const rowTwo = document.createElement("div");
      rowTwo.className = "external-tracking-command-row external-tracking-command-row-secondary";
      const move = (selector, target) => { const button = actions.querySelector(selector); if (button) target.append(button); };
      move("[data-external-cargo-sync]", rowOne);
      move("[data-external-manifest]", rowOne);
      move("[data-external-export]", rowOne);
      move("[data-external-add]", rowTwo);
      move("[data-external-import]", rowTwo);
      move("[data-external-documents]", rowTwo);
      move("[data-external-multiselect]", rowTwo);
      const importFile = actions.querySelector("[data-external-import-file]");
      const refreshButton = actions.querySelector("[data-external-refresh]");
      actions.replaceChildren(rowOne, rowTwo);
      if (importFile) actions.append(importFile);
      if (refreshButton) { refreshButton.title = "Kargo ve garanti kayitlarini yenile"; refreshButton.setAttribute("aria-label", "Yenile"); filters.append(refreshButton); }
    }
    panel?.querySelectorAll(".external-tracking-metrics article").forEach((card, index) => {
      if (card.querySelector(".external-tracking-metric-icon")) return;
      const icon = document.createElement("span");
      icon.className = "external-tracking-metric-icon external-tracking-metric-icon-" + index;
      icon.setAttribute("aria-hidden", "true");
      card.prepend(icon);
    });
    const serviceSelect = $("#externalTrackingService");
    if (serviceSelect) {
      const services = [...new Set(rows.map(row => row.external_service_name).filter(Boolean))].sort();
      serviceSelect.innerHTML = '<option value="">Yetkili Servis: T\u00FCm\u00FC</option>' + services.map(name => '<option>' + safe(name) + '</option>').join("");
    }
    refresh();
  };
  document.addEventListener("input", event => { if (page === "logistics" && event.target.id === "externalTrackingSearch") { pageIndex = 0; renderRows(); } });
  document.addEventListener("change", event => { if (page === "logistics" && ["externalTrackingStatus", "externalTrackingService", "externalTrackingMonth"].includes(event.target.id)) { pageIndex = 0; renderRows(); } });
  document.addEventListener("click", event => {
    if (page !== "logistics") return;
    const tab = event.target.closest("[data-external-view]");
    if (tab) { view = tab.dataset.externalView; $("#externalTrackingPanel").hidden = view !== "external"; $("#logisticsCargoPanel").hidden = view !== "cargo"; document.querySelectorAll("[data-external-view]").forEach(button => button.classList.toggle("active", button === tab)); $("#contextMenu")?.classList.remove("open", "external-tracking-context"); return; }
    if (event.target.closest("[data-external-add]")) { editRow({}); return; }
    const photoDelete = event.target.closest("[data-external-photo-delete]");
    if (photoDelete) { apiFetch("/api/desktop/external-tracking/photos", { method: "POST", body: JSON.stringify({ _action: "delete", id: photoDelete.dataset.externalPhotoDelete }) }).then(() => loadGallery($("#dialogBody [name=internal_tracking_no]")?.value || "")).catch(error => toast(error.message, "error")); return; }
    if (event.target.closest("[data-external-multiselect]")) { multiselect = !multiselect; if (!multiselect) selectedIds.clear(); renderRows(); const button = $("[data-external-multiselect]"); if (button) button.textContent = multiselect ? "\u00c7oklu Se\u00e7im A\u00e7\u0131k" : "\u00c7oklu Se\u00e7im"; return; }
    if (event.target.closest("[data-external-refresh]")) { refresh(); return; }
    if (event.target.closest("[data-external-manifest]")) { showCargoManifest(); return; }
    if (event.target.closest("[data-external-documents]")) { showDocumentsCenter().catch(error => toast(error.message, "error")); return; }
    if (event.target.closest("[data-external-export]")) { exportWorkbook(); return; }
    const pager = event.target.closest("[data-external-page]");
    if (pager) { pageIndex = Math.max(0, pageIndex + Number(pager.dataset.externalPage)); renderRows(); return; }
    const edit = event.target.closest("[data-external-edit]");
    if (edit) { const row = rows.find(item => String(item.id) === edit.dataset.externalEdit); if (row) editRow(row); return; }
    const remove = event.target.closest("[data-external-delete]");
    if (remove) { removeRow(remove.dataset.externalDelete).catch(error => toast(error.message, "error")); return; }
    const checkbox = event.target.closest("[data-external-select]");
    if (checkbox) { if (checkbox.checked) selectedIds.add(String(checkbox.dataset.externalSelect)); else selectedIds.delete(String(checkbox.dataset.externalSelect)); checkbox.closest("tr")?.classList.toggle("selected", checkbox.checked); return; }
    const selected = event.target.closest("[data-external-row]");
    if (selected) {
      const id = String(selected.dataset.externalRow);
      if (multiselect) { if (selectedIds.has(id)) selectedIds.delete(id); else selectedIds.add(id); }
      else { selectedIds.clear(); document.querySelectorAll("[data-external-row].selected").forEach(row => row.classList.remove("selected")); selectedIds.add(id); }
      selected.classList.toggle("selected", selectedIds.has(id));
      const checkbox = selected.querySelector("[data-external-select]");
      if (checkbox) checkbox.checked = selectedIds.has(id);
    }
  });
  document.addEventListener("dblclick", event => {
    if (page !== "logistics" || view !== "external" || !db.settings.doubleClick) return;
    const tr = event.target.closest("[data-external-row]");
    const row = tr && rows.find(item => String(item.id) === tr.dataset.externalRow);
    if (row) editRow(row);
  });
  document.addEventListener("contextmenu", event => {
    if (page !== "logistics" || view !== "external" || !ayecContextMenuEnabled()) return;
    const tr = event.target.closest("[data-external-row]");
    if (!tr) return;
    event.preventDefault();
    const id = String(tr.dataset.externalRow);
    if (!multiselect) { selectedIds.clear(); selectedIds.add(id); }
    else if (!selectedIds.size) selectedIds.add(id);
    const menu = $("#contextMenu");
    if (!menu) return;
    menu.dataset.targetId = id;
    menu.innerHTML = '<button type="button" role="menuitem" data-external-context="edit">D\u00FCzenle</button><button type="button" role="menuitem" data-external-context="delete">Sil</button><button type="button" role="menuitem" data-external-context="gallery">Foto\u011Fraf Galerisi</button><button type="button" role="menuitem" data-external-context="export">Secilileri Excel D\u0131\u015Fa Aktar</button>';
    menu.classList.add("external-tracking-context", "open");
    menu.style.left = Math.max(8, Math.min(event.clientX, innerWidth - menu.offsetWidth - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(event.clientY, innerHeight - menu.offsetHeight - 8)) + "px";
    renderRows();
  });
  let externalContextPressTimer = null;
  let externalContextPressOrigin = null;
  document.addEventListener("pointerdown", event => {
    if (page !== "logistics" || view !== "external" || event.pointerType === "mouse" || !ayecContextMenuEnabled()) return;
    const row = event.target.closest?.("[data-external-row]");
    if (!row) return;
    if (externalContextPressTimer) clearTimeout(externalContextPressTimer);
    const origin = { x: event.clientX, y: event.clientY };
    externalContextPressOrigin = origin;
    externalContextPressTimer = window.setTimeout(() => {
      externalContextPressTimer = null;
      externalContextPressOrigin = null;
      if (!row.isConnected || page !== "logistics" || view !== "external" || !ayecContextMenuEnabled()) return;
      row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: origin.x, clientY: origin.y }));
    }, 550);
  });
  const cancelExternalContextPress = event => {
    if (!externalContextPressTimer) return;
    if (event.type === "pointermove" && externalContextPressOrigin && Math.hypot(event.clientX - externalContextPressOrigin.x, event.clientY - externalContextPressOrigin.y) <= 10) return;
    clearTimeout(externalContextPressTimer);
    externalContextPressTimer = null;
    externalContextPressOrigin = null;
  };
  document.addEventListener("pointerup", cancelExternalContextPress);
  document.addEventListener("pointercancel", cancelExternalContextPress);
  document.addEventListener("pointermove", cancelExternalContextPress);
  document.addEventListener("keydown", event => {
    if (page !== "logistics" || view !== "external" || (event.key !== "ContextMenu" && !(event.shiftKey && event.key === "F10")) || !ayecContextMenuEnabled()) return;
    const row = event.target.closest?.("[data-external-row]");
    if (!row) return;
    const bounds = row.getBoundingClientRect();
    row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: bounds.left + Math.min(bounds.width / 2, 220), clientY: bounds.top + Math.min(bounds.height / 2, 16) }));
    const menu = $("#contextMenu");
    if (menu?.classList.contains("open") && menu.dataset.targetId === row.dataset.externalRow) {
      event.preventDefault();
      menu.querySelector("[data-external-context]")?.focus();
    }
  });
  document.addEventListener("click", event => {
    const action = event.target.closest("[data-external-context]");
    const menu = $("#contextMenu");
    if (!action) { if (menu) menu.classList.remove("open", "external-tracking-context"); return; }
    if (menu) menu.classList.remove("open", "external-tracking-context");
    const id = menu?.dataset.targetId;
    const row = rows.find(item => String(item.id) === String(id));
    if (action.dataset.externalContext === "edit" && row) editRow(row);
    if (action.dataset.externalContext === "delete" && row) removeRow(row.id).catch(error => toast(error.message, "error"));
    if (action.dataset.externalContext === "gallery" && row) openGallery(row);
    if (action.dataset.externalContext === "export") {
      if (!selectedIds.size && id) selectedIds.add(String(id));
      exportWorkbook().catch(error => toast(error.message, "error"));
    }
  });
})();
