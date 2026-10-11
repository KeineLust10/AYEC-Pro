# -*- coding: utf-8 -*-

import json
import ctypes
import inspect
import logging
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
try:
    import logging
    _diag_logger = logging.getLogger("ModernDesktopApp")
    _diag_logger.info("Asistan Motoru: Kütüphaneler yükleniyor...")
except Exception:
    pass

import time
try:
    import speech_recognition as sr
    _diag_logger.info("Asistan Motoru: speech_recognition yüklendi.")
except Exception as e:
    _diag_logger.error(f"Asistan Motoru: speech_recognition yükleme hatası: {e}")
    raise
from PyQt6.QtCore import QThread, pyqtSignal, QObject, pyqtSlot, QUrl
from PyQt6.QtWidgets import QApplication

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
except Exception:
    QMediaPlayer = None
    QAudioOutput = None

from src.utils.path_helper import PathHelper

logger = logging.getLogger("AYEC_TTS")
MIN_COMMAND_CONFIDENCE = 0.35
MAX_COMMAND_PHRASE_SECONDS = 15
_qt_player_bridge = None
_tts_lock = threading.Lock()
_tts_generation_lock = threading.Lock()
_tts_generation = 0
_tts_playback_active = False
_tts_mic_cooldown_until = 0.0
_active_tts_process = None


def _tts_generation_is_current(generation):
    if generation is None:
        return True
    with _tts_generation_lock:
        return generation == _tts_generation


def _tts_capture_snapshot():
    """Return speech generation and playback state for microphone echo filtering."""
    with _tts_generation_lock:
        suppress_capture = _tts_playback_active or time.monotonic() < _tts_mic_cooldown_until
        return _tts_generation, suppress_capture


def _discard_microphone_chunk(source):
    """Drain buffered speaker echo while assistant playback suppresses capture."""
    stream = getattr(source, "stream", None)
    read = getattr(stream, "read", None)
    chunk_size = int(getattr(source, "CHUNK", 0) or 0)
    if not callable(read) or chunk_size <= 0:
        return False
    audio_stream = getattr(stream, "pyaudio_stream", stream)
    get_read_available = getattr(audio_stream, "get_read_available", None)
    if callable(get_read_available):
        drained = False
        for _ in range(64):
            try:
                available = max(0, int(get_read_available()))
                if available == 0:
                    break
                read(min(chunk_size, available))
                drained = True
            except Exception:
                break
        return drained
    try:
        read(chunk_size)
        return True
    except Exception:
        return False


def _configure_microphone_recognizer(recognizer):
    """Tune phrase detection for conversational speech while keeping VAD adaptive."""
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_ratio = 1.2
    recognizer.pause_threshold = 0.85
    recognizer.phrase_threshold = 0.2
    recognizer.non_speaking_duration = 0.35


def _listen_for_microphone_phrase(recognizer, source):
    return recognizer.listen(source, timeout=2, phrase_time_limit=MAX_COMMAND_PHRASE_SECONDS)


def stop_tts_playback():
    """Cancel pending synthesis and stop the active local audio playback."""
    global _tts_generation, _tts_playback_active, _tts_mic_cooldown_until, _active_tts_process
    with _tts_generation_lock:
        _tts_generation += 1
        _tts_playback_active = False
        _tts_mic_cooldown_until = time.monotonic() + 0.65
    process = _active_tts_process
    if process is not None and process.poll() is None:
        try:
            process.terminate()
        except Exception:
            pass
    if os.name == "nt":
        try:
            mci = ctypes.windll.winmm.mciSendStringW
            mci("stop tts_audio", None, 0, None)
            mci("close tts_audio", None, 0, None)
        except Exception:
            pass
    try:
        bridge = _qt_player_bridge
        if bridge is not None:
            bridge.stop_requested.emit()
    except Exception:
        pass
    return True


def _normalize_tr_text(text):
    text = str(text or "").strip().lower()
    replacements = str.maketrans({
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    })
    return re.sub(r"\s+", " ", text.translate(replacements)).strip()


def _wake_word_variants(name):
    base = _normalize_tr_text(name)
    if not base:
        return []

    variants = [base]
    if base == "ayec":
        variants.extend(["ayek", "ayec pro", "ayek pro"])
    elif base.endswith(" pro"):
        short = base[:-4].strip()
        if short:
            variants.append(short)
            if short == "ayec":
                variants.extend(["ayek", "ayek pro"])

    seen = []
    for item in variants:
        if item and item not in seen:
            seen.append(item)
    return seen


def _parse_turkish_percentage(text):
    text = str(text or "").strip().lower()
    if not text:
        return None

    digit_match = re.search(r"(%\s*\d+|\d+\s*%)", text)
    if digit_match:
        digits = re.search(r"\d+", digit_match.group(1))
        if digits:
            value = int(digits.group(0))
            return value if 0 < value <= 100 else None

    plain_digit_match = re.search(r"(\d{1,3})", text)
    if plain_digit_match:
        value = int(plain_digit_match.group(1))
        if 0 < value <= 100:
            return value

    units = {
        "bir": 1, "iki": 2, "uc": 3, "üç": 3, "dort": 4, "dört": 4, "bes": 5, "beş": 5,
        "alti": 6, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9,
    }
    tens = {
        "on": 10, "yirmi": 20, "otuz": 30, "kirk": 40, "kırk": 40, "elli": 50,
        "altmis": 60, "altmış": 60, "yetmis": 70, "yetmiş": 70, "seksen": 80, "doksan": 90,
    }

    tokens = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+", text)
    if "yuzde" in tokens or "yüzde" in tokens:
        total = 0
        seen = False
        for token in tokens:
            if token in {"yuzde", "yüzde"}:
                continue
            if token in tens:
                total += tens[token]
                seen = True
                continue
            if token in units:
                total += units[token]
                seen = True
                continue
            if seen:
                break
        if seen and 0 < total <= 100:
            return total

    return None


