(function () {
  "use strict";

  var genericShellBeforeAnnouncements = genericShell;
  var genericTableBeforeAnnouncements = genericTable;
  var genericDialogBeforeAnnouncements = openGenericDialog;
  var loadGenericModuleBeforeAnnouncements = loadGenericModule;

  genericShell = function (meta) {
    if (meta.table !== "announcements") return genericShellBeforeAnnouncements(meta);
    return pageHead(
      meta.title,
      meta.description,
      '<button class="secondary" data-generic-refresh>Yenile</button>'
        + '<button class="primary" data-generic-add>+ Yeni Duyuru</button>'
    ) + '<section class="card announcements-card"><div class="toolbar">'
      + '<input class="control search" id="genericSearch" placeholder="Duyurularda ara...">'
      + '<span class="muted" id="genericCount">Y\u00fckleniyor...</span></div>'
      + '<div id="genericHost">' + empty("Duyurular y\u00fckleniyor", "Masa\u00fcst\u00fc veritaban\u0131 okunuyor.") + '</div></section>';
  };

  function priorityClass(value) {
    var normalized = String(value || "").toLocaleLowerCase("tr-TR");
    if (normalized === "yuksek" || normalized === "y\u00fcksek" || normalized === "high") return "high";
    if (normalized === "dusuk" || normalized === "d\u00fc\u015f\u00fck" || normalized === "low") return "low";
    return "normal";
  }

  genericTable = function (meta, data) {
    if (meta.table !== "announcements") return genericTableBeforeAnnouncements(meta, data);
    return '<div class="table-wrap"><table class="announcements-table"><thead><tr>'
      + '<th>Tarih</th><th>\u00d6ncelik</th><th>Ba\u015fl\u0131k</th><th>\u0130\u00e7erik</th><th>Yay\u0131nlayan</th>'
      + '</tr></thead><tbody>' + data.rows.map(function (row, index) {
        var rowAttributes = row.id
          ? ' tabindex="0" data-kind="generic" data-id="' + index + '" data-generic-row="' + index + '"'
          : ' class="announcement-sample-row"';
        return '<tr' + rowAttributes + '><td class="announcement-date">'
          + esc(row.date || "") + '</td><td><span class="announcement-priority '
          + priorityClass(row.priority) + '">' + esc(row.priority || "Normal")
          + '</span></td><td class="announcement-title">' + esc(row.title || "")
          + '</td><td class="announcement-content">'
          + esc(row.content || "").replace(/\r?\n/g, "<br>")
          + '</td><td class="announcement-author">' + esc(row.author || "Sistem")
          + '</td></tr>';
      }).join("") + '</tbody></table></div>';
  };

  loadGenericModule = async function (meta, query) {
    await loadGenericModuleBeforeAnnouncements(meta, query);
    if (meta.table !== "announcements" || String(query || "").trim()) return;
    var data = window.currentGenericData || {};
    if ((data.rows || []).length) return;
    var examples = [
      ["04.01.2026", "Y\u00fcksek", "\u26a1 Sistem Bak\u0131m\u0131", "Bu hafta sonu (06-07 Ocak) sunucu bak\u0131m\u0131 yap\u0131lacakt\u0131r. Sistemde ge\u00e7ici aksakl\u0131klar ya\u015fanabilir.", "Sistem Y\u00f6neticisi"],
      ["01.01.2026", "Normal", "\u{1f389} Yeni Y\u0131l Kutlamas\u0131", "T\u00fcm \u00e7al\u0131\u015fanlar\u0131m\u0131z\u0131n ve m\u00fc\u015fterilerimizin yeni y\u0131l\u0131 kutlu olsun! Sa\u011fl\u0131k, mutluluk ve ba\u015far\u0131 dolu bir y\u0131l dileriz.", "\u0130nsan Kaynaklar\u0131"],
      ["03.01.2026", "Y\u00fcksek", "\u{1f680} v2.0 Yay\u0131nda", "AYEC Pro v2.0 s\u00fcr\u00fcm\u00fc aktif edilmi\u015ftir. Yeni \u00f6zellikler ve iyile\u015ftirmeler i\u00e7in dok\u00fcmantasyonu inceleyiniz.", "Geli\u015ftirme Ekibi"],
      ["02.01.2026", "Normal", "\u{1f4ca} Ayl\u0131k Rapor Hat\u0131rlatmas\u0131", "Ocak ay\u0131 performans raporlar\u0131 10 Ocak'a kadar haz\u0131rlanmal\u0131d\u0131r. L\u00fctfen verilerinizi sisteme giriniz.", "Muhasebe"],
      ["31.12.2025", "D\u00fc\u015f\u00fck", "\u{1f4c5} Tatil Takvimi", "2026 y\u0131l\u0131 resmi tatil takvimi payla\u015f\u0131ld\u0131. Detaylar i\u00e7in \u015firket portal\u0131n\u0131 ziyaret ediniz.", "\u0130dari \u0130\u015fler"]
    ].map(function (row) {
      return { date: row[0], priority: row[1], title: row[2], content: row[3], author: row[4] };
    });
    $("#genericHost").innerHTML = genericTable(meta, {
      columns: ["date", "priority", "title", "content", "author"],
      rows: examples
    });
  };

  function announcementDialog(meta, row, columns) {
    var editing = Boolean(row && row.id);
    var priority = String(row && row.priority || "Normal");
    var priorities = [
      { value: "Normal", label: "Normal" },
      { value: "Y\u00fcksek", label: "Y\u00fcksek" },
      { value: "D\u00fc\u015f\u00fck", label: "D\u00fc\u015f\u00fck" }
    ];
    var options = priorities.map(function (item) {
      return '<option value="' + item.value + '"' + (priority.toLocaleLowerCase("tr-TR") === item.value.toLocaleLowerCase("tr-TR") ? " selected" : "") + '>' + item.label + '</option>';
    }).join("");
    var body = '<div class="announcement-editor"><h3>'
      + (editing ? 'Duyuru D\u00fczenle' : 'Yeni Duyuru Olu\u015ftur')
      + '</h3><div class="field"><label for="announcementTitle">Ba\u015fl\u0131k *</label>'
      + '<input id="announcementTitle" name="title" required maxlength="250" placeholder="Duyuru ba\u015fl\u0131\u011f\u0131n\u0131 giriniz" value="'
      + esc(row && row.title || "") + '"></div><div class="field"><label for="announcementPriority">\u00d6ncelik</label>'
      + '<select id="announcementPriority" name="priority">' + options
      + '</select></div><div class="field full"><label for="announcementContent">\u0130\u00e7erik *</label>'
      + '<textarea id="announcementContent" name="content" required placeholder="Duyuru i\u00e7eri\u011fini giriniz...">'
      + esc(row && row.content || "") + '</textarea></div></div>';

    openDialog(
      editing ? "Duyuru D\u00fczenle" : "Yeni Duyuru Ekle",
      "DUYURULAR",
      body,
      async function (formData) {
        var payload = Object.fromEntries(formData);
        if (editing) payload.id = row.id;
        payload._action = editing ? "update" : "create";
        try {
          await apiFetch("/api/desktop/table/announcements", {
            method: "POST",
            body: JSON.stringify(payload)
          });
          toast(editing ? "Duyuru g\u00fcncellendi." : "Duyuru eklendi.", "success");
          await loadGenericModule(meta, $("#genericSearch") && $("#genericSearch").value || "");
        } catch (error) {
          toast("Duyuru kaydedilemedi: " + (error.message || ""), "error");
          return false;
        }
      },
      editing ? "G\u00fcncelle" : "Kaydet"
    );

    var dialog = $("#appDialog");
    var footer = $("#dialogFooter");
    dialog.classList.add("announcements-edit-dialog");
    var dialogBody = $("#dialogBody");
    dialogBody.addEventListener("input", function (event) {
      if (event.target.matches('[name="title"], [name="content"], [name="priority"]')) {
        var confirmation = dialogBody.querySelector("[data-announcement-delete-confirm]");
        if (confirmation) confirmation.checked = false;
      }
    });

    if (editing) {
      var removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "danger announcement-delete-action";
      removeButton.textContent = "Sil";
      footer.prepend(removeButton);
      removeButton.onclick = async function () {
        var confirmation = dialogBody.querySelector("[data-announcement-delete-confirm]");
        if (!confirmation) {
          var notice = document.createElement("div");
          notice.className = "field full announcement-delete-confirm";
          notice.innerHTML = `<label><input type="checkbox" data-announcement-delete-confirm> "${esc(row.title || "")}" duyurusu silinecek. Bu islem geri al\u0131namaz. Onayl\u0131yorum.</label>`;
          dialogBody.append(notice);
          removeButton.textContent = "Evet, Sil";
          return;
        }
        if (!confirmation.checked) {
          toast("Duyuru silme i\u015flemini onaylay\u0131n.", "warning");
          return;
        }
        try {
          await apiFetch("/api/desktop/table/announcements", {
            method: "POST",
            body: JSON.stringify({ id: row.id, _action: "delete" })
          });
          toast("Duyuru ba\u015far\u0131yla silindi.", "success");
          dialog.close("deleted");
          await loadGenericModule(meta, $("#genericSearch") && $("#genericSearch").value || "");
        } catch (error) {
          toast("Duyuru silinemedi: " + (error.message || ""), "error");
        }
      };
    }
  }

  openGenericDialog = function (meta, row, columns) {
    if (meta.table === "announcements") return announcementDialog(meta, row || {}, columns || []);
    return genericDialogBeforeAnnouncements(meta, row, columns);
  };
}());
