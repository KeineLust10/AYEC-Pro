import json
from types import SimpleNamespace

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtTest import QTest

from src.services.assistant_ui_actions import (
    action_needs_confirmation,
    activate_table_row,
    apply_control,
    append_dictation,
    confirmation_summary,
    describe_controls,
    move_focus,
    move_item_selection,
    read_form_feedback,
    read_active_field,
    read_screen,
    search_screen,
    snapshot_control,
    restore_control,
    table_row_open_handler_available,
)
from src.services.assistant_conversation import LocalAssistantConversation
from src.services.assistant_manager import AssistantManager
from src.ui.dialogs.device_selection_dialog import DeviceSelectionDialog
from src.ui.mixins._main_window_func_mixin import MainWindowFuncMixin
from src.utils.asistan_motoru import BulutAsistan


def _app():
    return QApplication.instance() or QApplication([])


def test_hands_free_commands_are_recognized_without_wake_word():
    _app()
    commands = {
        "ekrani oku": "voice_read_screen",
        "aktif alani oku": "voice_read_field",
        "sonraki alana gec": "voice_focus_next",
        "onceki alana gec": "voice_focus_previous",
        "dikte modunu ac": "voice_dictation_on",
        "dikteyi bitir": "voice_dictation_off",
        "alani temizle": "voice_clear_field",
        "son kelimeyi sil": "voice_delete_word",
        "imleci basa al": "voice_cursor_start",
        "imleci sona al": "voice_cursor_end",
        "virgul koy": "voice_insert_comma",
        "nokta koy": "voice_insert_period",
        "yeni satir": "voice_insert_newline",
        "asagi kaydir": "voice_scroll_down",
        "yukari kaydir": "voice_scroll_up",
        "sonraki kayit": "voice_next_record",
        "onceki kayit": "voice_previous_record",
        "secili kaydi ac": "voice_open_record",
        "form hatalarini oku": "voice_read_form_feedback",
        "sayfada ara ayse": "voice_search_screen",
        "geri don": "voice_navigate_back",
        "son degisikligi geri al": "voice_undo",
        "son soyledigimi geri al": "voice_undo",
        "forma devam et": "voice_form_status",
        "formdaki eksikleri soyle": "voice_form_status",
        "formu bastan al": "voice_form_reset",
        "telefon alanini temizle": "voice_clear_named_field",
        "bekleyen islemi iptal et": "voice_cancel_pending",
        "stoklara resimden aktar": "voice_open_stock_ocr",
        "tekrar soyle": "voice_repeat_last",
        "sonraki komutlar": "voice_help_next",
        "konusmayi durdur": "voice_stop_speech",
    }
    for phrase, expected in commands.items():
        assert BulutAsistan._match_builtin_intent(None, phrase, phrase)[0] == expected


def test_technician_panel_trigger_does_not_capture_follow_up_selection():
    open_phrase = "teknisyen panelini ac"
    follow_up = "teknisyen paneli acildiktan sonra Burak Sahin'i sec"

    assert BulutAsistan._match_builtin_intent(None, open_phrase, open_phrase) == ("panel_ac", "")
    assert BulutAsistan._match_builtin_intent(None, follow_up, follow_up) == (
        "select_service_device",
        "Burak Sahin",
    )


def test_voice_business_commands_are_routed_with_their_payloads():
    commands = (
        ("asistan sezer ipek i\u00e7in indirim tavsiyesi ver", "discount_advice", "Sezer Ipek"),
        ("asistan toplant\u0131 notu al yar\u0131n m\u00fc\u015fteriyi ara", "add_quick_note_voice", "yarin musteriyi ara"),
        ("asistan yar\u0131n saat 14:30 i\u00e7in \u00f6deme hat\u0131rlat\u0131c\u0131 ekle", "add_reminder_voice", "yarin saat 14:30"),
        ("Burak \u015eahin'i se\u00e7", "select_service_device", "Burak Sahin"),
    )

    for phrase, expected_action, expected_payload in commands:
        command = phrase.removeprefix("asistan ")
        assert BulutAsistan._match_builtin_intent(None, command, command) == (
            expected_action,
            expected_payload,
        )


def test_panel_open_keeps_short_voice_follow_up_active():
    import time

    class Signal:
        def __init__(self):
            self.values = []

        def emit(self, *args):
            self.values.append(args)

    fake = SimpleNamespace(
        _normalize_settings=lambda value: value,
        _load_settings=lambda: {
            "panel_ac": {
                "triggers": ["teknisyen paneli", "teknisyen"],
                "action": "panel_ac",
            },
        },
        _match_builtin_intent=lambda text, clean: BulutAsistan._match_builtin_intent(
            None, text, clean
        ),
        _get_wake_words=lambda: [],
        _wake_is_recent=lambda: time.time() - fake.last_wake_time <= 10,
        wake_timeout_seconds=10,
        last_wake_time=0,
        last_wake_word="",
        tetik_sinyali=Signal(),
    )

    BulutAsistan.komut_coz(fake, "teknisyen panelini ac")
    BulutAsistan.komut_coz(fake, "Burak Sahin sec")

    assert fake.tetik_sinyali.values == [
        ("panel_ac", ""),
        ("select_service_device", "Burak Sahin"),
    ]


def test_voice_customer_selection_targets_the_open_device_picker_without_reopening_it():
    notifications = []
    spoken = []
    selected_targets = []

    class Picker:
        def isVisible(self):
            return True

        def select_by_voice(self, target):
            selected_targets.append(target)
            return True, "Cihazi sectim ve teknisyen panelini aciyorum."

    window = SimpleNamespace(
        _active_device_selection_dialog=Picker(),
        show_notification=lambda *args: notifications.append(args),
        on_menu_click=lambda *_args: pytest.fail("Voice selection must not reopen the menu"),
    )
    manager = SimpleNamespace(
        _assistant_prefix=lambda: "",
        _pending_voice_control=None,
        _pending_form_intake=None,
        _dictation_mode=False,
        main_window=window,
        _speak_async=spoken.append,
    )

    AssistantManager.aksiyon_merkezi(manager, "select_service_device", "Burak Sahin")

    assert selected_targets == ["Burak Sahin"]
    assert notifications == [("Cihazi sectim ve teknisyen panelini aciyorum.", "info")]
    assert spoken == ["Cihazi sectim ve teknisyen panelini aciyorum."]


def test_voice_record_selection_falls_back_to_current_menu_controls():
    continuations = []
    window = SimpleNamespace(
        _current_page_index=21,
        _active_device_selection_dialog=None,
        on_menu_click=lambda *_args: pytest.fail("Record selection must stay on the current screen"),
    )
    manager = SimpleNamespace(
        _assistant_prefix=lambda: "",
        _pending_voice_control=None,
        _pending_form_intake=None,
        _dictation_mode=False,
        main_window=window,
        _start_local_conversation=lambda utterance, continuation=False:
            continuations.append((utterance, continuation)),
    )

    AssistantManager.aksiyon_merkezi(manager, "select_service_device", "Burak Sahin")

    assert continuations == [("Burak Sahin sec", True)]


def test_voice_followup_mode_outlives_short_wake_word_timeout():
    fake = SimpleNamespace(
        followup_mode=True,
        last_wake_time=0,
        wake_timeout_seconds=10,
    )

    assert BulutAsistan._wake_is_recent(fake)
    fake.followup_mode = False
    assert not BulutAsistan._wake_is_recent(fake)