def _extract_customer_360_target(text):
    raw = _normalize_tr_text(text)
    if not raw:
        return ""
    for phrase in [
        "musteri 360 ac",
        "musteri 360",
        "musteri cari hesap",
        "musteri detaylarini ac",
    ]:
        raw = raw.replace(phrase, " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw.title()


def _extract_intent_target(text, phrases):
    raw = _normalize_tr_text(text)
    for phrase in phrases:
        raw = raw.replace(phrase, " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw.title()


class _QtTTSPlayerBridge(QObject):
    play_requested = pyqtSignal(str)
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.audio = None
        self.player = None
        self.current_path = None

        if QMediaPlayer is not None and QAudioOutput is not None:
            self.audio = QAudioOutput(self)
            self.audio.setVolume(1.0)
            self.player = QMediaPlayer(self)
            self.player.setAudioOutput(self.audio)
            self.player.mediaStatusChanged.connect(self._on_media_status)
            self.player.errorOccurred.connect(self._on_error)

        self.play_requested.connect(self.play_file)
        self.stop_requested.connect(self._finalize_current)

    @pyqtSlot(str)
    def play_file(self, filepath):
        if not self.player or not os.path.exists(filepath):
            _cleanup(filepath)
            return

        try:
            if self.current_path and self.current_path != filepath:
                _cleanup(self.current_path)
            self.current_path = filepath
            self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(filepath))
            self.player.play()
            logger.info("[TTS] Qt in-process player started")
        except Exception as e:
            logger.error("[TTS] Qt in-process player exception: %s", e)
            _cleanup(filepath)

    def _finalize_current(self):
        try:
            if self.player:
                self.player.stop()
        except Exception:
            pass
        if self.current_path:
            _cleanup(self.current_path)
            self.current_path = None

    def _on_media_status(self, status):
        if QMediaPlayer is None:
            return
        logger.debug("[TTS] Qt in-process player status changed: %s (Duration: %d ms)", status, self.player.duration())
        if status in {
            QMediaPlayer.MediaStatus.EndOfMedia,
            QMediaPlayer.MediaStatus.InvalidMedia,
            QMediaPlayer.MediaStatus.NoMedia,
        }:
            if status == QMediaPlayer.MediaStatus.InvalidMedia:
                logger.error("[TTS] Qt in-process player: Invalid Media error!")
            self._finalize_current()

    def _on_error(self, error, error_string):
        logger.error("[TTS] Qt in-process player error (%s): %s", error, error_string)
        self._finalize_current()


def _get_qt_player_bridge():
    global _qt_player_bridge
    app = QApplication.instance()
    if app is None or QMediaPlayer is None or QAudioOutput is None:
        return None
    if _qt_player_bridge is None:
        _qt_player_bridge = _QtTTSPlayerBridge()
        _qt_player_bridge.moveToThread(app.thread())
    return _qt_player_bridge


def _subprocess_window_kwargs():
    """Windows'ta yardımcı medya süreçlerini konsolsuz çalıştır."""
    if os.name != "nt":
        return {}

    kwargs = {}
    try:
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    except Exception:
        pass

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
    except Exception:
        pass

    return kwargs
def _cleanup(filepath):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


def _play_mp3(filepath, generation=None):
    """MP3 dosyasını ayrı bir süreçte veya in-process oynatır."""
    if not os.path.exists(filepath):
        logger.warning("[TTS] Dosya bulunamadı: %s", filepath)
        return False
    if not _tts_generation_is_current(generation):
        _cleanup(filepath)
        return False

    # Windows üzerinde öncelikle kararlı olan MCI (Windows native) oynatmayı dene
    if os.name == "nt":
        try:
            logger.info("[TTS] Windows: MCI playback (Windows native) başlatılıyor: %s", filepath)
            import ctypes
            mci = ctypes.windll.winmm.mciSendStringW
            
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.kernel32.GetShortPathNameW(filepath, buf, 512)
            short_path = buf.value if buf.value else filepath
            
            mci('close tts_audio', None, 0, None)
            res = mci(f'open "{short_path}" alias tts_audio', None, 0, None)
            if res == 0:
                play_res = mci('play tts_audio wait', None, 0, None)
                mci('close tts_audio', None, 0, None)
                if not _tts_generation_is_current(generation):
                    _cleanup(filepath)
                    return False
                if play_res == 0:
                    logger.info("[TTS] MCI playback completed")
                    _cleanup(filepath)
                    return True
                logger.error("[TTS] MCI play error code: %s", play_res)
            else:
                logger.error("[TTS] MCI open hatası kodu: %s", res)
        except Exception as e:
            logger.error("[TTS] MCI playback exception: %s", e)

    if not _tts_generation_is_current(generation):
        _cleanup(filepath)
        return False

    # Dondurulmuş (EXE) modda MCI başarısız olduysa Qt Multimedia Bridge dene
    if getattr(sys, "frozen", False):
        if not _tts_generation_is_current(generation):
            _cleanup(filepath)
            return False
        try:
            logger.info("[TTS] Frozen mod: Qt in-process bridge deneniyor...")
            bridge = _get_qt_player_bridge()
            if bridge and bridge.player:
                bridge.play_requested.emit(filepath)
                return True
        except Exception as e:
            logger.error("[TTS] Frozen mod Qt bridge hatası: %s", e)
        _cleanup(filepath)
        return False

    try:
        pythonw = sys.executable
        if os.name == "nt":
            candidate = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if os.path.exists(candidate):
                pythonw = candidate

        player_script = (
            "import sys\n"
            "from PyQt6.QtCore import QUrl, QEventLoop, QTimer\n"
            "from PyQt6.QtWidgets import QApplication\n"
            "from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput\n"
            "app = QApplication.instance() or QApplication([])\n"
            "audio = QAudioOutput()\n"
            "player = QMediaPlayer()\n"
            "player.setAudioOutput(audio)\n"
            "loop = QEventLoop()\n"
            "audio.setVolume(1.0)\n"
            "timed_out = {'v': False}\n"
            "def finish(*args):\n"
            "    if loop.isRunning():\n"
            "        loop.quit()\n"
            "player.mediaStatusChanged.connect(lambda status: finish() if status == QMediaPlayer.MediaStatus.EndOfMedia else None)\n"
            "player.errorOccurred.connect(lambda *args: finish())\n"
            "timer = QTimer()\n"
            "timer.setSingleShot(True)\n"
            "timer.timeout.connect(lambda: (timed_out.__setitem__('v', True), finish()))\n"
            "timer.start(30000)\n"
            "player.setSource(QUrl.fromLocalFile(sys.argv[1]))\n"
            "player.play()\n"
            "loop.exec()\n"
            "player.stop()\n"
            "sys.exit(0 if not timed_out['v'] else 1)\n"
        )

        global _active_tts_process
        process = subprocess.Popen(
            [pythonw, "-c", player_script, filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **_subprocess_window_kwargs(),
        )
        _active_tts_process = process
        deadline = time.monotonic() + 35.0
        while process.poll() is None:
            if not _tts_generation_is_current(generation) or time.monotonic() >= deadline:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except Exception:
                    process.kill()
                    process.wait()
                break
            time.sleep(0.05)
        stdout, stderr = process.communicate()
        if _active_tts_process is process:
            _active_tts_process = None
        if not _tts_generation_is_current(generation):
            _cleanup(filepath)
            return False
        result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
        if result.returncode == 0:
            logger.info("[TTS] Qt Multimedia subprocess OK")
            _cleanup(filepath)
            return True
        logger.error("[TTS] Qt Multimedia subprocess hatası: %s", (result.stderr or "").strip())
    except Exception as e:
        logger.error("[TTS] Qt Multimedia subprocess exception: %s", e)

    bridge = _get_qt_player_bridge()
    if bridge is not None:
        try:
            bridge.play_requested.emit(filepath)
            logger.info("[TTS] Qt in-process bridge fallback started")
            return True
        except Exception as e:
            logger.error("[TTS] Qt in-process bridge emit failed: %s", e)

    _cleanup(filepath)
    return False


def sesli_cevap(metin):
    """Basit sesli yanıt."""
    sesli_cevap_ver_async(metin, engine_type="auto")


class BulutAsistan(QThread):
    tetik_sinyali = pyqtSignal(str, str)
    hata_sinyali = pyqtSignal(str)
    hazir_sinyali = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ayarlar_yolu = os.path.join(PathHelper.get_app_data_dir(), "asistan_ayarlari.json")
        self.varsayilan_ayarlar_olustur()
        self.is_running = True
        self.last_wake_word = ""
        self.last_wake_time = 0.0
        self.wake_timeout_seconds = 10.0
        self.followup_mode = False
        self._ready_notified = False

    def varsayilan_ayarlar_olustur(self):
        if os.path.exists(self.ayarlar_yolu):
            return

        baslangic_ayarlar = {
            "stok_sorgu": ["stoklar", "eksik stok", "stok durumu"],
            "servis_ac": ["yeni servis", "kayıt oluştur", "servis aç"],
            "excel_islem": ["excel aç", "öğrenci bul", "rapor al"],
            "panel_ac": ["teknisyen paneli", "panel aç", "teknisyen"],
        }
        with open(self.ayarlar_yolu, "w", encoding="utf-8") as f:
            json.dump(baslangic_ayarlar, f, ensure_ascii=False, indent=4)

    def _load_settings(self):
        if not os.path.exists(self.ayarlar_yolu):
            self.varsayilan_ayarlar_olustur()

        path = self.ayarlar_yolu
        if not os.path.exists(path):
            legacy = os.path.join(os.getcwd(), "asistan_ayarlari.json")
            if os.path.exists(legacy):
                path = legacy

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_wake_words(self):
        wake_words = list(_wake_word_variants("asistan"))
        try:
            db_path = PathHelper.get_db_path("ayecpro.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM settings WHERE key='asistan_ozel_adi' LIMIT 1")
                    row = cur.fetchone()
                    if row and row[0]:
                        custom_name = str(row[0]).strip().lower()
                        wake_words.extend(_wake_word_variants(custom_name))
                finally:
                    conn.close()
        except Exception as e:
            logger.debug("Wake word lookup fallback used: %s", e)

        # Tekrarlı kayıtları temizle
        unique_words = []
        for word in wake_words:
            if word and word not in unique_words:
                unique_words.append(word)
        return unique_words

    def _is_wake_only_phrase(self, text, wake_words):
        cleaned = _normalize_tr_text(re.sub(r"[^\wçğıöşü\s]", " ", str(text or "").lower()))
        if cleaned in wake_words:
            return True
        for prefix in ("hey ", "merhaba ", "selam "):
            if cleaned.startswith(prefix) and cleaned[len(prefix):].strip() in wake_words:
                return True
        return False

    def _wake_is_recent(self):
        return bool(getattr(self, "followup_mode", False)) or (
            time.time() - self.last_wake_time
        ) <= self.wake_timeout_seconds

    def _match_builtin_intent(self, normalized_text, text_without_wake):
        text = _normalize_tr_text(text_without_wake or normalized_text or "")
        if not text:
            return None

        accessibility_commands = (
            (("son soyledigimi geri al", "son girdigimi geri al"), "voice_undo"),
            (("forma devam et", "formdaki eksikleri soyle", "hangi alanlar kaldi"), "voice_form_status"),
            (("formu bastan al", "formu sifirla", "formu temizle"), "voice_form_reset"),
            (("ekrani oku", "bu ekrani oku", "sayfayi oku"), "voice_read_screen"),
            (("form hatalarini oku", "dogrulama hatalarini oku", "formu kontrol et"), "voice_read_form_feedback"),
            (("aktif alani oku", "bu alani oku", "secili alani oku"), "voice_read_field"),
            (("sonraki alan", "sonraki alana gec", "ileri alan"), "voice_focus_next"),
            (("onceki alan", "onceki alana gec", "geri alan"), "voice_focus_previous"),
            (("dikte modunu ac", "dikteye basla", "yazmaya basla"), "voice_dictation_on"),
            (("dikteyi bitir", "dikte modunu kapat", "yazmayi bitir"), "voice_dictation_off"),
            (("alani temizle", "bu alani sil", "kutuyu temizle"), "voice_clear_field"),
            (("son kelimeyi sil", "bir onceki kelimeyi sil", "son sozcugu sil"), "voice_delete_word"),
            (("imleci basa al", "alanin basina git"), "voice_cursor_start"),
            (("imleci sona al", "alanin sonuna git"), "voice_cursor_end"),
            (("virgul koy", "virgul ekle"), "voice_insert_comma"),
            (("nokta koy", "nokta ekle"), "voice_insert_period"),
            (("yeni satir", "alt satira gec"), "voice_insert_newline"),
            (("asagi kaydir", "ekrani asagi indir"), "voice_scroll_down"),
            (("yukari kaydir", "ekrani yukari cikar"), "voice_scroll_up"),
            (("sonraki kayit", "sonraki satir", "listede ileri git"), "voice_next_record"),
            (("onceki kayit", "onceki satir", "listede geri git"), "voice_previous_record"),
            (("secili kaydi ac", "bu kaydi ac", "secili satiri ac"), "voice_open_record"),
            (("geri don", "onceki sayfaya don", "bir onceki ekrana don"), "voice_navigate_back"),
            (("son degisikligi geri al", "son yaptigimi geri al", "degisikligi geri al"), "voice_undo"),
            (("bekleyen islemi iptal et", "onay istegini iptal et", "sunu iptal et"), "voice_cancel_pending"),
            (("yanitini tekrar et", "son soyledigini tekrar et", "tekrar soyle"), "voice_repeat_last"),
            (("sonraki komutlar", "diger komutlari oku", "yetenege devam et"), "voice_help_next"),
            (("konusmayi durdur", "sesi durdur", "asistan sus", "sesli yaniti kes"), "voice_stop_speech"),
        )
        for phrases, intent in accessibility_commands:
            if any(phrase in text for phrase in phrases):
                return (intent, "")

        named_clear = re.search(r"(.+?)\s+alanini\s+temizle\b", text)
        if named_clear:
            return ("voice_clear_named_field", named_clear.group(1).strip())

        for prefix in ("bu ekranda ara ", "sayfada ara ", "ekranda ara ", "burada ara "):
            if text.startswith(prefix):
                return ("voice_search_screen", text[len(prefix):].strip())

        if text in {"teklif olustur", "yeni teklif", "teklif ekranini ac", "teklif olusturma ekranini ac"}:
            return ("open_page", "150")

        if "stok" in text and any(term in text for term in ("ocr", "resimden aktar", "faturayi tara", "goruntuden aktar")):
            return ("voice_open_stock_ocr", "")

        if any(phrase in text for phrase in ["gelismis finansal ozet", "nakit akis ozeti", "vade ozetini soyle"]):
            return ("financial_summary", "")

        if any(phrase in text for phrase in ["finans ozet", "finansal ozet", "mali ozet", "kasa ozeti"]):
            return ("accounting_summary", "")

        if text in {
            "evet",
            "evet tamam",
            "onayla",
            "onayliyorum",
            "evet onayliyorum",
            "evet devam et",
            "onay veriyorum",
            "uygula",
            "tamam",
            "yap",
            "yapabilirsin",
            "devam et",
        }:
            return ("confirm_yes", "")

        if text in {
            "hayir", "iptal", "vazgec", "uygulama", "uygulama istemiyorum",
            "hayir onaylamiyorum", "onaylamiyorum", "vazgeciyorum",
        }:
            return ("confirm_no", "")

        if "kritik stok" in text or "eksik stok" in text:
            return ("list_critical_stock", "")

        if any(phrase in text for phrase in ["bugunku randevular", "randevularimi soyle", "bugun randevum var mi", "randevulari ac"]):
            return ("check_appointments", "")

        if any(phrase in text for phrase in ["stok ozeti", "envanter ozeti", "stok durum ozeti"]):
            return ("stock_summary", "")

        if any(phrase in text for phrase in ["yonetici ozeti", "bugun ne oldu", "gunluk yonetici ozeti"]):
            return ("managerial_summary", "")

        if any(phrase in text for phrase in ["borclu musterileri soyle", "musteri borc durumunu soyle", "kimlerin borcu var"]):
            return ("customer_debt_summary", "")

        if any(phrase in text for phrase in ["servis is yukunu soyle", "kac cihaz bekliyor", "servis durum ozeti"]):
            return ("service_workload_summary", "")

        if any(phrase in text for phrase in ["simdi senkronize et", "senkronizasyon yap", "verileri sunucuyla esitle"]):
            return ("sync_now", "")

        if any(phrase in text for phrase in ["neler yapabilirsin", "hangi komutlari biliyorsun", "bana nasil yardim edebilirsin"]):
            return ("assistant_help", "")

        if any(phrase in text for phrase in ["borc ozeti", "kredi borc ozeti", "borc durumunu soyle"]):
            return ("loan_summary", "")

        if any(phrase in text for phrase in ["cek senet ozeti", "cek senet portfoyu", "cek senetleri ac"]):
            return ("check_summary", "")

        if any(phrase in text for phrase in ["yeni servis ac", "servis kaydi olustur", "servis formunu ac"]):
            return ("servis_ac", "")

        if any(phrase in text for phrase in ["cihaz durumu sorgula", "cihaz durumu", "servis durumu sorgula"]):
            return ("device_status_query", _extract_intent_target(
                text, ["cihaz durumu sorgula", "cihaz durumu", "servis durumu sorgula"]
            ))

        if any(phrase in text for phrase in ["stok karsilastirma yap", "stok karsilastirma", "hangi stok daha fazla"]):
            return ("stock_comparison", _extract_intent_target(
                text, ["stok karsilastirma yap", "stok karsilastirma", "hangi stok daha fazla"]
            ))

        if any(phrase in text for phrase in ["gun kapanis ozeti", "gunu kapat", "aksam ozetini ver"]):
            return ("closing_routine", "")

        if "musteri 360" in text or "musteri cari hesap" in text:
            return ("customer_360", _extract_customer_360_target(text))

        if "indirim tavsiyesi" in text or "indirim onerisi" in text:
            target = text
            for phrase in ("icin indirim tavsiyesi ver", "indirim tavsiyesi ver", "indirim tavsiyesi", "icin indirim onerisi ver", "indirim onerisi ver", "indirim onerisi"):
                target = target.replace(phrase, " ")
            return ("discount_advice", re.sub(r"\s+", " ", target).strip().title())

        note_match = re.search(r"(?:toplanti\s+)?notu\s+al\s+(.+)$", text)
        if note_match:
            return ("add_quick_note_voice", note_match.group(1).strip())

        reminder_match = re.search(r"(.+?)\s+(?:icin\s+)?(?:odeme\s+)?hatirlatici\s+(?:ekle|olustur)$", text)
        if reminder_match:
            return ("add_reminder_voice", reminder_match.group(1).strip())

        select_match = re.search(r"^(.+?)\s+(?:adli\s+)?(?:musteriyi\s+)?sec(?:\s+ve\s+ilerle)?$", text)
        if select_match:
            target = re.sub(r"['\u2019](?:yi|i|yu|u)$", "", select_match.group(1)).strip()
            target = re.sub(r"^(?:(?:teknisyen\s+)?paneli|panel)\s+acildiktan\s+sonra\s+", "", target)
            if target and target not in {"teknisyen paneli", "servis paneli"}:
                return ("select_service_device", target.title())

        if BulutAsistan._is_technician_panel_open_request(text):
            return ("panel_ac", "")

        if "zam" in text and "stok" in text:
            yuzde = _parse_turkish_percentage(text)
            if yuzde:
                return ("apply_zam", f"Stoklara %{yuzde} {text}")
            return ("apply_zam", "")

        return None

    @staticmethod
    def _is_technician_panel_open_request(text):
        """Match only a standalone request to open the technician panel."""
        normalized = _normalize_tr_text(text)
        words = normalized.split()
        while words and words[0] in {"hey", "merhaba", "selam", "asistan", "lutfen"}:
            words.pop(0)
        while words and words[-1] in {"lutfen", "rica", "ederim"}:
            words.pop()
        phrase = " ".join(words)
        return phrase in {
            "teknisyen panelini ac",
            "teknisyen paneli ac",
            "teknisyen panelini goster",
            "teknisyen paneli goster",
            "panel ac",
            "paneli ac",
            "teknisyen paneli",
            "teknisyen",
        }

    def _normalize_settings(self, raw):
        if not isinstance(raw, dict):
            return {}

        normalized = {}
        for key, value in raw.items():
            if isinstance(value, list):
                normalized[key] = {
                    "triggers": [_normalize_tr_text(v) for v in value if str(v).strip()],
                    "action": key,
                }
                continue

            if not isinstance(value, dict):
                continue

            triggers = value.get("triggers")
            if triggers is None:
                triggers = value.get("tetikleyiciler")
            if triggers is None:
                triggers = value.get("kelimeler")

            if isinstance(triggers, str):
                triggers = [t.strip() for t in triggers.replace(";", ",").split(",") if t.strip()]
            elif not isinstance(triggers, list):
                triggers = []

            action = value.get("action")
            if isinstance(action, dict):
                if action.get("type") == "builtin":
                    action_name = action.get("name") or key
                elif action.get("type") == "page":
                    action_name = "open_page"
                else:
                    action_name = key
            elif isinstance(action, str):
                action_name = action
            else:
                action_name = key

            normalized[key] = {
                "triggers": [_normalize_tr_text(v) for v in triggers if str(v).strip()],
                "action": action_name,
                "action_payload": action if isinstance(action, dict) else None,
            }

        return normalized

    @staticmethod
    def _find_configured_trigger(settings, text):
        matches = []
        for _, config in settings.items():
            for trigger in config.get("triggers", []):
                if not trigger:
                    continue
                start = text.find(trigger)
                if start < 0:
                    continue
                end = start + len(trigger)
                left_boundary = start == 0 or not (text[start - 1].isalnum() or text[start - 1] == "_")
                right_boundary = end == len(text) or not (text[end].isalnum() or text[end] == "_")
                if left_boundary and right_boundary:
                    matches.append((len(trigger), config, trigger))
        if not matches:
            return None
        best_length = max(item[0] for item in matches)
        best = [item for item in matches if item[0] == best_length]
        actions = {
            (str(item[1].get("action") or ""), repr(item[1].get("action_payload")))
            for item in best
        }
        if len(actions) > 1:
            return (None, None)
        return (best[0][1], best[0][2])

    def stop(self):
        self.is_running = False
        self.requestInterruption()

    def _pause(self, seconds):
        deadline = time.time() + seconds
        while self.is_running and time.time() < deadline:
            QThread.msleep(100)

    def run(self):
        recognizer = sr.Recognizer()
        _configure_microphone_recognizer(recognizer)
        mic_error_notified = False
        try:
            from src.utils.offline_turkish_asr import OfflineTurkishASR

            offline_asr = OfflineTurkishASR()
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                message = (
                    "\u00c7evrim d\u0131\u015f\u0131 T\u00fcrk\u00e7e konu\u015fma modeli bulunamad\u0131. "
                    "tools/setup/prepare_offline_asr.py arac\u0131n\u0131 \u00e7al\u0131\u015ft\u0131r\u0131n."
                )
            elif isinstance(e, ImportError):
                message = (
                    "Ses tan\u0131ma bile\u015fenleri uygulama paketinde eksik. "
                    "Program\u0131n ses bile\u015fenlerini g\u00fcncelleyin."
                )
            else:
                message = f"Ses tan\u0131ma motoru ba\u015flat\u0131lamad\u0131: {e}"
            logger.error("Offline Turkish ASR could not start: %s", e)
            self.hata_sinyali.emit(message)
            return

        quiet_timeouts = 0
        while self.is_running:
            try:
                with sr.Microphone() as source:
                    mic_error_notified = False
                    try:
                        recognizer.adjust_for_ambient_noise(source, duration=1)
                        logger.info(
                            "Voice input ready: device=%s sample_rate=%s energy_threshold=%.1f",
                            source.device_index,
                            source.SAMPLE_RATE,
                            recognizer.energy_threshold,
                        )
                        if not self._ready_notified:
                            self._ready_notified = True
                            self.hazir_sinyali.emit()
                    except Exception as e:
                        logger.error("Mikrofon ayarı yapılamadı: %s", e)
                        self._pause(2)
                        continue

                    for _ in range(100):
                        if not self.is_running:
                            break
                        try:
                            capture_generation, playback_active = _tts_capture_snapshot()
                            if playback_active:
                                _discard_microphone_chunk(source)
                                self._pause(0.15)
                                continue
                            audio = _listen_for_microphone_phrase(recognizer, source)
                            quiet_timeouts = 0
                            if not self.is_running:
                                break
                            current_generation, playback_active = _tts_capture_snapshot()
                            if playback_active or current_generation != capture_generation:
                                logger.debug("Ignored microphone audio overlapping assistant speech")
                                continue
                            audio_duration = len(audio.frame_data) / max(
                                1, audio.sample_rate * audio.sample_width
                            )
                            logger.info(
                                "Voice phrase captured: device=%s duration=%.2fs",
                                source.device_index,
                                audio_duration,
                            )
                            recognition = offline_asr.transcribe_with_confidence(audio)
                            if not self.is_running:
                                break
                            metin = str(recognition.get("text") or "").lower().strip()
                            confidence = float(recognition.get("confidence", 0.0))
                            logger.info("Voice recognition result: text=%r confidence=%.3f", metin, confidence)
                            if metin and confidence < MIN_COMMAND_CONFIDENCE:
                                logger.info("Low-confidence speech was not executed")
                                self.tetik_sinyali.emit("assistant_unclear", metin)
                            elif metin:
                                self.komut_coz(metin)
                        except sr.WaitTimeoutError:
                            quiet_timeouts += 1
                            if quiet_timeouts % 15 == 0:
                                logger.info(
                                    "Microphone is open with no detected phrase: device=%s energy_threshold=%.1f",
                                    source.device_index,
                                    recognizer.energy_threshold,
                                )
                            continue
                        except sr.UnknownValueError:
                            continue
                        except Exception as e:
                            logger.error("Dinleme hatası: %s", e)
            except AttributeError:
                msg = "PyAudio / mikrofon surucusu bulunamadi. Sesli asistan dinleme modu baslatilamadi."
                logger.warning(msg)
                if not mic_error_notified:
                    self.hata_sinyali.emit(msg)
                    mic_error_notified = True
                return
            except OSError as e:
                msg = f"Mikrofon bulunamadi veya erisim izni yok: {e}"
                logger.error(msg)
                if not mic_error_notified:
                    self.hata_sinyali.emit(msg)
                    mic_error_notified = True
                return
            except Exception as e:
                err = str(e)
                if "PyAudio" in err or "Could not find PyAudio" in err or "No Default Input Device" in err:
                    msg = "PyAudio eksik veya ses giris cihazi bulunamadi. Sesli asistan icin mikrofon gereklidir."
                    logger.warning(msg)
                    if not mic_error_notified:
                        self.hata_sinyali.emit(msg)
                        mic_error_notified = True
                    return
                msg = f"Genel Asistan Hatası: {e}"
                logger.error(msg)
                self.hata_sinyali.emit(msg)
                self._pause(2)

    def komut_coz(self, metin):
        try:
            ayarlar = self._normalize_settings(self._load_settings())
            original_text = str(metin or "").strip()
            normalized_text = _normalize_tr_text(metin)
            if not normalized_text:
                return

            if getattr(self, "dictation_mode", False):
                voice_intent = self._match_builtin_intent(normalized_text, normalized_text)
                if voice_intent and voice_intent[0].startswith("voice_"):
                    parametre = voice_intent[1]
                    if voice_intent[0] == "voice_search_screen":
                        match = re.match(
                            r"(?i)^(?:bu ekranda ara|sayfada ara|ekranda ara|burada ara)\s+",
                            original_text,
                        )
                        if match:
                            parametre = original_text[match.end():].strip()
                    self.tetik_sinyali.emit(voice_intent[0], parametre)
                else:
                    self.tetik_sinyali.emit("assistant_chat", str(metin or "").strip())
                return

            immediate_intent = self._match_builtin_intent(normalized_text, normalized_text)
            if immediate_intent and immediate_intent[0] in {"confirm_yes", "confirm_no"}:
                self.tetik_sinyali.emit(immediate_intent[0], immediate_intent[1])
                self.last_wake_time = 0.0
                self.last_wake_word = ""
                return

            # Built-in navigation commands are intentionally accepted without a
            # separate wake word. This keeps short commands such as "finans
            # ozeti" usable when speech recognition drops the wake word.
            direct_intent = self._match_builtin_intent(normalized_text, normalized_text)
            if direct_intent:
                parametre = direct_intent[1]
                if direct_intent[0] == "voice_search_screen":
                    match = re.match(
                        r"(?i)^(?:bu ekranda ara|sayfada ara|ekranda ara|burada ara)\s+",
                        original_text,
                    )
                    if match:
                        parametre = original_text[match.end():].strip()
                self.tetik_sinyali.emit(direct_intent[0], parametre)
                self.last_wake_time = time.time() if direct_intent[0] == "panel_ac" else 0.0
                self.last_wake_word = ""
                return

            # Exact user-configured commands should work without a wake word.
            # Previously these were checked only after the wake-word gate, so
            # ordinary commands such as "yeni servis ac" were silently dropped.
            configured_match = BulutAsistan._find_configured_trigger(ayarlar, normalized_text)
            if configured_match:
                cfg, matched_trigger = configured_match
                if cfg is None:
                    self.tetik_sinyali.emit("assistant_unclear", original_text)
                    return
                action = cfg.get("action")
                payload = cfg.get("action_payload")
                if action == "panel_ac" and not self._is_technician_panel_open_request(normalized_text):
                    self.tetik_sinyali.emit("assistant_chat", original_text)
                    return
                if isinstance(payload, dict) and payload.get("type") == "page":
                    page_index = payload.get("index", "")
                    remaining = normalized_text.replace(matched_trigger, "").strip()
                    if payload.get("auto_search") and remaining:
                        self.tetik_sinyali.emit("open_page_search", f"{page_index}|{remaining}")
                    else:
                        self.tetik_sinyali.emit("open_page", str(page_index))
                else:
                    self.tetik_sinyali.emit(str(action or ""), "")
                self.last_wake_time = time.time() if action == "panel_ac" else 0.0
                self.last_wake_word = ""
                return

            configured_trigger = any(
                trigger and trigger in normalized_text
                for config in ayarlar.values()
                for trigger in config.get("triggers", [])
            )
            if not configured_trigger and any(
                token in normalized_text.split()
                for token in ("ac", "acabilir", "goster", "getir", "git")
            ):
                self.tetik_sinyali.emit("assistant_chat", original_text)
                self.last_wake_time = 0.0
                self.last_wake_word = ""
                return

            wake_words = self._get_wake_words()
            matched_wake = next(
                (
                    word
                    for word in sorted(wake_words, key=len, reverse=True)
                    if word and re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", normalized_text)
                ),
                None,
            )
            if matched_wake:
                self.last_wake_word = matched_wake
                self.last_wake_time = time.time()
                if self._is_wake_only_phrase(normalized_text, wake_words):
                    logger.info("Uyanma kelimesi algılandı: %s", matched_wake)
                    self.tetik_sinyali.emit("wake_ack", "")
                    return
            elif not self._wake_is_recent():
                # Resolve exact visible menu/control names without waking the
                # conversational model. Unknown ambient speech stays inert.
                self.tetik_sinyali.emit("assistant_named_target", original_text)
                return

            text_without_wake = normalized_text.replace(matched_wake, "").strip() if matched_wake else normalized_text
            raw_without_wake = original_text
            if matched_wake:
                raw_without_wake = re.sub(
                    r"(?i)(?<!\w)" + re.escape(matched_wake) + r"(?!\w)",
                    "",
                    raw_without_wake,
                    count=1,
                ).strip()
                raw_without_wake = re.sub(r"^[\s,;:.-]+|[\s,;:.-]+$", "", raw_without_wake)

            builtin_intent = self._match_builtin_intent(normalized_text, text_without_wake)
            if builtin_intent:
                parametre = builtin_intent[1]
                if builtin_intent[0] == "voice_search_screen":
                    match = re.match(
                        r"(?i)^(?:bu ekranda ara|sayfada ara|ekranda ara|burada ara)\s+",
                        raw_without_wake,
                    )
                    if match:
                        parametre = raw_without_wake[match.end():].strip()
                self.tetik_sinyali.emit(builtin_intent[0], parametre)
                self.last_wake_time = 0.0
                self.last_wake_word = ""
                return

            configured_match = BulutAsistan._find_configured_trigger(ayarlar, normalized_text)
            if configured_match:
                cfg, matched_trigger = configured_match
                if cfg is None:
                    self.tetik_sinyali.emit("assistant_unclear", raw_without_wake)
                    return
                action = cfg.get("action")
                payload = cfg.get("action_payload")
                remaining = text_without_wake.replace(matched_trigger, "").strip()
                if isinstance(payload, dict) and payload.get("type") == "page":
                    page_index = payload.get("index")
                    if payload.get("auto_search") and remaining:
                        self.tetik_sinyali.emit("open_page_search", f"{page_index}|{remaining}")
                    else:
                        self.tetik_sinyali.emit("open_page", str(page_index))
                else:
                    self.tetik_sinyali.emit(str(action or ""), remaining.title())
                self.last_wake_time = 0.0
                self.last_wake_word = ""
                return
            self.tetik_sinyali.emit("assistant_chat", raw_without_wake)
            self.last_wake_time = 0.0
            self.last_wake_word = ""
        except Exception as e:
            logger.error("Komut çözme hatası: %s", e)


def sesli_cevap_ver_async(metin, engine_type="auto", voice=None, rate=None, pitch=None, efekt_aktif=False):
    """Generate Turkish speech with the isolated local EMA voice model."""
    del efekt_aktif
    if not metin:
        return
    global _tts_generation, _tts_playback_active
    stop_tts_playback()
    with _tts_generation_lock:
        _tts_generation += 1
        generation = _tts_generation
        _tts_playback_active = True
    engine_choice = str(engine_type or "ema-lightning").strip().lower()
    legacy_choices = {"auto", "system", "edge", "premium"}
    if engine_choice not in legacy_choices | {"freya", "local", "qwen", "ema", "ema-lightning"}:
        logger.warning("[TTS] Unknown engine '%s'; using local EMA Turkish TTS", engine_choice)

    def _run_tts():
        global _tts_mic_cooldown_until
        with _tts_lock:
            if not _tts_generation_is_current(generation):
                return
            temp_path = os.path.join(
                tempfile.gettempdir(),
                f"ayec_ema_{threading.current_thread().ident}.wav",
            )
            try:
                from src.utils.local_turkish_tts import synthesize_to_file

                logger.info("[TTS] Local EMA Turkish speech synthesis started")
                synthesize_to_file(metin, temp_path, voice=voice)
                if not _tts_generation_is_current(generation):
                    return
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
                    try:
                        accepts_generation = len(inspect.signature(_play_mp3).parameters) > 1
                    except (TypeError, ValueError):
                        accepts_generation = True
                    played = (
                        _play_mp3(temp_path, generation)
                        if accepts_generation
                        else _play_mp3(temp_path)
                    )
                    if played:
                        logger.info("[TTS] Local EMA Turkish speech completed")
                        return
                logger.error("[TTS] Local Turkish speech file could not be played")
            except Exception as exc:
                logger.exception("[TTS] EMA Turkish speech failed; no system voice fallback is enabled: %s", exc)
            finally:
                _cleanup(temp_path)
                with _tts_generation_lock:
                    if generation == _tts_generation:
                        _tts_playback_active = False
                        _tts_mic_cooldown_until = time.monotonic() + 0.65

    threading.Thread(target=_run_tts, daemon=True).start()
