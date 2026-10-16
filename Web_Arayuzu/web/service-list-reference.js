// Service list reference route for desktop web and mobile layouts.
const ayecServiceListState = {
  tab: "all", query: "", status: "all", date: "last_30", priority: "all",
  page: 1, pageSize: 15, selected: new Set()
};

const ayecServiceListTabs = [
  ["all", "T\u00fcm Cihazlar"], ["today", "Randevulu"],
  ["pending_approval", "Onay Bekleyen"], ["cargo", "Kargosu Beklenen"],
  ["invoiced", "Faturas\u0131 Kesilen"], ["uninvoiced", "Faturas\u0131 Kesilmeyen"],
  ["outbound", "Onar\u0131ma Giden"], ["inbound", "Onar\u0131mdan Gelen"]
];

function ayecServiceListRows() {
  return dashboardServices().map(item => ({
    ...item,
    id: ayecDashboardId(item),
    customer: item.customer || item.customer_name || "-",
    device: item.device || [item.brand, item.model].filter(Boolean).join(" ") || "Cihaz",
    entry: item.entry_date || item.date || "-",
    delivery: item.delivery || item.exit_date || "-",
    price: Number(item.amount || item.price || item.labor_cost || 0)
  }));
}

function ayecServiceListMatchTab(item, key) {
  if (key === "all") return true;
  if (key === "today") return Boolean(item.appointment_id || item.appointment_date);
  if (key === "pending_approval") return /onay|bekle/i.test(item.approval_status || item.status || "");
  if (key === "cargo") return serviceStatusKey(item) === "kargo" || /kargo/i.test(item.delivery_type || "");
  if (key === "invoiced") return Boolean(item.invoice_no || item.invoice_id);
  if (key === "uninvoiced") return !item.invoice_no && !item.invoice_id;
  if (key === "outbound") return /onar.maya giden|d.s servis/i.test(item.status || item.delivery_type || "");
  if (key === "inbound") return /onar.mdan gelen|servisten d.nd./i.test(item.status || item.delivery_type || "");
  return true;
}

function ayecServiceListStatusKey(item) {
  const status = String(item.status || "").replace(/[\u0131\u0130]/g, "i").replace(/[/-]/g, " ")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("tr-TR").replace(/\s+/g, " ").trim();
  if (!status) return "waiting";
  if (["iptal", "iptal edildi", "iptal iade", "iade edildi"].includes(status)) return "cancelled";
  if (["parca", "parca bekliyor", "siparis gecildi"].includes(status)) return "parts";
  if (["hazir", "bitti", "tamamlandi", "tamir edildi", "teslim", "teslim edildi", "teslim alindi", "musteriye teslim", "kapandi"].includes(status)) return "delivered";
  if (["test surecinde", "test ediliyor", "test asamasi", "kontrol ediliyor", "onay bekleyen", "onay bekliyor", "test / onay", "test/onay", "test onay"].includes(status)) return "testing";
  if (["tamirde", "serviste", "islemde", "onarimda"].includes(status)) return "repair";
  if (["bekliyor", "beklemede", "isleme alinacak", "siraya alinacak", "servise alinacak", "kayit", "yeni kayit", "none", "bilinmiyor", "kabul edildi"].includes(status)) return "waiting";
  return "";
}

function ayecServiceListDateMatches(item, filter) {
  const entry = String(item.entry || "").slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!entry) return false;
  const entryDate = new Date(Number(entry[1]), Number(entry[2]) - 1, Number(entry[3]));
  if (entryDate.getFullYear() !== Number(entry[1]) || entryDate.getMonth() !== Number(entry[2]) - 1 || entryDate.getDate() !== Number(entry[3])) return false;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dayNumber = value => Date.UTC(value.getFullYear(), value.getMonth(), value.getDate()) / 86400000;
  const days = dayNumber(today) - dayNumber(entryDate);
  if (filter === "today") return days === 0;
  if (filter === "week") return days <= 6;
  if (filter === "month") return entryDate.getFullYear() === today.getFullYear() && entryDate.getMonth() === today.getMonth();
  if (filter === "last_30") return days <= 29;
  if (filter === "year") return entryDate.getFullYear() === today.getFullYear();
  return true;
}

function ayecServiceListFiltered() {
  const state = ayecServiceListState;
  const query = state.query.toLocaleLowerCase("tr-TR");
  return ayecServiceListRows().filter(item => {
    if (!ayecServiceListMatchTab(item, state.tab)) return false;
    if (state.status !== "all" && ayecServiceListStatusKey(item) !== state.status) return false;
    if (state.priority !== "all" && String(item.priority || item.urgency || "Normal") !== state.priority) return false;
    if (state.date !== "all" && !ayecServiceListDateMatches(item, state.date)) return false;
    return !query || ayecDashboardText([
      item.id, item.customer, item.phone, item.device, item.device_model,
      item.serial_no, item.status, item.brand
    ].join(" ")).includes(query);
  });
}

function ayecServiceListMetric(label, value, note, tone, icon) {
  return `<article class="service-list-metric tone-${tone}"><span class="service-list-metric-icon">${icon}</span><small>${label}</small><strong>${value}</strong><span class="service-list-metric-note">${note}</span></article>`;
}