def test_assistant_help_lists_every_visible_control_and_menu_in_pages():
    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    for index in range(12):
        layout.addWidget(QPushButton("Action %02d" % index))
    dialog.show()
    app.processEvents()
    messages = []
    manager = SimpleNamespace(
        main_window=SimpleNamespace(
            _current_page_index=3,
            get_page_name_by_index=lambda _page: "Current page",
            show_notification=lambda message, _kind: messages.append(message),
        ),
        _assistant_help_state=None,
        _assistant_action_root=lambda _page: dialog,
        _visible_assistant_menu=lambda: [(index, "Menu %02d" % index) for index in range(10)],
        _speak_async=lambda message: messages.append(message),
    )
    manager._assistant_capability_entries = lambda root: AssistantManager._assistant_capability_entries(manager, root)

    AssistantManager._announce_assistant_capabilities(manager)
    AssistantManager._announce_assistant_capabilities(manager, continue_listing=True)
    AssistantManager._announce_assistant_capabilities(manager, continue_listing=True)
    combined = " ".join(messages)
    assert all("Action %02d" % index in combined for index in range(12))
    assert all("Menu %02d" % index in combined for index in range(10))
    assert manager._assistant_help_state is None
    dialog.close()


def test_dictation_preserves_turkish_transcription():
    _app()

    class Signal:
        def __init__(self):
            self.values = []

        def emit(self, *args):
            self.values.append(args)

    fake = SimpleNamespace(
        dictation_mode=True,
        _normalize_settings=lambda value: value,
        _load_settings=lambda: {},
        _match_builtin_intent=lambda text, clean: BulutAsistan._match_builtin_intent(
            None, text, clean
        ),
        tetik_sinyali=Signal(),
    )
    utterance = "\u00c7a\u011fr\u0131 i\u00e7in 125 TL"
    BulutAsistan.komut_coz(fake, utterance)
    assert fake.tetik_sinyali.values == [("assistant_chat", utterance)]
    fake.tetik_sinyali.values.clear()
    BulutAsistan.komut_coz(fake, "son kelimeyi sil")
    assert fake.tetik_sinyali.values == [("voice_delete_word", "")]


def test_clearing_text_stages_a_spoken_confirmation():
    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    field = QLineEdit("taslak bilgi")
    field.setObjectName("Aciklama")
    layout.addWidget(field)
    dialog.show()
    app.processEvents()

    manager = SimpleNamespace(
        _dictation_mode=True,
        voice_assistant_thread=None,
        _pending_voice_control=None,
        main_window=SimpleNamespace(get_page_name_by_index=lambda _page: "Servis Panosu"),
    )
    message = AssistantManager._stage_voice_confirmation(
        manager, field, "clear", None, False, dialog, 40
    )
    assert manager._dictation_mode is False
    assert manager._pending_voice_control["operation"] == "clear"
    assert "taslak bilgi" in message and "evet" in message and "hayir" in message


def test_voice_undo_restores_only_the_unchanged_last_form_value():
    import time

    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    field = QLineEdit("before")
    layout.addWidget(field)
    dialog.show()
    app.processEvents()
    before = snapshot_control(field)
    assert apply_control(field, "set", "after", overwrite=True)[0]
    after = snapshot_control(field)
    manager = SimpleNamespace(
        _last_voice_change={
            "control": field, "before": before, "after": after,
            "root": dialog, "page_id": 3, "expires_at": time.monotonic() + 60,
        },
        main_window=SimpleNamespace(
            _current_page_index=3,
            get_page=lambda _page: dialog,
        ),
        _assistant_action_root=lambda _page: dialog,
    )
    assert AssistantManager._undo_last_voice_change(manager)[0]
    assert field.text() == "before"

    assert apply_control(field, "set", "new value", overwrite=True)[0]
    manager._last_voice_change = {
        "control": field, "before": before, "after": after,
        "root": dialog, "page_id": 3, "expires_at": time.monotonic() + 60,
    }
    ok, message = AssistantManager._undo_last_voice_change(manager)
    assert not ok and "sonradan degistigi" in message
    assert field.text() == "new value"
    assert restore_control(field, before)[0]
    dialog.close()


def test_voice_ocr_opens_image_import_on_the_stock_page(monkeypatch):
    opened = []

    class Page:
        def open_smart_stock_import(self, initial_mode=""):
            opened.append(initial_mode)

    page = Page()
    window = SimpleNamespace(
        _current_page_index=7,
        get_page=lambda _page_id: page,
    )
    manager = SimpleNamespace(
        main_window=window,
        _visible_assistant_menu=lambda: [(7, "Stoklar")],
        _launch_stock_ocr_import=lambda page_id: AssistantManager._launch_stock_ocr_import(
            manager, page_id
        ),
    )
    monkeypatch.setattr(
        "src.services.assistant_manager.QTimer.singleShot",
        lambda _delay, callback: callback(),
    )
    ok, message = AssistantManager._open_stock_ocr_import(manager)
    assert ok and "onizlemeye" in message
    assert opened == ["image"]


def test_stock_import_dialog_starts_on_the_requested_ocr_tab(monkeypatch):
    from src.ui.dialogs.stock_smart_import_dialog import StockSmartImportDialog

    _app()
    selected_indexes = []

    def reject_after_inspecting(dialog):
        tabs = dialog.findChild(QTabWidget, "StockSmartImportTabs")
        selected_indexes.append(tabs.currentIndex())
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(StockSmartImportDialog, "exec", reject_after_inspecting)
    assert StockSmartImportDialog.get_import_request(initial_mode="image") == ("", "")
    assert selected_indexes == [2]


def test_read_screen_reads_bounded_ocr_preview_sample_rows():
    app = _app()
    preview_type = type("StockImportPreviewDialog", (QDialog,), {})
    preview = preview_type()
    layout = QVBoxLayout(preview)
    table = QTableWidget(1, 2)
    table.setHorizontalHeaderLabels(["Urun", "Fiyat"])
    table.setItem(0, 0, QTableWidgetItem("Kamera"))
    table.setItem(0, 1, QTableWidgetItem("1200"))
    layout.addWidget(table)
    preview.show()
    app.processEvents()

    spoken = read_screen(preview)
    assert "OCR onizlemesi toplam 1 satir" in spoken
    assert "Urun: Kamera" in spoken and "Fiyat: 1200" in spoken
    preview.close()


def test_asr_confidence_score_rejects_silence_and_low_quality():
    from src.utils.offline_turkish_asr import OfflineTurkishASR
    from src.utils import asistan_motoru

    assert OfflineTurkishASR.confidence_score(-0.3, 0.05) > 0.5
    assert OfflineTurkishASR.confidence_score(-2.0, 0.8) == 0.0
    assert OfflineTurkishASR.confidence_score(-1.6, 0.05) < asistan_motoru.MIN_COMMAND_CONFIDENCE


def test_offline_asr_retries_short_speech_without_vad(tmp_path):
    from src.utils.offline_turkish_asr import OfflineTurkishASR

    class Model:
        def __init__(self):
            self.vad_values = []

        def transcribe(self, audio_path, **options):
            self.vad_values.append(options["vad_filter"])
            if options["vad_filter"]:
                return iter(()), None
            return iter((SimpleNamespace(
                text=" finans \u00f6zeti ",
                avg_logprob=-0.3,
                no_speech_prob=0.05,
            ),)), None

    asr = object.__new__(OfflineTurkishASR)
    asr.model = Model()
    audio = SimpleNamespace(get_raw_data=lambda **kwargs: b"\x00\x00" * 16000)

    result = asr.transcribe_with_confidence(audio)

    assert asr.model.vad_values == [True, False]
    assert result["text"] == "finans \u00f6zeti"
    assert result["confidence"] > 0.5


