(function () {
  async function downloadBrandExport(format, printWindow = null) {
    const query = new URLSearchParams({
      q: document.querySelector("#genericSearch")?.value || "",
      group: document.querySelector("#brandGroupFilter")?.value || "",
      status: document.querySelector("#brandStatusFilter")?.value || "active"
    });
      const isPrint = format === "print";
      const extension = format === "pdf" || isPrint ? "pdf" : "xlsx";
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
      if (isPrint) {
        if (!printWindow || printWindow.closed) throw new Error("Allow pop-ups to open the filtered print preview.");
        printWindow.location = url;
        printWindow.focus();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
        window.toast("Filtered brand report opened. Use the PDF viewer print control.", "success");
        return;
      }
      const link = document.createElement("a");
      link.href = url;
      link.download = `markalar-${today()}.${extension}`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      window.toast(extension === "pdf" ? "Markalar PDF olarak kaydedildi." : "Markalar Excel dosyasi indirildi.", "success");
    } catch (error) {
      window.toast(error.message || "Export failed.", "error");
    }
  }

  document.addEventListener("click", async event => {
    const button = event.target.closest("[data-brand-refresh]");
    if (!button || window.currentGenericMeta?.table !== "device_brands") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    try {
      const result = await window.apiFetch("/api/desktop/device-brands/refresh-catalog", { method: "POST", body: "{}" });
      window.brandsReferencePage = 0;
      await window.loadGenericModule(window.currentGenericMeta, document.querySelector("#genericSearch")?.value || "");
      window.toast(`Reviewed catalog refreshed: ${Number(result.brand_count || 0)} brands and ${Number(result.model_count || 0)} models.`, "success");
    } catch (error) {
      window.toast(error.message || "Device catalog refresh failed.", "error");
    }
  }, true);

  document.addEventListener("click", event => {
    const button = event.target.closest("[data-brand-export]");
    if (!button || window.currentGenericMeta?.table !== "device_brands") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (button.dataset.brandExport === "print") {
      const printWindow = window.open("about:blank", "_blank");
      if (!printWindow) {
        window.toast("Allow pop-ups to open the filtered print preview.", "error");
        return;
      }
      try { printWindow.opener = null; } catch {}
      downloadBrandExport("print", printWindow);
      return;
    }
    downloadBrandExport(button.dataset.brandExport);
  }, true);
})();