function renderServiceListReference() {
  const all = ayecServiceListRows();
  const rows = ayecServiceListFiltered();
  const count = key => all.filter(item => ayecServiceListMatchTab(item, key)).length;
  const active = all.filter(item => /tamirde|onar\u0131mda|i\u015flemde|serviste/i.test(item.status || "")).length;
  const parts = all.filter(item => serviceStatusKey(item) === "parca").length;
  const cargo = all.filter(item => serviceStatusKey(item) === "kargo").length;
  const revenue = all.reduce((sum, item) => sum + item.price, 0);
  const pages = Math.max(1, Math.ceil(rows.length / ayecServiceListState.pageSize));
  ayecServiceListState.page = Math.min(ayecServiceListState.page, pages);
  const start = (ayecServiceListState.page - 1) * ayecServiceListState.pageSize;
  const visible = rows.slice(start, start + ayecServiceListState.pageSize);
  const tabs = ayecServiceListTabs.map(([key, label]) =>
    `<button type="button" class="service-list-tab ${ayecServiceListState.tab === key ? "active" : ""}" data-service-tab="${key}">${label}<b>${count(key)}</b></button>`
  ).join("");
  const body = visible.map(item => {
    const selected = ayecServiceListState.selected.has(String(item.id));
    const status = String(item.status || "Bekliyor");
    const statusTone = serviceStatusKey(item);
    const phone = item.phone || item.customer_contact || "";
    const serial = item.serial_no || item.serial || "";
    return `<tr data-kind="service" class="${selected ? "is-selected" : ""}" data-id="${esc(item.id)}" data-customer="${esc(item.customerId || item.customer_id || "")}">
      <td data-label="Se\u00e7"><input type="checkbox" data-service-select="${esc(item.id)}" ${selected ? "checked" : ""} aria-label="Kayd\u0131 se\u00e7"></td>
      <td data-label="Takip No"><strong class="service-list-ticket">${esc(item.id || "-")}</strong></td>
      <td data-label="M\u00fc\u015fteri"><strong>${esc(item.customer)}</strong><small>${esc(phone)}</small></td>
      <td data-label="Cihaz / Model"><strong>${esc(item.device)}</strong><small>${esc(serial ? `SN: ${serial}` : item.device_type || "")}</small></td>
      <td data-label="Kabul Tarihi">${esc(String(item.entry).slice(0, 10))}</td>
      <td data-label="Teslim Tarihi">${esc(String(item.delivery).slice(0, 10))}</td>
      <td data-label="\u00dccret"><strong class="service-list-price">${money(item.price, item.currency || "TRY")}</strong></td>
      <td data-label="Durum"><span class="service-list-status status-${statusTone}">${esc(status)}</span></td>
      <td data-label="Aciliyet"><span class="service-list-priority">${esc(item.priority || item.urgency || "Normal")}</span></td>
      <td data-label="\u0130\u015flemler"><div class="service-list-actions">
        <button type="button" data-action="service-detail" data-id="${esc(item.id)}" data-customer="${esc(item.customerId || item.customer_id || "")}" title="Servis ayr\u0131nt\u0131s\u0131" aria-label="Servis ayr\u0131nt\u0131s\u0131">&#9673;</button>
        <button type="button" data-action="technician-open" data-id="${esc(item.id)}" data-customer="${esc(item.customerId || item.customer_id || "")}" title="Teknisyen i\u015flemi" aria-label="Teknisyen i\u015flemi">&#9998;</button>
        <button type="button" data-service-command="row-print" data-id="${esc(item.id)}" title="Yazd\u0131r" aria-label="Yazd\u0131r">&#9113;</button>
        <button type="button" data-service-command="payment" data-id="${esc(item.id)}" title="\u00d6deme Al" aria-label="\u00d6deme Al">&#9678;</button>
        <button type="button" data-service-command="sms" data-id="${esc(item.id)}" title="SMS G\u00f6nder" aria-label="SMS G\u00f6nder">&#9993;</button>
        <button type="button" data-service-command="whatsapp" data-id="${esc(item.id)}" title="WhatsApp" aria-label="WhatsApp">&#9742;</button>
        <button type="button" data-service-command="status" data-id="${esc(item.id)}" title="Durum De\u011fi\u015ftir" aria-label="Durum De\u011fi\u015ftir">&#8635;</button>
        <button type="button" data-service-command="delete" data-id="${esc(item.id)}" title="Sil / Ar\u015fivle" aria-label="Sil / Ar\u015fivle">&#128465;</button>
      </div></td>
    </tr>`;
  }).join("");
  const metricHTML = [
    ayecServiceListMetric("AKT\u0130F TAM\u0130RDE", `${active} Cihaz`, "At\u00f6lyede i\u015flemde", "blue", "&#9881;"),
    ayecServiceListMetric("PAR\u00c7A BEKLEYEN", `${parts} Cihaz`, "Normal ak\u0131\u015f", "amber", "&#9203;"),
    ayecServiceListMetric("TESL\u0130ME HAZIR", `${all.filter(item => /haz.r|tamamland/i.test(item.status || "")).length} Cihaz`, "Onay bekleyen", "green", "&#10003;"),
    ayecServiceListMetric("KARGO SEVK\u0130YAT", `${cargo} Paket`, "Kurye \u00e7a\u011fr\u0131ld\u0131", "purple", "&#128666;"),
    ayecServiceListMetric("TAHM\u0130N\u0130 C\u0130RO", money(revenue, all[0]?.currency || "TRY"), "Servis kay\u0131tlar\u0131", "gold", "&#8378;"),
    ayecServiceListMetric("ORT. \u00c7\u00d6Z\u00dcM S\u00dcRES\u0130", "0.9 G\u00fcn", "Ayn\u0131 g\u00fcn teslim", "indigo", "&#9711;")
  ].join("");
  return `<div class="service-list-ref">
    <header class="service-list-heading"><div><span class="service-list-heading-icon">&#9881;</span><div><h1>Servis Listesi</h1><p>T\u00fcm teknik servis ve onar\u0131m kay\u0131tlar\u0131n\u0131 tek ekrandan y\u00f6netin, filtreleyin ve raporlay\u0131n.</p></div></div><div class="service-list-heading-actions"><div class="service-list-bulk"><button type="button" class="secondary" data-service-command="bulk-toggle" aria-expanded="false">Toplu \u0130\u015flemler</button><div class="service-list-bulk-menu" data-service-menu hidden><button type="button" data-service-command="bulk-export">Se\u00e7ili kay\u0131tlar\u0131 d\u0131\u015fa aktar</button><button type="button" data-service-command="bulk-print">Se\u00e7ili servis fi\u015flerini yazd\u0131r</button><hr><button type="button" data-service-command="bulk-select-page">Bu sayfan\u0131n t\u00fcm\u00fcn\u00fc se\u00e7</button><button type="button" data-service-command="bulk-clear">Se\u00e7imi kald\u0131r</button></div></div><button type="button" class="secondary" data-service-command="refresh">&#8635; Yenile</button><button type="button" class="secondary" data-service-command="history">&#9719; Servis Ge\u00e7mi\u015fi</button><button type="button" class="secondary" data-service-command="export">&#8681; D\u0131\u015fa Aktar</button><button type="button" class="primary" data-action="new-service">+ Yeni Cihaz Kayd\u0131</button></div></header>
    <section class="service-list-metrics">${metricHTML}</section>
    <nav class="service-list-tabs" aria-label="Servis kategorileri">${tabs}</nav>
    <section class="service-list-filters"><input id="serviceListSearch" type="search" value="${esc(ayecServiceListState.query)}" placeholder="Takip no, m\u00fc\u015fteri veya cihaz ara..." aria-label="Servis ara"><select id="serviceListStatus" aria-label="Durum filtresi"><option value="all">Durum: T\u00fcm\u00fc</option>${[["waiting","Bekliyor"],["repair","Tamirde"],["parts","Par\u00e7a Bekliyor"],["testing","Test S\u00fcrecinde"],["delivered","Teslim Edildi"],["cancelled","\u0130ptal / \u0130ade"]].map(([key,label])=>`<option value="${key}" ${ayecServiceListState.status === key ? "selected" : ""}>${label}</option>`).join("")}</select><select id="serviceListDate" aria-label="Tarih aral\u0131\u011f\u0131"><option value="all">Tarih Aral\u0131\u011f\u0131: T\u00fcm\u00fc</option><option value="today" ${ayecServiceListState.date === "today" ? "selected" : ""}>Bug\u00fcn</option><option value="week" ${ayecServiceListState.date === "week" ? "selected" : ""}>Bu Hafta</option><option value="month" ${ayecServiceListState.date === "month" ? "selected" : ""}>Bu Ay</option><option value="last_30" ${ayecServiceListState.date === "last_30" ? "selected" : ""}>Son 30 G\u00fcn</option><option value="year" ${ayecServiceListState.date === "year" ? "selected" : ""}>Bu Y\u0131l</option></select><select id="serviceListPriority" aria-label="\u00d6ncelik filtresi"><option value="all">\u00d6ncelik: T\u00fcm</option><option value="Normal" ${ayecServiceListState.priority === "Normal" ? "selected" : ""}>Normal</option><option value="Acil" ${ayecServiceListState.priority === "Acil" ? "selected" : ""}>Acil</option></select><button type="button" class="primary" data-service-command="filter">Filtrele</button><button type="button" class="secondary" data-service-command="clear">Temizle</button></section>
    <section class="service-list-quick-actions" aria-label="H\u0131zl\u0131 i\u015flemler"><button type="button" data-service-command="history">&#9719; Servis Ge\u00e7mi\u015fi</button><button type="button" data-service-command="print">&#9113; Detayl\u0131 Fi\u015f Yazd\u0131r</button><button type="button" data-service-command="cargo">&#128666; Kargo Fi\u015fi Yazd\u0131r</button><button type="button" data-service-command="dispatch">E-\u0130rsaliye</button><button type="button" data-service-command="invoice">E-Fatura</button><button type="button" data-service-command="whatsapp">WhatsApp Bildirim</button></section>
    <section class="service-list-table-wrap"><table class="service-list-table"><thead><tr><th><input type="checkbox" data-service-select-all aria-label="T\u00fcm kay\u0131tlar\u0131 se\u00e7"></th><th>TAK\u0130P NO</th><th>M\u00dc\u015eTER\u0130</th><th>C\u0130HAZ / MODEL</th><th>KABUL TAR\u0130H\u0130</th><th>TESL\u0130M TAR\u0130H\u0130</th><th>\u00dcCRET</th><th>DURUM</th><th>AC\u0130L\u0130YET</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>${body || `<tr><td colspan="10" class="service-list-empty">Bu filtrede servis kayd\u0131 bulunamad\u0131.</td></tr>`}</tbody></table></section>
    <footer class="service-list-pagination"><span>${rows.length} kay\u0131ttan ${rows.length ? start + 1 : 0}-${Math.min(start + ayecServiceListState.pageSize, rows.length)} aras\u0131 g\u00f6steriliyor.</span><div><label>Sayfa ba\u015f\u0131na <select id="serviceListPageSize"><option ${ayecServiceListState.pageSize === 15 ? "selected" : ""}>15</option><option ${ayecServiceListState.pageSize === 25 ? "selected" : ""}>25</option><option ${ayecServiceListState.pageSize === 50 ? "selected" : ""}>50</option></select></label><button type="button" data-service-page="prev" ${ayecServiceListState.page <= 1 ? "disabled" : ""} aria-label="\u00d6nceki">&lt;</button><b>${ayecServiceListState.page}</b><button type="button" data-service-page="next" ${ayecServiceListState.page >= pages ? "disabled" : ""} aria-label="Sonraki">&gt;</button></div></footer>
  </div>`;
}

