(() => {
  const button = document.querySelector("#assistantHeaderBtn");
  if (!button) return;
  const fab = document.querySelector("#assistantFab");
  let activeTrigger = button;

  let panel;
  let dragState = null;
  let voiceRecognition = null;
  let lastContentFocus = null;
  let dictationMode = false;
  let pendingFieldClear = null;
  let lastAssistantReply = "";
  let activeSpeechAudio = null;
  let activeSpeechUrl = "";
  let speechGeneration = 0;
  let lastVoiceFieldChange = null;
  let observedPage = String(document.body.dataset.page || "");
  let skipNextHistoryPush = false;
  const assistantPageHistory = [];

  if (typeof MutationObserver === "function") {
    new MutationObserver(() => {
      const nextPage = String(document.body.dataset.page || "");
      if (!nextPage || nextPage === observedPage) return;
      if (skipNextHistoryPush) skipNextHistoryPush = false;
      else if (observedPage) {
        assistantPageHistory.push(observedPage);
        if (assistantPageHistory.length > 100) assistantPageHistory.shift();
      }
      observedPage = nextPage;
    }).observe(document.body, { attributes: true, attributeFilter: ["data-page"] });
  }

  function activeAssistantContentRoot() {
    const dialog = document.querySelector("#appDialog");
    return dialog?.open ? dialog : document.querySelector("#content");
  }

  document.addEventListener("focusin", event => {
    const root = activeAssistantContentRoot();
    if (root?.contains(event.target)) lastContentFocus = event.target;
  });

  function resetVoiceInput() {
    const recognition = voiceRecognition;
    voiceRecognition = null;
    const voiceButton = panel?.querySelector("[data-assistant-voice]");
    if (voiceButton) {
      voiceButton.disabled = false;
      voiceButton.textContent = "\uD83C\uDF99";
      voiceButton.setAttribute("aria-label", dictationMode ? "Dikte modu acik" : "Sesli soru sor");
      voiceButton.setAttribute("aria-pressed", String(dictationMode));
    }
    if (recognition) {
      recognition.onend = null;
      try { recognition.abort(); } catch (_) {}
    }
  }

  function startVoiceInput() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const voiceButton = panel?.querySelector("[data-assistant-voice]");
    if (typeof Recognition !== "function" || !voiceButton) {
      if (typeof toast === "function") toast("Taray\u0131c\u0131 sesli soru \u00f6zelli\u011fini desteklemiyor.", "warning");
      return;
    }
    const recognition = new Recognition();
    voiceRecognition = recognition;
    recognition.lang = "tr-TR";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    voiceButton.disabled = true;
    voiceButton.textContent = "...";
    voiceButton.setAttribute("aria-label", dictationMode ? "Dikte ediliyor" : "Dinleniyor");
    recognition.onresult = event => {
      const transcript = String(event.results?.[0]?.[0]?.transcript || "").trim();
      if (!transcript) {
        if (typeof toast === "function") toast("Sesli soru alg\u0131lanamad\u0131.", "warning");
        return;
      }
      if (dictationMode) {
        const normalized = normalize(transcript);
        if (["dikteyi bitir", "dikte modunu kapat", "yazmayi bitir", "stop dictation"].some(phrase => normalized.includes(phrase))) {
          dictationMode = false;
          voiceButton.setAttribute("aria-pressed", "false");
          voiceButton.setAttribute("aria-label", "Sesli soru sor");
          addMessage("Dikte modunu kapattim.", true);
          return;
        }
        const result = appendDictation(transcript);
        addMessage(result.message, true);
        return;
      }
      const input = panel.querySelector("#desktopAssistantInput");
      if (!input) return;
      input.value = transcript;
      panel.querySelector(".desktop-assistant-compose")?.requestSubmit();
    };
    recognition.onerror = event => {
      if (typeof toast === "function") toast(event?.error === "not-allowed" ? "Mikrofon izni verilmedi." : "Sesli soru al\u0131namad\u0131.", "warning");
    };
    recognition.onend = () => {
      if (voiceRecognition !== recognition) return;
      voiceRecognition = null;
      voiceButton.disabled = false;
      voiceButton.textContent = "\uD83C\uDF99";
      voiceButton.setAttribute("aria-label", dictationMode ? "Dikte modu acik" : "Sesli soru sor");
    };
    try { recognition.start(); }
    catch (_) {
      resetVoiceInput();
      if (typeof toast === "function") toast("Mikrofon ba\u015flat\u0131lamad\u0131.", "warning");
    }
  }

  function ensurePanel() {
    if (panel) return panel;
    panel = document.createElement("aside");
    panel.id = "desktopAssistantPanel";
    panel.className = "desktop-assistant-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "AYEC Pro Core");
    panel.innerHTML = '<header class="desktop-assistant-head"><strong>AYEC Pro</strong><div class="desktop-assistant-head-actions"><button type="button" data-assistant-page-open aria-label="Bilgi Asistan\u0131 sayfas\u0131n\u0131 a\u00e7" title="Bilgi Asistan\u0131 sayfas\u0131n\u0131 a\u00e7">&#8599;</button><button type="button" data-assistant-close aria-label="Kapat">&#215;</button></div></header><div class="desktop-assistant-messages" aria-live="polite"><div class="desktop-assistant-message is-assistant">Merhaba! Size nasıl yardımcı olabilirim?</div></div><form class="desktop-assistant-compose"><input id="desktopAssistantInput" maxlength="1200" autocomplete="off" placeholder="Bir şeyler sorun..." aria-label="Asistana mesaj yazın"><button class="primary" type="submit">Gönder</button></form>';
    panel.querySelector("[data-assistant-page-open]").addEventListener("click", () => {
      closePanel();
      if (typeof navigate === "function") navigate("assistant");
    });
    document.body.appendChild(panel);
    const voiceButton = document.createElement("button");
    voiceButton.type = "button";
    voiceButton.className = "secondary desktop-assistant-voice";
    voiceButton.dataset.assistantVoice = "";
    voiceButton.setAttribute("aria-label", "Sesli soru sor");
    voiceButton.setAttribute("aria-pressed", "false");
    voiceButton.title = "Sesli soru sor";
    voiceButton.textContent = "\uD83C\uDF99";
    panel.querySelector(".desktop-assistant-compose button[type=submit]")?.before(voiceButton);
    panel.querySelector("[data-assistant-close]").addEventListener("click", closePanel);
    panel.querySelector(".desktop-assistant-compose").addEventListener("submit", sendMessage);
    panel.querySelector("[data-assistant-voice]").addEventListener("click", startVoiceInput);
    const header = panel.querySelector(".desktop-assistant-head");
    header.addEventListener("pointerdown", event => {
      if (event.button !== 0 || event.target.closest("button")) return;
      const rect = panel.getBoundingClientRect();
      dragState = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, left: rect.left, top: rect.top };
      panel.style.right = "auto";
      panel.style.bottom = "auto";
      event.preventDefault();
    });
    document.addEventListener("pointermove", event => {
      if (!dragState || event.pointerId !== dragState.pointerId) return;
      const maxLeft = Math.max(0, innerWidth - panel.offsetWidth);
      const maxTop = Math.max(0, innerHeight - panel.offsetHeight);
      panel.style.left = `${Math.max(0, Math.min(maxLeft, dragState.left + event.clientX - dragState.startX))}px`;
      panel.style.top = `${Math.max(0, Math.min(maxTop, dragState.top + event.clientY - dragState.startY))}px`;
    });
    document.addEventListener("pointerup", event => {
      if (dragState && event.pointerId === dragState.pointerId) dragState = null;
    });
    return panel;
  }

  function closePanel() {
    if (!panel) return;
    resetVoiceInput();
    stopReplySpeech();
    dictationMode = false;
    pendingFieldClear = null;
    panel.querySelector("[data-assistant-voice]")?.setAttribute("aria-pressed", "false");
    panel.hidden = true;
    button.setAttribute("aria-expanded", "false");
    fab?.setAttribute("aria-expanded", "false");
  }

  function openPanel() {
    const node = ensurePanel();
    node.hidden = false;
    button.setAttribute("aria-expanded", "true");
    fab?.setAttribute("aria-expanded", "true");
    node.querySelector("#desktopAssistantInput").focus();
  }

  function togglePanel(trigger) {
    activeTrigger = trigger;
    if (panel && !panel.hidden) closePanel();
    else openPanel();
  }

  function syncFabVisibility() {
    if (!fab) return;
    const internalSettings = typeof desktopInternalSettings === "undefined" ? {} : desktopInternalSettings;
    const settings = typeof desktopSettings === "undefined" ? {} : desktopSettings;
    const localSettings = typeof db === "undefined" ? {} : (db.settings || {});
    const configured = internalSettings.assistant_fab_enabled ?? settings.assistant_fab_enabled ?? localSettings.assistant_fab_enabled ?? "1";
    const hiddenPages = new Set(["customers", "field-service", "product-groups", "report-templates"]);
    fab.hidden = String(configured) === "0" || configured === false || hiddenPages.has(document.body.dataset.page || "");
  }

  function addMessage(text, isAssistant, shouldSpeak = true, rememberAssistant = true) {
    const node = document.createElement("div");
    node.className = `desktop-assistant-message ${isAssistant ? "is-assistant" : "is-user"}`;
    node.textContent = text;
    const list = panel.querySelector(".desktop-assistant-messages");
    list.appendChild(node);
    list.scrollTop = list.scrollHeight;
    if (isAssistant) {
      if (rememberAssistant) lastAssistantReply = String(text || "");
      if (shouldSpeak) speakReply(text);
    }
  }

  function stopReplySpeech() {
    speechGeneration += 1;
    try { window.speechSynthesis?.cancel(); } catch (_) {}
    if (activeSpeechAudio) {
      try { activeSpeechAudio.pause(); } catch (_) {}
      activeSpeechAudio = null;
    }
    if (activeSpeechUrl) {
      try { window.URL?.revokeObjectURL(activeSpeechUrl); } catch (_) {}
      activeSpeechUrl = "";
    }
  }

  async function speakReply(text) {
    const voiceSetting = typeof db !== "undefined" ? db.settings?.asistan_voice_enabled : undefined;
    if (voiceSetting === false || String(voiceSetting) === "0") return;
    stopReplySpeech();
    const generation = speechGeneration;
    try {
      const response = await fetch("/api/desktop/assistant/speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (generation !== speechGeneration) return;
      if (response.ok && typeof window.Audio === "function" && window.URL?.createObjectURL) {
        const audioUrl = window.URL.createObjectURL(await response.blob());
        if (generation !== speechGeneration) {
          window.URL.revokeObjectURL(audioUrl);
          return;
        }
        const audio = new window.Audio(audioUrl);
        activeSpeechUrl = audioUrl;
        activeSpeechAudio = audio;
        const release = () => {
          if (activeSpeechAudio === audio) activeSpeechAudio = null;
          if (activeSpeechUrl === audioUrl) activeSpeechUrl = "";
          window.URL.revokeObjectURL(audioUrl);
        };
        audio.addEventListener("ended", release, { once: true });
        audio.addEventListener("error", release, { once: true });
        try {
          await audio.play();
          return;
        } catch (_) {
          release();
        }
      }
    } catch (_) {}
    if (generation !== speechGeneration) return;
    if (!window.speechSynthesis || typeof window.SpeechSynthesisUtterance !== "function") return;
    try {
      const utterance = new window.SpeechSynthesisUtterance(text);
      utterance.lang = "tr-TR";
      window.speechSynthesis.speak(utterance);
    } catch (_) {}
  }

  function normalize(text) {
    return String(text || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("tr-TR")
      .replace(/\u0131/g, "i")
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function resolveNamedPage(text) {
    const tokens = normalize(text).split(" ").filter(Boolean);
    const leading = new Set(["hey", "merhaba", "selam", "asistan", "lutfen", "bana"]);
    const trailing = new Set(["lutfen", "ac", "acalim", "git", "goster", "goruntule", "sayfasini", "ekranini", "ekranina", "sayfasina"]);
    while (tokens.length && leading.has(tokens[0])) tokens.shift();
    while (tokens.length && trailing.has(tokens[tokens.length - 1])) tokens.pop();
    const spoken = tokens.join(" ");
    if (!spoken || typeof ayecSectorMenu !== "function") return null;
    const pages = [];
    const visit = items => {
      for (const item of items || []) {
        if (Array.isArray(item?.children)) visit(item.children);
        else if (item?.id && sectorPages[currentSector]?.has(item.id)) {
          const label = typeof labelFor === "function" ? labelFor(item, currentSector) : item.label || item.id;
          pages.push({ id: item.id, label: String(label || item.id) });
        }
      }
    };
    for (const group of ayecSectorMenu(currentSector) || []) visit(group.items || []);
    const matches = pages.filter(item => normalize(item.label) === spoken);
    return matches.length === 1 ? matches[0] : null;
  }

  function describeActivePageField() {
    const content = activeAssistantContentRoot();
    const active = document.activeElement;
    const control = content?.contains(active) ? active : content?.contains(lastContentFocus) ? lastContentFocus : null;
    if (!control) return "Okumak i\u00e7in i\u00e7erik alan\u0131nda bir kontrol se\u00e7in.";
    const label = String(control.getAttribute("aria-label") || control.labels?.[0]?.innerText || control.placeholder || control.name || control.id || "Alan").replace(/\s+/g, " ").trim();
    if (String(control.type || "").toLowerCase() === "password") return `${label}: parola alan\u0131 ${control.value ? "dolu" : "bo\u015f"}.`;
    const value = control instanceof HTMLSelectElement
      ? String(control.selectedOptions?.[0]?.textContent || "")
      : "value" in control ? String(control.value || "") : String(control.innerText || control.textContent || "");
    return `${label}: ${value.trim() || "bo\u015f"}.`;
  }

  function describeFormFeedback() {
    const root = activeAssistantContentRoot();
    if (!root) return "Kontrol edilecek bir form yok.";
    const markers = ["zorunlu", "gecersiz", "hata", "uyari", "eksik", "uygun degil", "invalid", "required", "error", "must be"];
    const feedback = [];
    root.querySelectorAll("label,small,p,[role=alert],.error,.warning,.field-error").forEach(node => {
      if (!node.getClientRects().length) return;
      const text = String(node.innerText || node.textContent || "").replace(/\\s+/g, " ").trim();
      if (text && markers.some(marker => normalize(text).includes(marker))) feedback.push(text);
    });
    root.querySelectorAll("input,textarea,select").forEach(control => {
      if (control.disabled || !control.getClientRects().length || !String(control.value || "").trim() || control.checkValidity()) return;
      const label = String(control.getAttribute("aria-label") || control.labels?.[0]?.innerText || control.name || control.id || "Alan").replace(/\\s+/g, " ").trim();
      feedback.push(`${label}: ${control.validationMessage || "deger dogrulamadan gecmedi."}`);
    });
    const unique = [...new Set(feedback)].slice(0, 8);
    return unique.length ? unique.join(". ") : "Gorunen bir form dogrulama hatasi yok.";
  }

  function describeFormStatus() {
    const root = activeAssistantContentRoot();
    if (!root) return "Durumu denetlenecek bir form yok.";
    const required = [...root.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="file"]),textarea,select')]
      .filter(control => !control.disabled && control.getClientRects().length > 0)
      .filter(control => control.required || control.getAttribute("aria-required") === "true");
    if (!required.length) return "Bu ekranda zorunlu metin alani yok.";
    const missing = required.filter(control => !String(control.value || "").trim());
    if (!missing.length) return "Zorunlu alan kalmadi.";
    const labels = missing.slice(0, 8).map(control => String(control.getAttribute("aria-label") || control.labels?.[0]?.innerText || control.placeholder || control.name || control.id || "zorunlu alan").replace(/\s+/g, " ").trim());
    return "Tamamlanmasi gereken zorunlu alanlar: " + labels.join(", ") + ".";
  }

  function searchActivePage(query) {
    const root = activeAssistantContentRoot();
    const value = String(query || "").trim();
    if (!root || !value) return { searched: false, message: "Aranacak metni soyleyin." };
    const markers = ["ara", "search", "bul", "filtre"];
    let fields = [...root.querySelectorAll('input:not([type="hidden"]):not([type="password"]):not([type="file"]):not([type="checkbox"]):not([type="radio"])')]
      .filter(field => !field.disabled && !field.readOnly && field.getClientRects().length > 0)
      .filter(field => {
        const label = normalize([field.getAttribute("aria-label"), field.labels?.[0]?.innerText, field.placeholder, field.name, field.id, field.title].filter(Boolean).join(" "));
        return markers.some(marker => label.includes(marker));
      });
    if (!fields.length) return { searched: false, message: "Bu ekranda sesle kullanilabilir bir arama alani bulamadim." };
    if (fields.length > 1) {
      const ranked = fields.filter(field => {
        const label = normalize([field.getAttribute("aria-label"), field.labels?.[0]?.innerText, field.placeholder, field.name, field.id, field.title].filter(Boolean).join(" "));
        return label.includes("ara") || label.includes("search");
      });
      fields = ranked.length ? ranked : fields;
    }
    if (fields.length !== 1) return { searched: false, message: "Birden fazla arama alani var. Hangi bolumde arayayim?" };
    const field = fields[0];
    const before = String(field.value || "");
    field.value = value;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
    if (before !== String(field.value || "")) rememberVoiceFieldChange(root, [{ control: field, value: before, selectedIndex: null, select: false }]);
    field.focus();
    return { searched: true, message: "Aramayi baslattim." };
  }

  function editFocusedTextControl(operation, value = "") {
    const root = activeAssistantContentRoot();
    const control = root?.contains(lastContentFocus) ? lastContentFocus : null;
    if (!isDictationTarget(control)) return { changed: false, message: "Once metin alanina odaklanin." };
    if (operation === "insert" && value.includes("\n") && !(control instanceof HTMLTextAreaElement)) {
      return { changed: false, message: "Yeni satir eklemek icin cok satirli bir metin alani secin." };
    }
    const text = String(control.value || "");
    let start = Number.isInteger(control.selectionStart) ? control.selectionStart : text.length;
    let end = Number.isInteger(control.selectionEnd) ? control.selectionEnd : start;
    if (operation === "cursor_start") start = end = 0;
    else if (operation === "cursor_end") start = end = text.length;
    else if (operation === "delete_word") {
      end = start;
      while (start > 0 && /\s/.test(text[start - 1])) start -= 1;
      while (start > 0 && !/\s/.test(text[start - 1])) start -= 1;
      if (start === end) return { changed: false, message: "Silinecek onceki bir kelime yok." };
      value = "";
    }
    control.setRangeText(String(value || ""), start, end, "end");
    if (operation === "cursor_start" || operation === "cursor_end") control.setSelectionRange(start, end);
    if (operation !== "cursor_start" && operation !== "cursor_end") {
      control.dispatchEvent(new Event("input", { bubbles: true }));
      control.dispatchEvent(new Event("change", { bubbles: true }));
      if (text !== String(control.value || "")) rememberVoiceFieldChange(root, [{ control, value: text, selectedIndex: null, select: false }]);
    }
    control.focus();
    const messages = { cursor_start: "Imleci alanin basina aldim.", cursor_end: "Imleci alanin sonuna aldim.", delete_word: "Onceki kelimeyi sildim.", insert: "Metin alanini guncelledim." };
    return { changed: true, message: messages[operation] || "Metin alanini guncelledim." };
  }

  function requestFocusedFieldClear() {
    const root = activeAssistantContentRoot();
    const control = root?.contains(lastContentFocus) ? lastContentFocus : null;
    if (!isDictationTarget(control)) return { pending: false, message: "Once temizlenecek metin alanina odaklanin." };
    const value = String(control.value || "");
    if (!value.trim()) return { pending: false, message: "Alan zaten bos." };
    pendingFieldClear = { root, entries: [{ control, value, selectedIndex: null, select: false }] };
    return { pending: true, message: "Alan dolu. Icerigini temizlememi onayliyor musunuz? Evet ya da hayir deyin." };
  }

  function requestNamedFieldClear(spokenLabel) {
    const root = activeAssistantContentRoot();
    const target = normalize(spokenLabel);
    const controls = [...(root?.querySelectorAll("input,textarea") || [])]
      .filter(control => isDictationTarget(control) && control.getClientRects().length > 0);
    const matches = controls.filter(control => {
      const label = normalize([control.getAttribute("aria-label"), control.labels?.[0]?.innerText, control.placeholder, control.name, control.id, control.title].filter(Boolean).join(" "));
      return target && (target === label || label.includes(target));
    });
    if (matches.length !== 1) return { pending: false, message: "Alan adi tek bir metin alanina eslesmedi." };
    const control = matches[0];
    const value = String(control.value || "");
    if (!value.trim()) return { pending: false, message: "Alan zaten bos." };
    pendingFieldClear = { root, entries: [{ control, value, selectedIndex: null, select: false }] };
    return { pending: true, message: "Belirtilen alan dolu. Icerigini temizlememi onayliyor musunuz? Evet ya da hayir deyin." };
  }

  function requestFormReset() {
    const root = activeAssistantContentRoot();
    if (!root) return { pending: false, message: "Temizlenecek bir form alani bulamadim." };
    const entries = [...root.querySelectorAll('input:not([type="hidden"]):not([type="password"]):not([type="file"]):not([type="checkbox"]):not([type="radio"]),textarea,select')]
      .filter(control => !control.disabled && !control.readOnly && control.getClientRects().length > 0)
      .filter(control => control instanceof HTMLSelectElement ? control.selectedIndex > 0 : String(control.value || "").trim())
      .map(control => ({
        control,
        value: String(control.value || ""),
        selectedIndex: control instanceof HTMLSelectElement ? control.selectedIndex : null,
        select: control instanceof HTMLSelectElement,
      }));
    if (!entries.length) return { pending: false, message: "Temizlenecek dolu form alani yok." };
    pendingFieldClear = { root, entries };
    return { pending: true, message: `Formdaki ${entries.length} dolu alan temizlenecek. Onaylamak icin evet, iptal etmek icin hayir deyin.` };
  }

  function resolveFieldClear(confirmed) {
    const pending = pendingFieldClear;
    pendingFieldClear = null;
    if (!pending) return { changed: false, message: "Onay bekleyen bir alan temizleme istegi yok." };
    if (!confirmed) return { changed: false, message: "Alan temizleme istegini iptal ettim." };
    const root = activeAssistantContentRoot();
    const unchanged = root === pending.root && pending.entries.every(entry => root.contains(entry.control)
      && (entry.select ? entry.control.selectedIndex === entry.selectedIndex : String(entry.control.value || "") === entry.value));
    if (!unchanged) {
      return { changed: false, message: "Alan degisti. Guvenlik icin temizleme istegini iptal ettim." };
    }
    pending.entries.forEach(entry => {
      if (entry.select) entry.control.selectedIndex = 0;
      else {
        entry.control.value = "";
        if (typeof entry.control.setSelectionRange === "function") {
          try { entry.control.setSelectionRange(0, 0); } catch (_) {}
        }
      }
      entry.control.dispatchEvent(new Event("input", { bubbles: true }));
      entry.control.dispatchEvent(new Event("change", { bubbles: true }));
    });
    rememberVoiceFieldChange(root, pending.entries);
    pending.entries[0].control.focus();
    return { changed: true, message: pending.entries.length === 1 ? "Metin alanini temizledim." : `Formdaki ${pending.entries.length} alani temizledim.` };
  }

  function rememberVoiceFieldChange(root, entries) {
    lastVoiceFieldChange = {
      root,
      entries: entries.map(entry => ({
        ...entry,
        afterValue: String(entry.control.value || ""),
        afterIndex: entry.select ? entry.control.selectedIndex : null,
      })),
    };
  }

  function undoLastFieldChange() {
    const change = lastVoiceFieldChange;
    if (!change) return { changed: false, message: "Geri alinabilecek son bir sesli alan degisikligi yok." };
    lastVoiceFieldChange = null;
    const root = activeAssistantContentRoot();
    const unchanged = root === change.root && change.entries.every(entry => root.contains(entry.control)
      && (entry.select ? entry.control.selectedIndex === entry.afterIndex : String(entry.control.value || "") === entry.afterValue));
    if (!unchanged) return { changed: false, message: "Alanlardan biri sonradan degistigi icin mevcut degerleri korudum." };
    change.entries.forEach(entry => {
      if (entry.select) entry.control.selectedIndex = entry.selectedIndex;
      else entry.control.value = entry.value;
      entry.control.dispatchEvent(new Event("input", { bubbles: true }));
      entry.control.dispatchEvent(new Event("change", { bubbles: true }));
    });
    change.entries[0].control.focus();
    return { changed: true, message: change.entries.length > 1 ? "Son sesli form temizlemesini geri aldim." : "Son sesli alan temizlemesini geri aldim." };
  }

  function navigateAssistantBack() {
    const currentPage = String(document.body.dataset.page || "");
    let previousPage = "";
    while (assistantPageHistory.length && !previousPage) {
      const candidate = assistantPageHistory.pop();
      if (candidate && candidate !== currentPage) previousPage = candidate;
    }
    if (!previousPage || typeof navigate !== "function") return { moved: false, message: "Geri donulecek bir ekran gecmisi yok." };
    skipNextHistoryPush = true;
    navigate(previousPage);
    return { moved: String(document.body.dataset.page || "") !== currentPage, message: "Onceki ekrana dondum." };
  }

  function visibleRecordRows() {
    const root = activeAssistantContentRoot();
    if (!root) return [];
    return [...root.querySelectorAll("table tbody tr, [role=grid] [role=row], [role=table] [role=row]")]
      .filter(row => row.getClientRects().length > 0 && String(row.innerText || row.textContent || "").trim());
  }

  function moveRecordSelection(forward) {
    const rows = visibleRecordRows();
    if (!rows.length) return { moved: false, message: "Bu ekranda gezilebilir bir kayit listesi yok." };
    const root = activeAssistantContentRoot();
    const focused = root?.contains(document.activeElement) ? document.activeElement.closest("tr,[role=row]") : null;
    const selected = rows.find(row => row.classList.contains("desktop-assistant-voice-selected"))
      || rows.find(row => row.getAttribute("aria-selected") === "true")
      || (rows.includes(focused) ? focused : null);
    const index = rows.indexOf(selected);
    const targetIndex = index < 0 ? 0 : Math.max(0, Math.min(rows.length - 1, index + (forward ? 1 : -1)));
    rows.forEach(row => {
      row.classList.remove("desktop-assistant-voice-selected");
      if (row.getAttribute("aria-selected") === "true") row.setAttribute("aria-selected", "false");
    });
    const target = rows[targetIndex];
    target.classList.add("desktop-assistant-voice-selected");
    target.setAttribute("aria-selected", "true");
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "0");
    target.focus();
    target.scrollIntoView?.({ block: "nearest" });
    const label = String(target.innerText || target.textContent || "").replace(/\s+/g, " ").trim().slice(0, 320);
    return { moved: true, message: label || "Kaydi sectim." };
  }

  function activateSelectedRecord() {
    const root = activeAssistantContentRoot();
    if (!root) return { opened: false, message: "Acik ekran bulunamadi." };
    const rows = visibleRecordRows();
    const row = rows.find(item => item.classList.contains("desktop-assistant-voice-selected"))
      || rows.find(item => item.getAttribute("aria-selected") === "true");
    if (!row) return { opened: false, message: "Once acmak istediginiz kaydi listeden secin." };
    row.focus();
    row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, view: window }));
    return { opened: true, message: "Secili kaydi acma komutunu gonderdim." };
  }

  function scrollActivePage(forward) {
    const root = activeAssistantContentRoot();
    if (!root) return { moved: false, message: "Kaydirilacak bir ekran yok." };
    const candidates = [root, ...root.querySelectorAll("*")];
    const area = candidates.find(node => {
      if (!node.getClientRects().length || node.scrollHeight <= node.clientHeight + 1) return false;
      const style = getComputedStyle(node);
      return style.overflowY === "auto" || style.overflowY === "scroll";
    });
    if (!area) return { moved: false, message: "Bu ekranda kaydirilabilir bir bolum bulamadim." };
    const delta = Math.max(40, Math.round(area.clientHeight * 0.7));
    const before = area.scrollTop;
    area.scrollTop = Math.max(0, Math.min(area.scrollHeight - area.clientHeight, before + (forward ? delta : -delta)));
    return { moved: area.scrollTop !== before, message: forward ? "Ekrani asagi kaydirdim." : "Ekrani yukari kaydirdim." };
  }

  function isDictationTarget(control) {
    if (!control || String(control.type || "").toLowerCase() === "password") return false;
    return control instanceof HTMLTextAreaElement
      || (control instanceof HTMLInputElement && ["text", "search", "email", "url", "tel"].includes(String(control.type || "text").toLowerCase()));
  }

  function appendDictation(text) {
    const root = activeAssistantContentRoot();
    const control = root?.contains(lastContentFocus) ? lastContentFocus : null;
    if (!isDictationTarget(control)) return { ok: false, message: "Once yazilacak metin alanina odaklanin." };
    const value = String(text || "").trim();
    if (!value) return { ok: false, message: "Dikte edilecek metin algilanmadi." };
    const current = String(control.value || "");
    const separator = current.trim() ? (control instanceof HTMLTextAreaElement ? "\n" : " ") : "";
    control.value = current + separator + value;
    control.setSelectionRange?.(control.value.length, control.value.length);
    control.dispatchEvent(new Event("input", { bubbles: true }));
    control.dispatchEvent(new Event("change", { bubbles: true }));
    rememberVoiceFieldChange(root, [{ control, value: current, selectedIndex: null, select: false }]);
    control.focus();
    return { ok: true, message: "Metni odaklanan alana ekledim." };
  }

  function movePageFocus(forward) {
    const root = activeAssistantContentRoot();
    if (!root) return { moved: false, message: "Odaklanacak bir i\u00e7erik alan\u0131 yok." };
    const selector = 'button:not([disabled]),a[href],input:not([type="hidden"]):not([disabled]),select:not([disabled]),textarea:not([disabled]),[role="button"]:not([aria-disabled="true"]),[tabindex]:not([tabindex="-1"])';
    const controls = [...root.querySelectorAll(selector)].filter((control, index, items) => {
      if (items.indexOf(control) !== index || control.disabled || control.getClientRects().length === 0) return false;
      const style = getComputedStyle(control);
      return style.display !== "none" && style.visibility !== "hidden";
    });
    if (!controls.length) return { moved: false, message: "Odaklan\u0131lacak ba\u015fka bir kontrol yok." };
    const current = root.contains(document.activeElement) ? document.activeElement : root.contains(lastContentFocus) ? lastContentFocus : null;
    const index = controls.indexOf(current);
    const nextIndex = index < 0 ? (forward ? 0 : controls.length - 1) : (index + (forward ? 1 : -1) + controls.length) % controls.length;
    const target = controls[nextIndex];
    target.focus();
    lastContentFocus = target;
    const label = String(target.getAttribute("aria-label") || target.title || target.innerText || target.value || target.labels?.[0]?.innerText || target.placeholder || target.id || "kontrol").replace(/\s+/g, " ").trim();
    return { moved: true, message: `${label} kontrol\u00fcne odakland\u0131m.` };
  }

  async function sendMessage(event) {
    event.preventDefault();
    const input = panel.querySelector("#desktopAssistantInput");
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, false);
    input.value = "";
    const submit = panel.querySelector('.desktop-assistant-compose button[type="submit"]');
    input.disabled = true;
    if (submit) submit.disabled = true;

    const normalized = normalize(text);
    const repeatSpeechRequested = ["son cevabi tekrarla", "son yaniti tekrarla", "tekrarla", "repeat last"].includes(normalized);
    const stopSpeechRequested = ["konusmayi durdur", "sesli yaniti durdur", "konusmayi kes", "stop speech"].includes(normalized);
    const actions = [
      { phrases: ["finans ozeti", "finansal ozet", "mali ozet", "kasa ozeti"], route: "finance", reply: "Finansal \u00f6zeti a\u00e7\u0131yorum." },
      { phrases: ["stok ozeti", "stok durumu", "stok listesi"], route: "stock", reply: "Stok \u00f6zetini a\u00e7\u0131yorum." },
      { phrases: ["randevular", "randevu listesi"], route: "appointments", reply: "Randevular\u0131 a\u00e7\u0131yorum." },
    ];
    const action = actions.find(item => item.phrases.some(phrase => normalized.includes(phrase)));
    const pageTarget = action ? null : resolveNamedPage(text);
    const readScreenRequested = ["ekrani oku", "sayfayi oku", "read screen"].some(phrase => normalized.includes(phrase));
    const readFieldRequested = ["alani oku", "odaklanan alani oku", "read field"].some(phrase => normalized.includes(phrase));
    const readFormFeedbackRequested = ["form geri bildirimini oku", "form hatalarini oku", "eksik alanlari oku", "read form feedback"].some(phrase => normalized.includes(phrase));
    const formStatusRequested = ["form durumu", "zorunlu alanlari kontrol et", "form status"].includes(normalized);
    const screenSearchRequested = ["bu ekranda ara", "sayfada ara", "ekranda ara", "burada ara", "search this screen"].some(phrase => normalized.includes(phrase));
    const textEditCommand = [
      { phrases: ["virgul ekle", "virgul koy", "insert comma"], operation: "insert", value: ", " },
      { phrases: ["nokta ekle", "nokta koy", "insert period"], operation: "insert", value: ". " },
      { phrases: ["yeni satir ekle", "alt satira gec", "insert newline"], operation: "insert", value: "\n" },
      { phrases: ["son kelimeyi sil", "onceki kelimeyi sil", "delete word"], operation: "delete_word" },
      { phrases: ["imleci basa al", "imleci basa gotur", "cursor start"], operation: "cursor_start" },
      { phrases: ["imleci sona al", "imleci sona gotur", "cursor end"], operation: "cursor_end" },
    ].find(item => item.phrases.some(phrase => normalized.includes(phrase)));
    const clearFieldRequested = ["alani temizle", "metni temizle", "clear field"].includes(normalized);
    const pendingCancelRequested = ["bekleyen islemi iptal et", "bekleyen islemi iptal", "iptal et", "cancel pending"].includes(normalized);
    const namedFieldClearMatch = normalized.match(/^(.+?) (?:alanini|metnini) temizle$/) || normalized.match(/^clear field (.+)$/);
    const formResetRequested = ["formu sifirla", "formu temizle", "form alanlarini temizle", "reset form"].includes(normalized);
    const voiceUndoRequested = ["geri al", "son degisikligi geri al", "sesli degisikligi geri al", "undo"].includes(normalized);
    const affirmativeConfirmation = ["evet", "onayla", "confirm yes", "yes"].includes(normalized);
    const negativeConfirmation = ["hayir", "iptal", "confirm no", "no"].includes(normalized);
    const recordDirection = ["sonraki kaydi sec", "sonraki kayit", "select next record"].some(phrase => normalized.includes(phrase)) ? 1
      : ["onceki kaydi sec", "onceki kayit", "select previous record"].some(phrase => normalized.includes(phrase)) ? -1 : 0;
    const openRecordRequested = ["secili kaydi ac", "kaydi ac", "open selected record"].some(phrase => normalized.includes(phrase));
    const navigateBackRequested = ["onceki ekrana don", "onceki sayfaya don", "geri git", "navigate back"].includes(normalized);
    const stockOcrRequested = ["stok ocr ice aktar", "stok resmi oku", "stock ocr import"].some(phrase => normalized.includes(phrase));
    const dictationStartRequested = ["dikte modunu ac", "dikteye basla", "yazmaya basla", "start dictation"].some(phrase => normalized.includes(phrase));
    const dictationStopRequested = ["dikteyi bitir", "dikte modunu kapat", "yazmayi bitir", "stop dictation"].some(phrase => normalized.includes(phrase));
    const scrollDirection = ["asagi kaydir", "ekrani asagi kaydir", "scroll down"].some(phrase => normalized.includes(phrase)) ? 1
      : ["yukari kaydir", "ekrani yukari kaydir", "scroll up"].some(phrase => normalized.includes(phrase)) ? -1 : 0;
    const focusDirection = ["sonraki alana gec", "sonraki kontrol", "next field"].some(phrase => normalized.includes(phrase)) ? 1
      : ["onceki alana gec", "onceki kontrol", "previous field"].some(phrase => normalized.includes(phrase)) ? -1 : 0;
    let keepPageFocus = false;
    try {
      if (pendingCancelRequested) {
        const hadPending = Boolean(pendingFieldClear);
        pendingFieldClear = null;
        keepPageFocus = Boolean(lastContentFocus && activeAssistantContentRoot()?.contains(lastContentFocus));
        addMessage(hadPending ? "Bekleyen sesli islemi iptal ettim." : "Iptal edilecek bekleyen bir islem yok.", true);
      } else if (pendingFieldClear && affirmativeConfirmation) {
        const result = resolveFieldClear(true);
        keepPageFocus = result.changed;
        addMessage(result.message, true);
      } else if (pendingFieldClear && negativeConfirmation) {
        const result = resolveFieldClear(false);
        keepPageFocus = Boolean(lastContentFocus && activeAssistantContentRoot()?.contains(lastContentFocus));
        addMessage(result.message, true);
      } else {
        if (pendingFieldClear) {
          pendingFieldClear = null;
          addMessage("Bekleyen alan temizleme istegini iptal ettim.", true);
        }
        if (affirmativeConfirmation || negativeConfirmation) {
          addMessage("Onay bekleyen bir alan temizleme istegi yok.", true);
        } else if (stopSpeechRequested) {
          stopReplySpeech();
          addMessage("Sesli yaniti durdurdum.", true, false, false);
        } else if (repeatSpeechRequested) {
          const reply = lastAssistantReply;
          if (reply) {
            addMessage("Son yaniti tekrar ediyorum.", true, false, false);
            speakReply(reply);
          } else {
            addMessage("Tekrar edebilecegim onceki bir yanit yok.", true, false, false);
          }
        } else if (recordDirection) {
          const result = moveRecordSelection(recordDirection > 0);
          keepPageFocus = result.moved;
          addMessage(result.message, true);
        } else if (openRecordRequested) {
          const result = activateSelectedRecord();
          keepPageFocus = result.opened;
          addMessage(result.message, true);
        } else if (navigateBackRequested) {
          const result = navigateAssistantBack();
          keepPageFocus = result.moved;
          addMessage(result.message, true);
        } else if (stockOcrRequested) {
          if (typeof navigate === "function" && sectorPages[currentSector]?.has("import")) {
            navigate("import");
            setTimeout(() => document.querySelector('[data-action="choose-import-mode"][data-mode="image"]')?.click(), 0);
            addMessage("Stok gorseli ice aktarma secimini aciyorum.", true);
          } else {
            addMessage("Stok ice aktarma ekrani bu modulde kullanilamiyor.", true);
          }
        } else if (dictationStartRequested) {
        const root = activeAssistantContentRoot();
        const control = root?.contains(lastContentFocus) ? lastContentFocus : null;
        if (isDictationTarget(control)) {
          dictationMode = true;
          keepPageFocus = true;
          const voiceButton = panel.querySelector("[data-assistant-voice]");
          voiceButton?.setAttribute("aria-pressed", "true");
          voiceButton?.setAttribute("aria-label", "Dikte modu acik");
          addMessage("Dikte modu acik. Metin alanina donup konusun; bitirmek icin dikteyi bitir deyin.", true);
        } else {
          addMessage("Once yazilacak metin alanina odaklanin.", true);
        }
      } else if (dictationStopRequested) {
        dictationMode = false;
        keepPageFocus = true;
        const voiceButton = panel.querySelector("[data-assistant-voice]");
        voiceButton?.setAttribute("aria-pressed", "false");
        voiceButton?.setAttribute("aria-label", "Sesli soru sor");
        addMessage("Dikte modunu kapattim.", true);
      } else if (screenSearchRequested) {
        const match = text.match(/(?:bu ekranda ara|sayfada ara|ekranda ara|burada ara|search this screen)\s+(.+)$/i);
        const result = searchActivePage(match?.[1] || "");
        keepPageFocus = result.searched;
        addMessage(result.message, true);
      } else if (textEditCommand) {
        const result = editFocusedTextControl(textEditCommand.operation, textEditCommand.value);
        keepPageFocus = result.changed || Boolean(lastContentFocus && activeAssistantContentRoot()?.contains(lastContentFocus));
        addMessage(result.message, true);
      } else if (clearFieldRequested) {
        const result = requestFocusedFieldClear();
        keepPageFocus = result.pending;
        addMessage(result.message, true);
      } else if (namedFieldClearMatch) {
        const result = requestNamedFieldClear(namedFieldClearMatch[1]);
        keepPageFocus = result.pending;
        addMessage(result.message, true);
      } else if (formResetRequested) {
        const result = requestFormReset();
        keepPageFocus = result.pending;
        addMessage(result.message, true);
      } else if (voiceUndoRequested) {
        const result = undoLastFieldChange();
        keepPageFocus = result.changed;
        addMessage(result.message, true);
      } else if (focusDirection) {
        const result = movePageFocus(focusDirection > 0);
        keepPageFocus = result.moved;
        addMessage(result.message, true);
      } else if (scrollDirection) {
        const result = scrollActivePage(scrollDirection > 0);
        keepPageFocus = true;
        addMessage(result.message, true);
      } else if (readFieldRequested) {
        addMessage(describeActivePageField(), true);
      } else if (readFormFeedbackRequested) {
        addMessage(describeFormFeedback(), true);
      } else if (formStatusRequested) {
        addMessage(describeFormStatus(), true);
      } else if (readScreenRequested) {
        const screenText = String(document.querySelector("#content")?.innerText || "").replace(/\s+/g, " ").trim();
        addMessage(screenText ? screenText.slice(0, 1800) : "Okunacak ekran i\u00e7eri\u011fi bulunamad\u0131.", true);
      } else if (action) {
        addMessage(action.reply, true);
        if (typeof navigate === "function") navigate(action.route);
      } else if (pageTarget) {
        addMessage(`${pageTarget.label} sayfas\u0131na ge\u00e7iyorum.`, true);
        if (typeof navigate === "function") navigate(pageTarget.id);
      } else {
        const result = await apiFetch("/api/desktop/assistant/query", {
          method: "POST",
          body: JSON.stringify({ question: text }),
        });
        if (!result?.success) throw new Error(result?.error || "Asistan yan\u0131t \u00fcretemedi.");
        addMessage(String(result.answer || "Yan\u0131t bulunamad\u0131."), true);
      }
      }
    } catch (error) {
      addMessage(`Hata: ${error.message || "Asistan hizmeti kullan\u0131lam\u0131yor."}`, true);
    } finally {
      input.disabled = false;
      if (submit) submit.disabled = false;
      if (!keepPageFocus) input.focus();
    }
  }

  button.innerHTML = "&#129302;";
  button.setAttribute("aria-label", "AYEC Pro asistan\u0131n\u0131 a\u00e7");
  button.setAttribute("title", "AYEC Pro Core");
  button.setAttribute("aria-controls", "desktopAssistantPanel");
  button.setAttribute("aria-expanded", "false");
  button.onclick = event => {
    event.preventDefault();
    togglePanel(button);
  };
  if (fab) fab.onclick = event => {
    event.preventDefault();
    togglePanel(fab);
  };
  syncFabVisibility();
  window.syncDesktopAssistantFab = syncFabVisibility;
  const content = document.querySelector("#content");
  if (content) new MutationObserver(syncFabVisibility).observe(content, { childList: true, subtree: true });
  new MutationObserver(syncFabVisibility).observe(document.body, { attributes: true, attributeFilter: ["data-page"] });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && panel && !panel.hidden) {
      closePanel();
      activeTrigger.focus();
    }
  });
})();
