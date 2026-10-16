/* WhatsApp reference layout for desktop and responsive web settings. */
(function () {
  function fieldMarkup(sectionKey, selectedKeys) {
    const definition = settingsDefinitions[sectionKey];
    if (!definition) return "";
    const selected = new Set(selectedKeys);
    const scope = definition.scope || "settings";
    return definition.fields
      .filter((field) => selected.has(field[0]))
      .map((field) => exactSettingsField(field, scope))
      .join("");
  }

  function statusValue(value, ready) {
    return `<span class="messaging-ref-status ${ready ? "ready" : "idle"}">${value}</span>`;
  }

  function renderMessagingReference(settings) {
    const values = settings || {};
    const has = (key) => String(values[key] || "").trim().length > 0;
    const mode = String(values.whatsapp_mode || "cloud_api");
    const whatsappReady = (mode === "cloud_api" && has("whatsapp_cloud_phone_id") && has("whatsapp_cloud_token"))
      || (mode === "provider_api" && has("twilio_account_sid") && has("twilio_auth_token"))
      || (mode === "desktop_manual" && has("whatsapp_number"));
    const smsReady = String(values.sms_active || "0") === "1";
    const telegramReady = has("telegram_bot_token");
    const aiReady = has("gemini_api_key");
    const modeField = fieldMarkup("messaging", ["whatsapp_mode"]);
    const gatewayFields = fieldMarkup("messaging", [
      "whatsapp_number", "whatsapp_cloud_phone_id", "whatsapp_cloud_token",
      "twilio_account_sid", "twilio_auth_token", "twilio_whatsapp_from"
    ]);
    const templateField = fieldMarkup("messaging", ["whatsapp_payment_template"]);
    const templateName = fieldMarkup("messaging", ["whatsapp_cloud_template"]);
    const reminderFields = fieldMarkup("messaging", [
      "whatsapp_payment_reminder_day", "whatsapp_payment_reminder_time", "whatsapp_payment_min_debt_try"
    ]);
    const reminderSwitch = fieldMarkup("messaging", ["whatsapp_payment_reminder_enabled"]);
    const activeSwitch = fieldMarkup("messaging", ["whatsapp_active"]);
    const smsFields = fieldMarkup("sms-settings", ["sms_username", "sms_password", "sms_title", "sms_active"]);
    const telegramFields = fieldMarkup("messaging", [
      "telegram_bot_token", "whatsapp_api_key", "whatsapp_admin_phone", "whatsapp_api_token"
    ]);
    const aiFields = fieldMarkup("ai-settings", ["gemini_api_key", "gemini_model"]);
    const cargoFields = fieldMarkup("cargo", [
      "cargo_default_company", "cargo_branch_code", "cargo_sender_name", "cargo_sender_phone",
      "cargo_delivery_days", "cargo_auto_track", "cargo_sms_notify", "cargo_require_receiver"
    ]);
    const stages = [
      ["repaired", "Onarim tamamlandi", "1 Gun", "repair_done_notify"],
      ["approval", "Musteri onayi bekleniyor", "2 Gun", "approval_pending"],
      ["parts", "Parca bekleniyor", "3 Gun", "part_waiting_info"],
      ["testing", "Test asamasinda", "0 (Anlik)", "testing_stage"],
      ["done", "Teslime hazir", "1 Gun", "ready_for_pickup"]
    ];
    const notificationRows = stages.map(([key, label, intervalDefault, templateDefault]) => {
      const intervalKey = `loop_${key}`;
      const templateKey = `loop_template_${key}`;
      const activeKey = `loop_active_${key}`;
      const interval = esc(values[intervalKey] || intervalDefault);
      const template = esc(values[templateKey] || templateDefault);
      const enabled = String(values[activeKey] ?? "1") !== "0";
      return `<tr><td><span class="messaging-ref-stage-dot"></span>${label}</td>
        <td class="messaging-ref-check ${whatsappReady ? "ready" : "idle"}">${whatsappReady ? "\u2713" : "\u2014"}</td>
        <td class="messaging-ref-check ${smsReady ? "ready" : "idle"}">${smsReady ? "\u2713" : "\u2014"}</td>
        <td><input class="exact-setting messaging-ref-table-input" data-setting-key="${intervalKey}" data-setting-scope="settings" aria-label="${label} tekrar araligi" value="${interval}"></td>
        <td><input class="exact-setting messaging-ref-table-input messaging-ref-code" data-setting-key="${templateKey}" data-setting-scope="settings" aria-label="${label} HSM sablonu" value="${template}"></td>
        <td><input class="switch exact-setting" data-setting-key="${activeKey}" data-setting-scope="settings" type="checkbox" ${enabled ? "checked" : ""} aria-label="${label} etkin"></td></tr>`;
    }).join("");
    const macros = [
      ["Ariza Hizli Sec", "#22c5ff"], ["Islem Detayi", "#10b981"],
      ["Gizli Not", "#f59e0b"], ["Aksesuar Listesi", "#a78bfa"]
    ].map(([label, tone]) => `<button class="messaging-ref-macro" type="button" data-settings-section="notes" style="--macro-tone:${tone}">${label}</button>`).join("");
    const previewText = esc(values.whatsapp_payment_template || "Merhaba {musteri_adi}, AYEC Pro hesabinizda {borc_tutari} TRY borc bulunuyor.");

    return `<section class="messaging-reference">
      <div class="messaging-ref-status-strip">
        <article><small>KANAL</small><strong>WHATSAPP</strong>${statusValue("Aktif", whatsappReady)}</article>
        <article><small>SABLON DURUMU</small><strong>${whatsappReady ? "HAZIR" : "BEKLIYOR"}</strong>${statusValue("Dogrulandi", whatsappReady)}</article>
        <article><small>GUVENLIK KATMANI</small><strong class="secure">TOKEN KORUMALI</strong><span class="messaging-ref-tag danger">256-bit</span></article>
        <article><small>HATIRLATMA DONGUSU</small><strong class="planned">${String(values.whatsapp_payment_reminder_enabled || "0") === "1" ? "PLANLI CRON" : "KAPALI"}</strong><span class="messaging-ref-tag">Haftalik</span></article>
      </div>
      <aside class="messaging-ref-notice"><b>i</b><span>Uc gonderim modu desteklenir: Meta Cloud API, resmi saglayici API ve WhatsApp Desktop kullanici onayli yardimci modu. Cloud API icin onayli sablon ve opt-in kaydi gerekir.</span></aside>
      <div class="messaging-ref-layout">
        <main class="messaging-ref-main">
          <section class="messaging-ref-card messaging-ref-gateway">
            <header><div><span class="messaging-ref-icon">WA</span><div><h3>WhatsApp Meta Cloud API Protokolu</h3><p>Kurumsal API kimlik dogrulamasi ve iletisim gecidi parametreleri</p></div></div><span class="messaging-ref-live ${whatsappReady ? "ready" : "idle"}">${whatsappReady ? "Aktif Mod: " + esc(mode) : "Kurulum bekliyor"}</span></header>
            <div class="messaging-ref-mode-field">${modeField}</div>
            <div class="messaging-ref-mode-tabs" role="group" aria-label="WhatsApp gonderim modu">
              <button type="button" data-whatsapp-mode="cloud_api" class="${mode === "cloud_api" ? "active" : ""}">Meta Cloud API</button>
              <button type="button" data-whatsapp-mode="desktop_manual" class="${mode === "desktop_manual" ? "active" : ""}">WA Desktop</button>
              <button type="button" data-whatsapp-mode="provider_api" class="${mode === "provider_api" ? "active" : ""}">Twilio API</button>
            </div>
            <div class="messaging-ref-fields">${gatewayFields}</div>
            <div class="messaging-ref-switch">${activeSwitch}</div>
            <div class="messaging-ref-variables"><small>Sablon dinamik degiskenleri</small>
              <div><button type="button" data-template-token="{musteri_adi}">+ {Musteri_Adi}</button><button type="button" data-template-token="{firma_adi}">+ {Firma_Adi}</button><button type="button" data-template-token="{borc_tutari}">+ {Borc_Tutari}</button><button type="button" data-template-token="{takip_no}">+ {Takip_No}</button><button type="button" data-template-token="{cihaz_model}">+ {Cihaz_Model}</button><button type="button" data-template-token="{teslim_tarihi}">+ {Teslim_Tarihi}</button></div>
            </div>
            <div class="messaging-ref-template">${templateField}</div>
            <aside class="messaging-ref-policy"><b>i</b><span>Meta Cloud API icin onayli HSM sablonlari gereklidir. 24 saat disinda yalnizca onaylanmis sablon tetiklenebilir.</span></aside>
          </section>
          <section class="messaging-ref-card messaging-ref-preview"><header><h3>Canli Sablon Onizleme</h3><div><small>Sablon:</small>${templateName}</div></header><div class="messaging-ref-bubble"><b>AYEC Servis Bilgilendirme</b><p>${previewText}</p><small>10:42\u3000\u2713\u2713</small></div></section>
        </main>
        <aside class="messaging-ref-aside">
          <section class="messaging-ref-card messaging-ref-matrix"><header><div><h3>Servis Durum Bildirim Donguleri &amp; SMS Ag Gecidi</h3><p>Servis durumlari gelistikce WhatsApp/SMS ile otomatik bildirim gonderin.</p></div><span class="messaging-ref-tag">5 Aktif Kural</span></header>
            <div class="messaging-ref-table-wrap"><table><thead><tr><th>Servis Durumu</th><th>WhatsApp</th><th>SMS Yedek</th><th>Tekrar</th><th>Meta HSM Sablonu</th><th>Durum</th></tr></thead><tbody>${notificationRows}</tbody></table></div>
            <details class="messaging-ref-sms-settings"><summary>SMS yedek ag gecidi ayarlari</summary><div class="messaging-ref-fields">${smsFields}</div></details>
          </section>
          <section class="messaging-ref-card messaging-ref-reminder"><header><h3>Haftalik Otomatik Borc Hatirlatma Modulu</h3>${reminderSwitch}</header><div class="messaging-ref-fields messaging-ref-reminder-fields">${reminderFields}</div></section>
          <div class="messaging-ref-addons">
            <section class="messaging-ref-card messaging-ref-addon"><header><h3>Kargo Otomasyonu</h3>${statusValue("Entegre", true)}</header><div class="messaging-ref-fields">${cargoFields}</div><button type="button" class="messaging-ref-link" data-settings-section="cargo">Kargo ayarlarini ac</button></section>
            <section class="messaging-ref-card messaging-ref-addon"><header><h3>Telegram &amp; AI Masasi</h3>${statusValue(telegramReady ? "Bagli" : "Kurulum", telegramReady)}</header><div class="messaging-ref-fields">${telegramFields}</div><button type="button" class="messaging-ref-link" data-settings-section="integrations">Telegram ayarlarini yonet</button></section>
            <section class="messaging-ref-card messaging-ref-addon"><header><h3>Hizli Not &amp; Makro Cipleri</h3><button type="button" class="messaging-ref-link" data-settings-section="notes">Duzenle</button></header><div class="messaging-ref-macros">${macros}</div></section>
            <section class="messaging-ref-card messaging-ref-addon"><header><h3>AYEC AI Core Asistani</h3>${statusValue(aiReady ? "Bagli" : "Anahtar gerekli", aiReady)}</header><div class="messaging-ref-fields">${aiFields}</div><button type="button" class="messaging-ref-link" data-settings-section="ai-settings">AI parametreleri</button></section>
          </div>
        </aside>
      </div>
      <footer class="messaging-ref-footer"><span>Ayar degisiklikleri AYEC Pro ayar kaydina yazilir.</span><div><button type="button" class="secondary" data-message-test>Test mesaji gonder</button><button type="button" class="primary" data-action="save-settings">Tum ayarlari kaydet</button></div></footer>
    </section>`;
  }

  const baseSettingBody = settingBody;
  settingBody = function (settings) {
    if (settingsSection === "messaging") return renderMessagingReference(settings);
    return baseSettingBody(settings);
  };

  document.addEventListener("click", (event) => {
    const modeButton = event.target.closest("[data-whatsapp-mode]");
    if (modeButton) {
      const select = document.querySelector('[data-setting-key="whatsapp_mode"]');
      if (select) {
        select.value = modeButton.dataset.whatsappMode;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        modeButton.parentElement.querySelectorAll("button").forEach((button) => button.classList.toggle("active", button === modeButton));
      }
      return;
    }
    const tokenButton = event.target.closest("[data-template-token]");
    if (tokenButton) {
      const input = document.querySelector('[data-setting-key="whatsapp_payment_template"]');
      if (input) {
        const token = tokenButton.dataset.templateToken;
        const start = input.selectionStart ?? input.value.length;
        const end = input.selectionEnd ?? start;
        input.setRangeText(token, start, end, "end");
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
      return;
    }
    const testButton = event.target.closest("[data-message-test]");
    if (testButton) {
      toast("Test mesaji gonderimi masaustu uygulamasinda kullanilabilir.", "info");
    }
  });
})();