const ayecRenderBeforeServiceListReference = render;
render = function () {
  if (page !== "service-list") return ayecRenderBeforeServiceListReference();
  document.body.dataset.page = page;
  $("#content").innerHTML = renderServiceListReference();
  bindPage();
  const content = $("#content");
  const search = $("#serviceListSearch");
  if (search) search.oninput = () => {
    ayecServiceListState.query = search.value;
    ayecServiceListState.page = 1;
    const start = search.selectionStart;
    render();
    const next = $("#serviceListSearch");
    next?.focus();
    next?.setSelectionRange(start, start);
  };
  $("#serviceListStatus").onchange = event => { ayecServiceListState.status = event.target.value; ayecServiceListState.page = 1; render(); };
  $("#serviceListDate").onchange = event => { ayecServiceListState.date = event.target.value; ayecServiceListState.page = 1; render(); };
  $("#serviceListPriority").onchange = event => { ayecServiceListState.priority = event.target.value; ayecServiceListState.page = 1; render(); };
  $("#serviceListPageSize").onchange = event => { ayecServiceListState.pageSize = Number(event.target.value) || 15; ayecServiceListState.page = 1; render(); };
  content.onclick = async event => {
    const tab = event.target.closest("[data-service-tab]");
    if (tab) { ayecServiceListState.tab = tab.dataset.serviceTab; ayecServiceListState.page = 1; render(); return; }
    const pageButton = event.target.closest("[data-service-page]");
    if (pageButton && !pageButton.disabled) { ayecServiceListState.page += pageButton.dataset.servicePage === "next" ? 1 : -1; render(); return; }
    const command = event.target.closest("[data-service-command]");
    if (!command) return;
    const action = command.dataset.serviceCommand;
    if (action === "bulk-toggle") {
      const menu = content.querySelector("[data-service-menu]");
      const expanded = command.getAttribute("aria-expanded") === "true";
      command.setAttribute("aria-expanded", String(!expanded));
      menu.hidden = expanded;
      return;
    }
    if (action === "bulk-select-page") {
      visibleRowsForServiceList().forEach(item => ayecServiceListState.selected.add(String(item.id)));
      render();
      return;
    }
    if (action === "bulk-clear") { ayecServiceListState.selected.clear(); render(); return; }
    if (action === "bulk-export") {
      const items = ayecServiceListFiltered().filter(item => ayecServiceListState.selected.has(String(item.id)));
      if (!items.length) { toast("Önce servis kay\u0131tlar\u0131n\u0131 se\u00e7in", "warning"); return; }
      download("servis-secili-kayitlar.csv", csv(items));
      return;
    }
    if (action === "bulk-print") {
      if (!ayecServiceListFiltered().some(item => ayecServiceListState.selected.has(String(item.id)))) { toast("Önce servis kay\u0131tlar\u0131n\u0131 se\u00e7in", "warning"); return; }
      const records = ayecServiceListFiltered()
        .filter(item => ayecServiceListState.selected.has(String(item.id)))
        .map(item => { const [customer, service] = findService(item.id); return {customer, service}; })
        .filter(item => item.customer && item.service);
      if (!records.length) { toast("\u00d6nce servis kay\u0131tlar\u0131n\u0131 se\u00e7in", "warning"); return; }
      openServiceBulkPrint(records);
      return;
    }
    if (action === "refresh") { try { await hydrateDesktop(false); render(); } catch (error) { toast(error.message || "Servis listesi yenilenemedi", "error"); } return; }
    if (action === "export") { download("servis-listesi.csv", csv(ayecServiceListFiltered())); return; }
    if (action === "clear") { Object.assign(ayecServiceListState, { tab: "all", query: "", status: "all", date: "all", priority: "all", page: 1 }); render(); return; }
    if (action === "filter") { ayecServiceListState.query = search?.value || ""; ayecServiceListState.page = 1; render(); return; }
    if (action === "print") { window.print(); return; }
    const selectedId = command.dataset.id || [...ayecServiceListState.selected][0];
    if (!selectedId) { toast("\u00d6nce bir servis kayd\u0131 se\u00e7in", "warning"); return; }
    const row = ayecServiceListRows().find(item => String(item.id) === String(selectedId));
    const [customer, service] = findService(selectedId);
    if (action === "dispatch") {
      toast(`Takip No: ${selectedId} i\u00e7in E-\u0130rsaliye mod\u00fcl\u00fc haz\u0131rlan\u0131yor...`, "info");
      return;
    }
    if (!service || !customer) { toast("Servis ayr\u0131nt\u0131s\u0131 bulunamad\u0131", "error"); return; }
    if (action === "invoice") {
      navigate("invoices");
      const input = document.querySelector("#invoiceCustomer");
      if (input) {
        input.value = customer.name || "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return;
    }
    if (action === "row-print") { openServicePrintMenu(customer, service); return; }
    if (action === "payment") {
      paymentDialog(customer);
      setTimeout(() => {
        const reference = document.querySelector('#dialogBody [name="reference"]');
        const description = document.querySelector('#dialogBody [name="description"]');
        if (reference && !reference.value) reference.value = service.no || selectedId;
        if (description) description.value = `Servis tahsilat\u0131 ${service.no || selectedId}`;
      }, 0);
      return;
    }
    if (action === "sms") {
      try { await openServiceSmsDialog(customer, service); }
      catch (error) { toast(error.message || "SMS ekran\u0131 a\u00e7\u0131lamad\u0131.", "error"); }
      return;
    }
    if (action === "status") { openServiceStatusDialog(customer, service); return; }
    if (action === "delete") {
      openDialog("Servis Kayd\u0131n\u0131 Sil", "S\u0130LME ONAYI", `<p>${esc(service.no || selectedId)} kayd\u0131n\u0131 silmek istedi\u011finize emin misiniz?</p><p>Bu i\u015flem geri al\u0131namaz.</p>`, async () => {
        const deviceId = Number(service.id);
        if (!Number.isInteger(deviceId) || deviceId <= 0) { toast("Servis kayd\u0131 kimli\u011fi bulunamad\u0131.", "error"); return false; }
        try {
          await apiFetch("/api/desktop/table/devices", {method:"POST", body:JSON.stringify({id:deviceId,_action:"delete"})});
          customer.services = (customer.services || []).filter(item => String(item.id) !== String(service.id));
          ayecServiceListState.selected.delete(String(selectedId));
          toast("Servis kayd\u0131 silindi.", "warning");
          render();
          return true;
        } catch (error) { toast(error.message || "Servis silinemedi.", "error"); return false; }
      }, "Evet, Sil");
      document.querySelector("#dialogCancel").textContent = "Hay\u0131r";
      document.querySelector("#dialogSubmit").classList.remove("primary");
      document.querySelector("#dialogSubmit").classList.add("danger");
      return;
    }
    if (action === "whatsapp") {
      let phone = String(customer.phone || service.customer_contact || service.phone || "").replace(/\D/g, "");
      if (phone.startsWith("0")) phone = phone.slice(1);
      if (phone.length === 10) phone = `90${phone}`;
      if (!phone) { toast("Telefon numaras\u0131 bulunamad\u0131.", "warning"); return; }
      const message = encodeURIComponent(`Merhaba ${customer.name || "M\u00fc\u015fteri"}, servis kayd\u0131n\u0131z hakk\u0131nda sizinle ileti\u015fime ge\u00e7iyoruz.`);
      window.open(`https://wa.me/${phone}?text=${message}`, "_blank", "noopener");
      return;
    }
    if (action === "cargo") { openServiceCargoReceipt(customer, service); return; }
    if (action === "history") serviceDetailDialog(customer, service);
  };
  content.onchange = event => {
    const checkbox = event.target.closest("[data-service-select]");
    if (checkbox) {
      const id = String(checkbox.dataset.serviceSelect);
      if (checkbox.checked) ayecServiceListState.selected.add(id); else ayecServiceListState.selected.delete(id);
      checkbox.closest("tr")?.classList.toggle("is-selected", checkbox.checked);
    }
    if (event.target.matches("[data-service-select-all]")) {
      visibleRowsForServiceList().forEach(item => event.target.checked
        ? ayecServiceListState.selected.add(String(item.id))
        : ayecServiceListState.selected.delete(String(item.id)));
      render();
    }
  };
};

function openServiceStatusDialog(customer, service) {
  const statuses = ["Bekliyor", "Tamirde", "Par\u00e7a Bekliyor", "Test S\u00fcrecinde", "Haz\u0131r", "Teslim Edildi", "\u0130ptal"];
  const options = statuses.map(status => `<option ${String(service.status || "") === status ? "selected" : ""}>${status}</option>`).join("");
  openDialog("Durum De\u011fi\u015ftir", "SERV\u0130S " + esc(service.no || ""), `<div class="field"><label>Yeni servis durumu</label><select name="status" required>${options}</select></div>`, async formData => {
    const deviceId = Number(service.id);
    if (!Number.isInteger(deviceId) || deviceId <= 0) throw Error("Servis kayd\u0131 kimli\u011fi bulunamad\u0131.");
    const status = String(formData.get("status") || "");
    await apiFetch("/api/desktop/table/devices", {method:"POST", body:JSON.stringify({id:deviceId,status,_action:"update"})});
    service.status = status;
    toast("Durum g\u00fcncellendi: " + status, "success");
    render();
    return true;
  }, "Durumu G\u00fcncelle");
}

async function openServiceSmsDialog(customer, service) {
  const tracking = ayecDashboardId(service);
  const target = await apiFetch("/api/desktop/service-sms/status?tracking_no=" + encodeURIComponent(tracking));
  const templates = [
    ["", "Özel Mesaj Yaz"],
    ["Cihaz\u0131n\u0131z servisimize kabul edilmi\u015ftir. Takip No: {tracking_no}", "Cihaz Al\u0131nd\u0131"],
    ["Cihaz\u0131n\u0131z i\u00e7in fiyat onay\u0131 gerekmektedir. L\u00fctfen ileti\u015fime ge\u00e7iniz.", "Fiyat Onay\u0131 Bekleniyor"],
    ["Cihaz\u0131n\u0131z\u0131n onar\u0131m\u0131 tamamlanm\u0131\u015ft\u0131r. Teslim alabilirsiniz.", "Onar\u0131m Tamamland\u0131"],
    ["Cihaz\u0131n\u0131z i\u00e7in yedek par\u00e7a sipari\u015fi verilmi\u015ftir.", "Yedek Par\u00e7a Bekleniyor"],
    ["Cihaz\u0131n\u0131z iade/iptal edilmi\u015ftir.", "Cihaz \u0130ade / \u0130ptal"]
  ];
  const options = templates.map(([value, label]) => `<option value="${esc(value)}">${label}</option>`).join("");
  openDialog("SMS G\u00f6nder - " + (customer.name || "M\u00fc\u015fteri"), "MÜŞTER\u0130 B\u0130LG\u0130LEND\u0130RME SMS'I", `<div class="form-grid"><div class="field"><label>Al\u0131c\u0131</label><input value="${esc(target.phone || "")}" disabled></div><div class="field"><label>Takip No</label><input value="${esc(tracking)}" disabled></div><div class="field full"><label>Haz\u0131r \u015fablon</label><select id="serviceSmsTemplate">${options}</select></div><div class="field full"><label>Mesaj</label><textarea id="serviceSmsMessage" name="message" rows="5" maxlength="1600" required></textarea><small id="serviceSmsCount">0 karakter</small></div></div>`, async formData => {
    const result = await apiFetch("/api/desktop/service-sms", {method:"POST", body:JSON.stringify({tracking_no:tracking,message:String(formData.get("message") || "").trim()})});
    toast("SMS g\u00f6nderildi" + (result.message_id ? " (" + result.message_id + ")" : ""), "success");
    return true;
  }, "SMS G\u00f6nder");
  const submit = document.querySelector("#dialogSubmit");
  const message = document.querySelector("#serviceSmsMessage");
  const template = document.querySelector("#serviceSmsTemplate");
  const counter = document.querySelector("#serviceSmsCount");
  if (submit) submit.disabled = !target.configured || !target.phone;
  if (!target.configured) toast("SMS servisi yap\u0131land\u0131r\u0131lmam\u0131\u015f veya devre d\u0131\u015f\u0131.", "warning");
  if (!target.phone) toast("Telefon numaras\u0131 bulunamad\u0131.", "warning");
  template?.addEventListener("change", () => { message.value = template.value.replace("{tracking_no}", tracking); counter.textContent = message.value.length + " karakter"; });
  message?.addEventListener("input", () => { counter.textContent = message.value.length + " karakter"; });
}

function openServiceCargoReceipt(customer, service) {
  const settings = desktopSettings || {};
  const tracking = ayecDashboardId(service);
  const sender = {
    name: settings.company_name || db.settings.company || "AYEC Pro",
    cargo: settings.cargo_company || "",
    agreement: settings.cargo_deal_no || "",
    address: settings.company_address || "",
    phone: settings.company_phone || settings.company_gsm || ""
  };
  const receiver = {
    name: customer.name || service.customer_name || "",
    company: customer.company_name || customer.company || "",
    phone: customer.phone || service.customer_contact || "",
    phone2: customer.phone2 || "",
    address: customer.address || customer.full_address || service.customer_address || ""
  };
  const item = [service.brand, service.model].filter(Boolean).join(" ") || service.device || service.device_type || "";
  const date = new Date().toLocaleString("tr-TR");
  const rows = (heading, values) => `<section><h2>${heading}</h2><dl>${values.map(([label, value]) => `<div><dt>${label}</dt><dd>${esc(value || "-")}</dd></div>`).join("")}</dl></section>`;
  const body = `<article class="service-cargo-receipt"><header><strong>KARGO B\u0130LG\u0130LER\u0130</strong><time>${esc(date)}</time><small>Takip No: ${esc(tracking)}</small></header>${rows("GÖNDEREN B\u0130LG\u0130LER\u0130", [["Firma", sender.name], ["Kargo", sender.cargo], ["Anla\u015fma", sender.agreement], ["Adres", sender.address], ["Telefon", sender.phone]])}${rows("ALICI B\u0130LG\u0130LER\u0130", [["Ad Soyad", receiver.name], ["Firma", receiver.company], ["Telefon", receiver.phone], ["Telefon 2", receiver.phone2], ["Cihaz", item], ["Seri No", service.serial || service.serial_no], ["Adres", receiver.address]])}<footer>G\u00f6nderi i\u00e7eri\u011fi servis kayd\u0131ndaki cihaz bilgileridir.</footer></article>`;
  const popup = window.open("", "_blank");
  if (!popup) { toast("Kargo fi\u015fi penceresi taray\u0131c\u0131 taraf\u0131ndan engellendi.", "warning"); return; }
  popup.document.open();
  popup.document.write(`<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Kargo Fi\u015fi ${esc(tracking)}</title><style>@page{size:105mm 150mm;margin:3mm}*{box-sizing:border-box}body{margin:0;color:#111827;font:11px Arial,sans-serif}.service-cargo-receipt{width:99mm;min-height:144mm;padding:3mm;border:1px solid #94a3b8}.service-cargo-receipt header{display:grid;grid-template-columns:1fr auto;gap:3mm;padding-bottom:3mm;border-bottom:1px solid #111827}.service-cargo-receipt header strong{font-size:15px}.service-cargo-receipt header small{grid-column:1/-1;font-weight:700}.service-cargo-receipt section{margin-top:4mm}.service-cargo-receipt h2{margin:0 0 2mm;padding:1.5mm;background:#e2e8f0;font-size:10px}.service-cargo-receipt dl{margin:0}.service-cargo-receipt dl div{display:grid;grid-template-columns:27mm 1fr;gap:2mm;padding:1.2mm 0;border-bottom:1px dotted #cbd5e1}.service-cargo-receipt dt{font-weight:700}.service-cargo-receipt dd{margin:0;overflow-wrap:anywhere}.service-cargo-receipt footer{margin-top:4mm;padding-top:2mm;border-top:1px solid #94a3b8;font-size:9px}@media screen{body{padding:16px;background:#e2e8f0}.service-cargo-receipt{margin:auto;background:#fff;box-shadow:0 4px 18px #0f172a22}}</style></head><body>${body}</body></html>`);
  popup.document.close();
  popup.focus();
  popup.print();
}

function openServicePrintMenu(customer, service) {
  const options = [
    ["short", "K\u0131sa Fi\u015f"], ["detailed", "Detayl\u0131 Fi\u015f Yazd\u0131r"],
    ["cargo", "Kargo Fi\u015fi"], ["label-a", "Cihaz Etiketi A"],
    ["label-b", "Cihaz Etiketi B"], ["form", "Yazd\u0131r"]
  ];
  const buttons = options.map(([key, label]) => `<button type="button" class="service-print-choice" data-print-choice="${key}">${label}</button>`).join("");
  openDialog("Fi\u015f / Yazd\u0131r", "SERV\u0130S YAZDIRMA SE\u00c7ENEKLER\u0130", `<div class="service-print-options">${buttons}</div>`, () => true, "Kapat");
  const dialog = $("#appDialog");
  $$('[data-print-choice]', dialog).forEach(button => button.onclick = () => {
    const choice = button.dataset.printChoice;
    dialog.close();
    runServicePrintChoice(customer, service, choice);
  });
}

function runServicePrintChoice(customer, service, choice) {
  if (choice === "cargo") return openServiceCargoReceipt(customer, service);
  if (choice === "short" || choice === "label-a" || choice === "label-b") return openServiceCompactPrint(customer, service, choice);
  if (choice === "detailed") return openServiceBulkPrint([{customer, service}]);
  if (choice === "form") return serviceDetailDialog(customer, service);
}

function openServiceCompactPrint(customer, service, mode) {
  const tracking = service.no || ayecDashboardId(service);
  const label = mode === "short" ? "K\u0131sa Servis Fi\u015fi" : mode === "label-a" ? "Etiket A" : "Etiket B";
  const size = mode === "short" ? "80mm 120mm" : mode === "label-a" ? "80mm 50mm" : "50mm 30mm";
  const compact = mode === "short";
  const fields = compact
    ? [["M\u00fc\u015fteri", customer.name], ["Telefon", customer.phone || service.customer_contact], ["Cihaz", service.device], ["Seri No", service.serial || service.serial_no], ["Durum", service.status], ["Ar\u0131za", service.fault_description || service.note], ["\u00dccret", money(service.amount || service.price || 0, service.currency || "TRY")]]
    : [["Takip No", tracking], ["M\u00fc\u015fteri", customer.name], ["Cihaz", service.device || [service.brand, service.model].filter(Boolean).join(" ")], ["Seri No", service.serial || service.serial_no]];
  const body = `<article class="service-compact-receipt ${compact ? "compact" : "label"}"><header><strong>${compact ? "AYEC PRO SERV\u0130S F\u0130\u015e\u0130" : "AYEC PRO"}</strong><small>${esc(tracking)}</small></header><dl>${fields.map(([name, value]) => `<div><dt>${name}</dt><dd>${esc(value || "-")}</dd></div>`).join("")}</dl></article>`;
  const popup = window.open("", "_blank");
  if (!popup) { toast("Yazd\u0131rma penceresi taray\u0131c\u0131 taraf\u0131ndan engellendi.", "warning"); return; }
  popup.document.open();
  popup.document.write(`<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>${label} ${esc(tracking)}</title><style>@page{size:${size};margin:3mm}*{box-sizing:border-box}body{margin:0;color:#111827;font:10px Arial,sans-serif}.service-compact-receipt{width:100%;padding:3mm;border:1px solid #64748b}.service-compact-receipt header{display:flex;justify-content:space-between;gap:3mm;padding-bottom:2mm;border-bottom:1px solid #111827;font-size:12px}.service-compact-receipt dl{margin:2mm 0}.service-compact-receipt dl div{display:grid;grid-template-columns:22mm 1fr;gap:2mm;padding:1.2mm 0;border-bottom:1px dotted #cbd5e1}.service-compact-receipt dt{font-weight:700}.service-compact-receipt dd{margin:0;overflow-wrap:anywhere}.label{font-size:8px}.label header{font-size:10px}.label dl div{grid-template-columns:17mm 1fr;padding:.6mm 0}.label dl{margin:1mm 0}@media screen{body{padding:16px;background:#e2e8f0}.service-compact-receipt{margin:auto;width:${size.split(" ")[0]};min-height:${size.split(" ")[1]};background:#fff;box-shadow:0 4px 18px #0f172a22}}</style></head><body>${body}</body></html>`);
  popup.document.close();
  popup.focus();
  popup.print();
}

async function openServicePhotosDialog(customer, service) {
  const tracking = service.no || ayecDashboardId(service);
  openDialog("Foto\u011fraf Galerisi - " + tracking, "C\u0130HAZ FOTO\u011eRAFLARI", '<div class="service-photo-gallery"><div class="field"><label>Foto\u011fraf Ekle</label><input id="servicePhotoFiles" type="file" accept="image/*" multiple><small>Her g\u00f6rsel en fazla 8 MB olabilir.</small></div><p id="servicePhotoStatus" role="status">Foto\u011fraflar y\u00fckleniyor...</p><div id="servicePhotoGrid"></div></div>', () => true, "Kapat");
  const status = $("#servicePhotoStatus"), grid = $("#servicePhotoGrid"), files = $("#servicePhotoFiles");
  const load = async () => {
    const result = await apiFetch("/api/desktop/external-tracking/photos?tracking_no=" + encodeURIComponent(tracking));
    const photos = result.rows || [];
    status.textContent = photos.length ? photos.length + " foto\u011fraf" : "Bu servis kayd\u0131 i\u00e7in foto\u011fraf bulunamad\u0131.";
    grid.innerHTML = photos.map(photo => `<figure><img src="${esc(photo.url || "")}" alt="${esc(photo.photo_label || "Servis foto\u011fraf\u0131")}"><figcaption>${esc(photo.photo_label || "Foto\u011fraf")}<button type="button" data-service-photo-delete="${esc(photo.id)}">Sil</button></figcaption></figure>`).join("");
  };
  try { await load(); } catch (error) { status.textContent = error.message || "Foto\u011fraflar y\u00fcklenemedi."; }
  grid.onclick = async event => {
    const button = event.target.closest("[data-service-photo-delete]");
    if (!button) return;
    openDialog("Servis Foto\u011fraf\u0131n\u0131 Sil", "S\u0130LME ONAYI", "<p>Bu foto\u011fraf silinsin mi?</p>", async () => {
      try { await apiFetch("/api/desktop/external-tracking/photos", {method:"POST",body:JSON.stringify({_action:"delete",id:button.dataset.servicePhotoDelete})}); await load(); return true; }
      catch (error) { toast(error.message || "Foto\u011fraf silinemedi.", "error"); return false; }
    }, "Evet, Sil");
    document.querySelector("#dialogCancel").textContent = "Hay\u0131r";
    document.querySelector("#dialogSubmit").classList.remove("primary");
    document.querySelector("#dialogSubmit").classList.add("danger");
  };
  files.onchange = async () => {
    for (const file of [...files.files]) {
      if (file.size > 8 * 1024 * 1024) { toast(file.name + ": 8 MB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor.", "error"); continue; }
      try {
        const data = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || ""); reader.onerror = () => reject(Error("Dosya okunamad\u0131.")); reader.readAsDataURL(file); });
        await apiFetch("/api/desktop/external-tracking/photos", {method:"POST",body:JSON.stringify({tracking_no:tracking,label:file.name,data})});
        await load();
      } catch (error) { toast(error.message || "Foto\u011fraf eklenemedi.", "error"); }
    }
    files.value = "";
  };
}

