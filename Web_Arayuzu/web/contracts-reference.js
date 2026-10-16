(function () {
  "use strict";

  const baseGenericTable = window.genericTable;
  let contractPage = 0;
  const contractPageSize = 4;

  function contractDaysUntil(value) {
    const match = String(value || "").slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return null;
    const target = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    const today = new Date();
    target.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);
    return Math.round((target.getTime() - today.getTime()) / 86400000);
  }

  function contractTodayKey() {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  }

  function contractMoney(value) {
    const setting = String(db.settings?.currency || db.settings?.default_currency || "TRY").toUpperCase();
    const code = setting.includes("USD") || setting.includes("$") ? "USD" : setting.includes("EUR") || setting.includes("\u20ac") ? "EUR" : "TRY";
    const symbol = code === "USD" ? "$" : code === "EUR" ? "\u20ac" : "\u20ba";
    const configuredPrecision = Number.parseInt(db.settings?.currency_precision || "2", 10);
    const precision = Number.isFinite(configuredPrecision) ? Math.min(3, Math.max(0, configuredPrecision)) : 2;
    const amount = Number(value || 0);
    return `${new Intl.NumberFormat("en-US", { minimumFractionDigits: precision, maximumFractionDigits: precision }).format(Number.isFinite(amount) ? amount : 0)} ${symbol}`;
  }

  function contractSearchKey(value) {
    return String(value || "").trim().toLocaleLowerCase("tr-TR").replace(/\u0131/g, "i").normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
  }

  function contractCategories(row) {
    const status = String(row.status || "").toLocaleLowerCase("tr-TR");
    const days = contractDaysUntil(row.end_date);
    const draft = status.includes("taslak") || status.includes("draft");
    const expired = days !== null && days < 0;
    return {
      active: status.includes("aktif") && !expired && !draft,
      renewal: !expired && !draft && (status.includes("yenileme") || (days !== null && days >= 0 && days <= 30)),
      expired,
      draft,
    };
  }

  function contractRows(meta, data) {
    const source = Array.isArray(data.rows) ? data.rows : [];
    const status = document.querySelector("[data-contract-status].active")?.dataset.contractStatus || "all";
    const type = document.querySelector("#contractType")?.value || "all";
    const query = contractSearchKey(document.querySelector("#genericSearch")?.value || "");
    const customerNames = new Map((Array.isArray(db.customers) ? db.customers : []).map((item) => [String(item.id), item.name || item.company_name || ""]));
    const rows = source.map((row, index) => ({ row, index })).filter(({ row }) => {
      const rowType = String(row.contract_type || "").toLocaleLowerCase();
      const categories = contractCategories(row);
      const sla = document.querySelector("#contractSla")?.value || "all";
      const rowSla = String(row.contract_type || "").toLocaleLowerCase();
      if (type !== "all" && rowType !== type.toLocaleLowerCase()) return false;
      if (sla !== "all" && rowSla !== sla.toLocaleLowerCase()) return false;
      if (status === "active" && !categories.active) return false;
      if (status === "renewal" && !categories.renewal) return false;
      if (status === "expired" && !categories.expired) return false;
      if (status === "draft" && !categories.draft) return false;
      if (!query) return true;
      const year = String(row.start_date || "").slice(0, 4) || "0000";
      const id = Number.parseInt(row.id, 10);
      const contractNo = `AGR-${year}-${String(Number.isFinite(id) ? id : 0).padStart(3, "0")}`;
      const customer = row.customer_name || customerNames.get(String(row.customer_id)) || row.customer_id || "-";
      const customerLine = `${customer}\n${row.title || ""}`.replace(/\s+$/, "");
      const validity = [row.start_date || "", row.end_date || ""].filter(Boolean).join("\n");
      const days = contractDaysUntil(row.end_date);
      const remaining = days === null ? "-" : days < 0 ? `${Math.abs(days)} G\u00fcn Ge\u00e7ti` : `${days} G\u00fcn Kald\u0131`;
      const values = [contractNo, customerLine, row.contract_type || "-", validity, remaining, contractMoney(row.price), row.description || "-", "-", row.status || "-"];
      return values.some((value) => contractSearchKey(value).includes(query));
    });
    rows.sort((left, right) => String(left.row.end_date || "").localeCompare(String(right.row.end_date || "")));
    const pageCount = Math.max(1, Math.ceil(rows.length / contractPageSize));
    contractPage = Math.min(contractPage, pageCount - 1);
    return { rows: rows.slice(contractPage * contractPageSize, (contractPage + 1) * contractPageSize), total: rows.length, pageCount, source };
  }

  function contractTable(meta, data) {
    const { rows, total, pageCount } = contractRows(meta, data);
    const source = Array.isArray(data.rows) ? data.rows : [];
    const activeCount = source.filter((item) => contractCategories(item).active).length;
    const renewalCount = source.filter((item) => contractCategories(item).renewal).length;
    const metricValues = document.querySelectorAll(".contracts-reference-metrics .metric strong");
    if (metricValues.length >= 4) {
      metricValues[0].textContent = String(activeCount);
      metricValues[1].textContent = String(renewalCount);
      metricValues[2].textContent = contractMoney(source.reduce((sum, item) => sum + Number(item.price || 0), 0));
      metricValues[3].textContent = String(source.length);
    }
    const chipCounts = {
      all: source.length,
      active: activeCount,
      renewal: renewalCount,
      expired: source.filter((item) => contractCategories(item).expired).length,
      draft: source.filter((item) => contractCategories(item).draft).length,
    };
    document.querySelectorAll("[data-contract-status]").forEach((button) => {
      const label = button.dataset.contractStatus === "all" ? "T\u00fcm\u00fc" : button.dataset.contractStatus === "active" ? "Aktif" : button.dataset.contractStatus === "renewal" ? "Yenileme Bekleyen" : button.dataset.contractStatus === "expired" ? "S\u00fcresi Dolanlar" : "Taslaklar";
      button.textContent = `${label} (${chipCounts[button.dataset.contractStatus] || 0})`;
    });
    const slaSelect = document.querySelector("#contractSla");
    if (slaSelect) {
      const selectedSla = slaSelect.value;
      const levels = [...new Set(source.map((item) => String(item.contract_type || "").trim()).filter(Boolean))];
      slaSelect.innerHTML = `<option value="all">SLA Seviyesi: T\u00fcm\u00fc</option>${levels.map((level) => `<option value="${esc(level)}">${esc(level)}</option>`).join("")}`;
      slaSelect.value = levels.includes(selectedSla) ? selectedSla : "all";
      slaSelect.disabled = levels.length === 0;
    }
    const customerNames = new Map((Array.isArray(db.customers) ? db.customers : []).map((item) => [String(item.id), item.name || item.company_name || ""]));
    const columns = [
      ["contractNo", "S\u00d6ZLE\u015eME NO"], ["customer", "M\u00dc\u015eTER\u0130 / KURUM"],
      ["type", "SLA"], ["validity", "GE\u00c7ERL\u0130L\u0130K"], ["remaining", "KALAN S\u00dcRE"],
      ["price", "YILLIK HAC\u0130M"], ["devicePark", "C\u0130HAZ / PARK"],
      ["periodic", "PER\u0130YOD\u0130K"], ["status", "DURUM"],
    ];
    const body = rows.map(({ row, index }) => {
      const customer = row.customer_name || customerNames.get(String(row.customer_id)) || row.customer_id || "-";
      const year = String(row.start_date || "").slice(0, 4) || "0000";
      const id = Number.parseInt(row.id, 10);
      const contractNo = `AGR-${year}-${String(Number.isFinite(id) ? id : 0).padStart(3, "0")}`;
      const customerLine = `${customer}\n${row.title || ""}`.replace(/\s+$/, "");
      const validity = [row.start_date || "", row.end_date || ""].filter(Boolean).join("\n");
      const days = contractDaysUntil(row.end_date);
      const remaining = days === null ? "-" : days < 0 ? `${Math.abs(days)} G\u00fcn Ge\u00e7ti` : `${days} G\u00fcn Kald\u0131`;
      const values = [contractNo, customerLine || "-", row.contract_type || "-", validity || "-", remaining, contractMoney(row.price), row.description || "-", "-", row.status || "-"];
      return `<tr tabindex="0" data-kind="generic" data-id="${index}" data-contract-id="${esc(row.id)}" data-generic-row="${index}">${values.map((value, i) => `<td data-label="${columns[i][1]}">${contractCell(value, i, days, row)}</td>`).join("")}<td data-label="\u0130\u015eLEMLER"><button type="button" class="mini" data-contract-detail="${esc(row.id)}">A\u00e7</button> <button class="mini generic-edit" data-index="${index}">D\u00fczenle</button> <button class="mini generic-delete" data-index="${index}">Sil</button></td></tr>`;
    }).join("");
    const host = document.querySelector("#genericHost");
    if (host) host.dataset.visibleCount = String(rows.length);
    const count = document.querySelector("#genericCount");
    if (count) count.textContent = `${total ? contractPage * contractPageSize + 1 : 0}-${Math.min((contractPage + 1) * contractPageSize, total)} / ${total} s\u00f6zle\u015fme`;
    const pageLabel = document.querySelector("[data-contract-page-label]");
    if (pageLabel) pageLabel.textContent = `${contractPage + 1} / ${pageCount}`;
    document.querySelector('[data-contract-page="-1"]')?.toggleAttribute("disabled", contractPage <= 0);
    document.querySelector('[data-contract-page="1"]')?.toggleAttribute("disabled", contractPage >= pageCount - 1);
    if (!rows.length) return empty("Kay\u0131t bulunamad\u0131", "Se\u00e7ili filtrelerle e\u015fle\u015fen s\u00f6zle\u015fme yok.");
    return `<div class="table-wrap contracts-reference-table-wrap"><table class="contracts-reference-table"><thead><tr>${columns.map(([, label]) => `<th>${label}</th>`).join("")}<th>\u0130\u015eLEMLER</th></tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function contractCell(value, index, days, row) {
    if (index === 8) {
      const categories = contractCategories(row);
      const state = categories.renewal || categories.expired ? "renewal" : categories.active ? "active" : "draft";
      return `<span class="contract-status-badge is-${state}">${esc(value || "-")}</span>`;
    }
    if (index === 4) {
      const state = days !== null && days <= 30 ? "urgent" : "safe";
      return `<span class="contract-remaining is-${state}">${esc(value)}</span>`;
    }
    return `<span style="white-space:pre-line">${esc(value)}</span>`;
  }

  window.genericTable = function (meta, data) {
    return meta?.table === "contracts" ? contractTable(meta, data) : baseGenericTable(meta, data);
  };

  const loadGenericBeforeContractPaging = loadGenericModule;
  const contractLoadPromises = new Map();
  let contractDataCache = null;
  let contractDataCacheQuery = null;
  function confirmContractDelete(meta,row) {
    const title=String(row?.title||row?.contract_name||"");
    openDialog("S\u00f6zle\u015fmeyi Sil","S\u0130LME ONAYI",`<p><strong>${esc(title)}</strong> s\u00f6zle\u015fmesini ve t\u00fcm eklerini silmek istedi\u011finize emin misiniz?</p><p>Bu i\u015flem geri al\u0131namaz.</p>`,async()=>{
      try {
        await apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify({id:row.id,_action:"delete"})});
        toast("Kay\u0131t silindi","warning");
        contractDataCache=null;
        contractDataCacheQuery=null;
        await loadGenericModule(meta,document.querySelector("#genericSearch")?.value||"");
        return true;
      } catch(error) {
        toast(error.message||"S\u00f6zle\u015fme silinemedi","error");
        return false;
      }
    },"Evet, Sil");
    document.querySelector("#dialogCancel").textContent="Hay\u0131r";
    document.querySelector("#dialogSubmit").classList.remove("primary");
    document.querySelector("#dialogSubmit").classList.add("danger");
  }
  document.addEventListener("click", (event) => {
    if (document.body.dataset.page !== "contracts" || !event.target.closest("[data-generic-add],.generic-edit,.generic-delete,[data-contract-delete]")) return;
    contractDataCache = null;
    contractDataCacheQuery = null;
  }, true);
  function renderContractData(meta, data) {
    if (document.body.dataset.page !== "contracts") return;
    const host = document.querySelector("#genericHost");
    if (!host) return;
    window.currentGenericData = data;
    window.currentGenericMeta = meta;
    host.innerHTML = data.rows.length ? genericTable(meta, data) : empty("Kay\u0131t bulunamad\u0131", "Masa\u00fcst\u00fc veritaban\u0131nda bu mod\u00fcle ait kay\u0131t yok.");
    const countLabel = document.querySelector("#genericCount");
    if (countLabel && !data.rows.length) countLabel.textContent = `Toplam Kay\u0131t: ${data.count}`;
    document.querySelectorAll(".generic-edit").forEach((button) => button.onclick = () => openGenericDialog(meta, data.rows[Number(button.dataset.index)], data.columns));
    document.querySelectorAll(".generic-delete").forEach((button) => button.onclick = () => confirmContractDelete(meta,data.rows[Number(button.dataset.index)]));
    document.querySelectorAll("[data-generic-row]").forEach((row) => {
      bindInteractiveRow(row);
    });
  }
  loadGenericModule = async function (meta, query = "") {
    if (meta?.table !== "contracts") return loadGenericBeforeContractPaging(meta, query);
    const key = "";
    if (contractDataCache && contractDataCacheQuery === key) {
      renderContractData(meta, contractDataCache);
      return;
    }
    if (contractLoadPromises.has(key)) return contractLoadPromises.get(key);
    const pending = (async () => {
      if (!document.querySelector("#genericHost")) return;
      try {
        const limit = 1000;
        let first = null;
        let count = 0;
        const allRows = [];
        do {
          const offset = allRows.length;
          const pageData = await apiFetch(`/api/desktop/table/contracts?limit=${limit}&offset=${offset}&q=${encodeURIComponent(key)}`);
          if (!first) first = pageData;
          allRows.push(...(Array.isArray(pageData.rows) ? pageData.rows : []));
          count = Math.max(0, Number(pageData.count) || allRows.length);
          if (!pageData.rows?.length || allRows.length >= count) break;
        } while (allRows.length < count);
        if (document.body.dataset.page !== "contracts") return;
        const data = {...(first || {}), rows: allRows, count};
        contractDataCache = data;
        contractDataCacheQuery = key;
        renderContractData(meta, data);
      } catch (error) {
        const host = document.querySelector("#genericHost");
        if (document.body.dataset.page === "contracts" && host) host.innerHTML = empty("Mod\u00fcl y\u00fcklenemedi", error.message);
      }
    })();
    contractLoadPromises.set(key, pending);
    try {
      await pending;
    } finally {
      if (contractLoadPromises.get(key) === pending) contractLoadPromises.delete(key);
    }
  };

  window.renderContractsReference = function () {
    const contracts = Array.isArray(db.contracts) ? db.contracts : [];
    const active = contracts.filter((item) => /aktif/i.test(String(item.status || ""))).length;
    const renewal = contracts.filter((item) => /yenile/i.test(String(item.status || ""))).length;
    const volume = contracts.reduce((sum, item) => sum + Number(item.price || 0), 0);
    const typeOptions = ["SLA", "Bak\u0131m", "Lisans", "Di\u011fer"];
    return `${pageHead("S\u00f6zle\u015fme Y\u00f6netimi", "Kurumsal bak\u0131m anla\u015fmalar\u0131n\u0131, SLA taahh\u00fctlerini ve yenileme takibini y\u00f6netin.", '<button class="secondary" type="button" data-contract-plan>Periyodik Bak\u0131m Planla</button><button class="secondary" type="button" data-contract-export>Excel Raporu</button><button class="secondary" type="button" data-generic-refresh>Yenile</button><button class="secondary danger" type="button" data-contract-delete>S\u00f6zle\u015fme Sil</button><button class="primary" type="button" data-generic-add>+ Yeni S\u00f6zle\u015fme</button>')}<div class="metric-grid contracts-reference-metrics">${metric("Aktif S\u00f6zle\u015fmeler", active, "Y\u00fcr\u00fcrl\u00fckte olan kurumsal SLA", "\u2713")}${metric("Yakla\u015fan Yenilemeler", renewal, "30 g\u00fcn i\u00e7inde bitecekler", "\u25f7")}${metric("S\u00f6zle\u015fme Hacmi", money(volume, "TRY"), "Kay\u0131tl\u0131 s\u00f6zle\u015fme bedelleri", "\u20ba")}${metric("Ortalama SLA Yan\u0131t S\u00fcresi", "-", "SLA \u00f6l\u00e7\u00fcm\u00fc bekleniyor", "\u231b")}</div><section class="card contracts-reference-list"><div class="contracts-reference-status" role="group" aria-label="S\u00f6zle\u015fme durumu">${[["all", "T\u00fcm\u00fc"], ["active", "Aktif"], ["renewal", "Yenileme Bekleyen"], ["expired", "S\u00fcresi Dolanlar"], ["draft", "Taslaklar"]].map(([value, label], index) => `<button class="secondary${index === 0 ? " active" : ""}" type="button" data-contract-status="${value}">${label}</button>`).join("")}</div><div class="toolbar contracts-reference-filters"><input class="control search" id="genericSearch" placeholder="S\u00f6zle\u015fme, m\u00fc\u015fteri veya ba\u015fl\u0131k ara" aria-label="S\u00f6zle\u015fme ara"><select class="control" id="contractType" aria-label="S\u00f6zle\u015fme t\u00fcr\u00fc"><option value="all">T\u00fcm t\u00fcrler</option>${typeOptions.map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join("")}</select><select class="control" id="contractSla" aria-label="SLA seviyesi"><option value="all">SLA Seviyesi: T\u00fcm\u00fc</option></select><span class="muted" id="genericCount">S\u00f6zle\u015fmeler y\u00fckleniyor</span></div><div id="genericHost">${empty("S\u00f6zle\u015fmeler y\u00fckleniyor", "Masa\u00fcst\u00fc veritaban\u0131 okunuyor.")}</div><div class="contracts-reference-pager"><span class="muted">Sayfa ba\u015f\u0131na ${4}</span><div><button class="secondary" type="button" data-contract-page="-1" disabled>&lt;</button><span data-contract-page-label>1 / 1</span><button class="secondary" type="button" data-contract-page="1" disabled>&gt;</button></div></div></section>`;
  };

  function bindContractControls() {
    if (document.body.dataset.page !== "contracts") return;
    const meta = genericModules.contracts;
    const search = document.querySelector("#genericSearch");
    const reload = () => loadGenericModule(meta, search?.value || "");
    const add = document.querySelector("[data-generic-add]");
    if (add) add.onclick = async () => {
      try {
        const customers = [];
        let count = 0;
        do {
          const data = await apiFetch(`/api/desktop/table/customers?limit=1000&offset=${customers.length}`);
          customers.push(...(Array.isArray(data.rows) ? data.rows : []));
          count = Math.max(0, Number(data.count) || customers.length);
          if (!data.rows?.length || customers.length >= count) break;
        } while (customers.length < count);
        openContractCreateDialog(meta, customers);
      } catch (error) {
        toast(error.message || "M\u00fc\u015fteriler y\u00fcklenemedi", "error");
      }
    };
    document.querySelectorAll("[data-generic-refresh]").forEach((button) => button.onclick = () => {
      contractDataCache = null;
      contractDataCacheQuery = null;
      contractPage = 0;
      reload();
    });
    document.querySelectorAll("[data-contract-status]").forEach((button) => {
      button.onclick = () => {
        document.querySelectorAll("[data-contract-status]").forEach((item) => item.classList.toggle("active", item === button));
        reload();
      };
    });
    document.querySelector("#contractType")?.addEventListener("change", () => { contractPage = 0; reload(); });
    document.querySelector("#contractSla")?.addEventListener("change", () => { contractPage = 0; reload(); });
    document.querySelectorAll("[data-contract-page]").forEach((button) => button.onclick = () => {
      contractPage = Math.max(0, contractPage + Number(button.dataset.contractPage));
      reload();
    });
    document.querySelector("[data-contract-plan]")?.addEventListener("click", () => navigate("appointments"));
    document.querySelector("[data-contract-delete]")?.addEventListener("click", () => {
      const selected = document.querySelector("#genericHost tr.is-selected[data-generic-row]");
      if (!selected) return toast("Silmek i\u00e7in bir s\u00f6zle\u015fme se\u00e7in", "warning");
      const row = window.currentGenericData?.rows?.[Number(selected.dataset.genericRow)];
      if (row) confirmContractDelete(meta,row);
    });
    document.querySelector("[data-contract-export]")?.addEventListener("click", async () => {
      const params = new URLSearchParams({
        search: search?.value || "",
        type: document.querySelector("#contractType")?.value || "all",
        sla: document.querySelector("#contractSla")?.value || "all",
        status: document.querySelector("[data-contract-status].active")?.dataset.contractStatus || "all",
        today: contractTodayKey(),
      });
      try {
        const response = await fetch(`/api/desktop/contracts/export.csv?${params}`, {
          credentials: "same-origin",
          headers: typeof ayecFiscalArchiveHeaders === "function" ? ayecFiscalArchiveHeaders() : {},
        });
        if (!response.ok) {
          let message = `Sunucu hatas\u0131 (${response.status})`;
          try { message = (await response.json()).error || message; } catch {}
          throw new Error(message);
        }
        const link = document.createElement("a");
        link.href = URL.createObjectURL(await response.blob());
        link.download = "sozlesmeler.csv";
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 0);
      } catch (error) {
        toast(error.message || "S\u00f6zle\u015fme raporu al\u0131namad\u0131", "error");
      }
    });
  }

  function contractDetailBody(data) {
    const contract = data.contract || {};
    const attachments = Array.isArray(data.attachments) ? data.attachments : [];
    const items = attachments.map((item) => `<article class="contract-attachment-row"><div><strong>${esc(item.filename || "-")}</strong><small>${esc(item.created_at || "")}</small></div>${item.available ? `<a class="secondary" href="/api/desktop/contracts/attachments/${encodeURIComponent(item.id)}/download" target="_blank" rel="noopener">A\u00e7 / G\u00f6r\u00fcnt\u00fcle</a>` : '<span class="muted">Dosya kullan\u0131lam\u0131yor</span>'}<button type="button" class="danger" data-contract-attachment-delete="${esc(item.id)}">Eki Sil</button></article>`).join("");
    return `<div class="contract-detail-modal" data-contract-id="${esc(contract.id)}"><section class="contract-detail-info"><div><small>BA\u015eLIK</small><strong>${esc(contract.title || "-")}</strong></div><div><small>M\u00dc\u015eTER\u0130</small><strong>${esc(contract.customer_name || "-")}</strong></div><div><small>T\u00dcR</small><strong>${esc(contract.contract_type || "-")}</strong></div><div class="full"><small>A\u00c7IKLAMA</small><p>${esc(contract.description || "-")}</p></div></section><section class="contract-detail-files"><header><h3>DOSYA EKLER\u0130</h3><span>${attachments.length}</span></header><div class="contract-attachment-list">${items || '<p class="muted">Bu s\u00f6zle\u015fmeye dosya eklenmemi\u015f.</p>'}</div><input id="contractAttachmentInput" type="file" multiple hidden><button type="button" class="secondary" data-contract-attachment-upload>+ Yeni Dosya Y\u00fckle</button><small class="muted">Dosya ba\u015f\u0131na en fazla 25 MB</small></section></div>`;
  }

  async function contractDetailData(contractId) {
    return apiFetch(`/api/desktop/contracts/${encodeURIComponent(contractId)}/attachments`);
  }

  async function openContractAttachmentDialog(contractId) {
    try {
      const data = await contractDetailData(contractId);
      window.currentContractDetailId = contractId;
      openDialog("S\u00f6zle\u015fme Detaylar\u0131 & Ekleri", "S\u00d6ZLE\u015eME", contractDetailBody(data), () => true, "Kapat");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function refreshContractAttachmentBody(contractId) {
    const data = await contractDetailData(contractId);
    const body = document.querySelector("#dialogBody");
    if (body && document.querySelector("#appDialog")?.open) body.innerHTML = contractDetailBody(data);
  }

  async function uploadContractFiles(contractId, files, options = {}) {
    let uploaded = 0;
    for (const file of files) {
      if (file.size > 25 * 1024 * 1024) throw new Error(`${file.name}: Dosya 25 MB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor.`);
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || "").split(",", 2)[1] || "");
        reader.onerror = () => reject(new Error(`${file.name}: Dosya okunamad\u0131.`));
        reader.readAsDataURL(file);
      });
      await apiFetch(`/api/desktop/contracts/${encodeURIComponent(contractId)}/attachments`, {
        method: "POST",
        body: JSON.stringify({filename: file.name, data_base64: dataUrl}),
      });
      uploaded += 1;
    }
    if (options.refresh !== false) await refreshContractAttachmentBody(contractId);
    if (options.notify !== false) toast(`${uploaded} dosya eklendi.`, "success");
  }

  function contractNextYearKey() {
    const date = new Date();
    const year = date.getFullYear() + 1;
    const day = Math.min(date.getDate(), new Date(year, date.getMonth() + 1, 0).getDate());
    return `${year}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  function openContractCreateDialog(meta, customers) {
    const types = ["Bak\u0131m", "Kiralama", "Servis", "Lisans", "Proje"];
    const customerOptions = customers.map((customer) => `<option value="${esc(customer.id)}">${esc(customer.name || customer.company_name || customer.id)}</option>`).join("");
    const body = `<div class="form-grid contract-create-form">
      <div class="field full"><label for="contractCreateCustomer">M\u00dc\u015eTER\u0130 SE\u00c7\u0130M\u0130</label><select id="contractCreateCustomer" name="customer_id"><option value="">M\u00fc\u015fteri se\u00e7in</option>${customerOptions}</select></div>
      <div class="field full"><label for="contractCreateTitle">S\u00d6ZLE\u015eME BA\u015eLI\u011eI</label><input id="contractCreateTitle" name="title" required placeholder="\u00d6rn: Kurumsal Bak\u0131m S\u00f6zle\u015fmesi"></div>
      <div class="contract-create-pair contract-create-type-price"><div class="field"><label for="contractCreateType">T\u00dcR</label><select id="contractCreateType" name="contract_type">${types.map((type) => `<option value="${esc(type)}">${esc(type)}</option>`).join("")}</select></div><div class="field"><label for="contractCreatePrice">BEDEL (${esc(String(db.settings?.currency || "TRY"))})</label><input id="contractCreatePrice" name="price" type="number" step="0.01" value="0.00"></div></div>
      <div class="contract-create-pair contract-create-dates"><div class="field"><label for="contractCreateStart">BA\u015eLANGI\u00c7</label><input id="contractCreateStart" name="start_date" type="date" required value="${contractTodayKey()}"></div><div class="field"><label for="contractCreateEnd">B\u0130T\u0130\u015e</label><input id="contractCreateEnd" name="end_date" type="date" required value="${contractNextYearKey()}"></div></div>
      <div class="field full contract-create-description"><label for="contractCreateDescription">A\u00c7IKLAMA</label><textarea id="contractCreateDescription" name="description" rows="3"></textarea></div>
      <div class="field full contract-create-files"><button type="button" class="secondary contract-file-select" data-contract-file-select>&#128206; S\u00f6zle\u015fme Dosyas\u0131 / Eki Ekle</button><input id="contractCreateFiles" type="file" multiple hidden><small class="muted" data-contract-file-name>Dosya ba\u015f\u0131na en fazla 25 MB</small></div>
    </div>`;
    openDialog("Yeni S\u00f6zle\u015fme Olu\u015ftur", meta.group, body, async (formData) => {
      const files = Array.from(document.querySelector("#contractCreateFiles")?.files || []);
      for (const file of files) {
        if (file.size > 25 * 1024 * 1024) throw new Error(`${file.name}: Dosya 25 MB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor.`);
      }
      const customerId = String(formData.get("customer_id") || "");
      const result = await apiFetch(`/api/desktop/table/${meta.table}`, {
        method: "POST",
        body: JSON.stringify({
          customer_id: customerId ? Number(customerId) : null,
          title: String(formData.get("title") || "").trim(),
          contract_type: formData.get("contract_type"),
          price: Number(formData.get("price") || 0),
          start_date: formData.get("start_date"),
          end_date: formData.get("end_date"),
          description: formData.get("description") || "",
        }),
      });
      if (files.length && result?.id) {
        try {
          await uploadContractFiles(result.id, files, {refresh: false, notify: false});
        } catch (error) {
          toast(`S\u00f6zle\u015fme kaydedildi; ek dosyalar\u0131n y\u00fcklenmesi tamamlanamad\u0131: ${error.message}`, "error");
        }
      } else if (files.length) {
        toast("S\u00f6zle\u015fme kaydedildi; ekler i\u00e7in kay\u0131t kimli\u011fi al\u0131namad\u0131.", "error");
      }
      contractDataCache = null;
      contractDataCacheQuery = null;
      contractPage = 0;
      await loadGenericModule(meta, "");
      if (!files.length) toast("S\u00f6zle\u015fme kaydedildi.", "success");
      return true;
    }, "S\u00f6zle\u015fmeyi Kaydet");
    const dialog = document.querySelector("#appDialog");
    dialog?.classList.add("contract-create-dialog");
    dialog?.addEventListener("close", () => dialog.classList.remove("contract-create-dialog"), {once: true});
    document.querySelector("#dialogCancel").textContent = "\u0130ptal";
    document.querySelector("#dialogEyebrow").hidden = true;
    const fileInput = document.querySelector("#contractCreateFiles");
    document.querySelector("[data-contract-file-select]")?.addEventListener("click", () => fileInput?.click());
    fileInput?.addEventListener("change", () => {
      const names = Array.from(fileInput.files || []).map((file) => file.name);
      const label = document.querySelector("[data-contract-file-name]");
      if (label) label.textContent = names.length ? names.join(", ") : "Dosya ba\u015f\u0131na en fazla 25 MB";
    });
  }

  document.addEventListener("dblclick", (event) => {
    if (document.body.dataset.page !== "contracts" || !db.settings.doubleClick) return;
    const row = event.target.closest(".contracts-reference-table tbody tr[data-contract-id]");
    if (!row || event.target.closest("button,a,input,select,textarea")) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    openContractAttachmentDialog(row.dataset.contractId);
  }, true);

  document.addEventListener("click", async (event) => {
    if (document.body.dataset.page !== "contracts") return;
    const detail = event.target.closest("[data-contract-detail]");
    if (detail) {
      event.preventDefault();
      openContractAttachmentDialog(detail.dataset.contractDetail);
      return;
    }
    const upload = event.target.closest("[data-contract-attachment-upload]");
    if (upload) {
      document.querySelector("#contractAttachmentInput")?.click();
      return;
    }
    const remove = event.target.closest("[data-contract-attachment-delete]");
    if (remove) {
      const attachmentId=Number(remove.dataset.contractAttachmentDelete),filename=remove.closest(".contract-attachment-row")?.querySelector("strong")?.textContent||"";
      openDialog("Eki Sil","SILME ONAYI",`<p>${esc(filename)} dosya eki kal\u0131c\u0131 olarak silinecek. Emin misiniz?</p>`,async()=>{
        try {
          await apiFetch("/api/desktop/contracts/attachments/delete",{
            method:"POST",
            body:JSON.stringify({attachment_id:attachmentId}),
          });
          await refreshContractAttachmentBody(window.currentContractDetailId);
          toast("Dosya silindi.","success");
          return true;
        } catch(error) {
          toast(error.message,"error");
          return false;
        }
      },"Evet, Sil");
      document.querySelector("#dialogCancel").textContent="Hay\u0131r";
      document.querySelector("#dialogSubmit").classList.remove("primary");
      document.querySelector("#dialogSubmit").classList.add("danger");
      return;
    }
  });

  document.addEventListener("dblclick", (event) => {
    if (document.body.dataset.page !== "contracts") return;
    const row = event.target.closest(".contract-attachment-row");
    if (!row || event.target.closest("a,button,input,select,textarea")) return;
    const openLink = row.querySelector('a[href*="/download"]');
    if (!openLink) return;
    event.preventDefault();
    openLink.click();
  });

  document.addEventListener("change", (event) => {
    if (document.body.dataset.page !== "contracts" || event.target.id !== "contractAttachmentInput") return;
    const files = Array.from(event.target.files || []);
    const contractId = window.currentContractDetailId;
    if (!files.length || !contractId) return;
    uploadContractFiles(contractId, files).catch((error) => toast(error.message, "error"));
    event.target.value = "";
  });

  const baseRender = window.render;
  window.render = function () {
    baseRender.apply(this, arguments);
    bindContractControls();
  };
  if (document.body.dataset.page === "contracts") window.render();
})();
