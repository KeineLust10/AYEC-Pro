(function () {
  async function downloadProductGroups(format) {
    const extension = format === "pdf" ? "pdf" : "xlsx";
    const query = new URLSearchParams({ q: document.querySelector("#groupSearch")?.value || "" });
    try {
      const response = await fetch(`/api/desktop/product-groups/export/${extension}?${query}`, { credentials: "same-origin" });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `Export failed (${response.status})`);
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `urun_gruplari-${new Date().toISOString().slice(0, 10)}.${extension}`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      window.toast(extension === "pdf" ? "Urun gruplari PDF olarak kaydedildi." : "Urun gruplari Excel dosyasi indirildi.", "success");
    } catch (error) {
      window.toast(error.message || "Export failed.", "error");
    }
  }

  document.addEventListener("click", event => {
    const button = event.target.closest("#groupExport, #groupPdf");
    if (!button || document.body.dataset.page !== "product-groups") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    downloadProductGroups(button.id === "groupPdf" ? "pdf" : "xlsx");
  }, true);
})();
