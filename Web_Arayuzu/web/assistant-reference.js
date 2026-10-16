(function () {
  const assistantFaq = {
    stok: "Stok Ekleme:\n1. Stok Y\u00f6netimi sayfas\u0131na gidin\n2. Yeni par\u00e7a ekleyin\n3. Bilgileri doldurun\n4. Kaydedin",
    musteri: "M\u00fc\u015fteri Kayd\u0131:\n1. M\u00fc\u015fteri \u0130\u015flemleri sayfas\u0131na gidin\n2. Yeni m\u00fc\u015fteri ekleyin\n3. Ad, telefon ve e-posta bilgilerini girin\n4. Kaydedin",
    servis: "Servis Takibi:\n1. Servis Operasyon Panosu'nu a\u00e7\u0131n\n2. Kartlar\u0131 durumlar\u0131na g\u00f6re takip edin\n3. Kart detay\u0131na t\u0131klay\u0131n\n4. \u0130\u015flemleri kaydedin",
    randevu: "Randevu Olu\u015fturma:\n1. Randevu sayfas\u0131na gidin\n2. Yeni randevu olu\u015fturun\n3. M\u00fc\u015fteri, tarih ve saat se\u00e7in\n4. Kaydedin",
    rapor: "Rapor Alma:\n1. Raporlar sayfas\u0131na gidin\n2. Tarih aral\u0131\u011f\u0131n\u0131 se\u00e7in\n3. Rapor t\u00fcr\u00fcn\u00fc belirleyin\n4. PDF veya Excel al\u0131n",
    yedek: "Yedekleme:\n1. Ayarlar sayfas\u0131na gidin\n2. Yedekle d\u00fc\u011fmesine bas\u0131n\n3. Yedek dosyas\u0131 olu\u015fturulur\n4. Yedekleme merkezinde saklan\u0131r"
  };
  const assistantSuggestions = [
    ["Stok nas\u0131l eklenir", "stok"], ["M\u00fc\u015fteri kayd\u0131 nas\u0131l yap\u0131l\u0131r", "musteri"],
    ["Servis takibi nas\u0131l \u00e7al\u0131\u015f\u0131r", "servis"], ["Randevu nas\u0131l olu\u015fturulur", "randevu"],
    ["Rapor nas\u0131l al\u0131n\u0131r", "rapor"], ["Yedekleme nas\u0131l yap\u0131l\u0131r", "yedek"]
  ];
  let assistantStatus = { configured: false, key_present: false, model: "" };
  function assistantShell() {
    return `<section class="assistant-reference"><header class="assistant-reference-head"><div><h2>Bilgi Asistan\u0131</h2><span>YEREL B\u0130LG\u0130 BANKASINDA ARAMA YAPIN</span></div><div class="assistant-status" id="assistantStatus">Ba\u011flant\u0131 denetleniyor</div></header><section class="assistant-welcome"><h3>Nas\u0131l yard\u0131mc\u0131 olabilirim?</h3><p>A\u015fa\u011f\u0131daki \u00f6nerilerden birini se\u00e7in veya sorunuzu yaz\u0131n. Haz\u0131r cevaplar yerel olarak g\u00f6sterilir; di\u011fer sorular etkinle\u015ftirilmi\u015fse i\u015fletmenizin AI asistan\u0131na iletilir.</p></section><h4 class="assistant-section-label">\u00d6NER\u0130LEN SORULAR</h4><div class="assistant-suggestions">${assistantSuggestions.map(([label, key]) => `<button type="button" data-assistant-faq="${key}">${label}</button>`).join("")}</div><form class="assistant-query" id="assistantQueryForm"><label for="assistantQuestion">VEYA KEND\u0130 SORUNUZU YAZIN</label><div><input id="assistantQuestion" maxlength="1200" placeholder="Sorunuzu buraya yaz\u0131n..." autocomplete="off"><button class="primary" type="submit" id="assistantSubmit">Ara</button></div></form><h4 class="assistant-section-label">CEVAP</h4><article class="assistant-answer" id="assistantAnswer" aria-live="polite">Bir soru se\u00e7in veya yaz\u0131n; cevab\u0131 burada g\u00f6receksiniz.</article></section>`;
  }
  async function loadAssistantStatus() {
    const node = document.querySelector("#assistantStatus");
    if (!node) return;
    try {
      assistantStatus = await apiFetch("/api/desktop/assistant/status");
      node.textContent = assistantStatus.configured ? `Jarvis \u00c7evrimi\u00e7i · ${assistantStatus.model}` : "\u00c7evrimd\u0131\u015f\u0131 Mod (Yerel)";
      node.classList.toggle("online", Boolean(assistantStatus.configured));
    } catch (error) {
      node.textContent = "Durum al\u0131namad\u0131";
      node.title = error.message;
    }
  }
  function showAssistantAnswer(text, kind = "") {
    const answer = document.querySelector("#assistantAnswer");
    if (!answer) return;
    answer.textContent = text;
    answer.classList.toggle("assistant-error", kind === "error");
    answer.classList.toggle("assistant-loading", kind === "loading");
  }
  async function askAssistant(question) {
    const value = String(question || "").trim();
    if (!value) return;
    const normalizedQuestion = value.toLocaleLowerCase("tr-TR").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\u0131/g, "i");
    const quickKey = Object.keys(assistantFaq).find((key) => normalizedQuestion.includes(key));
    if (quickKey) {
      showAssistantAnswer(`H\u0131zl\u0131 Cevap:\n\n${assistantFaq[quickKey]}`);
      return;
    }
    const button = document.querySelector("#assistantSubmit");
    if (button) button.disabled = true;
    showAssistantAnswer("Bilgi bankas\u0131 ve i\u015fletme verileri aran\u0131yor...\n\nL\u00fctfen bekleyin.", "loading");
    try {
      const result = await apiFetch("/api/desktop/assistant/query", { method: "POST", body: JSON.stringify({ question: value }) });
      if (!result.success) throw Error(result.error || "Asistan yan\u0131t \u00fcretemedi.");
      showAssistantAnswer(`Asistan:\n\n${result.answer || "Yan\u0131t bulunamad\u0131."}`);
    } catch (error) {
      showAssistantAnswer(`Hata:\n\n${error.message}`, "error");
    } finally {
      if (button) button.disabled = false;
    }
  }
  const baseRender = render;
  render = function () {
    if (page !== "assistant") return baseRender();
    document.body.dataset.page = page;
    $("#content").innerHTML = assistantShell();
    loadAssistantStatus();
  };
  document.addEventListener("click", (event) => {
    if (page !== "assistant") return;
    const button = event.target.closest("[data-assistant-faq]");
    if (!button) return;
    const key = button.dataset.assistantFaq;
    document.querySelector("#assistantQuestion").value = assistantSuggestions.find((item) => item[1] === key)?.[0] || "";
    showAssistantAnswer(assistantFaq[key] || "Bu konu hakk\u0131nda bilgi bulunamad\u0131.");
  });
  document.addEventListener("submit", (event) => {
    if (event.target.id !== "assistantQueryForm") return;
    event.preventDefault();
    askAssistant(document.querySelector("#assistantQuestion")?.value);
  });
})();
