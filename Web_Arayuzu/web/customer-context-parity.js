(function () {
  const baseShowContext = window.showContext;
  const groups = [
    [["M\u00fc\u015fteri Notlar\u0131", "notes"], ["M\u00fc\u015fteri 360", "360"], ["D\u00fczenle", "edit"]],
    [["Yeni Servis Kayd\u0131", "service"], ["Fatura Kes", "invoice"], ["Tahsilat / \u00d6deme Al", "payment"]],
    [["WhatsApp Mesaj", "whatsapp"], ["Bakiye Hat\u0131rlat (WA)", "debt-reminder"]],
    [["Excel'e Aktar", "excel"], ["PDF Olarak Kaydet", "pdf"], ["Yazd\u0131r", "print"]]
  ];

  function openPrintView(title, headers, rows) {
    document.querySelector("#customerListPrintArea")?.remove();
    const report = document.createElement("section");
    report.id = "customerListPrintArea";
    const heading = document.createElement("h1");
    heading.textContent = title;
    const table = document.createElement("table");
    const head = table.createTHead().insertRow();
    headers.forEach(value => { const cell = document.createElement("th"); cell.textContent = value; head.append(cell); });
    const body = table.createTBody();
    rows.forEach(values => {
      const row = body.insertRow();
      values.forEach(value => { const cell = row.insertCell(); cell.textContent = value; });
    });
    report.append(heading, table);
    document.body.append(report);
    document.body.dataset.customerListPrint = "1";
    const cleanup = () => {
      delete document.body.dataset.customerListPrint;
      report.remove();
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup, { once: true });
    window.print();
  }

  function printCustomerList() {
    const table = document.querySelector("#customerTable .customer-data-table");
    if (!table) return window.toast("M\u00fc\u015fteri listesi kullan\u0131lam\u0131yor.", "warning");
    const headers = ["M\u00fc No", "M\u00fc\u015fteri", "Tip", "\u0130leti\u015fim", "A\u00e7\u0131k Servis", "Bakiye", "Durum"];
    const rows = [...table.tBodies[0].rows].map(row => [1, 2, 3, 4, 5, 6, 7].map(index => row.cells[index]?.innerText.trim() || ""));
    openPrintView("M\u00fc\u015fteri Listesi", headers, rows);
  }

  async function exportCustomerPdf() {
    const table = document.querySelector("#customerTable .customer-data-table");
    if (!table) return window.toast("M\u00fc\u015fteri listesi kullan\u0131lam\u0131yor.", "warning");
    const rows = [...table.tBodies[0].rows].map(row => [1, 2, 3, 4, 5, 6, 7].map(index => row.cells[index]?.innerText.trim() || ""));
    try {
      const response = await fetch("/api/desktop/customers/export/pdf", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows })
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `PDF export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `musteri_listesi_${new Date().toISOString().slice(0, 10).replaceAll("-", "")}.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      window.toast("M\u00fc\u015fteri listesi PDF'e aktar\u0131ld\u0131.", "success");
    } catch (error) {
      window.toast(error.message || "PDF export failed.", "error");
    }
  }

  function openWhatsApp(customer, message) {
    let phone = String(customer.phone || "").replace(/\D/g, "");
    if (!phone) return window.toast("M\u00fc\u015fterinin telefon numaras\u0131 kay\u0131tl\u0131 de\u011fil.", "warning");
    if (phone.startsWith("0") && phone.length === 11) phone = "9" + phone;
    else if (phone.length === 10) phone = "90" + phone;
    const suffix = message ? "?text=" + encodeURIComponent(message) : "";
    window.open("https://wa.me/" + phone + suffix, "_blank", "noopener");
  }

  async function exportCustomers(customers, selected) {
    if (!customers.length) return window.toast("D\u0131\u015fa aktar\u0131lacak m\u00fc\u015fteri bulunamad\u0131.", "warning");
    const rows = customers.map(customer => [
      customer.desktopId || customer.id || "",
      customer.name || "",
      customer.company_name || customer.company || "",
      customer.phone || "",
      customer.email || "",
      customer.type || "",
      customer.address || ""
    ]);
    try {
      const response = await fetch("/api/desktop/customers/export/xlsx", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows })
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `Excel export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = selected ? "musteriler-secili.xlsx" : "musteriler.xlsx";
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      window.toast("M\u00fc\u015fteri listesi Excel'e aktar\u0131ld\u0131.", "success");
    } catch (error) {
      window.toast(error.message || "Excel export failed.", "error");
    }
  }

  async function sendDebtReminder(customer) {
    const id = Number(customer.desktopId || customer.id);
    if (!Number.isInteger(id) || id <= 0) return window.toast("M\u00fc\u015fteri bor\u00e7 detaylar\u0131 al\u0131namad\u0131.", "warning");
    try {
      const result = await window.apiFetch(`/api/desktop/customer/open-debts?customer_id=${id}&currency=TRY`);
      const openItems = result.items || [];
      const balance = Math.max(0, -Number(customer.balances && customer.balances.TRY || 0));
      const amount = openItems.reduce((sum, item) => sum + Number(item.remaining || 0), 0) || balance;
      if (amount <= 0) return window.toast("M\u00fc\u015fterinin borcu bulunmamaktad\u0131r.", "info");
      const formatted = money(amount, "TRY");
      const message = `Say\u0131n *${customer.name}*,\n\nG\u00fcncel bor\u00e7 bakiyeniz: *${formatted}*'dir.\n\n\u00d6demenizi rica eder, iyi \u00e7al\u0131\u015fmalar dileriz.\n\n*AYEC Pro*`;
      openWhatsApp(customer, message);
    } catch (error) {
      window.toast(error.message || "M\u00fc\u015fteri bakiyesi y\u00fcklenemedi.", "error");
    }
  }

  function deleteCustomer(customer) {
    const id = Number(customer.desktopId || customer.id);
    const body = `<p><strong>${esc(customer.name || "")}</strong> isimli m\u00fc\u015fteriyi silmek istedi\u011finize emin misiniz?</p><p>Bu i\u015flem geri al\u0131namaz.</p>`;
    window.openDialog("M\u00fc\u015fteriyi Sil", "S\u0130LME ONAYI", body, async () => {
      try {
        await window.apiFetch("/api/desktop/customer/delete", {
          method: "POST",
          body: JSON.stringify({ id })
        });
        db.customers = db.customers.filter(item => String(item.id) !== String(customer.id));
        save();
        window.render();
        window.toast("M\u00fc\u015fteri silindi.", "success");
        return true;
      } catch (error) {
        window.toast(error.message || "M\u00fc\u015fteri silinemedi.", "error");
        return false;
      }
    }, "Evet, Sil");
    document.querySelector("#dialogCancel").textContent = "Hay\u0131r";
    document.querySelector("#dialogSubmit").classList.remove("primary");
    document.querySelector("#dialogSubmit").classList.add("danger");
  }

  function customerAction(action, customer) {
    if (action === "notes") return window.openCustomerNotes(customer);
    if (action === "360") return window.customer360(customer);
    if (action === "edit") return window.openDialog("M\u00fc\u015fteriyi D\u00fczenle", "CRM", window.customerForm(customer), form => window.saveCustomer(form, customer), "G\u00fcncelle");
    if (action === "service") return window.serviceDialog(customer.desktopId || customer.id);
    if (action === "invoice") {
      window.navigate("invoices");
      const input = document.querySelector("#invoiceCustomer");
      if (input) {
        input.value = customer.name;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return;
    }
    if (action === "payment") return window.paymentDialog(customer);
    if (action === "whatsapp") return openWhatsApp(customer, "");
    if (action === "debt-reminder") return sendDebtReminder(customer);
    if (action === "excel") return exportCustomers(db.customers, false);
    if (action === "pdf") return exportCustomerPdf();
    if (action === "print") return printCustomerList();
    if (action === "selected-excel") {
      const selectedIds = new Set(window.ayecSelectedCustomerIds || [...document.querySelectorAll(".customer-row-select:checked")].map(input => String(input.dataset.id)));
      const rows = db.customers.filter(item => selectedIds.has(String(item.id)));
      if (!rows.length) return window.toast("\u00d6nce en az bir m\u00fc\u015fteri se\u00e7in.", "warning");
      return exportCustomers(rows, true);
    }
    if (action === "delete") return deleteCustomer(customer);
  }

  function showCustomerContext(event, id, row) {
    if (!window.ayecContextMenuEnabled()) return;
    event.preventDefault();
    window.currentCustomerId = id;
    const customer = db.customers.find(item => String(item.id) === String(id));
    if (!customer) return;
    const activeGroups = groups.map(group => group.slice());
    if (document.querySelector("#customerTable.multi-select")) activeGroups[3].push(["Se\u00e7ilileri Excel Aktar", "selected-excel"]);
    const menu = document.querySelector("#contextMenu");
    menu.innerHTML = activeGroups.map((group, index) => (index ? '<hr class="customer-context-separator">' : "") + group.map(([label, action]) => `<button type="button" data-customer-context-action="${action}">${label}</button>`).join("")).join("") + '<hr class="customer-context-separator"><button type="button" class="danger" data-customer-context-action="delete">M\u00fc\u015fteriyi Sil</button>';
    const buttonCount = menu.querySelectorAll("button").length;
    menu.style.left = `${Math.max(8, Math.min(event.clientX, innerWidth - 240))}px`;
    menu.style.top = `${Math.max(8, Math.min(event.clientY, innerHeight - buttonCount * 38 - 40))}px`;
    menu.classList.add("open");
    menu.querySelectorAll("[data-customer-context-action]").forEach(button => {
      button.onclick = () => {
        menu.classList.remove("open");
        customerAction(button.dataset.customerContextAction, customer, row);
      };
    });
  }

  if (typeof baseShowContext === "function") {
    window.showContext = function (event, kind, id) {
      if (kind !== "customer") return baseShowContext(event, kind, id);
      return showCustomerContext(event, id, event.currentTarget);
    };
  }
})();