def test_stop_tts_invalidates_pending_speech_and_stops_active_players(monkeypatch):
    from src.utils import asistan_motoru as voice_engine

    calls = []

    class Process:
        def poll(self):
            return None

        def terminate(self):
            calls.append("process")

    class Signal:
        def emit(self):
            calls.append("bridge")

    monkeypatch.setattr(voice_engine, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(voice_engine, "_active_tts_process", Process())
    monkeypatch.setattr(
        voice_engine, "_qt_player_bridge",
        SimpleNamespace(stop_requested=Signal()),
    )
    with voice_engine._tts_generation_lock:
        old_generation = voice_engine._tts_generation

    assert voice_engine.stop_tts_playback()
    assert not voice_engine._tts_generation_is_current(old_generation)
    assert calls == ["process", "bridge"]


def test_microphone_capture_waits_for_tts_echo_cooldown(monkeypatch):
    from src.utils import asistan_motoru as voice_engine

    clock = [100.0]
    monkeypatch.setattr(voice_engine.time, "monotonic", lambda: clock[0])
    with voice_engine._tts_generation_lock:
        voice_engine._tts_playback_active = False
        voice_engine._tts_mic_cooldown_until = 0.0

    assert voice_engine._tts_capture_snapshot()[1] is False
    voice_engine.stop_tts_playback()
    assert voice_engine._tts_capture_snapshot()[1] is True
    clock[0] += 0.66
    assert voice_engine._tts_capture_snapshot()[1] is False

    reads = []
    source = SimpleNamespace(
        CHUNK=512,
        stream=SimpleNamespace(read=lambda size: reads.append(size)),
    )
    assert voice_engine._discard_microphone_chunk(source)
    assert reads == [512]

    reads.clear()

    class BufferedStream:
        def __init__(self):
            self.available = 1300

        def get_read_available(self):
            return self.available

    buffered_stream = BufferedStream()

    def drain(size):
        reads.append(size)
        buffered_stream.available -= size

    source.stream = SimpleNamespace(
        read=drain,
        pyaudio_stream=buffered_stream,
    )
    assert voice_engine._discard_microphone_chunk(source)
    assert reads == [512, 512, 276]
    assert buffered_stream.available == 0


def test_microphone_recognizer_uses_adaptive_conversation_sensitivity():
    from types import SimpleNamespace
    from src.utils.asistan_motoru import _configure_microphone_recognizer

    recognizer = SimpleNamespace()
    _configure_microphone_recognizer(recognizer)

    assert recognizer.dynamic_energy_threshold is True
    assert recognizer.dynamic_energy_adjustment_ratio == 1.2
    assert recognizer.pause_threshold == 0.85
    assert recognizer.phrase_threshold == 0.2
    assert recognizer.non_speaking_duration == 0.35


def test_microphone_phrase_capture_keeps_long_conversational_requests_intact():
    from src.utils.asistan_motoru import (
        MAX_COMMAND_PHRASE_SECONDS,
        _listen_for_microphone_phrase,
    )

    calls = []
    recognizer = SimpleNamespace(
        listen=lambda source, **kwargs: calls.append((source, kwargs)) or "audio",
    )
    source = object()

    assert _listen_for_microphone_phrase(recognizer, source) == "audio"
    assert calls == [(source, {"timeout": 2, "phrase_time_limit": MAX_COMMAND_PHRASE_SECONDS})]
    assert MAX_COMMAND_PHRASE_SECONDS >= 12


def test_live_listener_pipeline_forwards_offline_transcription_to_command_router(monkeypatch):
    from src.utils import asistan_motoru, offline_turkish_asr

    _app()
    delivered = []
    audio = SimpleNamespace(
        frame_data=b"\x00\x00" * 16000,
        sample_rate=16000,
        sample_width=2,
    )

    class Recognizer:
        energy_threshold = 100

        def adjust_for_ambient_noise(self, _source, duration):
            assert duration == 1

        def listen(self, _source, **options):
            assert options == {"timeout": 2, "phrase_time_limit": 15}
            return audio

    class Microphone:
        device_index = 1
        SAMPLE_RATE = 16000

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class OfflineASR:
        def transcribe_with_confidence(self, captured_audio):
            assert captured_audio is audio
            return {"text": "finans ozet", "confidence": 0.9}

    monkeypatch.setattr(asistan_motoru.sr, "Recognizer", Recognizer)
    monkeypatch.setattr(asistan_motoru.sr, "Microphone", Microphone)
    monkeypatch.setattr(offline_turkish_asr, "OfflineTurkishASR", OfflineASR)
    monkeypatch.setattr(asistan_motoru, "_tts_capture_snapshot", lambda: (1, False))

    listener = BulutAsistan()

    def route(text):
        delivered.append(text)
        listener.is_running = False

    listener.komut_coz = route
    listener.run()

    assert delivered == ["finans ozet"]


def test_voice_stop_and_repeat_are_available_without_clearing_pending_confirmations(monkeypatch):
    calls = []
    notifications = []
    spoken = []
    pending = {"operation": "click", "expires_at": 9999999999}
    manager = SimpleNamespace(
        _pending_voice_control=pending,
        _last_spoken_response="Onaylayayim mi?",
        main_window=SimpleNamespace(
            _current_page_index=4,
            show_notification=lambda *args: notifications.append(args),
        ),
        _assistant_action_root=lambda _page: None,
        _speak_async=spoken.append,
    )
    monkeypatch.setattr(
        "src.utils.asistan_motoru.stop_tts_playback",
        lambda: calls.append("stop"),
    )
    AssistantManager._handle_voice_accessibility_command(manager, "voice_stop_speech")
    assert calls == ["stop"] and manager._pending_voice_control is pending
    assert spoken == [] and notifications

    manager.main_window.show_notification = lambda *_args: None
    AssistantManager._handle_voice_accessibility_command(manager, "voice_repeat_last")
    assert spoken == ["Onaylayayim mi?"]
    assert manager._pending_voice_control is pending


def test_voice_search_keeps_original_spelling():
    _app()

    class Signal:
        def __init__(self):
            self.values = []

        def emit(self, *args):
            self.values.append(args)

    fake = SimpleNamespace(
        dictation_mode=False,
        _normalize_settings=lambda value: value,
        _load_settings=lambda: {},
        _match_builtin_intent=lambda text, clean: BulutAsistan._match_builtin_intent(
            None, text, clean
        ),
        tetik_sinyali=Signal(),
    )
    BulutAsistan.komut_coz(fake, "bu ekranda ara \u00c7a\u011fr\u0131 Y\u0131lmaz")
    assert fake.tetik_sinyali.values == [
        ("voice_search_screen", "\u00c7a\u011fr\u0131 Y\u0131lmaz")
    ]


def test_wake_word_removed_without_normalizing_the_utterance():
    _app()

    class Signal:
        def __init__(self):
            self.values = []

        def emit(self, *args):
            self.values.append(args)

    fake = SimpleNamespace(
        dictation_mode=False,
        _normalize_settings=lambda value: value,
        _load_settings=lambda: {},
        _match_builtin_intent=lambda text, clean: BulutAsistan._match_builtin_intent(
            None, text, clean
        ),
        _get_wake_words=lambda: ["asistan"],
        _is_wake_only_phrase=lambda _text, _words: False,
        tetik_sinyali=Signal(),
    )
    utterance = "Asistan, M\u00fc\u015fteride \u00c7a\u011fr\u0131 ara"
    BulutAsistan.komut_coz(fake, utterance)
    assert fake.tetik_sinyali.values == [
        ("assistant_chat", "M\u00fc\u015fteride \u00c7a\u011fr\u0131 ara")
    ]


def test_local_conversation_can_navigate_then_search(monkeypatch):
    _app()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            body = {"message": {"content": json.dumps({
                "intent": "navigate_search",
                "page_id": 21,
                "query": "\u00c7a\u011fr\u0131 Y\u0131lmaz",
                "reply": "Musteriler ekraninda ariyorum.",
            })}}
            return json.dumps(body).encode("utf-8")

    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    worker = LocalAssistantConversation("musterilerde Cagri Yilmaz ara", [(21, "Musteriler")], 1)
    result = worker._resolve()
    assert result["intent"] == "navigate_search"
    assert result["page_id"] == 21
    assert result["query"] == "Cagri Yilmaz"


def test_natural_turkish_customer_service_request_routes_without_ollama():
    worker = LocalAssistantConversation(
        "Burak \u015eahin adl\u0131 m\u00fc\u015fterinin servislerini a\u00e7",
        [(42, "Servis Listesi")],
        40,
    )

    result = worker._resolve()

    assert result["intent"] == "navigate_search"
    assert result["page_id"] == 42
    assert result["query"] == "burak sahin"


def test_customer_service_search_accepts_common_spoken_turkish_variants():
    utterances = (
        "Burak \u015eahin'in servislerini a\u00e7",
        "Burak \u015eahin servislerini listele",
        "Burak \u015eahin'in servis kay\u0131tlar\u0131n\u0131 g\u00f6ster",
    )

    for utterance in utterances:
        result = LocalAssistantConversation(
            utterance, [(42, "Servis Listesi")], 42
        )._resolve()
        assert result["intent"] == "navigate_search", (utterance, result)
        assert result["page_id"] == 42
        assert result["query"] == "burak sahin"


def test_ambiguous_service_device_request_asks_for_identity():
    worker = LocalAssistantConversation(
        "Serviste bulunan cihaz\u0131 a\u00e7",
        [(42, "Servis Listesi")],
        42,
    )

    result = worker._resolve()

    assert result["intent"] == "clarify"
    assert "servis numaras" in result["reply"]


def test_spoken_menu_names_and_searches_resolve_from_catalog_without_ollama():
    pages = [(21, "M\u00fc\u015fteri Listesi"), (41, "Servis Panosu"), (42, "Servis Listesi")]
    menu = LocalAssistantConversation("Servis Listesi a\u00e7", pages, 40)._resolve()
    search = LocalAssistantConversation("M\u00fc\u015fterilerde \u00c7a\u011fr\u0131 ara", pages, 40)._resolve()

    assert menu["intent"] == "navigate" and menu["page_id"] == 42
    assert search["intent"] == "navigate_search"
    assert search["page_id"] == 21 and search["query"] == "\u00c7a\u011fr\u0131"


def test_spoken_customer_selection_uses_visible_service_row_and_advances():
    controls = [{
        "id": "c7",
        "type": "table",
        "label": "Islem yapilacak cihazi secin",
        "rows": [
            {"index": 0, "match_text": "DEMO-SRV-0015 | Burak \u015eahin | AYEC Test Cihaz 15 | Parca Bekliyor"},
            {"index": 1, "match_text": "DEMO-SRV-0014 | Derya Aydin | AYEC Test Cihaz 14 | Test Surecinde"},
        ],
    }]
    worker = LocalAssistantConversation(
        "Burak \u015eahin'i sec", [(62, "Teknisyen Paneli")], 62, controls=controls
    )

    result = worker._resolve()

    assert result["intent"] == "select_option", result
    assert result["control_id"] == "c7"
    assert "DEMO-SRV-0015" in result["value"]


def test_spoken_device_request_resolves_service_row_from_live_dialog_controls(monkeypatch):
    app = _app()

    class Db:
        def get_device_by_tracking_no(self, tracking_no):
            return {"tracking_no": tracking_no, "customer_name": "Burak \u015eahin"}

    monkeypatch.setattr(DeviceSelectionDialog, "_get_active_devices", lambda *_args: [])
    dialog = DeviceSelectionDialog(Db())
    dialog.load_data([
        {
            "tracking_no": "DEMO-SRV-0015",
            "customer_name": "Burak \u015eahin",
            "device_brand": "AYEC",
            "device_model": "Test Cihaz 15",
            "status": "Parca Bekliyor",
            "entry_date": "2026-09-21",
        },
        {
            "tracking_no": "DEMO-SRV-0014",
            "customer_name": "Derya Aydin",
            "device_brand": "AYEC",
            "device_model": "Test Cihaz 14",
            "status": "Test Surecinde",
            "entry_date": "2026-09-21",
        },
    ])
    dialog.show()
    app.processEvents()
    controls, _bindings = describe_controls(
        dialog, utterance="Burak \u015eahin'in servisindeki cihaz\u0131 a\u00e7"
    )
    worker = LocalAssistantConversation(
        "Burak \u015eahin'in servisindeki cihaz\u0131 a\u00e7",
        [(62, "Teknisyen Paneli")],
        62,
        controls=controls,
    )

    result = worker._resolve()

    assert result["intent"] == "select_option", result
    assert "DEMO-SRV-0015" in result["value"]
    dialog.close()


def test_voice_selecting_customer_in_device_picker_advances_to_selected_device(monkeypatch):
    app = _app()

    class Db:
        def get_device_by_tracking_no(self, tracking_no):
            return {"tracking_no": tracking_no, "customer_name": "Burak \u015eahin"}

    monkeypatch.setattr(DeviceSelectionDialog, "_get_active_devices", lambda *_args: [])
    dialog = DeviceSelectionDialog(Db())
    dialog.show()
    app.processEvents()
    dialog.load_data([{
        "tracking_no": "DEMO-SRV-0015",
        "customer_name": "Burak \u015eahin",
        "device_brand": "AYEC",
        "device_model": "Test Cihaz 15",
        "status": "Parca Bekliyor",
        "entry_date": "2026-09-21",
    }])

    selected, _message = dialog.select_by_voice("Burak Sahin")

    assert selected
    assert dialog.selected_device["tracking_no"] == "DEMO-SRV-0015"
    assert dialog.result() == dialog.DialogCode.Accepted
    dialog.close()


def test_voice_device_picker_asks_for_model_when_customer_has_multiple_active_devices(monkeypatch):
    app = _app()
    rows = [
        {
            "tracking_no": "DEMO-SRV-0015",
            "customer_name": "Burak \u015eahin",
            "device_brand": "AYEC",
            "device_model": "Test Cihaz 15",
            "status": "Parca Bekliyor",
            "entry_date": "2026-09-21",
        },
        {
            "tracking_no": "DEMO-SRV-0016",
            "customer_name": "Burak \u015eahin",
            "device_brand": "AYEC",
            "device_model": "Test Cihaz 16",
            "status": "Test Surecinde",
            "entry_date": "2026-09-22",
        },
    ]

    class Db:
        def get_device_by_tracking_no(self, tracking_no):
            return {"tracking_no": tracking_no}

    monkeypatch.setattr(
        DeviceSelectionDialog,
        "_get_active_devices",
        lambda _self, query="": rows if "burak" in query.lower() else [],
    )
    dialog = DeviceSelectionDialog(Db())
    dialog.show()
    app.processEvents()
    dialog.load_data(rows)

    selected, message = dialog.select_by_voice("Burak Sahin")

    assert not selected
    assert "birden fazla" in message.lower()
    assert dialog.isVisible()
    assert dialog.table.rowCount() == 2

    selected, _message = dialog.select_by_voice("Test Cihaz 15")

    assert selected
    assert dialog.selected_device["tracking_no"] == "DEMO-SRV-0015"
    dialog.close()


def test_spoken_customer_selection_ignores_turkish_case_endings():
    controls = [{
        "id": "c7",
        "type": "table",
        "label": "Islem yapilacak cihazi secin",
        "rows": [{
            "index": 0,
            "match_text": "DEMO-SRV-0015 | Burak \u015eahin | AYEC Test Cihaz 15 | Parca Bekliyor",
        }],
    }]
    worker = LocalAssistantConversation(
        "Burak \u015eahin'in servisteki cihazini ac",
        [(62, "Teknisyen Paneli")], 62, controls=controls,
    )

    result = worker._resolve()

    assert result["intent"] == "select_option"
    assert result["control_id"] == "c7"


def test_reopening_current_menu_does_not_navigate_again():
    result = LocalAssistantConversation(
        "Teknisyen Paneli ac", [(62, "Teknisyen Paneli")], 62
    )._resolve()

    assert result["intent"] == "respond"
    assert "zaten" in result["reply"]


def test_voice_selecting_device_opens_next_technician_dialog(monkeypatch):
    app = _app()
    selected_device = {"tracking_no": "DEMO-SRV-0015", "customer_name": "Burak \u015eahin"}

    class Db:
        def get_device_by_tracking_no(self, tracking_no):
            return selected_device if tracking_no == "DEMO-SRV-0015" else None

    monkeypatch.setattr(DeviceSelectionDialog, "_get_active_devices", lambda *_args: [])
    dialog = DeviceSelectionDialog(Db())
    dialog.load_data([{
        "tracking_no": "DEMO-SRV-0015",
        "customer_name": "Burak \u015eahin",
        "device_brand": "AYEC",
        "device_model": "Test Cihaz 15",
        "status": "Parca Bekliyor",
        "entry_date": "2026-09-21",
    }])
    dialog.show()
    app.processEvents()
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))
    controls, bindings = describe_controls(dialog, utterance="Burak \u015eahin sec")
    table_control = next(item for item in controls if item["type"] == "table")
    worker = SimpleNamespace(
        control_bindings=bindings,
        action_root=dialog,
        page_id=62,
    )
    manager = SimpleNamespace(
        main_window=SimpleNamespace(_current_page_index=62),
        _assistant_action_root=lambda _page_id: dialog,
    )

    reply = AssistantManager._run_voice_control(
        manager,
        "select_option",
        {
            "control_id": table_control["id"],
            "value": table_control["rows"][0]["match_text"],
        },
        worker,
    )
    app.processEvents()

    assert accepted == [True]
    assert dialog.selected_device == selected_device
    assert "teknisyen panelini" in reply
    dialog.close()