const ayecServiceBaseShowContext = showContext;
function serviceContextRolePermissions(){
  const role=userRoleKey(currentAuthUser?.role),admin=userAdminRole(currentAuthUser?.role);
  return {admin,canUpdate:admin||["teknisyen","technician"].includes(role),canTransactions:admin||["muhasebe","accounting"].includes(role)};
}
showContext = function(event, kind, id) {
  if (kind !== "service" || !["service-list", "dashboard"].includes(page)) return ayecServiceBaseShowContext(event, kind, id);
  if (!ayecContextMenuEnabled()) return;
  event.preventDefault();
  const menu = document.createElement("div");
  menu.className = "service-list-context-menu";
  menu.setAttribute("role", "menu");
  const permissions=serviceContextRolePermissions();
  const panelLabel=currentSector==="otomotiv"?"Bak\u0131m / Servis Paneli":"Teknisyen Paneli";
  const formLabel=currentSector==="otomotiv"?"Ara\u00e7 \u0130\u015f Emri":"Servis Formu";
  const closeLabel=currentSector==="otomotiv"?"\u0130\u015f Emrini Kapat":"\u0130\u015flemi Kapat";
  const labels = [
    ["technician", panelLabel], ["form", formLabel], ["edit", "D\u00fczenle"],
    ["customer", "M\u00fc\u015fteri 360\u00b0 Karne"], ["customer-info", "M\u00fc\u015fteri Bilgileri"],
    ["sms", "SMS G\u00f6nder"], ["whatsapp", "WhatsApp"], ["payment", "\u00d6deme Al"], ["photos", "Foto\u011fraflar / Medya"],
    ["print-detailed", "Detayli Fis Yazdir"], ["invoice", "E-Fatura Kes"], ["print-menu", "Fi\u015f / Yazd\u0131r"]
  ];
  const printChoices = [
    ["short", "K\u0131sa Fi\u015f"], ["detailed", "Detayl\u0131 Fi\u015f Yazd\u0131r"],
    ["cargo", "Kargo Fi\u015fi"], ["label-a", "Cihaz Etiketi A"],
    ["label-b", "Cihaz Etiketi B"], ["form", "Yazd\u0131r"]
  ];
  const statuses = currentSector === "otomotiv" ? ["Bekliyor", "Serviste", "Par\u00e7a Bekliyor", "Test S\u00fcrecinde", "Haz\u0131r", "Teslim Edildi", "\u0130ptal"] : ["Bekliyor", "Tamirde", "Par\u00e7a Bekliyor", "Test S\u00fcrecinde", "Haz\u0131r", "Teslim Edildi", "\u0130ptal"];
  const buttonMarkup=([action,label])=>'<button type="button" role="menuitem" data-service-context="'+action+'">'+label+'</button>';
  const firstActions=labels.slice(0,3).filter(([action])=>action==="technician"||permissions.canUpdate).map(buttonMarkup).join("");
  const statusMenuMarkup='<button type="button" role="menuitem" data-service-submenu-trigger="status" aria-haspopup="menu" aria-expanded="false"><span>Durumu De\u011fi\u015ftir</span><span aria-hidden="true">›</span></button>';
  const updateActions=permissions.canUpdate?statusMenuMarkup+'<hr>'+buttonMarkup(["close",closeLabel]):"";
  const customerActions=labels.slice(3,7).filter(([action])=>!(["sms","whatsapp"].includes(action))||permissions.canTransactions).map(buttonMarkup).join("");
  const printMenuMarkup='<button type="button" role="menuitem" data-service-submenu-trigger="print" aria-haspopup="menu" aria-expanded="false"><span>Fi\u015f / Yazd\u0131r</span><span aria-hidden="true">›</span></button>';
  const transactionActions=labels.slice(7,-1).map(buttonMarkup).join("")+printMenuMarkup;
  const deleteAction=permissions.admin?'<hr>'+buttonMarkup(["delete","Sil"]):"";
  menu.innerHTML=firstActions+(permissions.canUpdate?updateActions:"")+'<hr>'+customerActions+'<hr>'+transactionActions+deleteAction;
  document.body.append(menu);
  const printPanel=document.createElement("div");
  printPanel.className="service-list-context-menu service-list-context-submenu-panel";
  printPanel.setAttribute("role","menu");
  printPanel.hidden=true;
  printPanel.innerHTML=printChoices.map(([choice,label])=>'<button type="button" role="menuitem" data-service-print-choice="'+choice+'">'+label+'</button>').join("");
  printPanel.insertAdjacentHTML("afterbegin",'<button type="button" role="menuitem" data-service-submenu-back hidden>Geri</button>');
  document.body.append(printPanel);
  const statusPanel=document.createElement("div");
  statusPanel.className="service-list-context-menu service-list-context-submenu-panel";
  statusPanel.setAttribute("role","menu");
  statusPanel.hidden=true;
  statusPanel.innerHTML=statuses.map(status=>'<button type="button" role="menuitem" data-service-context="status" data-status="'+esc(status)+'">'+esc(status)+'</button>').join("");
  statusPanel.insertAdjacentHTML("afterbegin",'<button type="button" role="menuitem" data-service-submenu-back hidden>Geri</button>');
  document.body.append(statusPanel);
  menu.style.left = Math.max(8, Math.min(event.clientX, innerWidth - menu.offsetWidth - 8)) + "px";
  menu.style.top = Math.max(8, Math.min(event.clientY, innerHeight - menu.offsetHeight - 8)) + "px";
  const close = () => {
    menu.remove();
    printPanel.remove();
    statusPanel.remove();
    document.removeEventListener("pointerdown", outsidePointerDown, true);
  };
  const outsidePointerDown = e => {
    if (!menu.contains(e.target) && !printPanel.contains(e.target) && !statusPanel.contains(e.target)) close();
  };
  document.addEventListener("pointerdown", outsidePointerDown, true);
  menu.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
  printPanel.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
  statusPanel.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
  const printTrigger=menu.querySelector('[data-service-submenu-trigger="print"]');
  const statusTrigger=menu.querySelector('[data-service-submenu-trigger="status"]');
  const placeSubmenu=(trigger,panel)=>{
    const triggerRect=trigger.getBoundingClientRect();
    const panelWidth=panel.offsetWidth;
    const stacked=innerWidth<menu.offsetWidth+panelWidth+24;
    const backButton=panel.querySelector("[data-service-submenu-back]");
    if(backButton)backButton.hidden=!stacked;
    panel.classList.toggle("service-context-stacked",stacked);
    panel.style.width=stacked?Math.max(0,innerWidth-16)+"px":"";
    const panelHeight=panel.offsetHeight;
    const openLeft=triggerRect.right+panelWidth+4>innerWidth-8;
    const menuRect=menu.getBoundingClientRect();
    panel.style.left=stacked?"8px":Math.max(8,openLeft?menuRect.left-panelWidth-4:menuRect.right+4)+"px";
    panel.style.top=Math.max(8,Math.min(triggerRect.top,innerHeight-panelHeight-8))+"px";
  };
  const openPrintPanel=()=>{
    statusPanel.hidden=true;
    statusTrigger?.setAttribute("aria-expanded","false");
    printPanel.hidden=false;
    printTrigger?.setAttribute("aria-expanded","true");
    placeSubmenu(printTrigger,printPanel);
  };
  printTrigger?.addEventListener("pointerenter",openPrintPanel);
  const openStatusPanel=()=>{
    printPanel.hidden=true;
    printTrigger?.setAttribute("aria-expanded","false");
    statusPanel.hidden=false;
    statusTrigger?.setAttribute("aria-expanded","true");
    placeSubmenu(statusTrigger,statusPanel);
  };
  statusTrigger?.addEventListener("pointerenter",openStatusPanel);
  menu.onclick = async e => {
    const submenuTrigger=e.target.closest("[data-service-submenu-trigger]");
    if(submenuTrigger){submenuTrigger.dataset.serviceSubmenuTrigger==="status"?openStatusPanel():openPrintPanel();return}
    const button = e.target.closest("[data-service-context]");
    if (!button) return;
    const action = button.dataset.serviceContext, status = button.dataset.status;
    close();
    const [customer, service] = findService(id);
    if (!customer || !service) return toast("Servis ayr\u0131nt\u0131s\u0131 bulunamad\u0131.", "error");
    const currentPermissions=serviceContextRolePermissions();
    if(["edit","close","status"].includes(action)&&!currentPermissions.canUpdate)return toast("Servis g\u00fcncelleme yetkiniz yok.","error");
    if(["sms","whatsapp"].includes(action)&&!currentPermissions.canTransactions)return toast("\u0130\u015flem ekleme yetkiniz yok.","error");
    if(action==="delete"&&!currentPermissions.admin)return toast("Y\u00f6netici yetkisi gerekiyor.","error");
    if (action === "technician") return technicianDialog(customer, service);
    if (action === "form" || action === "edit") return dashboardServiceEditDialog(customer, service);
    if (action === "close") { openDialog("Servis \u0130\u015flemini Kapat", "TEKN\u0130SYEN PANEL\u0130", "<p>Servis i\u015flemini kapatmak i\u00e7in teknisyen paneli a\u00e7\u0131ls\u0131n m\u0131?</p>", () => { setTimeout(() => technicianDialog(customer, service), 0); return true; }, "Evet, A\u00e7"); document.querySelector("#dialogCancel").textContent = "Hay\u0131r"; return; }
    if (action === "customer" || action === "customer-info") return customer360(customer);
    if (action === "sms") { try { await openServiceSmsDialog(customer, service); } catch (error) { toast(error.message || "SMS ekran\u0131 a\u00e7\u0131lamad\u0131.", "error"); } return; }
    if (action === "whatsapp") { const row = [...document.querySelectorAll('.service-list-table tr[data-kind="service"]')].find(item => item.dataset.id === String(id)); row?.querySelector('[data-service-command="whatsapp"]')?.click(); return; }
    if (action === "payment") return paymentDialog(customer);
    if (action === "photos") { try { await openServicePhotosDialog(customer, service); } catch (error) { toast(error.message || "Foto\u011fraf galerisi a\u00e7\u0131lamad\u0131.", "error"); } return; }
    if (action === "invoice") { navigate("invoices"); setTimeout(() => { const input = $("#invoiceCustomer"); if (input) { input.value = customer.name || ""; input.dispatchEvent(new Event("input", {bubbles:true})); input.dispatchEvent(new Event("change", {bubbles:true})); } }, 0); return; }
    if (action === "print-detailed") return openServiceBulkPrint([{customer, service}]);
    if (action === "delete") return document.querySelector(`.service-list-table tr[data-id="${CSS.escape(String(id))}"] [data-service-command="delete"]`)?.click();
    if (action === "status") {
      const deviceId = Number(service.id);
      if (!Number.isInteger(deviceId) || deviceId <= 0) return toast("Servis kayd\u0131 kimli\u011fi bulunamad\u0131.", "error");
      try { await apiFetch("/api/desktop/table/devices", {method:"POST",body:JSON.stringify({id:deviceId,status,_action:"update"})}); service.status = status; toast("Durum g\u00fcncellendi: " + status, "success"); render(); }
      catch (error) { toast(error.message || "Durum g\u00fcncellenemedi.", "error"); }
    }
  };
  printPanel.onclick=e=>{
    if(e.target.closest("[data-service-submenu-back]")){printPanel.hidden=true;printTrigger?.setAttribute("aria-expanded","false");return}
    const button=e.target.closest("[data-service-print-choice]");
    if(!button)return;
    close();
    const [customer,service]=findService(id);
    if(!customer||!service)return toast("Servis ayr\u0131nt\u0131s\u0131 bulunamad\u0131.","error");
    runServicePrintChoice(customer,service,button.dataset.servicePrintChoice);
  };
  statusPanel.onclick=e=>{
    if(e.target.closest("[data-service-submenu-back]")){statusPanel.hidden=true;statusTrigger?.setAttribute("aria-expanded","false");return}
    menu.onclick(e);
  };
};

