from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_midnight_global_search_offers_accessible_turkish_voice_input():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'id="globalSearchVoice"' in html
    assert "window.SpeechRecognition||window.webkitSpeechRecognition" in app
    assert 'recognition.lang="tr-TR"' in app
    assert 'classList.add("listening")' in app
    assert ".global-search-voice.listening" in styles


def test_voice_shortcuts_are_configurable_persistent_and_responsive():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert '"voice-shortcuts"' in app
    assert 'settingsSection==="voice-shortcuts"?renderVoiceShortcuts()' in app
    assert 'localStorage.setItem("ayec.web.voice-shortcuts"' in app
    assert 'desktopSettings.voice_assistant_shortcuts' in app
    assert 'key:"voice_assistant_shortcuts",value:encoded' in app
    assert 'type:"builtin",name:action' in app
    assert 'type:"page",index:' in app
    assert 'data-voice-edit' in app
    assert 'data-voice-delete' in app
    assert 'data-voice-search' in app
    assert 'data-voice-type' in app
    assert 'data-voice-prev' in app and 'data-voice-next' in app
    assert 'data-kind="voice-shortcut"' in app
    assert 'voice-shortcut-edit' in app and 'voice-shortcut-delete' in app
    assert 'const ayecVoiceShortcutPageSize=4' in app
    assert 'function ayecRunVoiceShortcut' in app
    assert 'function ayecNormalizeVoicePhrase' in app
    assert 'shortcut?(matches(shortcut)?shortcut:null)' in app
    assert "@media(max-width:600px){.voice-shortcuts-page" in styles
    assert 'type==="Fonksiyon"?functions.map' in app
    assert 'name="action_type"' in app
    assert 'list="voiceActionOptions"' in app
    assert 'actionOptions.innerHTML=entries.map' in app
    assert 'titles[item.page][1]' in app
    assert 'panel_kapat:"dashboard"' in app
    assert '["servis_ac"].includes(action)' in app
    assert 'type==="Aksiyon"&&titles[action]' in app


def test_voice_shortcut_migrated_desktop_functions_resolve_to_web_pages():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'stok_sorgu:"stock"' in app
    assert 'list_critical_stock:"stock"' in app
    assert 'stock_summary:"stock"' in app
    assert 'financial_summary:"finance"' in app
    assert 'accounting_summary:"finance"' in app


def test_voice_shortcut_context_menu_matches_desktop_actions_and_geometry():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    parity = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "settings_widgets" / "voice_assistant_shortcuts.py").read_text(encoding="utf-8")
    start = app.index('showContext=function(event,kind,id){if(kind!=="voice-shortcut")')
    end = app.index("\n", start)
    web_menu = app[start:end]
    desktop_start = desktop.index("def _show_context_menu(self, position: QPoint):")
    desktop_end = desktop.index("def _edit_shortcut", desktop_start)
    desktop_menu = desktop[desktop_start:desktop_end]
    expected = ["voice-shortcut-edit", "voice-shortcut-delete", "voice-shortcut-separator", "voice-shortcut-add"]
    positions = [web_menu.index(action) for action in expected]

    assert positions == sorted(positions)
    assert '\\u270f\\ufe0f D\\u00fczenle' in web_menu
    assert '\\ud83d\\uddd1\\ufe0f Sil' in web_menu
    assert '\\u2795 Yeni Kestirme Ekle' in web_menu
    assert 'border-radius: 8px' in desktop_menu and 'padding: 4px' in desktop_menu
    assert 'padding: 8px 24px' in desktop_menu and 'border-radius: 4px' in desktop_menu
    assert '#contextMenu:has([data-context-action^="voice-shortcut-"])' in parity
    assert 'button:hover' in parity and 'padding:8px 24px' in parity
    assert 'customer_360:"customers"' in app
    assert 'device_status_query:"job-reports"' in app
    assert 'discount_advice:"customers"' in app
    assert 'loan_summary:"income"' in app
    assert 'check_summary:"checks"' in app
    assert 'add_quick_note_voice:"reminders"' in app
    assert 'service_workload_summary:"job-reports"' in app
    assert 'assistant_help:"assistant"' in app
    assert 'type==="Aksiyon"&&["stock_comparison"' in app


def test_voice_shortcut_editor_uses_desktop_sized_horizontal_form_layout():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'voiceShortcut=body.includes(\'voice-shortcut-form\')' in app
    assert '"voice-shortcut-editor-dialog"' in app
    assert 'class="form-grid voice-shortcut-form"' in app
    assert 'Kestirme D\\u00fczenle":"Yeni Kestirme' in app
    assert 'placeholder="\\u00f6rn: stok_sorgu"' in app
    assert 'placeholder="stoklar, stok, sto\\u011fa bak, envanter' in app
    assert "#appDialog.voice-shortcut-editor-dialog .voice-shortcut-form .field{display:grid" in styles
    assert "#appDialog.voice-shortcut-editor-dialog #dialogFooter button{flex:1 1 0" in styles