def test_selected_service_tracking_opens_technician_panel_without_picker(monkeypatch):
    device = {"tracking_no": "DEMO-SRV-0015", "customer_name": "Burak \u015eahin"}
    opened = []
    voice_thread = SimpleNamespace(followup_mode=False)

    class Db:
        def get_device_by_tracking_no(self, tracking_no):
            return device if tracking_no == device["tracking_no"] else None

    class Panel:
        def __init__(self, db, selected_device, parent, sector_manager=None):
            opened.append((db, selected_device, parent, sector_manager))

        def exec(self):
            opened.append("exec")
            opened.append(("followup_during_panel", voice_thread.followup_mode))

    monkeypatch.setattr(
        "src.ui.dialogs.technical_service_technician_panel.TechnicalServiceTechnicianPanel",
        Panel,
    )
    window = SimpleNamespace(
        db=Db(),
        sector_manager=None,
        _dialog_open=False,
        assistant=SimpleNamespace(voice_assistant_thread=voice_thread),
        _verify_technician_lock=lambda: True,
        _is_automotive=lambda: False,
    )

    MainWindowFuncMixin.open_technician_panel(window, "DEMO-SRV-0015")

    assert opened == [
        (window.db, device, window, None),
        "exec",
        ("followup_during_panel", True),
    ]
    assert window._dialog_open is False
    assert voice_thread.followup_mode is False