document.addEventListener("dblclick",event=>{
  const serviceRow=event.target.closest(".service-list-table tbody tr[data-kind=service]");
  if(serviceRow&&db.settings.doubleClick){
    const [customer,service]=findService(serviceRow.dataset.id);if(!customer||!service)return;
    event.preventDefault();event.stopImmediatePropagation();return technicianDialog(customer,service);
  }
  if(page!=="dashboard"||!db.settings.doubleClick)return;
  const row=event.target.closest(".dashboard-service-table tbody tr[data-kind=service]"),recent=event.target.closest(".dashboard-recent-row[data-action=service-detail]");if(!row&&!recent||row&&event.target.closest("button"))return;
  const cell=event.target.closest("td"),column=cell?.cellIndex;if(row&&column==null)return;
  const [customer,service]=findService(row?.dataset.id||recent.dataset.id);if(!customer||!service)return;
  event.preventDefault();event.stopImmediatePropagation();
  if(recent)return dashboardServiceEditDialog(customer,service);
  if(column===2)return customer360(customer);
  if(column===5||currentSector==="otomotiv"||[1,3].includes(column))return technicianDialog(customer,service);
  return dashboardServiceEditDialog(customer,service);
},true);

document.addEventListener("contextmenu",event=>{
  if(page!=="dashboard")return;
  const recent=event.target.closest(".dashboard-recent-row[data-action=service-detail]");if(!recent)return;
  showContext(event,"service",recent.dataset.id);
},true);
document.addEventListener("keydown",event=>{
  if(page!=="dashboard"||!(event.key==="ContextMenu"||(event.shiftKey&&event.key==="F10")))return;
  const recent=event.target.closest(".dashboard-recent-row[data-action=service-detail]");if(!recent)return;
  event.preventDefault();const box=recent.getBoundingClientRect();showContext({preventDefault(){},clientX:box.left+24,clientY:box.top+24,currentTarget:recent},"service",recent.dataset.id);
},true);

