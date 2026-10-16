(function () {
  "use strict";

  async function exportFinancePdf() {
    const response = await fetch("/api/desktop/accounting/ledger/export/pdf", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...ayecFiscalArchiveHeaders() },
      body: JSON.stringify(ayecFinanceExportOptions())
    });
    if (!response.ok) {
      let result = {};
      try { result = await response.json(); } catch (_) {}
      if (response.status === 401 && window.handleUnauthorized) window.handleUnauthorized();
      throw new Error(result.error || `PDF export failed (${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `cari-hareketler-${today()}.pdf`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  }

  const baseContextAction = contextAction;
  contextAction = function (kind, id, action, row) {
    if (kind === "finance" && action === "finance-pdf") {
      exportFinancePdf()
        .then(() => toast("Cari hareketler PDF olarak indirildi.", "success"))
        .catch(error => toast(error.message || "PDF export failed.", "error"));
      return;
    }
    return baseContextAction(kind, id, action, row);
  };
})();