def test_explicit_voice_open_activates_selected_table_row():
    app = _app()
    table = QTableWidget(1, 2)
    table.setItem(0, 0, QTableWidgetItem("Burak Sahin"))
    table.setItem(0, 1, QTableWidgetItem("Servis kaydi"))
    table.show()
    app.processEvents()
    activated = []
    table.cellDoubleClicked.connect(lambda row, column: activated.append((row, column)))
    table.setCurrentCell(0, 0)
    table.selectRow(0)

    assert table_row_open_handler_available(table)
    assert activate_table_row(table)

    assert activated == [(0, 0)]
    table.close()


def test_voice_open_row_intent_requires_explicit_open_verb():
    assert AssistantManager._voice_request_opens_selected_record("Burak Sahin sec") is False
    assert AssistantManager._voice_request_opens_selected_record("Burak Sahin'in servisini ac") is True


def test_natural_language_table_request_selects_and_opens_service_row():
    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    table = QTableWidget(1, 2)
    table.setHorizontalHeaderLabels(["Musteri", "Servis Cihazi"])
    table.setItem(0, 0, QTableWidgetItem("Burak Sahin"))
    table.setItem(0, 1, QTableWidgetItem("AYEC Test Cihaz 15"))
    layout.addWidget(table)
    dialog.resize(500, 240)
    dialog.show()
    app.processEvents()
    activated = []
    table.cellDoubleClicked.connect(lambda row, column: activated.append((row, column)))

    utterance = "Burak Sahin'in servisini ac"
    controls, bindings = describe_controls(dialog, utterance=utterance)
    worker = LocalAssistantConversation(
        utterance, [], 42, controls=controls
    )
    worker.control_bindings = bindings
    worker.action_root = dialog
    worker.page_id = 42
    worker.continuation = False
    table_result = worker._resolve_table_selection_request()
    assert table_result["intent"] == "select_option", (controls, table_result)
    result = worker._resolve()
    manager = SimpleNamespace(
        main_window=SimpleNamespace(_current_page_index=42),
        _assistant_action_root=lambda _page_id: dialog,
        _remember_voice_change=lambda *_args: None,
    )

    reply = AssistantManager._run_voice_control(manager, result["intent"], result, worker)
    QTest.qWait(150)

    assert result["intent"] == "select_option", result
    assert activated == [(0, 0)]
    assert "detayini aciyorum" in reply
    dialog.close()