const ayecDashboardContextMenuBase=showContext;
showContext=function(event,kind,id){
  const dashboardContext=kind==="service"&&page==="dashboard";
  ayecDashboardContextMenuBase(event,kind,id);
  if(!dashboardContext)return;
  const menu=[...document.querySelectorAll(".service-list-context-menu:not(.service-list-context-submenu-panel)")].at(-1);if(!menu)return;
  const baseClick=menu.onclick;
  menu.onclick=async event=>{
    const button=event.target.closest("[data-service-context]");if(!button)return;
    const action=button.dataset.serviceContext;if(action!=="whatsapp"&&action!=="delete")return baseClick?.call(menu,event);
    menu.remove();const [customer,service]=findService(id);if(!customer||!service)return toast("Servis ayr\u0131nt\u0131s\u0131 bulunamad\u0131.","error");
    if(action==="whatsapp"){let phone=String(customer.phone||service.customer_contact||service.phone||"").replace(/\D/g,"");if(phone.startsWith("0"))phone=phone.slice(1);if(phone.length===10)phone=`90${phone}`;if(!phone)return toast("Telefon numaras\u0131 bulunamad\u0131.","warning");const message=encodeURIComponent(`Merhaba ${customer.name||"M\u00fc\u015fteri"}, servis kayd\u0131n\u0131z hakk\u0131nda sizinle ileti\u015fime ge\u00e7iyoruz.`);window.open(`https://wa.me/${phone}?text=${message}`,"_blank","noopener");return}
    openDialog("Servis Kayd\u0131n\u0131 Sil","S\u0130LME ONAYI",`<p>${esc(service.no||id)} kayd\u0131n\u0131 silmek istedi\u011finize emin misiniz?</p><p>Bu i\u015flem geri al\u0131namaz.</p>`,async()=>{const deviceId=Number(service.id);if(!Number.isInteger(deviceId)||deviceId<=0){toast("Servis kayd\u0131 kimli\u011fi bulunamad\u0131.","error");return false}try{await apiFetch("/api/desktop/table/devices",{method:"POST",body:JSON.stringify({id:deviceId,_action:"delete"})});customer.services=(customer.services||[]).filter(item=>String(item.id)!==String(service.id));toast("Servis kayd\u0131 silindi.","warning");render();return true}catch(error){toast(error.message||"Servis silinemedi.","error");return false}},"Evet, Sil");document.querySelector("#dialogCancel").textContent="Hay\u0131r";document.querySelector("#dialogSubmit").classList.remove("primary");document.querySelector("#dialogSubmit").classList.add("danger");return
  };
};