def test_voice_shortcut_defaults_match_the_desktop_assistant_configuration():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'name:"stok_sorgu",phrases:["stoklar","eksik stok","stok durumu"],action_type:"Fonksiyon",action:"list_critical_stock"' in app
    assert 'name:"servis_ac",phrases:["yeni servis","kay\\u0131t olu\\u015ftur","servis a\\u00e7"],action_type:"Fonksiyon",action:"servis_ac"' in app
    assert 'name:"excel_islem",phrases:["excel a\\u00e7","\\u00f6\\u011frenci bul","rapor al"],action_type:"Fonksiyon",action:"accounting_summary"' in app
    assert 'name:"panel_ac",phrases:["teknisyen paneli","panel a\\u00e7","teknisyen"],action_type:"Fonksiyon",action:"panel_ac"' in app


def test_voice_stock_price_action_previews_before_confirmed_update():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'action==="sync_now"' in app
    assert 'hydrateDesktop().then(()=>{render();toast(' in app
    assert 'action==="apply_zam"' in app
    assert 'function ayecOpenVoiceStockPriceDialog(transcript="")' in app
    assert 'action:"preview",percentage,category' in app
    assert 'action:"apply",...preview' in app
    assert 'Onayla ve Uygula' in app
    assert 'geri al\\u0131namaz' in app


def test_voice_daily_and_closing_routines_present_tenant_schedule_and_stock():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'action==="greeting_routine"||action==="closing_routine"' in app
    assert 'async function ayecOpenVoiceDailyPlanDialog()' in app
    assert 'apiFetch("/api/desktop/bootstrap")' in app
    assert 'item.date||"").slice(0,10)===dateKey' in app
    assert 'item.min_stock!==null&&item.min_stock!==undefined' in app
    assert 'Bug\\u00fcn\\u00fcn randevular\\u0131' in app


def test_voice_settings_speech_preview_uses_local_ema_audio_route():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "async function playVoiceSettingsPreview(button)" in app
    assert 'if(settingsSection==="voice-settings")return renderVoiceReferenceSettings()' in app
    assert 'fetch("/api/desktop/assistant/speech"' in app
    assert 'last_triggered:alert.last_triggered,_action:"update"' in app
    assert 'String(alert.last_triggered||"").slice(0,10)===dateKey' in app
    assert 'data-voice-speech-preview onclick="playVoiceSettingsPreview(this)"' in app
    assert "data-voice-reminder-settings onclick=\"settingsSection='voice-shortcuts';render()\"" in app
    assert 'readValue("asistan_ozel_adi","AYEC")' in app
    assert 'readValue("asistan_user_name","Efendim,")' in app
    assert "async function testVoiceMicrophone(button)" in app
    assert 'navigator.mediaDevices.getUserMedia(deviceId?{audio:{deviceId:{exact:deviceId}}}:{audio:true})' in app
    assert 'track.stop()' in app
    assert 'data-voice-microphone-test onclick="testVoiceMicrophone(this)"' in app
    assert 'function refreshVoiceInputDevices(preferred="")' in app
    assert 'localStorage.getItem("ayec.web.voice.input-device")' in app
    assert 'getUserMedia(deviceId?{audio:{deviceId:{exact:deviceId}}}:{audio:true})' in app


def test_voice_settings_lists_every_desktop_scheduled_alert():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert '["service_delivery","Servis Teslimat\\u0131","Tamamlanan servislerin teslimini hat\\u0131rlat\\u0131r","17:30"]' in app
    assert 'Number(alert.is_enabled??1)!==1' in app
    assert 'data-voice-alert="${type}"' in app
    assert 'data-voice-alert-time="${type}"' in app
    assert 'onchange="saveVoiceReminderTime(this)"' in app
    assert "async function saveVoiceReminderTime(input)" in app
    assert "await apiFetch(\"/api/desktop/table/scheduled_alerts\"" in app


def test_scheduled_voice_alerts_follow_quiet_hours_and_feature_settings():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "function isWithinVoiceQuietHours(now)" in app
    assert 'desktopInternalSettings.feature_scheduled_alerts_active??"1"' in app
    assert 'desktopInternalSettings.feature_voice_alerts_active??"1"' in app
    assert "if(!voiceEnabled||quiet&&!critical)return" in app
    assert 'fetch("/api/desktop/assistant/speech"' in app