def test_local_conversation_falls_back_to_offline_navigation_and_form_values(monkeypatch):
    _app()
    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    navigation = LocalAssistantConversation(
        "Musteriler ekraninda musteri ekle",
        [(21, "M\u00fc\u015fteriler")],
        1,
    )._resolve()
    assert navigation["intent"] == "navigate"
    assert navigation["page_id"] == 21 and navigation["continue_action"]

    field = LocalAssistantConversation(
        "Telefon alanina +90 555 123 45 67 yaz",
        [],
        21,
        controls=[{"id": "c1", "type": "text", "label": "Telefon"}],
    )._resolve()
    assert field["intent"] == "set_field"
    assert field["value"] == "+90 555 123 45 67"

    composite_field = LocalAssistantConversation(
        "Musteri adi Burak Sahin olarak yaz",
        [],
        21,
        controls=[{
            "id": "c3", "type": "text",
            "label": "Musteri Adi / Unvani / cmb_customer / Ad Soyad giriniz",
        }],
    )._resolve()
    assert composite_field["intent"] == "set_field"
    assert composite_field["control_id"] == "c3"
    assert composite_field["value"] == "Burak Sahin"

    selection = LocalAssistantConversation(
        "Durum alaninda Hazir sec",
        [],
        21,
        controls=[{"id": "c2", "type": "combo", "label": "Durum", "options": ["Haz\u0131r", "Bekliyor"]}],
    )._resolve()
    assert selection["intent"] == "select_option"
    assert selection["value"] == "Haz\u0131r"


def test_local_assistant_prioritizes_matching_controls_beyond_first_page_limit():
    controls = [
        {"id": "c%d" % index, "type": "text", "label": "Field %d" % index}
        for index in range(120)
    ]
    controls[-1] = {"id": "c119", "type": "text", "label": "Telefon"}
    worker = LocalAssistantConversation(
        "Telefon alanina 555 yaz", [], 21, controls=controls
    )
    assert "c119" in {item["id"] for item in worker.controls}
    assert len(worker.controls) <= 80


def test_local_conversation_can_request_one_action_continuation(monkeypatch):
    _app()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return json.dumps({"message": {"content": json.dumps({
                "intent": "navigate",
                "page_id": 7,
                "continue_action": True,
                "reply": "Stok ekranina geciyorum.",
            })}}).encode("utf-8")

    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    worker = LocalAssistantConversation(
        "Stoklari ice aktar", [(7, "Stoklar")], 1
    )
    result = worker._resolve()
    assert result["intent"] == "navigate"
    assert result["continue_action"] is True


def test_post_navigation_continuation_runs_only_on_expected_page():
    starts = []
    messages = []
    manager = SimpleNamespace(
        main_window=SimpleNamespace(
            _current_page_index=7,
            show_notification=lambda *args: messages.append(args),
        ),
        _start_local_conversation=lambda utterance, continuation=False:
            starts.append((utterance, continuation)),
        _speak_async=lambda message: messages.append(message),
    )
    AssistantManager._continue_voice_request(manager, 7, "Stoklari ice aktar")
    assert starts == [("Stoklari ice aktar", True)]

    manager.main_window._current_page_index = 8
    AssistantManager._continue_voice_request(manager, 7, "Stoklari ice aktar")
    assert starts == [("Stoklari ice aktar", True)]
    assert any("Hedef ekrana gecemedim" in message for message in messages if isinstance(message, str))


def test_technician_dialog_continuation_runs_while_menu_callback_is_modal(monkeypatch):
    app = _app()
    modal = DeviceSelectionDialog(SimpleNamespace())
    monkeypatch.setattr(QApplication, "activeModalWidget", lambda: modal)
    starts = []
    manager = SimpleNamespace(
        main_window=SimpleNamespace(
            _current_page_index=42,
            show_notification=lambda *_args: None,
        ),
        _start_local_conversation=lambda utterance, continuation=False:
            starts.append((utterance, continuation)),
        _speak_async=lambda _message: None,
    )

    AssistantManager._continue_voice_request(
        manager, 62, "Teknisyen Panelini Ac, Burak Sahin'i Sec"
    )

    assert starts == [("Teknisyen Panelini Ac, Burak Sahin'i Sec", True)]
    modal.close()


def test_navigation_result_schedules_only_one_same_request_continuation(monkeypatch):
    callbacks = []
    continued = []
    events = []

    class Window:
        _current_page_index = 1

        def on_menu_click(self, page_id):
            events.append("menu")
            self._current_page_index = page_id

        def show_notification(self, *_args):
            pass

    manager = SimpleNamespace(
        main_window=Window(),
        _conversation_history=[],
        _visible_assistant_menu=lambda: [(7, "Stoklar")],
        _continue_voice_request=lambda page_id, utterance: continued.append((page_id, utterance)),
        _speak_async=lambda _message: None,
    )
    monkeypatch.setattr(
        "src.services.assistant_manager.QTimer.singleShot",
        lambda delay, callback: (events.append("scheduled"), callbacks.append((delay, callback))),
    )
    worker = SimpleNamespace(continuation=False)
    AssistantManager._apply_conversation_result(
        manager,
        {
            "intent": "navigate", "page_id": 7, "continue_action": True,
            "utterance": "Stoklari ice aktar", "reply": "Stok ekranina geciyorum.",
        },
        worker,
    )
    assert len(callbacks) == 1 and callbacks[0][0] == 700
    assert events == ["scheduled", "menu"]
    callbacks[0][1]()
    assert continued == [(7, "Stoklari ice aktar")]

    callbacks.clear()
    manager.main_window._current_page_index = 1
    worker.continuation = True
    AssistantManager._apply_conversation_result(
        manager,
        {
            "intent": "navigate", "page_id": 7, "continue_action": True,
            "utterance": "Stoklari ice aktar", "reply": "Bir baska ekrana geciyorum.",
        },
        worker,
    )
    assert callbacks == []


def test_local_conversation_validates_batch_field_ids(monkeypatch):
    _app()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return json.dumps({"message": {"content": json.dumps({
                "intent": "set_fields",
                "fields": [
                    {"control_id": "c0", "value": "Ahmet", "overwrite": False},
                    {"control_id": "c1", "value": "Telefon", "overwrite": False},
                ],
                "reply": "Iki alan dolduracagim.",
            })}}).encode("utf-8")

    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    worker = LocalAssistantConversation(
        "Ahmet musteri, telefon Telefon",
        [(21, "Musteriler")],
        21,
        controls=[
            {"id": "c0", "type": "text", "label": "Musteri"},
            {"id": "c1", "type": "text", "label": "Telefon"},
        ],
    )
    result = worker._resolve()
    assert result["intent"] == "set_fields"
    assert len(result["fields"]) == 2


def test_local_conversation_preserves_spoken_field_values_and_digits(monkeypatch):
    _app()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return json.dumps({"message": {"content": json.dumps({
                "intent": "set_fields",
                "fields": [
                    {"control_id": "c1", "value": "Wrong name", "overwrite": True},
                    {"control_id": "c2", "value": "55512:4", "overwrite": True},
                ],
            })}}).encode("utf-8")

    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    worker = LocalAssistantConversation(
        "Musteri adini Burak Sahin, Iletisim telefonunu 5551234 olarak doldur",
        [],
        40,
        controls=[
            {"id": "c1", "type": "text", "label": "Musteri Adi / Unvani", "filled": False},
            {"id": "c2", "type": "text", "label": "Iletisim Telefonu", "filled": False},
        ],
    )

    result = worker._resolve()

    assert result["intent"] == "set_fields"
    assert [(item["control_id"], item["value"]) for item in result["fields"]] == [
        ("c1", "Burak Sahin"),
        ("c2", "5551234"),
    ]
    assert all(not item["overwrite"] for item in result["fields"])


def test_offline_fallback_fills_multiple_explicit_form_fields():
    worker = LocalAssistantConversation(
        "Musteri adini Burak Sahin, Iletisim telefonunu 5551234 olarak doldur",
        [(42, "Servis Listesi")],
        42,
        controls=[
            {"id": "c1", "type": "text", "label": "Musteri Adi / Unvani"},
            {"id": "c2", "type": "text", "label": "Iletisim Telefonu"},
        ],
    )

    result = worker._resolve_offline_fallback()

    assert result["intent"] == "set_fields"
    assert [(item["control_id"], item["value"]) for item in result["fields"]] == [
        ("c1", "Burak Sahin"),
        ("c2", "5551234"),
    ]


