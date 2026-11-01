(function () {
  const baseAction = window.ayecExecuteVoiceAction;
  if (typeof baseAction !== "function") return;

  const normalize = (value) => {
    const text = String(value || "");
    const normalized = typeof ayecNormalizeVoicePhrase === "function"
      ? ayecNormalizeVoicePhrase(text)
      : text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[\u0131\u0130]/g, "i").toLowerCase();
    return normalized.replace(/[^a-z0-9]+/g, " ").trim();
  };
  let helpState = null;
  const showAssistantHelp = (continueListing = false) => {
    const content = document.querySelector("#content") || document.body || document;
    const pageId = String(typeof page !== "undefined" ? page : document.body?.dataset?.page || "");
    const heading = typeof content.querySelector === "function" ? content.querySelector("h1, h2, h3") : null;
    const pageTitle = typeof titles !== "undefined" ? titles[pageId] : null;
    const title = String(heading?.textContent || (Array.isArray(pageTitle) ? pageTitle[1] : pageTitle) || pageId || "Aktif ekran").trim();
    if (continueListing && (!helpState || helpState.pageId !== pageId)) {
      helpState = null;
      toast("Devam edilecek g\u00fcncel bir yetenek listesi yok. Neler yapabilirim diye sorun.", "warning");
      return false;
    }
    if (!continueListing) {
      const selector = 'button:not([disabled]), a[href], input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [role="button"]';
      const contentControls = typeof content.querySelectorAll === "function" ? [...content.querySelectorAll(selector)] : [];
      const navigationControls = typeof document.querySelectorAll === "function" ? [...document.querySelectorAll(`#nav ${selector}`)] : [];
      const controls = [...contentControls, ...navigationControls];
      const labels = [...new Set(controls.filter((control) => {
        if (control.disabled || typeof control.getClientRects !== "function" || control.getClientRects().length === 0) return false;
        const style = typeof getComputedStyle === "function" ? getComputedStyle(control) : null;
        return !style || (style.display !== "none" && style.visibility !== "hidden");
      }).map((control) => {
        const label = String(control.getAttribute("aria-label") || control.title || control.innerText || control.textContent || control.value || control.labels?.[0]?.innerText || control.placeholder || "").replace(/\s+/g, " ").trim();
        if (!label) return "";
        const tag = String(control.tagName || "").toLowerCase();
        const kind = tag === "button" || control.getAttribute("role") === "button" ? "D\u00fc\u011fme" : tag === "a" ? "Ba\u011flant\u0131" : tag === "select" ? "Se\u00e7im listesi" : "Alan";
        return `${kind}: ${label}`;
      }).filter(Boolean))];
      helpState = { pageId, title, entries: labels, offset: 0 };
    }
    const items = helpState.entries.slice(helpState.offset, helpState.offset + 8);
    helpState.offset += items.length;
    const more = helpState.offset < helpState.entries.length;
    const details = items.length ? items.join("; ") : "Eri\u015filebilir ek kontrol veya men\u00fc bulamad\u0131m";
    let message = `${helpState.title} ekran\u0131ndas\u0131n\u0131z. `;
    if (!continueListing) message += "Ekran\u0131 okuyabilir, sonraki alana ge\u00e7ebilir, dikte modunu a\u00e7abilir veya bu ekranda arama yapabilirsiniz. Kritik kaydetme, silme ve \u00f6deme ad\u0131mlar\u0131nda onay\u0131n\u0131z\u0131 isterim. ";
    message += `Kullan\u0131labilir oge listesi: ${details}.`;
    if (more) message += " Devam\u0131 i\u00e7in sonraki komutlar deyin.";
    else helpState = null;
    toast(message, "info");
    return true;
  };

  window.ayecExecuteVoiceAction = function (item, transcript = "") {
    const action = String(item?.action?.name || item?.action || item?.page || "");
    if (action === "musteri_bul") {
      const spoken = ` ${normalize(transcript)} `;
      const customers = (typeof customerDirectoryRows === "function" ? customerDirectoryRows() : [])
        .filter((customer) => customer && String(customer.name || "").trim())
        .sort((left, right) => String(right.name).length - String(left.name).length);
      const customer = customers.find((candidate) => {
        const name = normalize(candidate.name);
        return name && spoken.includes(` ${name} `);
      });
      navigate("customers");
      setTimeout(() => {
        const search = document.querySelector("#customerSearch");
        if (!search) return;
        search.value = customer ? customer.name : "";
        search.dispatchEvent(new Event("input", { bubbles: true }));
        search.focus();
      }, 0);
      toast(customer
        ? `M\u00fc\u015fteri aramas\u0131 haz\u0131r: ${customer.name}`
        : "M\u00fc\u015fteri listesi a\u00e7\u0131ld\u0131.", "info");
      return true;
    }
    if (action === "assistant_help") return showAssistantHelp(false);
    if (action === "voice_help_next") return showAssistantHelp(true);
    return baseAction(item, transcript);
  };
})();
