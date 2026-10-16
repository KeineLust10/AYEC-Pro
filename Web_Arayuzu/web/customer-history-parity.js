(function () {
  const workbookMime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const baseCustomer360 = window.customer360;

  function addSelectionColumn(panel, kind) {
    const table = panel && panel.querySelector("table");
    if (!table || table.dataset.historySelectionReady) return;
    table.dataset.historySelectionReady = "1";
    const header = document.createElement("th");
    header.textContent = "Se\u00e7";
    table.tHead.rows[0].prepend(header);
    for (const row of table.tBodies[0].rows) {
      const cell = row.insertCell(0);
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = true;
      checkbox.dataset.customerHistorySelect = kind;
      checkbox.setAttribute("aria-label", "Select row for export");
      cell.append(checkbox);
    }
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "secondary customer-history-select-all";
    toggle.textContent = "T\u00fcm\u00fcn\u00fc Se\u00e7 / Kald\u0131r";
    toggle.addEventListener("click", () => {
      const boxes = [...table.querySelectorAll(`input[data-customer-history-select="${kind}"]`)];
      const next = boxes.length ? !boxes[0].checked : true;
      boxes.forEach(box => { box.checked = next; });
    });
    panel.insertBefore(toggle, table.parentElement);
  }

  function selectedRows(table, boxes, values, project) {
    if (!table) return [];
    return [...table.tBodies[0].rows].flatMap((row, index) =>
      boxes[index] && boxes[index].checked && values[index] ? [project(values[index])] : []
    );
  }

  function bindCustomerHistory(c) {
    const dialog = document.querySelector("#appDialog");
    const servicePanel = dialog.querySelector('[data-c360-panel="service"]');
    const financePanel = dialog.querySelector('[data-c360-panel="cari"]');
    addSelectionColumn(servicePanel, "service");
    addSelectionColumn(financePanel, "finance");

    const services = Array.isArray(c.services) ? c.services : [];
    const finance = (window.db && Array.isArray(window.db.finance) ? window.db.finance : [])
      .filter(item => item.customer === c.name);
    const serviceTable = servicePanel && servicePanel.querySelector("table");
    const financeTable = financePanel && financePanel.querySelector("table");
    const excel = dialog.querySelector("#c360Excel");
    if (excel) excel.onclick = async () => {
      const serviceBoxes = [...servicePanel.querySelectorAll('input[data-customer-history-select="service"]')];
      const financeBoxes = [...financePanel.querySelectorAll('input[data-customer-history-select="finance"]')];
      const serviceRows = selectedRows(serviceTable, serviceBoxes, services, item => [
        item.no || "", item.device || "", item.note || "", item.status || "",
        window.money(item.amount || 0, item.currency || "TRY"), String(item.date || "").slice(0, 10)
      ]);
      const financeRows = selectedRows(financeTable, financeBoxes, finance, item => [
        item.category || "", item.description || "", item.type || "", String(item.date || "").slice(0, 10),
        window.money(item.amount || 0, item.currency || "TRY")
      ]);
      try {
        const response = await fetch("/api/desktop/customer/history/export/xlsx", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ customer_name: c.name, service_rows: serviceRows, finance_rows: financeRows })
        });
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.error || `Excel export failed (${response.status})`);
        }
        const blob = await response.blob();
        if (blob.type && blob.type !== workbookMime) throw new Error("Invalid Excel response");
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "musteri_gecmisi.xlsx";
        document.body.append(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        window.toast("Se\u00e7ilen kay\u0131tlar Excel dosyas\u0131na aktar\u0131ld\u0131.", "success");
      } catch (error) {
        window.toast(error.message || "Excel export failed.", "error");
      }
    };

    const pdf = dialog.querySelector("#c360Pdf");
    if (pdf) pdf.onclick = () => {
      const boxes = [...servicePanel.querySelectorAll('input[data-customer-history-select="service"]')];
      const rows = selectedRows(serviceTable, boxes, services, item => item);
      if (!rows.length) {
        window.toast("PDF raporu i\u00e7in en az bir servis kayd\u0131 se\u00e7in.", "warning");
        return;
      }
      document.querySelector("#customerHistoryPrintArea")?.remove();
      const report = document.createElement("section");
      report.id = "customerHistoryPrintArea";
      const title = document.createElement("h1");
      title.textContent = `${c.name} - Se\u00e7ili Kay\u0131tlar`;
      const table = document.createElement("table");
      const headers = ["Cihaz", "Ariza", "Ucret", "Tarih"];
      const head = table.createTHead().insertRow();
      headers.forEach(value => { const cell = document.createElement("th"); cell.textContent = value; head.append(cell); });
      const body = table.createTBody();
      rows.forEach(item => {
        const row = body.insertRow();
        [item.device || "", item.note || "", window.money(item.amount || 0, item.currency || "TRY"), String(item.date || "").slice(0, 10)]
          .forEach(value => { const cell = row.insertCell(); cell.textContent = value; });
      });
      report.append(title, table);
      document.body.append(report);
      document.body.dataset.customerHistoryPrint = "1";
      const cleanup = () => {
        delete document.body.dataset.customerHistoryPrint;
        report.remove();
        window.removeEventListener("afterprint", cleanup);
      };
      window.addEventListener("afterprint", cleanup, { once: true });
      window.print();
    };
  }

  if (typeof baseCustomer360 === "function") {
    window.customer360 = function (customer) {
      baseCustomer360(customer);
      bindCustomerHistory(customer);
    };
  }
})();
