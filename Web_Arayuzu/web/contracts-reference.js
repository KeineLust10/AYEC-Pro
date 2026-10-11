(function () {
  "use strict";

  const baseGenericTable = window.genericTable;
  let contractPage = 0;
  const contractPageSize = 4;

  function contractRows(meta, data) {
    const source = Array.isArray(data.rows) ? data.rows : [];
    const status = document.querySelector("[data-contract-status].active")?.dataset.contractStatus || "all";
    const type = document.querySelector("#contractType")?.value || "all";
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const rows = source.map((row, index) => ({ row, index })).filter(({ row }) => {
      const rowStatus = String(row.status || "").toLocaleLowerCase();
      const rowType = String(row.contract_type || "").toLocaleLowerCase();
      const end = Date.parse(String(row.end_date || "").slice(0, 10));
      const days = Number.isFinite(end) ? Math.ceil((end - today.getTime()) / 86400000) : null;
      const sla = document.querySelector("#contractSla")?.value || "all";
      const rowSla = String(row.sla_level || row.contract_type || "").toLocaleLowerCase();
      if (type !== "all" && rowType !== type.toLocaleLowerCase()) return false;
      if (sla !== "all" && rowSla !== sla.toLocaleLowerCase()) return false;
      if (status === "active") return rowStatus.includes("aktif");
      if (status === "renewal") return rowStatus.includes("yenile") || (days !== null && days >= 0 && days <= 30);
      if (status === "expired") return rowStatus.includes("suresi") || rowStatus.includes("s\u00fcresi") || (days !== null && days < 0);
      if (status === "draft") return rowStatus.includes("taslak") || rowStatus.includes("draft");
      return true;
    });
    const pageCount = Math.max(1, Math.ceil(rows.length / contractPageSize));
    contractPage = Math.min(contractPage, pageCount - 1);
    return { rows: rows.slice(contractPage * contractPageSize, (contractPage + 1) * contractPageSize), total: rows.length, pageCount, source };
  }

  function contractTable(meta, data) {
    const { rows, total, pageCount } = contractRows(meta, data);
    const source = Array.isArray(data.rows) ? data.rows : [];
    const activeCount = source.filter((item) => /aktif/i.test(String(item.status || ""))).length;
    const renewalCount = source.filter((item) => {
      const days = Math.ceil((Date.parse(String(item.end_date || "").slice(0, 10)) - Date.now()) / 86400000);
      return /yenile/i.test(String(item.status || "")) || (Number.isFinite(days) && days >= 0 && days <= 30);
    }).length;
    const metricValues = document.querySelectorAll(".contracts-reference-metrics .metric strong");
    if (metricValues.length >= 4) {
      metricValues[0].textContent = String(activeCount);
      metricValues[1].textContent = String(renewalCount);
      metricValues[2].textContent = money(source.reduce((sum, item) => sum + Number(item.price || 0), 0), "TRY");
      metricValues[3].textContent = String(source.length);
    }
    const chipCounts = {
      all: source.length,
      active: activeCount,
      renewal: renewalCount,
      expired: source.filter((item) => /suresi|s\u00fcresi/i.test(String(item.status || "")) || Date.parse(String(item.end_date || "").slice(0, 10)) < Date.now()).length,
      draft: source.filter((item) => /taslak|draft/i.test(String(item.status || ""))).length,
    };
    document.querySelectorAll("[data-contract-status]").forEach((button) => {
      const label = button.dataset.contractStatus === "all" ? "T\u00fcm\u00fc" : button.dataset.contractStatus === "active" ? "Aktif" : button.dataset.contractStatus === "renewal" ? "Yenileme Bekleyen" : button.dataset.contractStatus === "expired" ? "S\u00fcresi Dolanlar" : "Taslaklar";
      button.textContent = `${label} (${chipCounts[button.dataset.contractStatus] || 0})`;
    });
    const slaSelect = document.querySelector("#contractSla");
    if (slaSelect) {
      const selectedSla = slaSelect.value;
      const levels = [...new Set(source.map((item) => String(item.sla_level || item.contract_type || "").trim()).filter(Boolean))];
      slaSelect.innerHTML = `<option value="all">SLA Seviyesi: T\u00fcm\u00fc</option>${levels.map((level) => `<option value="${esc(level)}">${esc(level)}</option>`).join("")}`;
      slaSelect.value = levels.includes(selectedSla) ? selectedSla : "all";
      slaSelect.disabled = levels.length === 0;
    }
    const customerNames = new Map((Array.isArray(db.customers) ? db.customers : []).map((item) => [String(item.id), item.name || item.company_name || ""]));
    const columns = [
      ["id", "ID"], ["customer", "M\u00dc\u015eTER\u0130"], ["title", "BA\u015eLIK"],
      ["type", "SLA / T\u00dcR"], ["start", "BA\u015eLANGI\u00c7"], ["end", "B\u0130T\u0130\u015e"],
      ["status", "DURUM"], ["remaining", "KALAN S\u00dcRE"], ["price", "S\u00d6ZLE\u015eME BEDEL\u0130"],
    ];
    const body = rows.map(({ row, index }) => {
      const customer = row.customer_name || customerNames.get(String(row.customer_id)) || row.customer_id || "-";
      const end = Date.parse(String(row.end_date || "").slice(0, 10));
      const days = Number.isFinite(end) ? Math.ceil((end - Date.now()) / 86400000) : null;
      const remaining = days === null ? "-" : days < 0 ? `${Math.abs(days)} g\u00fcn ge\u00e7ti` : `${days} g\u00fcn`;
      const values = [row.id, customer, row.title || "-", row.sla_level || row.contract_type || "-", row.start_date || "-", row.end_date || "-", row.status || "-", remaining, money(Number(row.price || 0), "TRY")];
      return `<tr tabindex="0" data-kind="generic" data-id="${index}" data-generic-row="${index}">${values.map((value, i) => `<td data-label="${columns[i][1]}">${contractCell(value, i, days)}</td>`).join("")}<td data-label="\u0130\u015eLEMLER"><button class="mini generic-edit" data-index="${index}">D\u00fczenle</button> <button class="mini generic-delete" data-index="${index}">Sil</button></td></tr>`;
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

  function contractCell(value, index, days) {
    if (index === 6) {
      const normalized = String(value || "").toLocaleLowerCase();
      const state = normalized.includes("aktif") ? "active" : normalized.includes("yenile") ? "renewal" : normalized.includes("taslak") || normalized.includes("draft") ? "draft" : "expired";
      return `<span class="contract-status-badge is-${state}">${esc(value || "-")}</span>`;
    }
    if (index === 7) {
      const state = days !== null && days <= 30 ? "urgent" : "safe";
      return `<span class="contract-remaining is-${state}">${esc(value)}</span>`;
    }
    return genericValue(value, ["id", "customer", "title", "type", "start", "end", "status", "remaining", "price"][index]);
  }

  window.genericTable = function (meta, data) {
    return meta?.table === "contracts" ? contractTable(meta, data) : baseGenericTable(meta, data);
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
      if (row) deleteGenericRow(meta, row);
    });
    document.querySelector("[data-contract-export]")?.addEventListener("click", () => {
      const rows = window.currentGenericData?.rows || [];
      if (!rows.length) return toast("D\u0131\u015fa aktar\u0131lacak s\u00f6zle\u015fme bulunamad\u0131", "warning");
      const fields = ["id", "customer_id", "title", "contract_type", "start_date", "end_date", "status", "price", "description"];
      const csv = [fields.join(","), ...rows.map((row) => fields.map((field) => `"${String(row[field] ?? "").replaceAll('"', '""')}"`).join(","))].join("\r\n");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
      link.download = "ayec-contracts.csv";
      link.click();
      URL.revokeObjectURL(link.href);
    });
  }

  const baseRender = window.render;
  window.render = function () {
    baseRender.apply(this, arguments);
    bindContractControls();
  };
  if (document.body.dataset.page === "contracts") window.render();
})();
