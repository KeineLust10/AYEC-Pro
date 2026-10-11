// Service list reference route for desktop web and mobile layouts.
const ayecServiceListState = {
  tab: "all", query: "", status: "all", date: "all", priority: "all",
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

function ayecServiceListFiltered() {
  const state = ayecServiceListState;
  const query = state.query.toLocaleLowerCase("tr-TR");
  return ayecServiceListRows().filter(item => {
    if (!ayecServiceListMatchTab(item, state.tab)) return false;
    if (state.status !== "all" && serviceStatusKey(item) !== state.status) return false;
    if (state.priority !== "all" && String(item.priority || item.urgency || "Normal") !== state.priority) return false;
    if (state.date !== "all") {
      const days = (Date.now() - new Date(item.entry).getTime()) / 86400000;
      if (!Number.isFinite(days) || days < 0 || days > Number(state.date)) return false;
    }
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
    return `<tr data-kind="service" data-id="${esc(item.id)}" data-customer="${esc(item.customerId || item.customer_id || "")}">
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
        <button type="button" data-service-command="print" data-id="${esc(item.id)}" title="Fi\u015f yazd\u0131r" aria-label="Fi\u015f yazd\u0131r">&#9113;</button>
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
    <header class="service-list-heading"><div><span class="service-list-heading-icon">&#9881;</span><div><h1>Servis Listesi</h1><p>T\u00fcm teknik servis ve onar\u0131m kay\u0131tlar\u0131n\u0131 tek ekrandan y\u00f6netin, filtreleyin ve raporlay\u0131n.</p></div></div><div class="service-list-heading-actions"><button type="button" class="secondary" data-service-command="refresh">&#8635; Yenile</button><button type="button" class="secondary" data-service-command="history">&#9719; Servis Ge\u00e7mi\u015fi</button><button type="button" class="secondary" data-service-command="export">&#8681; D\u0131\u015fa Aktar</button><button type="button" class="primary" data-action="new-service">+ Yeni Cihaz Kayd\u0131</button></div></header>
    <section class="service-list-metrics">${metricHTML}</section>
    <nav class="service-list-tabs" aria-label="Servis kategorileri">${tabs}</nav>
    <section class="service-list-filters"><input id="serviceListSearch" type="search" value="${esc(ayecServiceListState.query)}" placeholder="Takip no, m\u00fc\u015fteri veya cihaz ara..." aria-label="Servis ara"><select id="serviceListStatus" aria-label="Durum filtresi"><option value="all">Durum: T\u00fcm\u00fc</option>${[["bekliyor","Bekliyor"],["tamirde","Tamirde"],["parca","Par\u00e7a Bekliyor"],["kargo","Kargoda"],["teslim","Teslim Edildi"]].map(([key,label])=>`<option value="${key}" ${ayecServiceListState.status === key ? "selected" : ""}>${label}</option>`).join("")}</select><select id="serviceListDate" aria-label="Tarih aral\u0131\u011f\u0131"><option value="all">Tarih Aral\u0131\u011f\u0131: T\u00fcm\u00fc</option><option value="30" ${ayecServiceListState.date === "30" ? "selected" : ""}>Son 30 G\u00fcn</option><option value="7" ${ayecServiceListState.date === "7" ? "selected" : ""}>Son 7 G\u00fcn</option></select><select id="serviceListPriority" aria-label="\u00d6ncelik filtresi"><option value="all">\u00d6ncelik: T\u00fcm</option><option value="Normal" ${ayecServiceListState.priority === "Normal" ? "selected" : ""}>Normal</option><option value="Acil" ${ayecServiceListState.priority === "Acil" ? "selected" : ""}>Acil</option></select><button type="button" class="primary" data-service-command="filter">Filtrele</button><button type="button" class="secondary" data-service-command="clear">Temizle</button></section>
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
    if (action === "refresh") { try { await hydrateDesktop(false); render(); } catch (error) { toast(error.message || "Servis listesi yenilenemedi", "error"); } return; }
    if (action === "export") { download("servis-listesi.csv", csv(ayecServiceListFiltered())); return; }
    if (action === "clear") { Object.assign(ayecServiceListState, { tab: "all", query: "", status: "all", date: "all", priority: "all", page: 1 }); render(); return; }
    if (action === "filter") { ayecServiceListState.query = search?.value || ""; ayecServiceListState.page = 1; render(); return; }
    if (action === "print") { window.print(); return; }
    const selectedId = command.dataset.id || [...ayecServiceListState.selected][0];
    if (!selectedId) { toast("\u00d6nce bir servis kayd\u0131 se\u00e7in", "warning"); return; }
    const row = ayecServiceListRows().find(item => String(item.id) === String(selectedId));
    const [customer, service] = findService(selectedId);
    if (!service || !customer) { toast("Servis ayr\u0131nt\u0131s\u0131 bulunamad\u0131", "error"); return; }
    if (["history", "cargo", "dispatch", "invoice", "whatsapp"].includes(action)) {
      serviceDetailDialog(customer, service);
    }
  };
  content.onchange = event => {
    const checkbox = event.target.closest("[data-service-select]");
    if (checkbox) {
      const id = String(checkbox.dataset.serviceSelect);
      if (checkbox.checked) ayecServiceListState.selected.add(id); else ayecServiceListState.selected.delete(id);
    }
    if (event.target.matches("[data-service-select-all]")) {
      visibleRowsForServiceList().forEach(item => event.target.checked
        ? ayecServiceListState.selected.add(String(item.id))
        : ayecServiceListState.selected.delete(String(item.id)));
      render();
    }
  };
};

function visibleRowsForServiceList() {
  const start = (ayecServiceListState.page - 1) * ayecServiceListState.pageSize;
  return ayecServiceListFiltered().slice(start, start + ayecServiceListState.pageSize);
}

const ayecServiceMenu = ayecSectorMenuModels.teknik_servis
  .flatMap(group => group.items)
  .find(item => item.id === "service-parent");
if (ayecServiceMenu && !ayecServiceMenu.children.some(item => item.id === "service-list")) {
  ayecServiceMenu.children.splice(0, 0, { id: "service-list", label: "Servis Listesi" });
}
if (typeof titles !== "undefined") titles["service-list"] = ["Servis Y\u00f6netimi", "Servis Listesi"];
if (typeof renderNav === "function") renderNav();
