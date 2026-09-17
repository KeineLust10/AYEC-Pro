# -*- coding: utf-8 -*-

import logging
import sys
import io
import json
import re
try:
    from google import genai
    HAS_GEMINI_LIB = True
except Exception:
    HAS_GEMINI_LIB = False
    genai = None

# Safe stdout encoding fix
try:
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        current_encoding = getattr(sys.stdout, 'encoding', None)
        if current_encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    pass  # Silently ignore any stdout issues in frozen mode

logger = logging.getLogger(__name__)


DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
RECOMMENDED_GEMINI_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
)
RETIRED_GEMINI_MODELS = {
    "gemini-1.0-pro": DEFAULT_GEMINI_MODEL,
    "gemini-1.5-flash": DEFAULT_GEMINI_MODEL,
    "gemini-1.5-pro": "gemini-3.5-flash",
    "gemini-2.0-flash": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-lite": "gemini-3.5-flash-lite",
}


def normalize_gemini_model(model_name):
    raw_name = str(model_name or "").strip().split(" ")[0]
    if raw_name.startswith("models/"):
        raw_name = raw_name[7:]
    if not raw_name:
        return DEFAULT_GEMINI_MODEL
    return RETIRED_GEMINI_MODELS.get(raw_name, raw_name)


class AIService:
    def __init__(self, db_or_keys=None, model_name=None):
        self.api_keys = [""]
        self.current_key_index = 0
        self.model_id = normalize_gemini_model(model_name)
        self.client = None
        self.is_configured = False
        self.db = None

        # DB veya List destegi (Backward Compatibility)
        if hasattr(db_or_keys, 'get_setting'):
            self.db = db_or_keys
            key_str = self.db.get_setting("gemini_api_key", "")
            if key_str:
                self.api_keys = [k.strip() for k in key_str.replace(',', '\n').split('\n') if k.strip()]
            saved_model = (self.db.get_setting("gemini_model", "") or "").strip()
            if saved_model:
                self.model_id = normalize_gemini_model(saved_model)
        elif isinstance(db_or_keys, list) and db_or_keys:
            self.api_keys = db_or_keys

        self._setup_client()

    def _setup_client(self):
        try:
            if not self.api_keys:
                self.is_configured = False
                return False

            if self.current_key_index >= len(self.api_keys):
                self.current_key_index = 0

            current_key = str(self.api_keys[self.current_key_index]).strip()
            if '\n' in current_key:
                current_key = current_key.split('\n')[0].strip()
            if ',' in current_key:
                current_key = current_key.split(',')[0].strip()

            if not current_key:
                self.is_configured = False
                return False

            if not HAS_GEMINI_LIB:
                logger.warning("Google GenAI kutuphanesi eksik.")
                return False

            if hasattr(genai, 'Client'):
                self.client = genai.Client(api_key=current_key)
            else:
                logger.error("google-genai 'Client' bulunamadi. Lutfen 'pip install google-genai' yapin.")
                return False

            self.is_configured = True
            logger.info(f"[OK] Jarvis anahtar {self.current_key_index + 1} ile baglandi.")
            return True
        except Exception as e:
            logger.error(f"Baglanti hatasi: {e}")
            self.is_configured = False
            return False

    def generate_response(self, prompt, _retry_count=0):
        """Asenkron calismaya uygun ana metod"""
        if not self.client:
            if not self._setup_client():
                return "Sistem hazir degil. (API Anahtari Yok)"

        try:
            if hasattr(self.client, 'models'):
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                return response.text
            else:
                return "Model yuklenemedi veya SDK surumu uyumsuz."
        except Exception as e:
            error_str = str(e)
            # Kota asimi (429) durumunda bir kez anahtar degistir - sonsuz donguden kacinmak icin max 1 retry
            if "429" in error_str and len(self.api_keys) > 1 and _retry_count < 1:
                logger.warning("429 Kota hatasi - Anahtar degistiriliyor...")
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                if self._setup_client():
                    return self.generate_response(prompt, _retry_count=_retry_count + 1)

            return f"Jarvis: Su an yanit veremiyorum. (Hata: {error_str[:50]}...)"

    def get_urgent_report(self):
        """Kritik durumlari (stok vb) kontrol eder ve raporlar."""
        if not self.db:
            return None
        try:
            stats = self.db.get_sectoral_widget_data("teknik_servis")
            critical_count = stats.get("critical_stock", 0)
            if critical_count > 0:
                prompt = f"Teknik serviste {critical_count} adet urunun stoku kritik seviyenin altina dustu. Bu durumu belirten kisa ve ciddi bir uyari cumlesi olustur."
                return self.generate_response(prompt)
        except Exception as e:
            logger.error(f"Urgent report error: {e}")
        return None

    def generate_specialized_report(self, shift_type="morning"):
        """Sabah/Aksam raporu olusturur."""
        if not self.db:
            return "Veritabani baglantisi yok."
        try:
            stats = self.db.get_summary_data()
            sectoral = self.db.get_sectoral_widget_data("teknik_servis")

            context = (
                f"Sektor: Teknik Servis. "
                f"Bekleyen Isler: {stats.get('pending_jobs', 0)}. "
                f"Bugunku Yeni Kayitlar: {sectoral.get('new_entries_today', 0)}. "
                f"Bugün Teslim Edilenler: {sectoral.get('delivered_today', 0)}. "
            )

            if shift_type == "morning":
                prompt = f"Gune baslarken teknik servis yoneticisi icin kisa bir motivasyonel ozet raporu olustur. Veriler: {context}"
            else:
                prompt = f"Gunun sonunda teknik servis yoneticisi icin kisa bir kapanis ozeti raporu olustur. Veriler: {context}"

            return self.generate_response(prompt)
        except Exception as e:
            logger.error(f"Specialized report error: {e}")
            return "Rapor olusturulurken bir hata olustu."

    def get_available_models(self):
        """Online model arama fonksiyonu"""
        try:
            if not self.client:
                self._setup_client()

            if hasattr(self.client, 'models'):
                models = self.client.models.list()
                valid_models = []
                for m in models:
                    name = normalize_gemini_model(getattr(m, "name", ""))
                    actions = (
                        getattr(m, "supported_actions", None)
                        or getattr(m, "supported_generation_methods", None)
                        or []
                    )
                    if actions and "generateContent" not in actions:
                        continue
                    if name and name not in valid_models:
                        valid_models.append(name)
                ordered = [
                    name for name in RECOMMENDED_GEMINI_MODELS
                    if name in valid_models
                ]
                ordered.extend(name for name in valid_models if name not in ordered)
                return ordered or list(RECOMMENDED_GEMINI_MODELS)
            else:
                return list(RECOMMENDED_GEMINI_MODELS)
        except Exception as e:
            logger.error(f"Model listeleme hatasi: {e}")
            return list(RECOMMENDED_GEMINI_MODELS)

    def send_whatsapp(self, message):
        """WhatsApp mesaji gonderir using the configured delivery mode."""
        if not message:
            return
        phone = ""
        if self.db:
            phone = (
                self.db.get_setting("whatsapp_admin_phone", "")
                or self.db.get_setting("admin_whatsapp", "")
                or ""
            )
        try:
            from src.services.whatsapp_service import WhatsAppService

            return WhatsAppService(self.db).send(phone, message)
        except Exception as error:
            logger.warning("WhatsApp message could not be prepared: %s", error)
            return {"ok": False, "error": str(error)}

    def generate_customer_insight(self, history_summary):
        """Musteri gecmisine dayanarak kisa bir bilgi notu olusturur."""
        prompt = (
            "Sen bir musteri iliskileri uzmanissin. Asagida bir musterinin servis gecmisi ozeti var. "
            "Teknisyen icin 1-2 cumlelik kisa ve faydali bir 'Istihbarat Notu' olustur. "
            "Ornegin: 'Bu musteri genelde ekran kirigi sikayetiyle geliyor, odemelerini duzenli yapiyor.' gibi.\n\n"
            f"Gecmis Ozeti: {history_summary}"
        )
        return self.generate_response(prompt)

    def refine_technical_note(self, raw_text):
        """Ham metni profesyonel teknik servis notuna donusturur."""
        prompt = (
            "Sen uzman bir teknik servis asistanisin. Asagidaki ham metni, bir teknik servis formuna "
            "uygun olacak sekilde, profesyonel, net ve dil bilgisi kurallarina uygun olarak yeniden yaz. "
            "Sadece sonucu ver, yorum yapma.\n\n"
            f"Ham Metin: {raw_text}"
        )
        return self.generate_response(prompt)

    def get_smart_response(self, question):
        """Gelismis veri analizi destekli yanit uretme."""
        if not self.is_configured:
            return {
                'success': True,
                'answer': "Jarvis icin henuz gecerli bir API anahtari girilmemis. Lutfen Ayarlar > Jarvis menuunden ayar yapin.",
                'error': None
            }

        try:
            schema_info = """
            VERITABANI SEMASI:
            - customers: id, name, phone, email, type, tax_id, address
            - devices: id, tracking_no, customer_name, device_brand, device_model, status, price, created_at
            - accounting: id, type (Gelir/Gider), category, amount, description, date, payment_method
            - personnel: id, name, role, department, status, last_seen
            - parts: id, name, stock, price, min_stock, unit

            ONEMLI: Soru veritabani istatistigi iceriyorsa (ornegin 'kac', 'toplam', 'en cok', 'bakiyesi')
            sadece SQL sorgusunu iceren bir yanit ver. Format: SQL: SELECT ...
            Eger genel bir soruysa normal yanit ver.
            """

            prompt = f"{schema_info}\n\nSoru: {question}"
            raw_response = self.generate_response(prompt)

            if "SQL:" in raw_response.upper():
                sql = re.search(r"SELECT.*", raw_response, re.IGNORECASE | re.DOTALL)
                if sql and self.db:
                    sql_cmd = sql.group(0).replace('`', '').strip()
                    data = self.db.execute_read_only_query(sql_cmd)

                    analysis_prompt = (
                        f"Kullanici sorusu: {question}\n"
                        f"Veritabanindan gelen veriler: {json.dumps(data, ensure_ascii=False)}\n\n"
                        "Bu verileri kullanarak kullaniciya dogal dilde, profesyonel bir analiz raporu ver."
                    )
                    final_ans = self.generate_response(analysis_prompt)
                    return {'success': True, 'answer': final_ans, 'error': None}

            return {'success': True, 'answer': raw_response, 'error': None}

        except Exception as e:
            return {'success': False, 'answer': None, 'error': str(e)}

    def ask_jarvis(self, question):
        return self.get_smart_response(question)

    def setup_gemini(self, api_key):
        """External setup helper"""
        if isinstance(api_key, str):
            parsed_keys = [k.strip() for k in api_key.replace(",", "\n").split("\n") if k.strip()]
            self.api_keys = parsed_keys or [api_key]
        elif isinstance(api_key, list):
            self.api_keys = [str(k).strip() for k in api_key if str(k).strip()]
        else:
            self.api_keys = [str(api_key).strip()]
        self.current_key_index = 0
        if self.db:
            saved_model = (self.db.get_setting("gemini_model", "") or "").strip()
            if saved_model:
                self.model_id = normalize_gemini_model(saved_model)
        return self._setup_client()

    def record_and_process_voice(self, timeout=5, phrase_time_limit=15):
        """Mikrofondan ses alir ve Google Speech Recognition ile metne cevirir."""
        try:
            import speech_recognition as sr
        except ImportError:
            raise Exception("Ses modulu (speech_recognition) yuklu degil.")

        try:
            r = sr.Recognizer()
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    text = r.recognize_google(audio, language="tr-TR")
                    return text
            except AttributeError:
                logger.warning("PyAudio eksik; sesli giris devre disi birakildi.")
                return ""
            except OSError as e:
                raise Exception(f"Mikrofon bulunamadi veya erisip olemiyor: {e}")
            except sr.WaitTimeoutError:
                raise Exception("Ses algilanmadi. Lutfen tekrar konusun.")
            except sr.UnknownValueError:
                raise Exception("Ses anlasilamadi.")
        except Exception as e:
            raise Exception(f"Ses isleme hatasi: {str(e)}")
