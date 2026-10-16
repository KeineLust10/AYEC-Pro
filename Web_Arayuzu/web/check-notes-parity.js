(function () {
  "use strict";

  var originalShowContext = showContext;
  showContext = function (event, kind, id) {
    if (kind !== "check-note") return originalShowContext(event, kind, id);
    if (!ayecContextMenuEnabled()) return;
    event.preventDefault();
    var menu = document.querySelector("#contextMenu");
    var row = document.querySelector('#genericHost tbody tr[data-id="' + CSS.escape(String(id)) + '"]');
    var currentStatus = row ? row.dataset.checkStatus : "";
    var statuses = ["Portf\u00f6yde", "Tahsil Edildi", "Ciro Edildi", "\u00d6dendi", "Kar\u015f\u0131l\u0131ks\u0131z", "\u0130ade"]
      .filter(function (status) { return status !== currentStatus; });
    var statusButtons = statuses.map(function (status) {
      return '<button type="button" role="menuitem" data-check-context-action="' + esc(status) + '">' + esc(status) + '</button>';
    }).join("");
    menu.innerHTML = '<button type="button" role="menuitem" data-check-context-action="detail">Detay G\u00f6r\u00fcnt\u00fcle</button>'
      + '<hr><div class="check-note-context-submenu"><button type="button" role="menuitem" aria-haspopup="menu" aria-expanded="false" data-check-status-toggle>Durum De\u011fi\u015ftir <span aria-hidden="true">\u203a</span></button>'
      + '<div class="check-note-context-submenu-panel" role="menu" hidden>' + statusButtons + '</div></div>';
    menu.style.left = Math.max(8, Math.min(event.clientX, innerWidth - 210)) + "px";
    menu.style.top = Math.max(8, Math.min(event.clientY, innerHeight - statuses.length * 40 - 80)) + "px";
    menu.classList.add("open");
    var statusToggle = menu.querySelector("[data-check-status-toggle]");
    var statusPanel = menu.querySelector(".check-note-context-submenu-panel");
    var statusSubmenu = menu.querySelector(".check-note-context-submenu");
    function setStatusMenuOpen(open) {
      statusPanel.hidden = !open;
      statusToggle.setAttribute("aria-expanded", String(open));
      menu.classList.toggle("check-context-opens-left", menu.getBoundingClientRect().right + 200 > innerWidth);
    }
    statusToggle.onclick = function (clickEvent) {
      clickEvent.stopPropagation();
      setStatusMenuOpen(true);
    };
    statusToggle.onmouseenter = function () { setStatusMenuOpen(true); };
    statusSubmenu.onmouseleave = function () { setStatusMenuOpen(false); };
    menu.querySelectorAll("[data-check-context-action]").forEach(function (button) {
      button.onclick = function () {
        menu.classList.remove("open");
        var action = button.dataset.checkContextAction;
        var record = (window.currentGenericData && window.currentGenericData.rows || []).find(function (item) {
          return String(item.id) === String(id);
        });
        if (action === "detail" && record) {
          showCheckNoteDetail(record);
        } else if (record) {
          changeCheckNoteStatus(id, action);
        }
      };
    });
  };

  var originalLoadChecks = loadChecksReference;
  loadChecksReference = async function (meta, query) {
    var result = await originalLoadChecks(meta, query);
    if (page !== "checks") return result;
    document.querySelectorAll("#genericHost tbody tr").forEach(function (row) {
      var detail = row.querySelector("[data-check-detail]");
      if (!detail) return;
      row.dataset.kind = "check-note";
      row.dataset.id = detail.dataset.checkDetail;
      row.dataset.checkStatus = row.querySelector(".check-status")?.textContent.trim() || "";
      bindInteractiveRow(row);
    });
    document.querySelectorAll(".check-actions button[data-check-status]").forEach(function (button) {
      button.onclick = function () {
        changeCheckNoteStatus(button.dataset.checkId, button.dataset.checkStatus);
      };
    });
    document.querySelectorAll("[data-check-detail]").forEach(function (button) {
      button.onclick = function () {
        var record = (window.currentGenericData && window.currentGenericData.rows || []).find(function (item) {
          return String(item.id) === String(button.dataset.checkDetail);
        });
        if (record) showCheckNoteDetail(record);
      };
    });
    var add = document.querySelector("[data-check-add]");
    if (add) {
      var freshAdd = add.cloneNode(true);
      add.replaceWith(freshAdd);
      freshAdd.onclick = showCheckNoteCreate;
    }
    var bulk = document.querySelector("[data-check-bulk]");
    if (bulk) bulk.onclick = async function () {
      var ids = Array.from(document.querySelectorAll("[data-check-select]:checked"), function (box) {
        return box.value;
      });
      if (!ids.length) return toast("\u00d6nce evrak se\u00e7in", "warning");
      try {
        for (var index = 0; index < ids.length; index += 1) {
          await submitCheckNoteStatus(ids[index], "Ciro Edildi", null);
        }
        toast(ids.length + " evrak bankaya takas i\u015flemine verildi", "success");
        await refreshChecks();
      } catch (error) {
        toast(error.message || "Toplu takas i\u015flemi tamamlanamad\u0131", "error");
      }
    };
    return result;
  };

  async function changeCheckNoteStatus(checkId, status) {
    try {
      var options = await apiFetch("/api/desktop/checks/" + encodeURIComponent(checkId)
        + "/status-options?status=" + encodeURIComponent(status));
      if (options.bank_transaction_type && options.bank_accounts.length) {
        var choices = options.bank_accounts.map(function (account) {
          return '<option value="' + esc(account.id) + '">' + esc(account.bank_name) + '</option>';
        }).join("");
        openDialog("Banka/Kasa Se\u00e7imi", "\u00c7EK / SENET", '<div class="field"><label>\u0130\u015flem hesab\u0131</label><select name="bank_account_id"><option value="-1">Banka/Kasa se\u00e7meyin (yaln\u0131zca durum de\u011fi\u015fsin)</option>' + choices + '</select></div>', async function (formData) {
          await submitCheckNoteStatus(checkId, status, formData.get("bank_account_id"));
          toast("Evrak durumu ve finans kay\u0131tlar\u0131 g\u00fcncellendi", "success");
          await refreshChecks();
          return true;
        }, "Onayla");
        return;
      }
      await submitCheckNoteStatus(checkId, status, null);
      toast("Evrak durumu ve finans kay\u0131tlar\u0131 g\u00fcncellendi", "success");
      await refreshChecks();
    } catch (error) {
      toast(error.message || "Evrak durumu g\u00fcncellenemedi", "error");
    }
  }

  async function submitCheckNoteStatus(checkId, status, bankAccountId) {
    await apiFetch("/api/desktop/checks/" + encodeURIComponent(checkId) + "/status", {
      method: "POST",
      body: JSON.stringify({ status: status, bank_account_id: bankAccountId })
    });
  }

  async function refreshChecks() {
    await loadGenericModule(window.currentGenericMeta || genericModules.checks,
      document.querySelector("#genericSearch")?.value || "");
  }

  function showCheckNoteDetail(record) {
    var direction = String(record.direction || "").startsWith("Giri\u015f")
      ? "\u2199 Al\u0131nan" : "\u2197 Verilen";
    var parties = [record.issuer, record.recipient].filter(Boolean).join("\n");
    var bank = [record.bank_name, record.branch_name].filter(Boolean).join("\n");
    var fields = [
      ["T\u00fcr", record.type], ["Y\u00f6n", direction],
      ["Ke\u015fideci/Bor\u00e7lu", parties], ["Banka", bank],
      ["Evrak / Seri No", record.check_no || record.portfolio_no],
      ["Tutar", checkMoney(Number(record.amount || 0), window.checksReferenceCurrency || "USD")],
      ["Vade", String(record.due_date || "").slice(0, 10)], ["Durum", record.status]
    ];
    var body = '<div class="form-grid check-note-detail">' + fields.map(function (item) {
      var multiline = item[0] === "Ke\u015fideci/Bor\u00e7lu" || item[0] === "Banka";
      return '<div class="field"><label>' + esc(item[0]) + '</label><div'
        + (multiline ? ' class="check-note-multiline"' : '') + '>' + esc(item[1] || "-") + '</div></div>';
    }).join("") + '</div>';
    openDialog("\u00c7ek / Senet Detay", "\u00c7EK / SENET", body, async function () { return true; }, "Kapat");
    document.querySelector("#dialogCancel").hidden = true;
  }

  function showCheckNoteCreate() {
    var now = new Date();
    var dueDate = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
    var body = '<div class="form-grid">'
      + '<div class="field"><label>Evrak Tipi</label><select name="type"><option>\u00c7ek</option><option>Senet</option></select></div>'
      + '<div class="field"><label>Y\u00f6n</label><select name="direction"><option>Giri\u015f (Al\u0131nan)</option><option>\u00c7\u0131k\u0131\u015f (Verilen)</option></select></div>'
      + '<div class="field"><label>Tutar</label><input name="amount" type="number" min="0.01" step="0.01" required></div>'
      + '<div class="field"><label>Banka</label><input name="bank_name"></div>'
      + '<div class="field"><label>\u015eube</label><input name="branch_name"></div>'
      + '<div class="field"><label>Ke\u015fideci/Bor\u00e7lu</label><input name="issuer"></div>'
      + '<div class="field"><label>Al\u0131c\u0131</label><input name="recipient"></div>'
      + '<div class="field"><label>Vade Tarihi</label><input name="due_date" type="date" value="' + dueDate + '" required></div>'
      + '<div class="field"><label>Durum</label><select name="status"><option>Portf\u00f6yde</option><option>Tahsil Edildi</option><option>Ciro Edildi</option><option>\u00d6dendi</option><option>Kar\u015f\u0131l\u0131ks\u0131z</option><option>\u0130ade</option></select></div>'
      + '</div>';
    openDialog("\u00c7ek / Senet Giri\u015fi", "\u00c7EK / SENET", body, async function (formData) {
      var payload = Object.fromEntries(formData);
      payload.amount = Number(payload.amount);
      if (!Number.isFinite(payload.amount) || payload.amount <= 0) throw new Error("Tutar 0'dan b\u00fcy\u00fck olmal\u0131d\u0131r.");
      if (!payload.issuer.trim() && !payload.recipient.trim()) throw new Error("Ke\u015fideci/Bor\u00e7lu veya Al\u0131c\u0131 alanlar\u0131ndan en az biri doldurulmal\u0131d\u0131r.");
      var result = await apiFetch("/api/desktop/check-notes", { method: "POST", body: JSON.stringify(payload) });
      toast(result.finance_warning ? "Evrak olu\u015ftu; ilk finans kayd\u0131 yaz\u0131lamad\u0131" : "Kay\u0131t eklendi ve finans mod\u00fcl\u00fcne i\u015flendi.", result.finance_warning ? "warning" : "success");
      await refreshChecks();
    }, "Kaydet");
  }
})();
