(function () {
  const steps = [
    ["1. Ba\u011flant\u0131", "Telefonunuzun ve bilgisayar\u0131n\u0131z\u0131n ayn\u0131 Wi-Fi a\u011f\u0131nda oldu\u011fundan emin olun."],
    ["2. Tarama", "QR kodu telefonunuzun kameras\u0131yla okutun veya manuel adresi taray\u0131c\u0131ya girin."],
    ["3. Ba\u015flang\u0131\u00e7", "A\u00e7\u0131lan ekranda oturum a\u00e7\u0131n. Stok sayfas\u0131nda Barkod Tara d\u00fc\u011fmesine dokunup kamera izni verin."],
    ["4. Ak\u0131ll\u0131 Stok", "Barkod okutun. Bulunan \u00fcr\u00fcn\u00fc stokta aray\u0131n; yeni \u00fcr\u00fcn\u00fc stok formundan kaydedin."]
  ];

  function guideShell() {
    const target = new URL("/?page=stock", window.location.origin).href;
    const qr = `/api/desktop/mobile-guide/qr?target=${encodeURIComponent(target)}`;
    return `<section class="mobile-guide-reference"><header class="mobile-guide-head"><div><span class="mobile-guide-kicker">STOK / MOB\u0130L ER\u0130\u015e\u0130M</span><h2>Mobil Optik Giri\u015f (Ak\u0131ll\u0131 Stok)</h2><p>Telefonunuzu barkod okuyucu olarak kullan\u0131n. Stok kay\u0131tlar\u0131n\u0131 AYEC Pro i\u00e7inde y\u00f6netin.</p></div><span class="mobile-guide-icon" aria-hidden="true">&#128241;</span></header><div class="mobile-guide-card"><div class="mobile-guide-steps">${steps.map(([title, body], index) => `<article class="mobile-guide-step"><span>${index + 1}</span><div><h3>${title}</h3><p>${body}</p></div></article>`).join("")}<div class="mobile-guide-link"><strong>Manuel Adres</strong><a href="${target}" target="_blank" rel="noopener">${target}</a><button type="button" class="secondary" data-mobile-guide-copy>Ba\u011flant\u0131y\u0131 Kopyala</button></div></div><aside class="mobile-guide-qr"><img src="${qr}" alt="Mobil stok sayfas\u0131 i\u00e7in QR kod"><strong>Telefon kameras\u0131yla taray\u0131n</strong><small>Giri\u015f yapt\u0131ktan sonra stok sayfas\u0131nda barkod kameras\u0131n\u0131 a\u00e7\u0131n.</small></aside></div><p class="mobile-guide-note">Kamera kullan\u0131m\u0131 i\u00e7in HTTPS gerekir. Taray\u0131c\u0131 kamera eri\u015fimi desteklemiyorsa barkodu elle girebilirsiniz.</p></section>`;
  }

  const baseRender = render;
  render = function () {
    if (page !== "mobile-guide") return baseRender();
    document.body.dataset.page = page;
    $("#content").innerHTML = guideShell();
    const copy = $("[data-mobile-guide-copy]");
    if (copy) copy.onclick = async () => {
      try {
        await navigator.clipboard.writeText(new URL("/?page=stock", window.location.origin).href);
        toast("Ba\u011flant\u0131 kopyaland\u0131", "success");
      } catch {
        toast("Ba\u011flant\u0131 kopyalanamad\u0131", "error");
      }
    };
    const image = $(".mobile-guide-qr img");
    if (image) image.onerror = () => {
      image.hidden = true;
      const fallback = document.createElement("strong");
      fallback.className = "mobile-guide-qr-error";
      fallback.textContent = "QR kodu y\u00fcklenemedi. Manuel adresi kullan\u0131n.";
      image.parentElement.prepend(fallback);
    };
  };
})();