def test_local_conversation_clarifies_instead_of_accepting_empty_field_values(monkeypatch):
    _app()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return json.dumps({"message": {"content": json.dumps({
                "intent": "set_fields",
                "fields": [
                    {"control_id": "c1", "value": "Burak Sahin"},
                    {"control_id": "c2", "value": ""},
                ],
            })}}).encode("utf-8")

    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    worker = LocalAssistantConversation(
        "Musteri adini Burak Sahin, Iletisim telefonunu doldur",
        [],
        40,
        controls=[
            {"id": "c1", "type": "text", "label": "Musteri Adi", "filled": False},
            {"id": "c2", "type": "text", "label": "Iletisim Telefonu", "filled": False},
        ],
    )

    result = worker._resolve()

    assert result["intent"] == "clarify"
    assert "tekrar" in result["reply"]


def test_local_conversation_preserves_spoken_value_for_single_field(monkeypatch):
    _app()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return json.dumps({"message": {"content": json.dumps({
                "intent": "set_field",
                "control_id": "c1",
                "value": "55512:4",
                "overwrite": True,
            })}}).encode("utf-8")

    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    worker = LocalAssistantConversation(
        "Iletisim telefonunu 5551234 olarak yaz",
        [],
        40,
        controls=[
            {"id": "c1", "type": "text", "label": "Iletisim Telefonu", "filled": False},
        ],
    )

    result = worker._resolve()

    assert result["intent"] == "set_field"
    assert result["value"] == "5551234"
    assert result["overwrite"] is False


def test_local_conversation_returns_a_bounded_clarification(monkeypatch):
    _app()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return json.dumps({"message": {"content": json.dumps({
                "intent": "clarify",
                "reply": "Hangi musteri kaydini acmam\u0131 istiyorsunuz?",
            })}}).encode("utf-8")

    monkeypatch.setattr(
        "src.services.assistant_conversation.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    worker = LocalAssistantConversation(
        "Musteri kaydini ac", [(21, "Musteriler")], 21,
        history=[("assistant", "Hangi musteri?")],
    )
    result = worker._resolve()
    assert result["intent"] == "clarify"
    assert result["reply"].endswith("?")
    assert result["utterance"] == "Musteri kaydini ac"


def test_voice_batch_fill_refuses_unconfirmed_overwrite():
    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    name = QLineEdit("Onceki ad")
    name.setObjectName("Musteri")
    phone = QLineEdit()
    phone.setObjectName("Telefon")
    customer = QComboBox()
    customer.setEditable(True)
    customer.addItem("Burak Sahin")
    customer.addItem("Ayse Yilmaz")
    customer.setCurrentIndex(1)
    layout.addWidget(name)
    layout.addWidget(phone)
    layout.addWidget(customer)
    dialog.show()
    app.processEvents()
    worker = SimpleNamespace(
        page_id=21,
        action_root=dialog,
        control_bindings={"c0": name, "c1": phone, "c2": customer},
    )
    manager = SimpleNamespace(
        main_window=SimpleNamespace(_current_page_index=21),
        _assistant_action_root=lambda _page: dialog,
        _pending_voice_control=None,
        _last_voice_change=None,
        _dictation_mode=False,
        voice_assistant_thread=None,
    )
    manager._remember_voice_batch_change = lambda *args: AssistantManager._remember_voice_batch_change(manager, *args)
    manager._voice_form_batch_recap = lambda *args: AssistantManager._voice_form_batch_recap(manager, *args)
    manager._form_required_followup = lambda *args: ""
    result = {
        "fields": [
            {"control_id": "c0", "value": "Yeni ad", "overwrite": False},
            {"control_id": "c1", "value": "5551234", "overwrite": False},
            {"control_id": "c2", "value": "Burak Sahin", "overwrite": False, "operation": "select_option"},
        ]
    }
    reply = AssistantManager._run_voice_control_batch(manager, result, worker)
    assert "Dolu alan" in reply and name.text() == "Onceki ad" and not phone.text()
    assert customer.currentText() == "Ayse Yilmaz"
    result["fields"][0]["overwrite"] = True
    reply = AssistantManager._run_voice_control_batch(manager, result, worker)
    assert manager._pending_voice_control["batch"]
    assert "Yeni ad" in reply and name.text() == "Onceki ad"
    manager.main_window.show_notification = lambda *_args: None
    manager._speak_async = lambda *_args: None
    AssistantManager._confirm_voice_control(manager, True)
    assert name.text() == "Yeni ad" and phone.text() == "5551234"
    assert customer.currentText() == "Burak Sahin"
    manager._undo_last_voice_change = lambda: AssistantManager._undo_last_voice_change(manager)
    ok, _message = manager._undo_last_voice_change()
    assert ok and name.text() == "Onceki ad" and not phone.text()
    assert customer.currentText() == "Ayse Yilmaz"
    dialog.close()


