(function () {
  async function downloadBrandExport(format) {
    const query = new URLSearchParams({
      q: document.querySelector("#genericSearch")?.value || "",
      group: document.querySelector("#brandGroupFilter")?.value || "",
      status: document.querySelector("#brandStatusFilter")?.value || "active"
    });
    const extension = format === "pdf" ? "pdf" : "xlsx";
    try {
      const response = await fetch(`/api/desktop/device-brands/export/${extension}?${query}`, {
        credentials: "same-origin"
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `Export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `markalar-${new Date().toISOString().slice(0, 10)}.${extension}`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      window.toast(extension === "pdf" ? "Markalar PDF olarak kaydedildi." : "Markalar Excel dosyasi indirildi.", "success");
    } catch (error) {
      window.toast(error.message || "Export failed.", "error");
    }
  }

  document.addEventListener("click", event => {
    const button = event.target.closest("[data-brand-export]");
    if (!button || button.dataset.brandExport === "print" || window.currentGenericMeta?.table !== "device_brands") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    downloadBrandExport(button.dataset.brandExport);
  }, true);
})();
