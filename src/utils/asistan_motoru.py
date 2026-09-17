# -*- coding: utf-8 -*-

import json
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
import pyttsx3
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
_qt_player_bridge = None
_tts_lock = threading.Lock()


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


def _play_mp3(filepath):
    """MP3 dosyasını ayrı bir süreçte veya in-process oynatır."""
    if not os.path.exists(filepath):
        logger.warning("[TTS] Dosya bulunamadı: %s", filepath)
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
                if play_res == 0:
                    logger.info("[TTS] MCI playback completed")
                    _cleanup(filepath)
                    return True
                logger.error("[TTS] MCI play error code: %s", play_res)
            else:
                logger.error("[TTS] MCI open hatası kodu: %s", res)
        except Exception as e:
            logger.error("[TTS] MCI playback exception: %s", e)

    # Dondurulmuş (EXE) modda MCI başarısız olduysa Qt Multimedia Bridge dene
    if getattr(sys, "frozen", False):
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

        result = subprocess.run(
            [pythonw, "-c", player_script, filepath],
            capture_output=True,
            text=True,
            timeout=35,
            **_subprocess_window_kwargs(),
        )
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


def _select_turkish_pyttsx3_voice(engine):
    """pyttsx3 motorunda Türkçe sesi bulup ayarlar."""
    voices = engine.getProperty("voices")
    if not voices:
        return False

    tr_keywords = [
        "turkish",
        "türkçe",
        "turkce",
        "türkçe",
        "tr-tr",
        "tr_tr",
        "tolga",
        "yelda",
        "hakan",
        "filiz",
        "emel",
        "microsoft server speech text to speech voice (tr-tr",
    ]

    for voice in voices:
        v_name = voice.name.lower()
        v_id = voice.id.lower()
        if any(key in v_name or key in v_id for key in tr_keywords):
            engine.setProperty("voice", voice.id)
            return True

    if os.name == "nt":
        for voice in voices:
            if "tr" in voice.id.lower():
                engine.setProperty("voice", voice.id)
                return True

    for voice in voices:
        for lang in getattr(voice, "languages", []):
            if "tr" in str(lang).lower():
                engine.setProperty("voice", voice.id)
                return True

    return False


def sesli_cevap(metin):
    """Basit sesli yanıt."""
    sesli_cevap_ver_async(metin, engine_type="auto")


class BulutAsistan(QThread):
    tetik_sinyali = pyqtSignal(str, str)
    hata_sinyali = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.ayarlar_yolu = os.path.join(PathHelper.get_app_data_dir(), "asistan_ayarlari.json")
        self.varsayilan_ayarlar_olustur()
        self.is_running = True
        self.last_wake_word = ""
        self.last_wake_time = 0.0
        self.wake_timeout_seconds = 10.0

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
        return (time.time() - self.last_wake_time) <= self.wake_timeout_seconds

    def _match_builtin_intent(self, normalized_text, text_without_wake):
        text = _normalize_tr_text(text_without_wake or normalized_text or "")
        if not text:
            return None

        if any(phrase in text for phrase in ["gelismis finansal ozet", "nakit akis ozeti", "vade ozetini soyle"]):
            return ("financial_summary", "")

        if any(phrase in text for phrase in ["finans ozet", "finansal ozet", "mali ozet", "kasa ozeti"]):
            return ("accounting_summary", "")

        if text in {
            "evet",
            "evet tamam",
            "onayla",
            "onayliyorum",
            "uygula",
            "tamam",
            "yap",
            "yapabilirsin",
            "devam et",
        }:
            return ("confirm_yes", "")

        if text in {"hayir", "hayır", "iptal", "vazgec", "vazgeç", "uygulama", "uygulama istemiyorum"}:
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

        if "teknisyen paneli" in text or text == "panel ac":
            return ("panel_ac", "")

        if "zam" in text and "stok" in text:
            yuzde = _parse_turkish_percentage(text)
            if yuzde:
                return ("apply_zam", f"Stoklara %{yuzde}")
            return ("apply_zam", text.title())

        return None

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

    def stop(self):
        self.is_running = False
        if self.isRunning() and not self.wait(3000):
            logger.warning("Voice assistant listener did not stop within timeout; terminating thread.")
            self.terminate()
            self.wait(1000)

    def _pause(self, seconds):
        deadline = time.time() + seconds
        while self.is_running and time.time() < deadline:
            QThread.msleep(100)

    def run(self):
        recognizer = sr.Recognizer()
        request_error_notified = False
        mic_error_notified = False
        while self.is_running:
            try:
                with sr.Microphone() as source:
                    mic_error_notified = False
                    try:
                        recognizer.adjust_for_ambient_noise(source, duration=1)
                        logger.info("Asistan aktif: dinliyor...")
                    except Exception as e:
                        logger.error("Mikrofon ayarı yapılamadı: %s", e)
                        self._pause(2)
                        continue

                    for _ in range(100):
                        if not self.is_running:
                            break
                        try:
                            audio = recognizer.listen(source, timeout=2, phrase_time_limit=5)
                            metin = recognizer.recognize_google(audio, language="tr-TR").lower()
                            logger.info("Duyuldu: %s", metin)
                            self.komut_coz(metin)
                        except sr.WaitTimeoutError:
                            continue
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError as e:
                            logger.error("Google API Hatası: %s", e)
                            if not request_error_notified:
                                self.hata_sinyali.emit("Ses tanima servisine ulasilamadi. Internet baglantisini kontrol edin.")
                                request_error_notified = True
                            self._pause(5)
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
            normalized_text = _normalize_tr_text(metin)
            if not normalized_text:
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
                self.tetik_sinyali.emit(direct_intent[0], direct_intent[1])
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
                return

            text_without_wake = normalized_text.replace(matched_wake, "").strip() if matched_wake else normalized_text

            builtin_intent = self._match_builtin_intent(normalized_text, text_without_wake)
            if builtin_intent:
                self.tetik_sinyali.emit(builtin_intent[0], builtin_intent[1])
                self.last_wake_time = 0.0
                self.last_wake_word = ""
                return

            for _, cfg in ayarlar.items():
                aksiyon = cfg.get("action")
                payload = cfg.get("action_payload")
                triggers = sorted(cfg.get("triggers", []), key=lambda item: len(str(item or "")), reverse=True)
                matched_trigger = None

                for kelime in triggers:
                    pattern = r"(?<!\w)" + re.escape(kelime) + r"(?!\w)"
                    if re.search(pattern, normalized_text, flags=re.IGNORECASE):
                        matched_trigger = kelime
                        break

                if not matched_trigger:
                    for kelime in triggers:
                        if kelime in normalized_text:
                            matched_trigger = kelime
                            break

                if matched_trigger:
                    kalan = text_without_wake.replace(matched_trigger, "").strip()
                    if isinstance(payload, dict) and payload.get("type") == "page":
                        try:
                            page_index = payload.get("index")
                            auto_search = bool(payload.get("auto_search"))
                            if auto_search and kalan:
                                self.tetik_sinyali.emit("open_page_search", f"{page_index}|{kalan}")
                            else:
                                self.tetik_sinyali.emit("open_page", str(page_index))
                        except Exception:
                            self.tetik_sinyali.emit("open_page", str(payload.get("index", "")))
                    else:
                        self.tetik_sinyali.emit(str(aksiyon or ""), kalan.title())
                    self.last_wake_time = 0.0
                    self.last_wake_word = ""
                    return
        except Exception as e:
            logger.error("Komut çözme hatası: %s", e)


