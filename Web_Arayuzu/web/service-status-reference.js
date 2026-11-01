function ayecStatusNormalizeText(value) {
  return String(value || "").toUpperCase().replace(/[\u0130\u0131]/g, "I").replace(/\u00c7/g, "C");
}

function ayecStatusCriticalMatch(status, urgency) {
  const combined = ayecStatusNormalizeText(status) + " " + ayecStatusNormalizeText(urgency);
  return ["PARCA", "BEKLIYOR", "ACIL"].some(token => combined.includes(token));
}

function ayecStatusCategoryMatch(status, category) {
  const normalized = ayecStatusNormalizeText(status);
  const delivered = normalized.includes("TESLIM") && !normalized.includes("HAZIR");
  const parts = normalized.includes("PARCA");
  return category === "all" || (category === "done" && delivered) || (category === "parts" && parts) || (category === "open" && !delivered && !parts);
}

function ayecStatusSearchMatch(row, query) {
  const needle = String(query || "").trim().toLocaleLowerCase("tr-TR");
  if (!needle) return true;
  const device = [row.device_brand, row.device_model].filter(Boolean).join(" ");
  const values = [row.tracking_no || "-", row.customer_name || "-", device, row.serial_no || "", row.status || "Bekliyor", row.entry_date, row.estimated_date || "-", row.urgency || "Normal", row.delivered_at || row.exit_date || "-"];
  return values.some(value => String(value || "").toLocaleLowerCase("tr-TR").includes(needle));
}

(function() {
  const params = new URLSearchParams(window.location.search);
  const isTvDisplay = params.get("display") === "status-wall";
  window.ayecStatusWallDisplayMode = isTvDisplay;
  if (isTvDisplay) document.body.dataset.statusDisplay = "wall";

  function filteredRows() {
    const query = String(document.querySelector("#genericSearch")?.value || "").trim().toLocaleLowerCase("tr-TR");
    const sort = document.querySelector("#statusWallSort")?.value || "newest";
    const rows = ayecStatusRows.filter(row => {
      const critical = ayecStatusCriticalMatch(row.status, row.urgency);
      return ayecStatusSearchMatch(row, query) &&
        ayecStatusCategoryMatch(row.status, ayecStatusFilter) &&
        (!ayecStatusCriticalOnly || critical);
    });
    ayecStatusSortRows(rows, sort);
    return rows;
  }

  function showHelp() {
    openDialog("Bilgi", "CANLI SERV\u0130S DURUMU", "<p>Bu sayfa TV veya ikinci bir ekranda tam ekran servis panosu olarak a\u00e7\u0131l\u0131r.</p><ol><li>Yay\u0131n ba\u011flant\u0131s\u0131n\u0131 kopyalay\u0131n.</li><li>TV taray\u0131c\u0131s\u0131nda ba\u011flant\u0131y\u0131 a\u00e7\u0131n ve ayn\u0131 \u015firket hesab\u0131yla oturum a\u00e7\u0131n.</li><li>Taray\u0131c\u0131dan tam ekran\u0131 etkinle\u015ftirin. Kay\u0131tlar 5 saniyede bir yenilenir.</li></ol>", () => true, "Tamam");
  }

  const renderStatusRows = ayecStatusRender;
  ayecStatusRender = function() {
    renderStatusRows();
    const toolbar = document.querySelector(".status-wall-toolbar");
    const table = document.querySelector(".status-wall-table");
    if (!toolbar || !table) return;
    let toggle = document.querySelector("#statusWallTargetToggle");
    if (!toggle) {
      const label = document.createElement("label");
      label.className = "status-wall-target-toggle";
      toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.id = "statusWallTargetToggle";
      label.append(toggle, document.createTextNode(" Hedef Tarih"));
      toolbar.append(label);
      toggle.addEventListener("change", () => {
        document.body.dataset.statusTargetDate = toggle.checked ? "visible" : "hidden";
      });
    }
    const headRow = table.tHead?.rows[0];
    if (headRow && headRow.cells.length === 8) {
      const targetHeader = headRow.cells[5];
      targetHeader.textContent = "HEDEF TAR\u0130H";
      targetHeader.classList.add("status-wall-target-date");
      const deliveryHeader = document.createElement("th");
      deliveryHeader.textContent = "TESL\u0130M";
      headRow.insertBefore(deliveryHeader, targetHeader);
    }
    table.tBodies[0]?.querySelectorAll("tr").forEach(tr => {
      if (tr.cells.length !== 8) return;
      const targetCell = tr.cells[5];
      targetCell.dataset.label = "Hedef Tarih";
      targetCell.classList.add("status-wall-target-date");
      const tracking = tr.cells[0]?.textContent.trim();
      const row = ayecStatusRows.find(item => String(item.tracking_no || ("SRV-" + item.id)) === tracking);
      const delivery = document.createElement("td");
      delivery.dataset.label = "Teslim";
      delivery.textContent = row?.delivered_at || row?.exit_date || "-";
      tr.insertBefore(delivery, targetCell);
    });
    if (toggle) document.body.dataset.statusTargetDate = toggle.checked ? "visible" : "hidden";
  };

  document.addEventListener("click", event => {
    const help = event.target.closest("[data-status-help]");
    const shareButton = event.target.closest("[data-status-share]");
    const exportButton = event.target.closest("[data-status-export]");
    if (!help && !shareButton && !exportButton) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (help) {
      showHelp();
      return;
    }
    if (shareButton) {
      const url = new URL(window.location.href);
      url.searchParams.set("page", "service-status");
      url.searchParams.set("display", "status-wall");
      const share = { title: "AYEC Pro - Durum Paneli", text: "Canl\u0131 servis durumu", url: url.toString() };
      if (navigator.share) navigator.share(share).catch(() => {});
      else if (navigator.clipboard) navigator.clipboard.writeText(share.url).then(() => toast("TV pano ba\u011flant\u0131s\u0131 kopyaland\u0131.", "success")).catch(() => toast(share.url, "info"));
      else toast(share.url, "info");
      return;
    }
    const columns = [
      ["Takip No", row => row.tracking_no || ("SRV-" + row.id)],
      ["M\u00fc\u015fteri", row => row.customer_name || "-"],
      ["Cihaz / Model", row => [row.device_brand, row.device_model].filter(Boolean).join(" ") || row.device_type || "-"],
      ["Durum", row => row.status || "Belirtilmedi"],
      ["Giri\u015f", row => row.entry_date || "-"],
      ["Hedef Tarih", row => row.estimated_date || "-"],
      ["\u00d6ncelik", row => row.urgency || "Normal"],
      ["\u0130\u015flemler", () => ""],
      ["Teslim", row => row.delivered_at || row.exit_date || "-"]
    ];
    const records = filteredRows().map(row => Object.fromEntries(columns.map(([label, value]) => [label, value(row)])));
    download("durum-paneli-" + today() + ".csv", csv(records));
  }, true);

})();
