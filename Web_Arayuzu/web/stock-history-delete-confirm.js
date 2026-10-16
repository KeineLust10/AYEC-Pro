(function () {
  "use strict";

  var originalContextAction = contextAction;
  contextAction = function (kind, id, action, row) {
    if (kind !== "movement" || action !== "movement-delete") {
      return originalContextAction(kind, id, action, row);
    }
    if (!(db.movements || []).some(function (item) {
      return String(item.id) === String(id);
    })) return;

    openDialog(
      "Hareket Kayd\u0131n\u0131 Ge\u00E7mi\u015Ften Sil",
      "STOK HAREKET GE\u00C7M\u0130\u015E\u0130",
      '<p>Bu ge\u00E7mi\u015F kayd\u0131n\u0131 silmek i\u00E7in giri\u015F \u015Fifrenizi girin.</p>' +
        '<div class="field"><label>Giri\u015F parolan\u0131z</label>' +
        '<input name="password" type="password" autocomplete="current-password" required></div>',
      async function (form) {
        var password = form.get("password");
        openDialog(
          "Hareketi Sil",
          "STOK HAREKET GE\u00C7M\u0130\u015E\u0130",
          "<p>Bu i\u015Flem sadece log kayd\u0131n\u0131 siler, finans\u0131 ve ger\u00E7ek sto\u011Fu de\u011Fi\u015Ftirmez! Ge\u00E7mi\u015F kayd\u0131n\u0131 silmek istedi\u011Finize emin misiniz?</p>",
          async function () {
            await apiFetch("/api/desktop/stock/movements/delete", {
              method: "POST",
              body: JSON.stringify({ id: Number(id), password: password })
            });
            await hydrateDesktop(false);
            render();
            toast("Hareket ge\u00E7mi\u015Ften silindi.", "success");
            return true;
          },
          "Ge\u00E7mi\u015Ften Sil"
        );
        return false;
      },
      "Ge\u00E7mi\u015Ften Sil"
    );
  };
}());
