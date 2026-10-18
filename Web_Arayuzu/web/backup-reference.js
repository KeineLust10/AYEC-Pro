(function () {
  "use strict";

  renderBackupPage = function () {
    var definition = settingsDefinitions.backup;
    var regular = definition.fields.filter(function (field) { return field[2] !== "checkbox"; });
    var toggles = definition.fields.filter(function (field) { return field[2] === "checkbox"; });
    var fields = '<div class="form-grid">' + regular.map(function (field) {
      return exactSettingsField(field, definition.scope || "settings");
    }).join("") + '</div><div class="settings-grid">' + toggles.map(function (field) {
      return exactSettingsField(field, definition.scope || "settings");
    }).join("") + '</div>';
    return pageHead(
      "Yedekleme ve Veri G\u00fcvenli\u011fi Merkezi",
      "Tenant veritaban\u0131n\u0131 merkezi yedek ar\u015fivine kaydedin ve gerekti\u011finde indirin."
    ) + '<section class="backup-reference-actions">'
      + '<button type="button" class="primary" data-backup-create>Hemen Sunucu Yede\u011fi Al</button>'
      + '<button type="button" class="secondary" data-backup-restore>Geri Y\u00fckleme Merkezini A\u00e7</button>'
      + '<button type="button" class="secondary" data-backup-stage>Dosyadan Merkezi Geri Y\u00fckleme Haz\u0131rla</button>'
      + '<input type="file" id="backupRestoreFile" accept=".db,.sqlite,.sqlite3" hidden>'
      + '<button type="button" class="secondary" data-action="export-all">Web JSON D\u0131\u015fa Aktar</button>'
      + '</section>'
      + '<section class="backup-reference-metrics">'
      + '<article><small>SON SUNUCU YEDE\u011e\u0130</small><strong id="backupLatestValue">Y\u00fckleniyor</strong><span id="backupLatestMeta">Merkezi ar\u015fiv okunuyor.</span></article>'
      + '<article><small>AR\u015e\u0130V KAYDI</small><strong id="backupCountValue">-</strong><span>Etkin tenant ve \u00fcr\u00fcn kay\u0131tlar\u0131</span></article>'
      + '<article><small>VER\u0130TABANI B\u00dcT\u00dcNL\u00dc\u011e\u00dc</small><strong>SQLite kontrol\u00fc</strong><span>Yedek kayd\u0131 saklanmadan \u00f6nce do\u011frulan\u0131r.</span></article>'
      + '<article><small>GER\u0130 Y\u00dcKLEME</small><strong>Merkezi y\u00f6netim</strong><span>Restore komutlar\u0131 Admin Konsolu taraf\u0131ndan y\u00f6netilir.</span></article>'
      + '</section>'
      + '<section class="card backup-reference-archive"><header><div><h3>Merkezi Yedek Ar\u015fivi</h3>'
      + '<p class="muted">Yedekler tenant, \u00fcr\u00fcn, checksum ve olu\u015fturma zaman\u0131yla kaydedilir.</p></div>'
      + '<button type="button" class="secondary" data-backup-refresh>Ar\u015fivi Yenile</button></header>'
      + '<div id="tenantBackupRows">' + empty("Yedekler y\u00fckleniyor", "Tenant ar\u015fivi okunuyor.") + '</div></section>'
      + '<section class="card backup-reference-drive"><header><div><h3>Google Drive Yedekleme</h3>'
      + '<p class="muted">Web OAuth istemci dosyas\u0131n\u0131 se\u00e7in, Google hesab\u0131n\u0131 ba\u011flay\u0131n ve do\u011frulanm\u0131\u015f tenant yede\u011fini Drive\u0027a aktar\u0131n.</p></div>'
      + '<strong id="backupDriveStatus" role="status">Ba\u011flant\u0131 durumu okunuyor</strong></header>'
      + '<div class="backup-reference-drive-actions"><label class="drive-client-file">OAuth Web istemci JSON dosyas\u0131'
      + '<input type="file" id="backupDriveClientFile" accept="application/json,.json"></label>'
      + '<button type="button" class="secondary" data-backup-drive-connect>Google Drive hesab\u0131n\u0131 ba\u011fla</button>'
      + '<button type="button" class="primary" data-backup-drive-upload disabled>Yede\u011fi Drive\u0027a aktar</button>'
      + '<button type="button" class="secondary" data-backup-drive-disconnect disabled>Ba\u011flant\u0131y\u0131 kald\u0131r</button></div>'
      + '<p class="muted">Google OAuth istemcisini Web application olarak kaydedip a\u015fa\u011f\u0131daki callback adresini yetkili adreslere ekleyin:</p>'
      + '<code id="backupDriveRedirectUri"></code></section>'
      + '<section class="backup-reference-lower"><article class="card"><header><div><h3>Otomatik Yedekleme Tercihleri</h3>'
      + '<p class="muted">G\u00fcnl\u00fck yedek sunucuda se\u00e7ilen saatte, bu tenant i\u00e7in kaydedilen saat diliminde al\u0131n\u0131r.</p></div>'
      + '<button type="button" class="primary" data-backup-save-settings>Tercihleri Kaydet</button></header>'
      + '<div class="backup-reference-settings">' + fields + '</div></article>'
      + '<article class="card backup-reference-json"><header><div><h3>Web JSON Aktar\u0131m\u0131</h3>'
      + '<p class="muted">Bu i\u015flem taray\u0131c\u0131 \u00e7al\u0131\u015fma alan\u0131n\u0131 aktar\u0131r; tenant SQLite yede\u011fi yerine ge\u00e7mez.</p></div></header>'
      + '<div class="actions"><button type="button" class="secondary" data-action="restore-backup">Web JSON Yede\u011fi \u0130\u00e7e Aktar</button></div></article></section>';
  };

  var bindPageBeforeBackupReference = bindPage;
  bindPage = function () {
    bindPageBeforeBackupReference();
    if (page !== "backup") return;
    var create = document.querySelector("[data-backup-create]");
    var refresh = document.querySelector("[data-backup-refresh]");
    var restore = document.querySelector("[data-backup-restore]");
    var stageRestore = document.querySelector("[data-backup-stage]");
    var restoreFile = document.querySelector("#backupRestoreFile");
    var saveSettings = document.querySelector("[data-backup-save-settings]");
    var driveConnect = document.querySelector("[data-backup-drive-connect]");
    var driveUpload = document.querySelector("[data-backup-drive-upload]");
    var driveDisconnect = document.querySelector("[data-backup-drive-disconnect]");
    var dailyEnabled = document.querySelector('[data-setting-key="backup_daily_enabled"]');
    var dailyTime = document.querySelector('[data-setting-key="backup_daily_time"]');
    if (dailyTime) dailyTime.disabled = !dailyEnabled || !dailyEnabled.checked;
    if (dailyEnabled && dailyTime) dailyEnabled.addEventListener("change", function () {
      dailyTime.disabled = !dailyEnabled.checked;
    });
    if (create) create.addEventListener("click", createTenantBackup);
    if (refresh) refresh.addEventListener("click", loadTenantBackups);
    if (restore) restore.addEventListener("click", openRestoreCenter);
    if (stageRestore && restoreFile) {
      stageRestore.addEventListener("click", function () { restoreFile.click(); });
      restoreFile.addEventListener("change", stageRestoreBackup);
    }
    if (saveSettings) saveSettings.addEventListener("click", saveBackupSettings);
    if (driveConnect) driveConnect.addEventListener("click", connectGoogleDrive);
    if (driveUpload) driveUpload.addEventListener("click", uploadBackupToGoogleDrive);
    if (driveDisconnect) driveDisconnect.addEventListener("click", disconnectGoogleDrive);
    loadGoogleDriveStatus();
    loadTenantBackups();
  };

  async function loadGoogleDriveStatus() {
    var status = document.querySelector("#backupDriveStatus");
    var upload = document.querySelector("[data-backup-drive-upload]");
    var disconnect = document.querySelector("[data-backup-drive-disconnect]");
    var redirectUri = document.querySelector("#backupDriveRedirectUri");
    if (!status) return;
    try {
      var result = await apiFetch("/api/desktop/backups/google-drive/status");
      if (redirectUri) redirectUri.textContent = result.redirect_uri || "";
      status.textContent = result.connected ? "Google Drive ba\u011fl\u0131" : result.configured ? "Google Drive hesab\u0131 bekleniyor" : "Google Drive ba\u011fl\u0131 de\u011fil";
      if (upload) upload.disabled = !result.connected;
      if (disconnect) disconnect.disabled = !result.configured;
    } catch (error) {
      status.textContent = error.message || "Google Drive durumu okunamad\u0131";
    }
  }

  async function connectGoogleDrive(event) {
    var button = event.currentTarget;
    var input = document.querySelector("#backupDriveClientFile");
    var file = input && input.files && input.files[0];
    if (!file) return toast("\u00d6nce OAuth Web istemci JSON dosyas\u0131n\u0131 se\u00e7in.", "error");
    if (file.size > 512 * 1024) return toast("OAuth istemci dosyas\u0131 512 KB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor.", "error");
    button.disabled = true;
    try {
      var clientConfig = JSON.parse(await file.text());
      var result = await apiFetch("/api/desktop/backups/google-drive/connect", { method: "POST", body: JSON.stringify({ client_config: clientConfig }) });
      window.location.assign(result.authorization_url);
    } catch (error) {
      toast(error.message || "Google OAuth ba\u011flant\u0131s\u0131 ba\u015flat\u0131lamad\u0131.", "error");
      button.disabled = false;
    }
  }

  async function uploadBackupToGoogleDrive(event) {
    var button = event.currentTarget;
    button.disabled = true;
    try {
      var result = await apiFetch("/api/desktop/backups/google-drive", { method: "POST", body: "{}" });
      toast("Tenant yede\u011fi merkezi ar\u015five ve Google Drive\u0027a kaydedildi.", "success");
      await loadTenantBackups();
    } catch (error) {
      toast(error.message || "Google Drive yedeklemesi ba\u015far\u0131s\u0131z.", "error");
    } finally {
      button.disabled = false;
      await loadGoogleDriveStatus();
    }
  }

  async function disconnectGoogleDrive() {
    openDialog("Google Drive Ba\u011flant\u0131s\u0131n\u0131 Kald\u0131r", "YEDEKLEME", "<p>Google Drive ba\u011flant\u0131s\u0131 ve bu tenant\u2019a ait kay\u0131tl\u0131 token silinsin mi?</p>", async function () {
      try {
        await apiFetch("/api/desktop/backups/google-drive/disconnect", { method: "POST", body: "{}" });
        toast("Google Drive ba\u011flant\u0131s\u0131 kald\u0131r\u0131ld\u0131.", "success");
        await loadGoogleDriveStatus();
        return true;
      } catch (error) {
        toast(error.message || "Google Drive ba\u011flant\u0131s\u0131 kald\u0131r\u0131lamad\u0131.", "error");
        return false;
      }
    }, "Ba\u011flant\u0131y\u0131 Kald\u0131r");
    document.querySelector("#dialogCancel").textContent = "Hay\u0131r";
    document.querySelector("#dialogSubmit").classList.remove("primary");
    document.querySelector("#dialogSubmit").classList.add("danger");
  }

  function formatBackupSize(value) {
    var size = Number(value || 0);
    if (size < 1024) return size + " B";
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB";
    return (size / (1024 * 1024)).toFixed(2) + " MB";
  }

  async function loadTenantBackups() {
    var host = document.querySelector("#tenantBackupRows");
    if (!host) return;
    host.innerHTML = empty("Yedekler y\u00fckleniyor", "Tenant ar\u015fivi okunuyor.");
    try {
      var result = await apiFetch("/api/desktop/backups");
      var backups = result.backups || [];
      window.currentTenantBackups = backups;
      var count = document.querySelector("#backupCountValue");
      var latest = document.querySelector("#backupLatestValue");
      var latestMeta = document.querySelector("#backupLatestMeta");
      if (count) count.textContent = String(backups.length);
      if (latest) latest.textContent = backups.length ? String(backups[0].created_at || "Kay\u0131t var") : "Yedek yok";
      if (latestMeta) latestMeta.textContent = backups.length ? formatBackupSize(backups[0].size_bytes) + " - " + String(backups[0].source || "web") : "Hen\u00fcz sunucu yede\u011fi al\u0131nmad\u0131.";
      if (!backups.length) {
        host.innerHTML = empty("Merkezi ar\u015fiv bo\u015f", "Sunucu yede\u011fi olu\u015fturarak ba\u015flay\u0131n.");
        return;
      }
      host.innerHTML = '<div class="table-wrap"><table class="backup-reference-table"><thead><tr>'
        + '<th>Yedek Dosyas\u0131</th><th>Boyut</th><th>Tarih</th><th>Kaynak</th><th>Checksum</th><th>\u0130\u015flem</th>'
        + '</tr></thead><tbody>' + backups.map(function (backup) {
          return '<tr><td><strong>' + esc(backup.filename || "backup.db") + '</strong><small>'
            + esc(backup.product_code || "") + '</small></td><td>' + esc(formatBackupSize(backup.size_bytes))
            + '</td><td>' + esc(backup.created_at || "-") + '</td><td>' + esc(backup.source || "web")
            + '</td><td><code>' + esc(String(backup.sha256 || "").slice(0, 12)) + '</code></td><td>'
            + '<button type="button" class="mini" data-backup-download="' + esc(backup.id) + '">SQLite \u0130ndir</button></td></tr>';
        }).join("") + '</tbody></table></div>';
      host.querySelectorAll("[data-backup-download]").forEach(function (button) {
        button.addEventListener("click", function () { downloadTenantBackup(button.dataset.backupDownload, button); });
      });
    } catch (error) {
      host.innerHTML = empty("Ar\u015fiv y\u00fcklenemedi", error.message || "");
    }
  }

  async function createTenantBackup(event) {
    var button = event.currentTarget;
    button.disabled = true;
    var label = button.textContent;
    button.textContent = "Yedek al\u0131n\u0131yor...";
    try {
      var result = await apiFetch("/api/desktop/backups", { method: "POST", body: "{}" });
      toast("Tenant SQLite yede\u011fi merkezi ar\u015five kaydedildi.", "success");
      await loadTenantBackups();
      if (result.product_archive_ok === false) toast("Ar\u015fiv kaydedildi ancak \u00fcr\u00fcn aynas\u0131 olu\u015fturulamad\u0131.", "warning");
    } catch (error) {
      toast("Sunucu yede\u011fi olu\u015fturulamad\u0131: " + (error.message || ""), "error");
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  }

  async function downloadTenantBackup(id, button) {
    button.disabled = true;
    try {
      var response = await fetch("/api/desktop/backups/" + encodeURIComponent(id) + "/download", { credentials: "same-origin" });
      if (!response.ok) {
        var errorBody = await response.json().catch(function () { return {}; });
        throw Error(errorBody.error || "Yedek indirilemedi (" + response.status + ")");
      }
      var blob = await response.blob();
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.href = url;
      link.download = (window.currentTenantBackups || []).find(function (backup) { return String(backup.id) === String(id); })?.filename || "ayec-tenant-backup.db";
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast("SQLite yede\u011fi indirildi.", "success");
    } catch (error) {
      toast(error.message || "Yedek indirilemedi.", "error");
    } finally {
      button.disabled = false;
    }
  }

  function openRestoreCenter() {
    if (typeof canAccessControlCenter === "function" && canAccessControlCenter()) {
      navigate("control-center");
      return;
    }
    openDialog(
      "Merkezi Geri Y\u00fckleme",
      "TENANT YEDEK G\u00dcVENL\u0130\u011e\u0130",
      '<p>Geri y\u00fckleme i\u015flemleri merkezi restore komutu olarak Admin Konsolu taraf\u0131ndan uygulan\u0131r. Tenant veritaban\u0131 bu ekrandan do\u011frudan de\u011fi\u015ftirilmez.</p>',
      function () { return true; },
      "Anlad\u0131m"
    );
  }

  async function stageRestoreBackup(event) {
    var input = event.currentTarget;
    var file = input.files && input.files[0];
    var button = document.querySelector("[data-backup-stage]");
    if (!file || !button) return;
    if (file.size <= 0 || file.size > 1024 * 1024 * 1024) {
      toast("Yedek dosyas\u0131 boyutu ge\u00e7ersiz.", "error");
      input.value = "";
      return;
    }
    var label = button.textContent;
    button.disabled = true;
    button.textContent = "Yedek denetleniyor...";
    try {
      var response = await fetch("/api/desktop/backups/import", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-AYEC-Backup-Name": encodeURIComponent(file.name) },
        body: file
      });
      var result = await response.json().catch(function () { return {}; });
      if (!response.ok) throw Error(result.error || "Yedek merkezi ar\u015five kaydedilemedi.");
      await loadTenantBackups();
      openDialog(
        "Yedek Geri Y\u00fckleme i\u00e7in Haz\u0131r",
        "TENANT YEDEK G\u00dcVENL\u0130\u011e\u0130",
        '<div class="form-grid"><p class="muted full">' + esc(result.filename || file.name) + ' do\u011fruland\u0131 ve tenant\u2019\u0131n merkezi yedek ar\u015fivine eklendi. Geri y\u00fckleme komutunu Admin Konsolu y\u00f6netir.</p><div class="field full"><label>Merkezi yedek numaras\u0131</label><input readonly value="' + esc(result.backup_id) + '"></div><div class="field full"><label>SHA-256</label><input readonly value="' + esc(result.sha256 || "") + '"></div></div>',
        function () { return true; },
        "Kapat"
      );
    } catch (error) {
      toast(error.message || "Yedek merkezi ar\u015five eklenemedi.", "error");
    } finally {
      input.value = "";
      button.disabled = false;
      button.textContent = label;
    }
  }

  async function saveBackupSettings(event) {
    var button = event.currentTarget;
    var fields = Array.from(document.querySelectorAll(".backup-reference-settings .exact-setting"));
    button.disabled = true;
    try {
      for (var field of fields) {
        var value = field.type === "checkbox" ? (field.checked ? "1" : "0") : field.value;
        var scope = field.dataset.settingScope || "settings";
        var key = field.dataset.settingKey;
        await desktopWrite(scope, { key: key, value: value });
        if (scope === "internal_settings") desktopInternalSettings[key] = value;
        else desktopSettings[key] = value;
      }
      var timezoneName = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      if (timezoneName) {
        await desktopWrite("settings", { key: "backup_timezone", value: timezoneName });
        desktopSettings.backup_timezone = timezoneName;
      }
      toast("Yedekleme tercihleri kaydedildi.", "success");
    } catch (error) {
      toast("Tercihler kaydedilemedi: " + (error.message || ""), "error");
    } finally {
      button.disabled = false;
    }
  }
}());