def sesli_cevap_ver_async(metin, engine_type="auto", voice=None, rate=None, pitch=None, efekt_aktif=False):
    """
    Generate speech with Premium/Edge TTS only.

    The ``efekt_aktif`` argument is retained for backward compatibility.
    """
    del efekt_aktif

    if not metin:
        return
    engine_choice = str(engine_type or "auto").strip().lower()

    def _try_edge_tts():
        """Edge TTS ile Türkçe sentez ve oynatma."""
        try:
            import asyncio
            import edge_tts
            import re as _re

            logger.info("[TTS] Edge TTS başlatılıyor... metin=%s...", metin[:50])

            edge_voice = "tr-TR-AhmetNeural"
            if voice and "Neural" in str(voice) and str(voice).startswith("tr-"):
                edge_voice = str(voice)

            edge_rate = str(rate).strip() if rate else "+0%"
            if not _re.match(r"^[+-]\d+%$", edge_rate):
                edge_rate = "+0%"

            edge_pitch = str(pitch).strip() if pitch else "-5Hz"
            if not _re.match(r"^[+-]\d+Hz$", edge_pitch):
                edge_pitch = "-5Hz"

            logger.info("[TTS] Edge params: voice=%s, rate=%s, pitch=%s", edge_voice, edge_rate, edge_pitch)

            temp_path = os.path.join(tempfile.gettempdir(), f"ayec_tts_{threading.current_thread().ident}.mp3")
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

            async def _synthesize():
                comm = edge_tts.Communicate(metin, edge_voice, rate=edge_rate, pitch=edge_pitch)
                await comm.save(temp_path)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_synthesize())
            finally:
                loop.close()

            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
                logger.info("[TTS] Edge TTS MP3 oluşturuldu: %s bytes", os.path.getsize(temp_path))
                return _play_mp3(temp_path)

            logger.warning("[TTS] Edge TTS: dosya oluşturulamadı")
            _cleanup(temp_path)
            return False
        except ImportError as e:
            logger.error("[TTS] edge_tts import hatası: %s", e)
            return False
        except Exception as e:
            logger.exception("[TTS] Edge TTS hatası: %s", e)
            return False

    def _try_system_tts():
        """Speak through the local operating-system voice."""
        com_initialized = False
        engine = None
        try:
            if os.name == "nt":
                try:
                    import pythoncom

                    pythoncom.CoInitialize()
                    com_initialized = True
                except Exception as exc:
                    logger.debug("[TTS] COM initialization fallback: %s", exc)

            engine = pyttsx3.init()
            _select_turkish_pyttsx3_voice(engine)
            current_rate = int(engine.getProperty("rate") or 180)
            rate_match = re.match(r"^([+-])(\d+)%$", str(rate or "+0%").strip())
            if rate_match:
                percentage = int(rate_match.group(2))
                if rate_match.group(1) == "-":
                    percentage *= -1
                current_rate = max(80, min(320, int(current_rate * (1 + percentage / 100))))
            engine.setProperty("rate", current_rate)
            engine.setProperty("volume", 1.0)
            engine.say(str(metin))
            engine.runAndWait()
            engine.stop()
            logger.info("[TTS] System voice speech completed")
            return True
        except Exception as exc:
            logger.exception("[TTS] System voice error: %s", exc)
            return False
        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
            if com_initialized:
                try:
                    import pythoncom

                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    def _run_tts():
        with _tts_lock:
            logger.info("[TTS] Speech started with engine=%s", engine_choice)
            if engine_choice == "system":
                _try_system_tts()
                return
            if engine_choice in {"auto", "edge", "premium"} and _try_edge_tts():
                logger.info("[TTS] Premium/Edge speech completed")
                return
            logger.warning("[TTS] Edge speech unavailable; using system voice fallback")
            _try_system_tts()

    threading.Thread(target=_run_tts, daemon=True).start()
