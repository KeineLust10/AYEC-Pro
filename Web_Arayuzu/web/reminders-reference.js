(function () {
  "use strict";

  var genericShellBeforeReminders = genericShell;
  var loadGenericModuleBeforeReminders = loadGenericModule;
  var selectedReminderId = null;
  var reminderMeta = genericModules.reminders;
  var reminderPersonnel = [];

  genericShell = function (meta) {
    if (meta.table !== "reminders") return genericShellBeforeReminders(meta);
    return '<div class="page-head reminders-page-head"><div><h2>Hat\u0131rlat\u0131c\u0131 Y\u00f6netimi</h2></div><div class="actions"></div></div>'
      + '<section class="card reminders-reference">'
      + '<nav class="reminder-tabs" role="tablist">'
      + '<button type="button" role="tab" class="active" aria-selected="true" data-reminder-tab="add">Hat\u0131rlat\u0131c\u0131 Ekle</button>'
      + '<button type="button" role="tab" aria-selected="false" data-reminder-tab="list">Liste ve D\u00fczenleme</button>'
      + '</nav>'
      + '<section class="reminder-pane" data-reminder-pane="add" role="tabpanel">'
      + '<form id="reminderCreateForm" class="reminder-form">'
      + '<fieldset><legend>Yeni Hat\u0131rlatma Detaylar\u0131</legend>'
      + '<div class="reminder-fields">'
      + '<label class="field reminder-title-field"><span>Ba\u015fl\u0131k</span><input name="title" required placeholder="\u00d6rn: M\u00fc\u015fteri Aramas\u0131"></label>'
      + '<label class="field"><span>\u0130lgili Personel</span><select name="personnel"></select></label>'
      + '<label class="field"><span>Tarih</span><input name="date" type="date" value="' + localDateInputValue() + '" required></label>'
      + '</div>'
      + '<label class="field reminder-description"><span>A\u00e7\u0131klama / Notlar</span>'
      + '<textarea name="description" placeholder="Hat\u0131rlat\u0131lacak konunun detaylar\u0131n\u0131 buraya giriniz..."></textarea></label>'
      + '</fieldset><div class="reminder-form-actions"><button type="submit" class="primary" data-reminder-save>Kaydet ve Ekle</button></div></form>'
      + '</section>'
      + '<section class="reminder-pane" data-reminder-pane="list" role="tabpanel" hidden>'
      + '<div class="reminder-list-actions"><button type="button" class="secondary" data-generic-refresh>Yenile</button>'
      + '<button type="button" class="danger" data-reminder-delete>Se\u00e7ili Olan\u0131 Sil</button></div>'
      + '<div id="reminderListHost"></div>'
      + '<input id="genericSearch" type="search" hidden><span id="genericCount" hidden></span>'
      + '</section></section>';
  };

  function localDateInputValue() {
    var now = new Date();
    return String(now.getFullYear()) + "-" + String(now.getMonth() + 1).padStart(2, "0")
      + "-" + String(now.getDate()).padStart(2, "0");
  }

  function personnelName(id) {
    var match = reminderPersonnel.find(function (person) {
      return String(person.id) === String(id);
    });
    return match && match.name || "";
  }

  function normalizeReminder(row) {
    var assigned = row.personnel || row.personnel_name || personnelName(row.personnel_id);
    var title = row.title || row.message || row.tracking_no || "";
    var description = row.description || row.message || "";
    var date = row.date || row.due_date || "";
    var status = row.status || (Number(row.is_read) === 1 ? "Okundu" : "Aktif");
    return {
      id: row.id,
      title: title,
      personnel: assigned || "Genel (Herkes)",
      date: date,
      description: description,
      status: status,
      source: row
    };
  }

  function renderReminderRows(data) {
    var host = document.querySelector("#reminderListHost");
    if (!host) return;
    selectedReminderId = null;
    var rows = (data.rows || []).map(normalizeReminder).sort(function (left, right) {
      return String(right.date || "").localeCompare(String(left.date || ""));
    });
    if (!rows.length) {
      host.innerHTML = empty("Hat\u0131rlat\u0131c\u0131 yok", "Yeni bir hat\u0131rlat\u0131c\u0131 ekleyerek ba\u015flay\u0131n.");
      updateDeleteButton();
      return;
    }
    host.innerHTML = '<div class="table-wrap"><table class="reminder-table"><thead><tr>'
      + '<th>ID</th><th>Ba\u015fl\u0131k</th><th>Personel</th><th>Tarih</th><th>A\u00e7\u0131klama</th><th>Durum</th>'
      + '</tr></thead><tbody>' + rows.map(function (row) {
        return '<tr tabindex="0" data-reminder-id="' + esc(row.id) + '" aria-selected="false">'
          + '<td>' + esc(row.id) + '</td><td class="reminder-row-title">' + esc(row.title) + '</td>'
          + '<td>' + esc(row.personnel) + '</td><td>' + esc(row.date) + '</td>'
          + '<td class="reminder-row-description">' + esc(row.description) + '</td>'
          + '<td>' + esc(row.status) + '</td></tr>';
      }).join("") + '</tbody></table></div>';
    updateDeleteButton();
  }

  function updateDeleteButton() {
    var button = document.querySelector("[data-reminder-delete]");
    if (button) button.disabled = false;
  }

  function setReminderTab(tab) {
    document.querySelectorAll("[data-reminder-tab]").forEach(function (button) {
      var active = button.dataset.reminderTab === tab;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
    document.querySelectorAll("[data-reminder-pane]").forEach(function (pane) {
      pane.hidden = pane.dataset.reminderPane !== tab;
    });
  }

  function setPersonnelOptions(personnel) {
    reminderPersonnel = personnel || [];
    var select = document.querySelector('#reminderCreateForm [name="personnel"]');
    if (!select) return;
    select.innerHTML = '<option value="">Genel (Herkes)</option>' + reminderPersonnel.map(function (person) {
      return '<option value="' + esc(person.id) + '">' + esc(person.name || "") + '</option>';
    }).join("");
  }

  loadGenericModule = async function (meta, query) {
    if (meta.table !== "reminders") return loadGenericModuleBeforeReminders(meta, query);
    var listHost = document.querySelector("#reminderListHost");
    if (!listHost) return;
    listHost.innerHTML = empty("Y\u00fckleniyor", "Hat\u0131rlat\u0131c\u0131lar veritaban\u0131ndan okunuyor.");
    try {
      var result = await Promise.all([
        apiFetch("/api/desktop/table/reminders?limit=500&q=" + encodeURIComponent(query || "")),
        apiFetch("/api/desktop/table/personnel?limit=500")
      ]);
      window.currentGenericData = result[0];
      window.currentGenericMeta = meta;
      reminderPersonnel = result[1].rows || [];
      setPersonnelOptions(reminderPersonnel);
      renderReminderRows(result[0]);
    } catch (error) {
      listHost.innerHTML = empty("Hat\u0131rlat\u0131c\u0131lar y\u00fcklenemedi", error.message || "");
    }
  };

  document.addEventListener("click", function (event) {
    var tab = event.target.closest("[data-reminder-tab]");
    if (tab) {
      setReminderTab(tab.dataset.reminderTab);
      return;
    }
    var row = event.target.closest("[data-reminder-id]");
    if (row) {
      document.querySelectorAll("[data-reminder-id]").forEach(function (item) {
        var selected = item === row;
        item.classList.toggle("selected", selected);
        item.setAttribute("aria-selected", String(selected));
      });
      selectedReminderId = row.dataset.reminderId;
      updateDeleteButton();
      return;
    }
    if (event.target.closest("[data-reminder-delete]")) deleteSelectedReminder();
  });

  document.addEventListener("keydown", function (event) {
    if ((event.key === "Enter" || event.key === " ") && event.target.matches("[data-reminder-id]")) {
      event.preventDefault();
      event.target.click();
    }
  });

  document.addEventListener("submit", async function (event) {
    if (event.target.id !== "reminderCreateForm") return;
    event.preventDefault();
    var form = event.target;
    var values = Object.fromEntries(new FormData(form));
    var title = String(values.title || "").trim();
    if (!title) {
      toast("L\u00fctfen bir ba\u015fl\u0131k giriniz.", "warning");
      return;
    }
    var saveButton = form.querySelector("[data-reminder-save]");
    saveButton.disabled = true;
    try {
      var body = {
        title: title,
        personnel: personnelName(values.personnel) || "",
        personnel_id: values.personnel ? Number(values.personnel) : null,
        date: values.date,
        description: String(values.description || "").trim(),
        status: "Aktif",
        is_read: 0
      };
      await apiFetch("/api/desktop/table/reminders", {
        method: "POST",
        body: JSON.stringify(body)
      });
      toast("Hat\u0131rlat\u0131c\u0131 sisteme eklendi.", "success");
      form.elements.title.value = "";
      form.elements.description.value = "";
      await loadGenericModule(reminderMeta, "");
      setReminderTab("list");
    } catch (error) {
      toast("Hat\u0131rlat\u0131c\u0131 eklenemedi: " + (error.message || ""), "error");
    } finally {
      saveButton.disabled = false;
    }
  });

  async function deleteSelectedReminder() {
    if (selectedReminderId === null) {
      toast("L\u00fctfen silinecek bir sat\u0131r se\u00e7in.", "warning");
      return;
    }
    openDialog("Hat\u0131rlat\u0131c\u0131y\u0131 Sil", "SILME ONAYI", "<p>Bu hat\u0131rlat\u0131c\u0131 kal\u0131c\u0131 olarak silinecek. Emin misiniz?</p>", async () => {
      try {
        await apiFetch("/api/desktop/table/reminders", {
          method: "POST",
          body: JSON.stringify({ id: Number(selectedReminderId), _action: "delete" })
        });
        toast("Kay\u0131t silindi.", "success");
        await loadGenericModule(reminderMeta, "");
        return true;
      } catch (error) {
        toast("Silinemedi: " + (error.message || ""), "error");
        return false;
      }
    }, "Evet, Sil");
    document.querySelector("#dialogCancel").textContent = "Hay\u0131r";
    document.querySelector("#dialogSubmit").classList.remove("primary");
    document.querySelector("#dialogSubmit").classList.add("danger");
  }

}());