function visibleRowsForServiceList() {
  const start = (ayecServiceListState.page - 1) * ayecServiceListState.pageSize;
  return ayecServiceListFiltered().slice(start, start + ayecServiceListState.pageSize);
}

function openServiceBulkPrint(records) {
  const slips = records.map(({customer, service}) => {
    const tracking = service.no || ayecDashboardId(service);
    const parts = (service.used_parts || []).map(part => `<li>${esc(part.part_name)} x ${Number(part.quantity || 1)}</li>`).join("");
    return `<article class="service-bulk-slip"><header><strong>AYEC PRO SERV\u0130S F\u0130\u015e\u0130</strong><span>${esc(tracking)}</span></header><dl><div><dt>M\u00fc\u015fteri</dt><dd>${esc(customer.name || "-")}</dd></div><div><dt>Telefon</dt><dd>${esc(customer.phone || service.customer_contact || "-")}</dd></div><div><dt>Cihaz / Ara\u00e7</dt><dd>${esc(service.device || [service.brand, service.model].filter(Boolean).join(" ") || "-")}</dd></div><div><dt>Seri No / Plaka</dt><dd>${esc(service.serial || service.plate || "-")}</dd></div><div><dt>Giri\u015f Tarihi</dt><dd>${esc(service.date || service.entry_date || "-")}</dd></div><div><dt>Tahmini Teslim</dt><dd>${esc(service.delivery || service.estimated_date || "-")}</dd></div><div><dt>Durum</dt><dd>${esc(service.status || "Bekliyor")}</dd></div><div><dt>Teknisyen</dt><dd>${esc(service.technician || "-")}</dd></div><div><dt>Ar\u0131za / Talep</dt><dd>${esc(service.fault_description || service.note || "-")}</dd></div><div><dt>Yap\u0131lan \u0130\u015flem</dt><dd>${esc(service.repair_details || "-")}</dd></div><div><dt>\u00dccret</dt><dd>${money(service.amount || service.price || service.labor_cost || 0, service.currency || "TRY")}</dd></div><div><dt>\u00d6deme</dt><dd>${esc(service.payment_status || "Beklemede")}</dd></div></dl><strong>Kullan\u0131lan Par\u00e7alar</strong><ul>${parts || "<li>Par\u00e7a kullan\u0131lmad\u0131</li>"}</ul><footer>\u0130mza: ____________________</footer></article>`;
  }).join("");
  openDialog("Se\u00e7ili Servis Fi\u015fleri", "TOPLU SERV\u0130S \u00c7IKTISI", `<div class="service-bulk-print">${slips}</div>`, () => true, "Kapat");
  const dialog = $("#appDialog");
  dialog.classList.add("dialog-wide", "service-print-dialog");
  document.body.classList.add("service-form-open");
  dialog.addEventListener("close", () => { dialog.classList.remove("dialog-wide", "service-print-dialog"); document.body.classList.remove("service-form-open"); }, {once:true});
  $("#dialogFooter").innerHTML = '<button type="button" class="secondary" id="serviceBulkPrintClose">Kapat</button><button type="button" class="primary" id="serviceBulkPrintAction">Yazd\u0131r / PDF</button>';
  $("#serviceBulkPrintClose").onclick = () => dialog.close();
  $("#serviceBulkPrintAction").onclick = () => window.print();
}

const ayecServiceMenu = ayecSectorMenuModels.teknik_servis
  .flatMap(group => group.items)
  .find(item => item.id === "service-parent");
if (ayecServiceMenu && !ayecServiceMenu.children.some(item => item.id === "service-list")) {
  ayecServiceMenu.children.splice(0, 0, { id: "service-list", label: "Servis Listesi" });
}
if (typeof titles !== "undefined") titles["service-list"] = ["Servis Y\u00f6netimi", "Servis Listesi"];
if (typeof renderNav === "function") renderNav();