def test_voice_controls_cover_forms_tables_and_critical_confirmation():
    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    field = QLineEdit()
    combo = QComboBox()
    combo.addItems(["Servis", "Stok"])
    checkbox = QCheckBox("Etkin")
    active_checkbox = QCheckBox("Aktif")
    radio = QRadioButton("Standart")
    radio_advanced = QRadioButton("Gelistirilmis")
    table = QTableWidget(2, 2)
    table.setHorizontalHeaderLabels(["Musteri", "Durum"])
    table.setItem(0, 0, QTableWidgetItem("Ayse"))
    table.setItem(0, 1, QTableWidgetItem("Bekliyor"))
    table.setItem(1, 0, QTableWidgetItem("Mehmet"))
    table.setItem(1, 1, QTableWidgetItem("Hazir"))
    save = QPushButton("Kaydet")
    unknown_action = QPushButton("Verileri isle")
    filter_action = QPushButton("Kayitlari filtrele")
    date = QDateEdit()
    time = QTimeEdit()
    datetime = QDateTimeEdit()
    spin = QSpinBox()
    spin.setRange(0, 10)
    decimal_spin = QDoubleSpinBox()
    decimal_spin.setRange(0.0, 10.0)
    slider = QSlider()
    slider.setRange(0, 10)
    search = QLineEdit()
    search.setPlaceholderText("Musteri ara")
    invalid = QLineEdit()
    invalid.setObjectName("Telefon")
    invalid.setValidator(QIntValidator(0, 9999, invalid))
    invalid.setText("abc")
    for widget in (field, combo, checkbox, active_checkbox, radio, radio_advanced, table, date, time, datetime, spin, decimal_spin, slider, search, invalid, save, unknown_action, filter_action):
        layout.addWidget(widget)
    dialog.show()
    app.processEvents()

    controls, bindings = describe_controls(dialog)
    kinds = {control["type"] for control in controls}
    assert {"text", "combo", "check", "table", "button"} <= kinds
    assert apply_control(combo, "select", "Stok")[0]
    assert apply_control(checkbox, "toggle", True)[0]
    assert action_needs_confirmation(save) and action_needs_confirmation(checkbox)
    assert action_needs_confirmation(active_checkbox)
    assert "radio" in kinds
    radio.setChecked(True)
    radio_before = snapshot_control(radio_advanced)
    assert apply_control(radio_advanced, "toggle", True)[0]
    assert radio_advanced.isChecked() and not radio.isChecked()
    assert restore_control(radio_advanced, radio_before)[0] and radio.isChecked()
    assert not apply_control(radio, "toggle", False)[0]
    assert action_needs_confirmation(unknown_action)
    assert not action_needs_confirmation(filter_action)
    click_ok, click_message = apply_control(filter_action, "click")
    assert click_ok and "\u011frulayam\u0131yorum" in click_message
    price_label = QLabel("Satis Fiyati")
    price_field = QLineEdit()
    price_label.setBuddy(price_field)
    layout.addWidget(price_label)
    layout.addWidget(price_field)
    assert action_needs_confirmation(price_field, dialog)
    assert apply_control(date, "set", "2026-10-11")[0]
    assert apply_control(time, "set", "14:35")[0]
    assert apply_control(datetime, "set", "2026-10-11 14:35")[0]
    assert apply_control(spin, "set", "7")[0] and spin.value() == 7
    assert apply_control(decimal_spin, "set", "4.5")[0] and decimal_spin.value() == 4.5
    assert apply_control(slider, "set", "8")[0] and slider.value() == 8
    assert not apply_control(spin, "set", "11")[0] and spin.value() == 7
    assert date.date().toString("yyyy-MM-dd") == "2026-10-11"
    assert time.time().toString("HH:mm") == "14:35"
    field.setText("\u00c7a\u011fr\u0131")
    field.setObjectName("Musteri")
    field.setFocus()
    summary = confirmation_summary(dialog, save, "click")
    assert "\u00c7a\u011fr\u0131" in summary
    secret = QLineEdit()
    secret.setEchoMode(QLineEdit.EchoMode.Password)
    secret.setText("secret123")
    layout.addWidget(secret)
    app.processEvents()
    password_confirmation = confirmation_summary(dialog, secret, "set", "secret123")
    assert "secret123" not in password_confirmation
    protected = confirmation_summary(dialog, save, "click")
    assert "secret123" not in protected and "parola alani" in protected
    field.setText("eski deger")
    assert not apply_control(field, "set", "\u00c7a\u011fr\u0131")[0]
    field.clear()
    field.setFocus()
    assert append_dictation(dialog, "\u00c7a\u011fr\u0131")[0]
    assert field.text() == "\u00c7a\u011fr\u0131"
    field.setText("Merhaba dunya")
    field.setCursorPosition(len(field.text()))
    assert apply_control(field, "delete_word")[0]
    assert field.text() == "Merhaba "
    assert move_focus(dialog, True)[0]
    table_id = next(item["id"] for item in controls if item["type"] == "table")
    assert apply_control(bindings[table_id], "select", "Ayse")[0]
    assert "Ayse" in read_active_field(dialog)
    assert move_item_selection(dialog, True)[0]
    assert "Mehmet" in read_active_field(dialog)
    assert "Kaydet" in read_screen(dialog)
    assert search_screen(dialog, "Ayse")[0] and search.text() == "Ayse"
    assert "dogrulamadan gecmedi" in read_form_feedback(dialog)
    invalid.clear()
    assert not apply_control(invalid, "set", "12345")[0]
    assert invalid.text() == ""
    dialog.close()


def test_form_controls_infer_unlinked_labels_and_include_spoken_combo_option():
    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    customer_label = QLabel("Musteri Adi / Unvani")
    customer = QComboBox()
    customer.setEditable(True)
    customer.addItems(["Musteri %d" % index for index in range(55)])
    customer.addItem("Burak \u015eahin")
    phone_label = QLabel("Iletisim Telefonu")
    phone = QLineEdit()
    layout.addWidget(customer_label)
    layout.addWidget(customer)
    layout.addWidget(phone_label)
    layout.addWidget(phone)
    dialog.show()
    app.processEvents()

    controls, bindings = describe_controls(
        dialog, utterance="Musteri adi Burak \u015eahin telefon 5551234"
    )
    customer_control = next(item for item in controls if item["type"] == "combo")
    phone_control = next(item for item in controls if item["type"] == "text")
    assert "Musteri Adi / Unvani" in customer_control["label"]
    assert "Burak \u015eahin" in customer_control["options"]
    assert "Iletisim Telefonu" in phone_control["label"]
    assert bindings[customer_control["id"]] is customer
    dialog.close()


def test_form_opening_asks_consent_then_starts_voice_intake():
    app = _app()
    dialog = QDialog()
    dialog.setModal(True)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("Musteri Adi *"))
    customer = QLineEdit()
    layout.addWidget(customer)
    layout.addWidget(QLabel("Telefon *"))
    phone = QLineEdit()
    layout.addWidget(phone)
    dialog.show()
    app.processEvents()
    messages = []
    manager = SimpleNamespace(
        main_window=SimpleNamespace(
            _current_page_index=21,
            show_notification=lambda message, _kind: messages.append(message),
        ),
        _conversation_history=[],
        _pending_form_intake=None,
        _speak_async=messages.append,
        _log_soft_failure=lambda *_args: None,
    )
    manager._form_required_followup = lambda form_root: AssistantManager._form_required_followup(manager, form_root)
    manager._form_missing_required = lambda form_root: AssistantManager._form_missing_required(manager, form_root)

    assert AssistantManager._offer_form_assistance(manager, 21)
    assert manager._pending_form_intake["status"] == "awaiting_consent"
    assert any("doldural" in message.casefold() for message in messages)
    assert AssistantManager._resolve_form_assistance_confirmation(manager, True)
    assert manager._pending_form_intake["status"] == "active"
    assert any("m\u00fc\u015fteri ad\u0131" in message.casefold() for message in messages)
    assert any("Musteri Adi" in message for message in messages)
    customer.setText("Burak Sahin")
    assert "Telefon" in AssistantManager._form_required_followup(manager, dialog)
    dialog.close()


def test_voice_form_reset_waits_for_confirmation_and_can_be_undone():
    app = _app()
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    name = QLineEdit("Burak Sahin")
    phone = QLineEdit("5551234")
    status = QComboBox()
    status.addItems(["Bekliyor", "Hazir"])
    status.setCurrentIndex(1)
    layout.addWidget(name)
    layout.addWidget(phone)
    layout.addWidget(status)
    dialog.show()
    app.processEvents()
    manager = SimpleNamespace(
        main_window=SimpleNamespace(_current_page_index=21, show_notification=lambda *_args: None),
        _pending_voice_control=None,
        _pending_form_intake=None,
        _last_voice_change=None,
        _assistant_action_root=lambda _page: dialog,
        _speak_async=lambda *_args: None,
    )
    manager._remember_voice_batch_change = lambda *args: AssistantManager._remember_voice_batch_change(manager, *args)
    manager._voice_form_batch_recap = lambda *args: AssistantManager._voice_form_batch_recap(manager, *args)
    manager._form_required_followup = lambda *_args: ""

    ok, prompt = AssistantManager._stage_form_reset(manager, dialog)
    assert ok and "Onaylamak" in prompt and name.text() == "Burak Sahin"
    AssistantManager._confirm_voice_control(manager, True)
    assert not name.text() and not phone.text()
    assert status.currentText() == "Bekliyor"
    manager._undo_last_voice_change = lambda: AssistantManager._undo_last_voice_change(manager)
    ok, _message = manager._undo_last_voice_change()
    assert ok and name.text() == "Burak Sahin" and phone.text() == "5551234"
    assert status.currentText() == "Hazir"
    dialog.close()
