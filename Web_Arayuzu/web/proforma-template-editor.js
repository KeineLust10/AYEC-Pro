(function () {
  "use strict";

  settingsGroups.push(["TASARIM", [["proforma-template", "[PDF]", "Proforma Sablonu"]]]);
  settingsDefinitions.company.fields = settingsDefinitions.company.fields.filter(([key]) => key !== "proforma_template_path");

  const tokens = [
    ["Firma adi", "{{firma_adi}}"], ["Musteri", "{{musteri_adi}}"],
    ["Yetkili", "{{yetkili}}"], ["Proje", "{{proje}}"],
    ["Teklif no", "{{teklif_no}}"], ["Tarih", "{{tarih}}"],
    ["Gecerlilik", "{{gecerlilik}}"], ["Para birimi", "{{para_birimi}}"],
    ["Logo", "{{logo}}"], ["Urun tablosu", "{{urun_tablosu}}"],
    ["Toplamlar", "{{toplamlar}}"], ["Ticari kosullar", "{{ticari_kosullar}}"],
    ["Imza alani", "{{imza_alani}}"]
  ];
  const starter = [
    "<p><b>{{firma_adi}}</b></p>", "<p>PROFORMA</p>", "<p>Teklif: {{teklif_no}} | Tarih: {{tarih}} | Gecerlilik: {{gecerlilik}}</p>",
    "<p>Musteri: {{musteri_adi}} | Yetkili: {{yetkili}} | Proje: {{proje}}</p>", "{{urun_tablosu}}", "{{toplamlar}}",
    "<p>{{ticari_kosullar}}</p>", "{{imza_alani}}"
  ].join("\n");

  const templateTags = new Set(["P", "DIV", "BR", "B", "STRONG", "I", "EM", "U", "S", "SPAN", "UL", "OL", "LI", "TABLE", "THEAD", "TBODY", "TR", "TD", "TH", "H1", "H2", "H3", "H4", "H5", "H6", "IMG", "HR", "BLOCKQUOTE"]);
  const discardTags = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED", "SVG", "MATH", "FORM", "INPUT", "BUTTON"]);
  let activeLegacyImagePlaceholder = null;

  function localImageName(source) {
    const value = String(source || "").trim();
    let path = value;
    if (/^file:/i.test(value)) {
      try {
        const url = new URL(value);
        path = `${url.hostname ? `/${url.hostname}` : ""}${decodeURIComponent(url.pathname)}`;
      } catch (_) { return ""; }
    } else if (!/^(?:[a-z]:[\\/]|\\\\)/i.test(value)) return "";
    path = path.replace(/\\/g, "/").split(/[?#]/, 1)[0];
    return path.split("/").filter(Boolean).pop() || "";
  }

  function sanitizeTemplateHtml(markup) {
    const parsed = new DOMParser().parseFromString(String(markup || ""), "text/html");
    for (const element of [...parsed.body.querySelectorAll("*")]) {
      if (!templateTags.has(element.tagName)) {
        if (discardTags.has(element.tagName)) element.remove();
        else element.replaceWith(...element.childNodes);
        continue;
      }
      const imageSource = element.tagName === "IMG" ? element.getAttribute("src") || "" : "";
      const legacyImage = element.tagName === "SPAN" && element.classList.contains("proforma-legacy-image")
        ? element.getAttribute("data-proforma-legacy-image") || ""
        : "";
      const spans = element.tagName === "TD" || element.tagName === "TH"
        ? { colspan: element.getAttribute("colspan"), rowspan: element.getAttribute("rowspan") }
        : null;
      const styleValues = [];
      for (const declaration of (element.getAttribute("style") || "").split(";")) {
        const separator = declaration.indexOf(":");
        if (separator < 0) continue;
        const key = declaration.slice(0, separator).trim().toLowerCase();
        const value = declaration.slice(separator + 1).trim();
        if (key === "text-align" && /^(left|center|right|justify)$/i.test(value)) styleValues.push(`text-align:${value.toLowerCase()}`);
        if (key === "color" && /^(#[0-9a-f]{3,8}|rgb\(\s*[0-9, %]+\s*\))$/i.test(value)) styleValues.push(`color:${value}`);
        if (key === "font-family" && /^[A-Za-z0-9 ,_-]{1,64}$/.test(value.replace(/['\"]/g, ""))) styleValues.push(`font-family:${value}`);
        if (key === "font-size" && /^(?:[8-9]|1[0-9]|2[0-8])(?:\.\d+)?pt$/i.test(value)) styleValues.push(`font-size:${value}`);
        if (key === "font-weight" && /^(normal|bold|[1-9]00)$/i.test(value)) styleValues.push(`font-weight:${value}`);
        if (key === "font-style" && /^(normal|italic)$/i.test(value)) styleValues.push(`font-style:${value}`);
        if (key === "text-decoration" && /^(none|underline|line-through)$/i.test(value)) styleValues.push(`text-decoration:${value}`);
      }
      for (const attribute of [...element.attributes]) element.removeAttribute(attribute.name);
      if (styleValues.length) element.setAttribute("style", styleValues.join(";"));
      if (legacyImage) {
        element.className = "proforma-legacy-image";
        element.setAttribute("data-proforma-legacy-image", legacyImage);
        element.setAttribute("contenteditable", "false");
        element.setAttribute("role", "button");
        element.setAttribute("tabindex", "0");
      }
      if (element.tagName === "IMG") {
        if (/^data:image\/(?:png|jpeg);base64,[A-Za-z0-9+/=]{16,180000}$/.test(imageSource)) element.setAttribute("src", imageSource);
        else {
          const fileName = localImageName(imageSource);
          if (!fileName) element.remove();
          else {
            const placeholder = parsed.createElement("span");
            placeholder.className = "proforma-legacy-image";
            placeholder.setAttribute("data-proforma-legacy-image", fileName);
            placeholder.setAttribute("contenteditable", "false");
            placeholder.setAttribute("role", "button");
            placeholder.setAttribute("tabindex", "0");
            placeholder.textContent = `\u00d6nceki masa\u00fcst\u00fc g\u00f6rseli: ${fileName} (de\u011fi\u015ftirmek i\u00e7in t\u0131klay\u0131n)`;
            element.replaceWith(placeholder);
          }
        }
      }
      if (spans) {
        for (const key of ["colspan", "rowspan"]) {
          if (/^[1-9][0-9]?$/.test(spans[key] || "")) element.setAttribute(key, spans[key]);
        }
      }
    }
    return parsed.body.innerHTML;
  }

  let savedEditorRange = null;

  function templateCanvas() { return document.getElementById("proformaTemplateCanvas"); }
  function templateSource() { return document.getElementById("proformaTemplateHtml"); }
  function syncSourceFromCanvas() {
    const canvas = templateCanvas();
    const source = templateSource();
    if (canvas && source) source.value = sanitizeTemplateHtml(canvas.innerHTML);
  }
  function unresolvedLegacyImageCount() {
    return templateCanvas()?.querySelectorAll(".proforma-legacy-image").length || 0;
  }
  function editorRange() {
    const canvas = templateCanvas();
    if (!canvas) return null;
    const selection = window.getSelection();
    if (selection?.rangeCount && canvas.contains(selection.getRangeAt(0).commonAncestorContainer)) return selection.getRangeAt(0).cloneRange();
    if (savedEditorRange && canvas.contains(savedEditorRange.commonAncestorContainer)) return savedEditorRange.cloneRange();
    const range = document.createRange();
    range.selectNodeContents(canvas);
    range.collapse(false);
    return range;
  }
  function rememberEditorRange() {
    const canvas = templateCanvas();
    const selection = window.getSelection();
    if (canvas && selection?.rangeCount && canvas.contains(selection.getRangeAt(0).commonAncestorContainer)) savedEditorRange = selection.getRangeAt(0).cloneRange();
  }
  function insertEditorNode(node) {
    const canvas = templateCanvas();
    const range = editorRange();
    if (!canvas || !range) return;
    range.deleteContents();
    range.insertNode(node);
    const selection = window.getSelection();
    const nextRange = document.createRange();
    nextRange.setStartAfter(node);
    nextRange.collapse(true);
    selection.removeAllRanges();
    selection.addRange(nextRange);
    savedEditorRange = nextRange.cloneRange();
    canvas.focus();
    syncSourceFromCanvas();
  }

  function renderEditor() {
    activeLegacyImagePlaceholder = null;
    const html = sanitizeTemplateHtml(desktopSettings.proforma_editor_html || "");
    const active = ["1", "true", "True"].includes(String(desktopSettings.proforma_use_custom_editor || "0"));
    const customPdfUploaded = String(desktopSettings.proforma_template_uploaded || "0") === "1";
    const customPdfName = String(desktopSettings.proforma_template_filename || "");
    const legacyPdfNotice = String(desktopSettings.proforma_local_pdf_path_present || "0") === "1" && !customPdfUploaded ? '<p class="proforma-legacy-pdf-notice" role="status">Yerel PDF yolu web taray\u0131c\u0131s\u0131na aktar\u0131lmad\u0131. Dosyay\u0131 yeniden se\u00e7ip y\u00fckleyin.</p>' : "";
    return `<div class="proforma-template-editor">
      <header class="proforma-template-head"><div><h3>Proforma Sablon Tasarimcisi</h3><p>HTML sablonunu duzenleyin, ortak ayarlara kaydedin ve PC Builder proforma penceresinden secin.</p></div><label class="proforma-template-active"><input class="exact-setting" type="checkbox" data-setting-scope="settings" data-setting-key="proforma_use_custom_editor" ${active ? "checked" : ""}><span>Sablonu etkinlestir</span></label></header>
      <section class="proforma-custom-pdf"><div><strong>Ozel PDF arka plan sablonu</strong><p>${customPdfUploaded ? `Yuklu dosya: ${esc(customPdfName)}` : "Bir PDF yukleyip PC Builder proforma seceneklerine ekleyin."}</p><small>PDF, teklif bilgileriyle kaplanir. En fazla 8 MB ve 50 sayfa.</small></div>${legacyPdfNotice}<input type="file" accept="application/pdf,.pdf" data-proforma-pdf-file hidden><button type="button" class="secondary" data-proforma-pdf-picker>${customPdfUploaded ? "Sablonu degistir" : "PDF sablonu yukle"}</button>${customPdfUploaded ? '<button type="button" class="mini" data-proforma-pdf-remove>Sablonu kaldir</button>' : ""}</section>
      <div class="proforma-template-toolbar"><button type="button" class="secondary" data-proforma-starter>Baslangic sablonu yukle</button><button type="button" class="secondary" data-proforma-preview>Ornek PDF onizle</button><button type="button" class="secondary" data-proforma-image>Gorsel ekle</button><input type="file" accept="image/png,image/jpeg" data-proforma-image-file hidden><span>Bi\u00e7im:</span><button type="button" class="mini" data-proforma-format="bold"><b>B</b></button><button type="button" class="mini" data-proforma-format="italic"><i>I</i></button><button type="button" class="mini" data-proforma-format="underline"><u>U</u></button><button type="button" class="mini" data-proforma-format="left">Sola</button><button type="button" class="mini" data-proforma-format="center">Ortala</button><button type="button" class="mini" data-proforma-format="right">Saga</button><button type="button" class="mini" data-proforma-format="list">Liste</button><label class="proforma-template-color">Renk <input type="color" data-proforma-color value="#1f2937"></label><select aria-label="Yazi tipi" data-proforma-font><option value="Arial">Arial</option><option value="Segoe UI">Segoe UI</option><option value="Tahoma">Tahoma</option><option value="Verdana">Verdana</option><option value="Times New Roman">Times New Roman</option><option value="Courier New">Courier New</option></select><select aria-label="Yazi boyutu" data-proforma-size>${[8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28].map(size => `<option value="${size}">${size}</option>`).join("")}</select><span>Alan ekle:</span>${tokens.map(([label, token]) => `<button type="button" class="mini" data-proforma-token="${token}">${label}</button>`).join("")}</div>
      <label class="proforma-template-label">Canli sayfa duzenleyici</label><div id="proformaTemplateCanvas" class="proforma-template-canvas" contenteditable="true" role="textbox" aria-multiline="true">${html}</div>
      <details class="proforma-template-source-details"><summary>HTML kaynagini goster / duzenle</summary><textarea id="proformaTemplateHtml" class="exact-setting proforma-template-source" data-setting-scope="settings" data-setting-key="proforma_editor_html" spellcheck="false">${esc(html)}</textarea></details>
      <p class="muted">Gorsel duzenleyicide metni secip bicim araclarini kullanin. HTML kaynak gorunumu ileri duzenleme icindir. Sablonu kaydetmek icin sayfanin ustundeki Ayarlari Kaydet dugmesini kullanin.</p>
    </div>`;
  }

  document.addEventListener("selectionchange", rememberEditorRange);
  document.addEventListener("input", function (event) {
    if (event.target.closest("#proformaTemplateCanvas")) syncSourceFromCanvas();
    if (event.target.closest("#proformaTemplateHtml")) {
      const canvas = templateCanvas();
      if (canvas) canvas.innerHTML = sanitizeTemplateHtml(event.target.value);
    }
  });
  function insertSafeMarkup(markup, text) {
    const safe = markup ? sanitizeTemplateHtml(markup) : esc(text).replace(/\n/g, "<br>");
    const holder = document.createElement("template");
    holder.innerHTML = safe;
    const fragment = holder.content;
    const range = editorRange();
    if (!range || !fragment.childNodes.length) return;
    range.deleteContents();
    const lastNode = fragment.lastChild;
    range.insertNode(fragment);
    const selection = window.getSelection();
    const nextRange = document.createRange();
    if (lastNode?.parentNode) nextRange.setStartAfter(lastNode);
    else nextRange.selectNodeContents(templateCanvas());
    nextRange.collapse(true);
    selection.removeAllRanges();
    selection.addRange(nextRange);
    savedEditorRange = nextRange.cloneRange();
    syncSourceFromCanvas();
  }
  document.addEventListener("paste", function (event) {
    if (!event.target.closest("#proformaTemplateCanvas")) return;
    event.preventDefault();
    insertSafeMarkup(event.clipboardData?.getData("text/html"), event.clipboardData?.getData("text/plain") || "");
  });
  document.addEventListener("drop", function (event) {
    if (!event.target.closest("#proformaTemplateCanvas")) return;
    event.preventDefault();
    insertSafeMarkup(event.dataTransfer?.getData("text/html"), event.dataTransfer?.getData("text/plain") || "");
  });

  async function requestTemplatePdf() {
    const response = await fetch("/api/desktop/pc-builder/proforma.pdf", {
      method: "POST", headers: { "Content-Type": "application/json" }, credentials: "same-origin",
      body: JSON.stringify({ company_name: desktopSettings.company_name || "AYEC Pro", customer_name: "Ornek Musteri", project_name: "Sablon Onizleme", reference_no: "PRF-ONIZLEME", currency: "TRY", template: "editor_template", items: [{ component: "Ornek", product: "Proforma kalemi", qty: 1, price: 1000 }] })
    });
    if (!response.ok) throw new Error((await response.json()).error || "PDF onizlemesi olusturulamadi.");
    return response.blob();
  }

  async function saveTemplateSettings() {
    const unresolvedImages = unresolvedLegacyImageCount();
    if (unresolvedImages) throw new Error(`${unresolvedImages} masa\u00fcst\u00fc g\u00f6rselini kaydetmeden \u00f6nce de\u011fi\u015ftirin veya kald\u0131r\u0131n.`);
    const controls = Array.from(document.querySelectorAll('.settings-content .exact-setting[data-setting-key]'));
    const values = Object.fromEntries(controls.map(control => [
      control.dataset.settingKey,
      control.type === "checkbox" ? (control.checked ? "1" : "0") : sanitizeTemplateHtml(control.value)
    ]));
    const shouldActivate = values.proforma_use_custom_editor === "1";
    const previousSettings = (await apiFetch("/api/desktop/bootstrap")).settings || {};
    const previousHtml = String(previousSettings.proforma_editor_html ?? desktopSettings.proforma_editor_html ?? "");
    const previousActiveValue = previousSettings.proforma_use_custom_editor ?? desktopSettings.proforma_use_custom_editor ?? "0";
    const previousActivation = ["1", "true", "True"].includes(String(previousActiveValue)) ? "1" : "0";
    const persist = async (key, value) => {
      await apiFetch("/api/desktop/table/settings", { method: "POST", body: JSON.stringify({ key, value }) });
      desktopSettings[key] = value;
    };
    try {
      await persist("proforma_use_custom_editor", "0");
      await persist("proforma_editor_html", values.proforma_editor_html || "");
      if (!shouldActivate) return null;
      const preview = await requestTemplatePdf();
      await persist("proforma_use_custom_editor", "1");
      return preview;
    } catch (error) {
      try {
        await persist("proforma_use_custom_editor", "0");
        await persist("proforma_editor_html", previousHtml);
        await persist("proforma_use_custom_editor", previousActivation);
      } catch (_) {
        desktopSettings.proforma_use_custom_editor = "0";
      }
      throw error;
    }
  }

  const previousSettingBody = settingBody;
  settingBody = function (settings) {
    if (settingsSection === "proforma-template") return renderEditor();
    return previousSettingBody(settings);
  };

  document.addEventListener("click", async function (event) {
    if (settingsSection !== "proforma-template" || !event.target.closest('[data-action="save-settings"]')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const button = event.target.closest('[data-action="save-settings"]');
    if (unresolvedLegacyImageCount()) {
      toast("Eski masa\u00fcst\u00fc g\u00f6rsellerini kaydetmeden \u00f6nce de\u011fi\u015ftirin veya kald\u0131r\u0131n.", "error");
      return;
    }
    button.disabled = true;
    try {
      await saveTemplateSettings();
      toast("Proforma sablon ayarlari kaydedildi.", "success");
    } catch (error) {
      const toggle = document.querySelector('[data-setting-key="proforma_use_custom_editor"]');
      if (toggle) toggle.checked = ["1", "true", "True"].includes(String(desktopSettings.proforma_use_custom_editor || "0"));
      toast("Proforma sablonu kaydedilemedi: " + error.message, "error");
    } finally {
      button.disabled = false;
    }
  }, true);

  document.addEventListener("click", function (event) {
    const starterButton = event.target.closest("[data-proforma-starter]");
    const tokenButton = event.target.closest("[data-proforma-token]");
    if (!starterButton && !tokenButton) return;
    const input = document.getElementById("proformaTemplateHtml");
    if (!input) return;
    if (starterButton) {
      const safeStarter = sanitizeTemplateHtml(starter);
      input.value = safeStarter;
      const canvas = templateCanvas();
      if (canvas) canvas.innerHTML = safeStarter;
      const toggle = document.querySelector('[data-setting-key="proforma_use_custom_editor"]');
      if (toggle) toggle.checked = true;
    } else {
      const token = tokenButton.dataset.proformaToken;
      const block = new Set(["{{logo}}", "{{urun_tablosu}}", "{{toplamlar}}", "{{ticari_kosullar}}", "{{imza_alani}}"]).has(token);
      const wrapper = block ? document.createElement("p") : document.createTextNode(token);
      if (block) wrapper.textContent = token;
      insertEditorNode(wrapper);
    }
    if (starterButton) input.dispatchEvent(new Event("input", { bubbles: true }));
  });

  document.addEventListener("click", function (event) {
    const legacyPlaceholder = event.target.closest(".proforma-legacy-image");
    if (legacyPlaceholder) {
      activeLegacyImagePlaceholder = legacyPlaceholder;
      document.querySelector("[data-proforma-image-file]")?.click();
      return;
    }
    if (event.target.closest("[data-proforma-image]")) {
      activeLegacyImagePlaceholder = null;
      document.querySelector("[data-proforma-image-file]")?.click();
    }
    if (event.target.closest("[data-proforma-pdf-picker]")) document.querySelector("[data-proforma-pdf-file]")?.click();
  });

  document.addEventListener("keydown", function (event) {
    if (!event.target.closest(".proforma-legacy-image") || !["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    activeLegacyImagePlaceholder = event.target.closest(".proforma-legacy-image");
    document.querySelector("[data-proforma-image-file]")?.click();
  });

  document.addEventListener("change", async function (event) {
    const picker = event.target.closest("[data-proforma-pdf-file]");
    const file = picker?.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf") || file.size > 8 * 1024 * 1024) {
      toast("PDF secin (en fazla 8 MB).", "error");
      picker.value = "";
      return;
    }
    try {
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("PDF dosyasi okunamadi."));
        reader.readAsDataURL(file);
      });
      const dataBase64 = String(dataUrl).split(",", 2)[1] || "";
      if (!dataBase64.startsWith("JVBERi0")) throw new Error("Dosya PDF olarak taninamadi.");
      const result = await apiFetch("/api/desktop/pc-builder/proforma-template", {
        method: "POST", body: JSON.stringify({ action: "upload", filename: file.name, data_base64: dataBase64 })
      });
      desktopSettings.proforma_template_uploaded = "1";
      desktopSettings.proforma_template_filename = result.filename || file.name;
      toast("Ozel PDF sablonu yuklendi.", "success");
      render();
    } catch (error) {
      toast("Ozel PDF sablonu yuklenemedi: " + error.message, "error");
    } finally {
      picker.value = "";
    }
  });

  document.addEventListener("click", async function (event) {
    if (!event.target.closest("[data-proforma-pdf-remove]")) return;
    const button = event.target.closest("[data-proforma-pdf-remove]");
    button.disabled = true;
    try {
      await apiFetch("/api/desktop/pc-builder/proforma-template", {
        method: "POST", body: JSON.stringify({ action: "delete" })
      });
      desktopSettings.proforma_template_uploaded = "0";
      desktopSettings.proforma_template_filename = "";
      toast("Ozel PDF sablonu kaldirildi.", "success");
      render();
    } catch (error) {
      toast("Ozel PDF sablonu kaldirilamadi: " + error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  document.addEventListener("change", async function (event) {
    const picker = event.target.closest("[data-proforma-image-file]");
    const file = picker?.files?.[0];
    if (!file) return;
    if (!new Set(["image/png", "image/jpeg"]).has(file.type) || file.size > 10 * 1024 * 1024) {
      toast("PNG veya JPEG dosyasi secin (en fazla 10 MB).", "error");
      picker.value = "";
      return;
    }
    try {
      const source = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("Gorsel okunamadi."));
        reader.readAsDataURL(file);
      });
      const image = await new Promise((resolve, reject) => {
        const node = new Image();
        node.onload = () => resolve(node);
        node.onerror = () => reject(new Error("Gorsel acilamadi."));
        node.src = source;
      });
      if (!image.width || !image.height || image.width * image.height > 20000000) throw new Error("Gorsel cozunurlugu cok yuksek.");
      const scale = Math.min(1, 1200 / Math.max(image.width, image.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.width * scale));
      canvas.height = Math.max(1, Math.round(image.height * scale));
      const context = canvas.getContext("2d");
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.72);
      if (dataUrl.length > 180000) throw new Error("Gorsel boyutu sablon sinirini asiyor.");
      const embedded = document.createElement("img");
      embedded.src = dataUrl;
      if (activeLegacyImagePlaceholder?.isConnected) {
        activeLegacyImagePlaceholder.replaceWith(embedded);
        activeLegacyImagePlaceholder = null;
        syncSourceFromCanvas();
      } else insertEditorNode(embedded);
    } catch (error) {
      toast("Gorsel sablona eklenemedi: " + error.message, "error");
    } finally {
      picker.value = "";
    }
  });

  function wrapSelection(open, close) {
    const range = editorRange();
    const canvas = templateCanvas();
    if (!canvas || !range) return;
    const template = document.createElement("template");
    template.innerHTML = open;
    const wrapper = template.content.firstElementChild;
    if (!wrapper) return;
    const wasCollapsed = range.collapsed;
    const contents = range.extractContents();
    if (wasCollapsed) wrapper.textContent = close ? "Metin" : "";
    else wrapper.append(contents);
    range.insertNode(wrapper);
    const selection = window.getSelection();
    const nextRange = document.createRange();
    nextRange.selectNodeContents(wrapper);
    selection.removeAllRanges();
    selection.addRange(nextRange);
    savedEditorRange = nextRange.cloneRange();
    canvas.focus();
    syncSourceFromCanvas();
  }

  document.addEventListener("keydown", function (event) {
    const editor = event.target.closest("#proformaTemplateCanvas");
    if (!editor || !(event.ctrlKey || event.metaKey) || event.altKey) return;
    const formats = { b: "bold", i: "italic", u: "underline" };
    const tag = formats[event.key.toLowerCase()];
    if (!tag) return;
    event.preventDefault();
    const wrappers = { bold: ["<b>", "</b>"], italic: ["<i>", "</i>"], underline: ["<u>", "</u>"] };
    wrapSelection(...wrappers[tag]);
  });

  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-proforma-format]");
    if (!button) return;
    const tag = button.dataset.proformaFormat;
    const commands = { left: "justifyLeft", center: "justifyCenter", right: "justifyRight", list: "insertUnorderedList" };
    if (commands[tag]) {
      const range = editorRange();
      const selection = window.getSelection();
      templateCanvas()?.focus();
      if (range) {
        selection.removeAllRanges();
        selection.addRange(range);
      }
      document.execCommand(commands[tag], false, null);
      syncSourceFromCanvas();
      return;
    }
    const formats = {
      bold: ["<b>", "</b>"], italic: ["<i>", "</i>"], underline: ["<u>", "</u>"],
      left: ['<p style="text-align:left">', "</p>"], center: ['<p style="text-align:center">', "</p>"],
      right: ['<p style="text-align:right">', "</p>"], list: ["<ul><li>", "</li></ul>"]
    };
    if (formats[tag]) wrapSelection(...formats[tag]);
  });

  document.addEventListener("change", function (event) {
    const control = event.target;
    if (control.matches("[data-proforma-color]")) wrapSelection(`<span style="color:${control.value}">`, "</span>");
    if (control.matches("[data-proforma-font]")) wrapSelection(`<span style="font-family:${control.value}">`, "</span>");
    if (control.matches("[data-proforma-size]")) wrapSelection(`<span style="font-size:${control.value}pt">`, "</span>");
  });

  document.addEventListener("click", async function (event) {
    const button = event.target.closest("[data-proforma-preview]");
    if (!button) return;
    button.disabled = true;
    try {
      const validatedBlob = await saveTemplateSettings();
      const url = URL.createObjectURL(validatedBlob || await requestTemplatePdf());
      const viewer = window.open(url, "_blank", "noopener");
      if (!viewer) window.location.assign(url);
    } catch (error) {
      toast("Proforma onizlemesi olusturulamadi: " + error.message, "error");
    } finally {
      button.disabled = false;
    }
  });
})();
