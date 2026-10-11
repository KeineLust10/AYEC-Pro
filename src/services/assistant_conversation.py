"""Local-only conversational intent parsing for the desktop voice assistant."""

import json
import re
import unicodedata
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal


class LocalAssistantConversation(QThread):
    """Resolve one utterance against the currently visible application menus."""

    MODEL_NAME = "qwen3:4b"
    resolved = pyqtSignal(dict)

    def __init__(self, utterance, menu_catalog, current_page, history=None, controls=None, parent=None, continuation=False):
        super().__init__(parent)
        self.utterance = str(utterance or "")[:800]
        self.menu_catalog = [
            {"id": int(page_id), "label": str(label)[:100]}
            for page_id, label in menu_catalog
        ]
        self.current_page = int(current_page) if current_page is not None else None
        self.history = list(history or [])[-8:]
        self.controls = self._select_relevant_controls(self.utterance, controls or [])
        self.continuation = bool(continuation)

    @classmethod
    def _select_relevant_controls(cls, utterance, controls, limit=80):
        terms = {
            token for token in re.findall(r"\w+", cls._normalize_text(utterance))
            if len(token) > 2
        }
        stop_words = {
            "lutfen", "bir", "bana", "icin", "olsun", "yap", "yapabilir", "misin",
            "mi", "mu", "alanina", "alana", "ekranda",
            "ac", "acabilir", "goster", "git", "gec", "setir", "the",
        }
        terms -= stop_words
        scored = []
        for index, control in enumerate(list(controls)[:1000]):
            label = cls._normalize_text(
                str(control.get("label") or "") + " " + str(control.get("hint") or "")
                + " " + " ".join(
                    str(row.get("match_text") or "")
                    for row in control.get("rows", []) if isinstance(row, dict)
                )
            )
            label_terms = set(re.findall(r"\w+", label))
            option_terms = {
                cls._normalize_text(option)
                for option in control.get("options", [])
                if cls._normalize_text(option) in cls._normalize_text(utterance)
            }
            overlap = len(terms.intersection(label_terms))
            score = overlap * 4 + (3 if option_terms else 0)
            scored.append((score, -index, control))
        prioritized = [item[2] for item in sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)]
        return prioritized[:limit]

    def run(self):
        result = self._resolve()
        self.resolved.emit(result)

    def _resolve(self):
        table_request = self._resolve_table_selection_request()
        if table_request is not None:
            return table_request
        known_request = self._resolve_known_service_request()
        if known_request is not None:
            return known_request
        navigation_request = self._resolve_navigation_request()
        if navigation_request is not None:
            return navigation_request
        named_target = self._resolve_exact_named_target()
        if named_target and named_target.get("intent") != "unavailable":
            return named_target

        catalog = json.dumps(self.menu_catalog, ensure_ascii=True)
        current_page = json.dumps(self.current_page)
        history = json.dumps(self.history, ensure_ascii=True)
        request_controls = []
        utterance_terms = set(re.findall(r"\w+", self._normalize_text(self.utterance)))
        for item in self.controls:
            copied = dict(item)
            options = copied.get("options")
            if isinstance(options, list) and len(options) > 12:
                matching = [
                    option for option in options
                    if self._normalize_text(option) in self._normalize_text(self.utterance)
                    or set(re.findall(r"\w+", self._normalize_text(option))).intersection(utterance_terms)
                ]
                copied["options"] = (matching or options[:12])[:20]
                copied["more_options_exist"] = len(options) > len(copied["options"])
            request_controls.append(copied)
        controls = json.dumps(request_controls, ensure_ascii=True)
        prompt = (
            "You are a Turkish voice assistant inside a technical service ERP. "
            "Interpret the user's Turkish utterance using only this menu catalog: "
            + catalog
            + ". Current page id: "
            + current_page
            + ". Recent conversation: "
            + history
            + ". Controls currently visible on the active page or dialog: "
            + controls
            + ". Return exactly one JSON object. For a request to open a listed page, "
            "return {\"intent\":\"navigate\",\"page_id\":integer,\"reply\":Turkish sentence}. "
            "If the user explicitly asks to perform an action on a different menu, first return "
            "navigate with continue_action:true; the app will open that menu, rediscover its real "
            "controls, and resume the same request once. Do not set continue_action for a simple "
            "request to open a page. Never invent a control or execute an unrelated action. "
            + ("This is the one allowed post-navigation continuation. Do not navigate again; use the "
               "currently supplied controls or ask one clarification question. " if self.continuation else "")
            + "If the user asks to open a menu and search for a value, return "
            "{\"intent\":\"navigate_search\",\"page_id\":integer,\"query\":string,\"reply\":Turkish sentence}. "
            "For opening a new service form when the user says yeni servis, servis kaydi "
            "ac/olustur, return {\"intent\":\"new_service\",\"reply\":Turkish sentence}. "
            "For normal conversation or a question that needs no app action, return "
            "{\"intent\":\"chat\",\"reply\":Turkish answer}. For a request to change, "
            "delete, save, send, sync, pay, or otherwise mutate data, select its visible "
            "control; the app will ask before risky actions. For visible table rows, "
            "inspect the supplied row values and use select_option with the table id "
            "and one unique row's exact match_text; if several match, ask which record. "
            "For other visible controls, use "
            "click_control with control_id, set_field with control_id/value, "
            "select_option with control_id/value (also to select one unique matching row "
            "in a visible table), or set_toggle with control_id/value. Use nearby form labels "
            "as field names when present. For editable combo boxes, choose an existing exact "
            "option; if the requested value is not an available option, ask a short clarification. "
            "If the user provides values for several visible text fields in one request, "
            "return set_fields with fields [{control_id,value,overwrite}] for several "
            "visible text or multiline controls; editable combo controls may be included "
            "only when the requested value exactly matches one supplied option. Do not "
            "save or submit as part of filling. If the user explicitly corrects a value "
            "that is already present, target that field and set overwrite:true; otherwise "
            "never overwrite a filled field. After a correction request, confirm which "
            "field value should replace the old one if the replacement is unclear. "
            "Use intent clarify with {\"intent\":\"clarify\",\"reply\":one short Turkish question} "
            "when the target, requested operation, or a required value is ambiguous or missing. "
            "Never guess customer, device, amount, date, record, or destructive scope. "
            "Treat recent conversation as active context: interpret short answers against the "
            "most recent assistant question, but ask again if multiple interpretations remain. "
            "Do not claim a form is complete or saved just because fields were filled. "
            "For stock price changes, require an explicit percentage and state that the current "
            "voice bulk-price action covers all active stock cards before asking for approval. "
            "If a named category or narrower scope is requested but unavailable, clarify instead "
            "of applying the change to all stock. For OCR imports, "
            "treat extracted values as unverified, guide the user through the preview, and never "
            "commit imported stock without the user's explicit confirmation. "
            "Use only an exact id from the supplied controls. Never invent control ids. "
            "Never invent menu ids, claim an action is complete before it is run, or "
            "return any intent other than navigate, navigate_search, new_service, chat, clarify, click_control, set_fields, "
            "set_field, select_option, set_toggle. "
            "User utterance: "
            + json.dumps(self.utterance, ensure_ascii=True)
        )
        body = json.dumps(
            {
                "model": self.MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 180},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read(256_000).decode("utf-8"))
            content = payload.get("message", {}).get("content", "")
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            parsed = json.loads(match.group(0)) if match else {}
            intent = parsed.get("intent")
            reply = str(parsed.get("reply") or "")[:500]
            if intent not in {"navigate", "navigate_search", "new_service", "chat", "clarify", "click_control", "set_field", "set_fields", "select_option", "set_toggle"}:
                raise ValueError("Unsupported assistant intent")
            if self.continuation and intent in {"navigate", "navigate_search"}:
                return {
                    "intent": "clarify",
                    "reply": "Bu ekrandayim. Hangi kaydi veya islemi yapmami istiyorsunuz?",
                    "utterance": self.utterance,
                }
            if intent == "clarify":
                if not reply:
                    raise ValueError("Clarification question is required")
                return {"intent": intent, "reply": reply, "utterance": self.utterance}
            if intent in {"navigate", "navigate_search"}:
                page_id = int(parsed.get("page_id"))
                if page_id not in {item["id"] for item in self.menu_catalog}:
                    raise ValueError("Requested page is not available in the menu")
                result = {"intent": intent, "page_id": page_id, "reply": reply, "utterance": self.utterance}
                if intent == "navigate" and not self.continuation:
                    result["continue_action"] = parsed.get("continue_action") is True
                if intent == "navigate_search":
                    query = str(parsed.get("query") or "").strip()
                    if not query:
                        raise ValueError("A search query is required for navigate_search")
                    result["query"] = query[:160]
                return result
            if intent in {"click_control", "set_field", "select_option", "set_toggle"}:
                control_id = str(parsed.get("control_id") or "")
                if control_id not in {item.get("id") for item in self.controls}:
                    raise ValueError("Requested control is not currently available")
                result = {"intent": intent, "control_id": control_id, "reply": reply, "utterance": self.utterance}
                if intent == "set_field":
                    source_values = self._extract_explicit_field_values()
                    value = source_values.get(control_id, str(parsed.get("value") or ""))
                    if not value.strip():
                        return {
                            "intent": "clarify",
                            "reply": "Bu alan icin bir deger duyamadim. Degeri tekrar soyler misiniz?",
                            "utterance": self.utterance,
                        }
                    result["value"] = value[:500]
                    control = next(item for item in self.controls if item.get("id") == control_id)
                    result["overwrite"] = bool(parsed.get("overwrite", False)) if control.get("filled") else False
                elif intent == "select_option":
                    result["value"] = str(parsed.get("value") or "")[:160]
                elif intent == "set_toggle":
                    result["value"] = bool(parsed.get("value"))
                return result
            if intent == "set_fields":
                fields = parsed.get("fields")
                if not isinstance(fields, list) or not 2 <= len(fields) <= 10:
                    raise ValueError("set_fields requires two to ten field updates")
                available = {
                    item.get("id") for item in self.controls
                    if item.get("type") in {"text", "multiline"}
                    or (item.get("type") == "combo" and item.get("editable"))
                }
                result_fields = []
                seen = set()
                source_values = self._extract_explicit_field_values()
                for item in fields:
                    if not isinstance(item, dict):
                        raise ValueError("Invalid field update")
                    control_id = str(item.get("control_id") or "")
                    if control_id not in available or control_id in seen:
                        raise ValueError("Field control is unavailable or repeated")
                    seen.add(control_id)
                    available_control = next(item for item in self.controls if item.get("id") == control_id)
                    value = source_values.get(control_id, str(item.get("value") or ""))[:500]
                    if not value.strip():
                        return {
                            "intent": "clarify",
                            "reply": "Alanlardan biri icin deger alamadim. Eksik degeri tekrar soyler misiniz?",
                            "utterance": self.utterance,
                        }
                    if available_control.get("type") == "combo":
                        options = [str(option) for option in available_control.get("options", [])]
                        if not any(self._normalize_text(option) == self._normalize_text(value) for option in options):
                            raise ValueError("Editable combo value must match an available option")
                    result_fields.append({
                        "control_id": control_id,
                        "value": value,
                        "overwrite": bool(item.get("overwrite", False)) if available_control.get("filled") else False,
                        "operation": "select_option" if available_control.get("type") == "combo" else "set_field",
                    })
                return {
                    "intent": intent,
                    "fields": result_fields,
                    "reply": reply,
                    "utterance": self.utterance,
                }
            return {"intent": intent, "reply": reply, "utterance": self.utterance}
        except Exception:
            return self._resolve_offline_fallback()

    def _resolve_exact_named_target(self):
        """Resolve only an exact visible page/control name before model use."""
        words = self._normalize_text(self.utterance).strip(" ,.!?").split()
        while words and words[0] in {"hey", "merhaba", "selam", "asistan", "lutfen", "bana"}:
            words.pop(0)
        command_words = {"ac", "acalim", "git", "goster", "goruntule", "sayfasini", "sayfasina", "ekranini", "ekranina"}
        while words and words[-1] in command_words:
            words.pop()
        spoken_name = self._canonical_spoken_name(" ".join(words))
        if not spoken_name:
            return None

        page_matches = [
            item for item in self.menu_catalog
            if self._canonical_spoken_name(item.get("label")) == spoken_name
        ]
        if len(page_matches) == 1:
            target = page_matches[0]
            if target.get("id") == self.current_page:
                return {"intent": "respond", "reply": target.get("label", "Ekran") + " zaten acik.", "utterance": self.utterance}
            return {
                "intent": "navigate", "page_id": target.get("id"),
                "reply": target.get("label", "Ekran") + " ekranina geciyorum.", "utterance": self.utterance,
            }
        if len(page_matches) > 1:
            return {"intent": "clarify", "reply": "Bu menu adi birden fazla ekranda var.", "utterance": self.utterance}

        matches = []
        for control in self.controls:
            control_type = str(control.get("type") or "")
            label = self._normalize_text(control.get("label"))
            if control_type in {"tabs", "combo"}:
                matches.extend(
                    (control, option, "select_option")
                    for option in control.get("options", [])
                    if self._canonical_spoken_name(option) == spoken_name
                )
            elif control_type in {"button", "action"} and self._canonical_spoken_name(label) == spoken_name:
                matches.append((control, None, "click_control"))
        if len(matches) == 1:
            control, value, intent = matches[0]
            result = {
                "intent": intent, "control_id": control.get("id"),
                "reply": "Istenen kontrolu seciyorum.", "utterance": self.utterance,
            }
            if intent == "select_option":
                result["value"] = value
            return result
        if len(matches) > 1:
            return {"intent": "clarify", "reply": "Bu isimde birden fazla gorunen kontrol var.", "utterance": self.utterance}
        return None

    def _resolve_known_service_request(self):
        """Resolve unambiguous service-list requests without an LLM round trip."""
        text = self._normalize_text(self.utterance)
        if not text:
            return None

        if re.search(r"\bserviste\s+bulunan\s+(?:cihaz|telefon|urun)\w*\s+(?:ac|goster|goruntule)\b", text):
            return {
                "intent": "clarify",
                "reply": "Hangi cihaz\u0131 a\u00e7mam\u0131 istersiniz? M\u00fc\u015fteri ad\u0131, cihaz modeli veya servis numaras\u0131n\u0131 s\u00f6yleyin.",
                "utterance": self.utterance,
            }

        customer_service = re.search(
            r"^\s*(?:lutfen\s+)?(?P<name>.+?)"
            r"(?:['’](?:nin|in)\s+|\s+(?:(?:adli\s+)?musteri(?:nin|si(?:nin)?)?\s+)?)"
            r"servis(?:lerini|ler|\s+kayitlarini|\s+kayitlari)\s+"
            r"(?:ac|goster|goruntule|listele)\b",
            text,
        )
        if not customer_service:
            return None

        page = next((item for item in self.menu_catalog if item["id"] == 42), None)
        customer_name = customer_service.group("name").strip(" ,.!?'’\"")
        if page is None or not customer_name:
            return {
                "intent": "clarify",
                "reply": "Servis listesi bu kullan\u0131c\u0131 i\u00e7in eri\u015filebilir de\u011fil veya m\u00fc\u015fteri ad\u0131n\u0131 alamad\u0131m.",
                "utterance": self.utterance,
            }
        return {
            "intent": "navigate_search",
            "page_id": 42,
            "query": customer_name,
            "reply": customer_name + " ad\u0131na kay\u0131tl\u0131 servisleri ar\u0131yorum.",
            "utterance": self.utterance,
        }

    def _resolve_table_selection_request(self):
        """Resolve a spoken selection only when one supplied visible row matches."""
        text = self._normalize_text(self.utterance)
        words = set(re.findall(r"\w+", text))
        selection_words = {
            "sec", "secin", "secelim", "ac", "acalim", "goster",
            "goruntule", "detay", "ilerle", "onayla",
        }
        if not words.intersection(selection_words):
            return None
        ignored = selection_words | {
            "kayit", "kaydi", "servis", "serviste", "servisteki", "cihaz", "cihazi",
            "musteri", "panel", "teknisyen", "listeden", "sonraki",
            "lutfen", "bana", "icin", "ait", "bulunan", "olan",
            "ad", "adli", "kayitli", "servisindeki", "servislerindeki",
        }
        suffixes = (
            "lerindeki", "larindaki", "lerinin", "larinin", "lerini", "larini",
            "larindan", "lerinden", "larina", "lerine", "lari", "leri", "lar",
            "ler", "nin", "nun", "dan", "den", "tan", "ten", "nda", "nde",
            "daki", "deki", "ini", "unu", "sini", "sunu", "si", "i", "u",
            "e", "a",
        )

        def stem_term(word):
            for _ in range(2):
                for suffix in suffixes:
                    if len(word) > len(suffix) + 2 and word.endswith(suffix):
                        word = word[:-len(suffix)]
                        break
            return word

        ignored_roots = {stem_term(word) for word in ignored}
        terms = {
            stem_term(word) for word in words - ignored
            if len(word) > 2 and stem_term(word) not in ignored_roots
        }
        if not terms:
            return None

        matches = []
        for control in self.controls:
            if control.get("type") != "table":
                continue
            for row in control.get("rows", []):
                if not isinstance(row, dict):
                    continue
                normalized = self._normalize_text(row.get("match_text") or "")
                if all(term in normalized for term in terms):
                    matches.append((control, row))
        if len(matches) == 1:
            control, row = matches[0]
            return {
                "intent": "select_option",
                "control_id": control.get("id"),
                "value": str(row.get("match_text") or "")[:500],
                "reply": "Eslesen servis kaydini secip paneli aciyorum.",
                "utterance": self.utterance,
            }
        if len(matches) > 1:
            return {
                "intent": "clarify",
                "reply": "Bu musteri icin birden fazla servis var. Cihaz modelini veya takip numarasini soyler misiniz?",
                "utterance": self.utterance,
            }
        return None

    def _resolve_navigation_request(self):
        """Handle clear menu and menu-search speech from the live menu catalog."""
        text = self._normalize_text(self.utterance)
        words = re.findall(r"\w+", text)
        navigation_verbs = {
            "ac", "acalim", "git", "goster", "goruntule", "listele", "gir",
            "menuye", "ekranina", "ekranini", "sayfasina", "sayfasini",
        }
        search_verbs = {"ara", "bul", "ara", "listele"}
        if not navigation_verbs.intersection(words) and not search_verbs.intersection(words):
            return None

        generic_menu_words = {
            "liste", "listesi", "panel", "paneli", "yonetim", "yonetimi",
            "takip", "merkez", "merkezi", "ekran", "ekrani", "sayfa", "sayfasi",
            "modulu", "bolumu", "islemleri",
        }
        stop_words = {
            "ac", "acalim", "git", "goster", "goruntule", "listele", "gir",
            "menuye", "ekranina", "ekranini", "sayfasina", "sayfasini", "ara",
            "bul", "lutfen", "bana", "bir", "icin", "de", "da", "mi", "mu",
            "kaydi", "kayit", "kayitlari", "olan", "bulunan", "mevcut", "tum",
            "benim", "bizim", "su", "bu", "ve", "olarak",
        }

        def stem(token):
            suffixes = (
                "lerindeki", "larindaki", "lerinin", "larinin", "lerini", "larini",
                "larindan", "lerinden", "larina", "lerine", "lari", "leri", "lar",
                "ler", "nin", "nun", "dan", "den", "ina", "ine", "ini", "unu",
                "nda", "nde", "daki", "deki", "da", "de", "yi", "yu",
            )
            for _ in range(2):
                for suffix in suffixes:
                    if len(token) > len(suffix) + 2 and token.endswith(suffix):
                        token = token[:-len(suffix)]
                        break
            return token

        exact = [
            item for item in self.menu_catalog
            if self._normalize_text(item["label"]) in text
        ]
        candidates = exact
        if not candidates:
            input_terms = {stem(word) for word in words if word not in stop_words}
            scored = []
            for item in self.menu_catalog:
                label_terms = {
                    stem(word)
                    for word in re.findall(r"\w+", self._normalize_text(item["label"]))
                    if word not in generic_menu_words
                }
                overlap = input_terms.intersection(label_terms)
                if overlap:
                    scored.append((len(overlap), item))
            if scored:
                best = max(score for score, _item in scored)
                candidates = [item for score, item in scored if score == best]

        if len(candidates) != 1:
            return None

        target = candidates[0]
        search_requested = bool(search_verbs.intersection(words))
        if search_requested:
            label_terms = {
                stem(word)
                for word in re.findall(r"\w+", self._normalize_text(target["label"]))
                if word not in generic_menu_words
            }
            original_terms = []
            for word in re.findall(r"[^\W_]+", self.utterance, flags=re.UNICODE):
                normalized = self._normalize_text(word)
                root = stem(normalized)
                if root not in label_terms and normalized not in stop_words:
                    original_terms.append(word)
            if original_terms:
                return {
                    "intent": "navigate_search",
                    "page_id": target["id"],
                    "query": " ".join(original_terms)[:160],
                    "reply": target["label"] + " ekran\u0131nda ar\u0131yorum.",
                    "utterance": self.utterance,
                }
            return None

        if target["id"] == self.current_page and not exact:
            return None

        continue_action = bool(
            {
                "ekle", "olustur", "kaydet", "sil", "guncelle", "degistir",
                "sec", "secin", "secelim", "doldur", "dolduralim",
            }.intersection(words)
        )
        if target["id"] == self.current_page:
            return {
                "intent": "respond",
                "reply": target["label"] + " zaten a\u00e7\u0131k. Bu ekranda hangi kayd\u0131 veya i\u015flemi istedi\u011finizi s\u00f6yleyin.",
                "utterance": self.utterance,
            }
        return {
            "intent": "navigate",
            "page_id": target["id"],
            "continue_action": bool(continue_action and not self.continuation),
            "reply": target["label"] + " ekran\u0131na ge\u00e7iyorum.",
            "utterance": self.utterance,
        }

    @staticmethod
    def _normalize_text(value):
        text = unicodedata.normalize("NFKD", str(value or "").casefold())
        return "".join(char for char in text if not unicodedata.combining(char)).replace("\u0131", "i")

    @classmethod
    def _canonical_spoken_name(cls, value):
        return " ".join(re.findall(r"\w+", cls._normalize_text(value)))

    @classmethod
    def _normalized_text_with_map(cls, value):
        normalized = []
        source_positions = []
        for index, char in enumerate(str(value or "")):
            folded = unicodedata.normalize("NFKD", char.casefold())
            for item in folded:
                if unicodedata.combining(item):
                    continue
                normalized.append("i" if item == "\u0131" else item)
                source_positions.append(index)
        return "".join(normalized), source_positions

    def _extract_explicit_field_values(self):
        """Read values following spoken visible-field labels without rewriting them."""
        normalized, source_positions = self._normalized_text_with_map(self.utterance)
        aliases = {}
        for control in self.controls:
            if control.get("type") not in {"text", "multiline"} and not (
                control.get("type") == "combo" and control.get("editable")
            ):
                continue
            control_id = str(control.get("id") or "")
            label = str(control.get("label") or "").replace("*", "")
            for part in re.split(r"[/|\n]", label):
                alias = self._normalize_text(part).strip()
                if len(alias) > 2:
                    aliases.setdefault(alias, set()).add(control_id)

        occurrences = []
        spoken_suffixes = (
            "larindan", "lerinden", "larina", "lerine", "larini", "lerini",
            "larinda", "lerinde", "larinin", "lerinin", "sindan", "sinden",
            "sina", "sine", "sini", "sunu", "sina", "suna", "sunu",
            "nin", "nun", "nin", "ndan", "nden", "nda", "nde", "ni",
            "nu", "na", "ne", "ya", "ye", "yi", "yu", "n",
        )
        for alias, control_ids in aliases.items():
            if len(control_ids) != 1:
                continue
            start = 0
            while True:
                start = normalized.find(alias, start)
                if start < 0:
                    break
                end = start + len(alias)
                left_ok = start == 0 or not normalized[start - 1].isalnum()
                right_ok = end == len(normalized) or not normalized[end].isalnum()
                suffix_length = 0
                if not right_ok:
                    for suffix in spoken_suffixes:
                        suffix_end = end + len(suffix)
                        if (
                            normalized.startswith(suffix, end)
                            and suffix_end <= len(normalized)
                            and (suffix_end == len(normalized) or not normalized[suffix_end].isalnum())
                        ):
                            suffix_length = len(suffix)
                            break
                if left_ok and (right_ok or suffix_length):
                    occurrences.append((start, end + suffix_length, next(iter(control_ids)), alias))
                start = end
        occurrences.sort(key=lambda item: (item[0], -(item[1] - item[0])))
        labels = []
        for item in occurrences:
            if labels and item[0] < labels[-1][1]:
                continue
            labels.append(item)

        values = {}
        for index, (_start, label_end, control_id, _alias) in enumerate(labels):
            value_start = label_end
            value_end = labels[index + 1][0] if index + 1 < len(labels) else len(normalized)
            segment = normalized[value_start:value_end]
            prefix = re.match(
                r"\s*(?:(?:alanina|alana|icin|degerini|deger|olarak|su)\s*)*[:=,\-]*\s*",
                segment,
            )
            if prefix:
                value_start += prefix.end()
            segment = normalized[value_start:value_end]
            command = re.search(
                r"(?:^|\s+)(?:olarak\s+)?(?:doldur(?:un|alim)?|yaz(?:in)?|gir(?:in)?|ekle|olsun|yap(?:in)?|ayarla|kaydet)\b\s*[.!?]*$",
                segment,
            )
            if command:
                value_end = value_start + command.start()
            while value_start < value_end and normalized[value_start] in " ,.:;!?=":
                value_start += 1
            while value_end > value_start and normalized[value_end - 1] in " ,.:;!?=":
                value_end -= 1
            if value_start >= value_end or value_end - 1 >= len(source_positions):
                continue
            source_start = source_positions[value_start]
            source_end = source_positions[value_end - 1] + 1
            value = self.utterance[source_start:source_end].strip(" \t,.:;!?=\"'")
            if value:
                values[control_id] = value
        return values

    def _resolve_offline_fallback(self):
        """Keep exact menu and visible-control commands usable without local LLM."""
        text = self._normalize_text(self.utterance)
        navigation_verbs = {
            "ac", "git", "goster", "goruntule", "menuye", "ekranina",
            "sayfasina", "panosuna",
        }
        asks_to_navigate = bool(navigation_verbs.intersection(text.split()))
        if any(word in text.split() for word in {"yapma", "dokunma", "degil", "vazgec", "sorma"}):
            return {
                "intent": "clarify",
                "reply": "Olumsuz veya soru \u015feklindeki iste\u011fi g\u00fcvenli yorumlayamad\u0131m; hi\u00e7bir i\u015flem yapmad\u0131m.",
                "utterance": self.utterance,
            }
        matching_menus = [
            item for item in self.menu_catalog
            if self._normalize_text(item["label"]) in text
        ]
        if len(matching_menus) == 1 and (
            asks_to_navigate or matching_menus[0]["id"] != self.current_page
        ):
            target = matching_menus[0]
            continue_action = any(
                verb in text.split()
                for verb in {"ekle", "olustur", "kaydet", "sil", "guncelle", "degistir"}
            )
            return {
                "intent": "navigate",
                "page_id": target["id"],
                "continue_action": bool(continue_action and not self.continuation),
                "reply": target["label"] + " ekran\u0131na ge\u00e7iyorum.",
                "utterance": self.utterance,
            }
        if len(matching_menus) > 1:
            return {
                "intent": "clarify",
                "reply": "Birden fazla men\u00fc ad\u0131 e\u015fle\u015fti. Hangisini a\u00e7mam\u0131 istersiniz?",
                "utterance": self.utterance,
            }

        matches = []
        for control in self.controls:
            label = self._normalize_text(control.get("label"))
            aliases = [self._normalize_text(part) for part in re.split(r"[/|\n]", str(control.get("label") or ""))]
            aliases = [alias.strip() for alias in aliases if len(alias.strip()) > 2]
            if label:
                aliases.append(label)
            matched_aliases = [alias for alias in set(aliases) if alias in text]
            if matched_aliases:
                matches.append((control, max(matched_aliases, key=len)))
            elif control.get("type") in {"combo", "tabs"}:
                option_matches = [
                    self._normalize_text(option)
                    for option in control.get("options", [])
                    if self._normalize_text(option) == text
                ]
                if option_matches:
                    matches.append((control, option_matches[0]))
        if len(matches) == 1:
            control, matched_label = matches[0]
            control_type = control.get("type")
            control_id = control.get("id")
            if control_type in {"combo", "tabs"}:
                options = [
                    str(option) for option in control.get("options", [])
                    if self._normalize_text(option) in text
                ]
                if len(options) == 1:
                    return {
                        "intent": "select_option", "control_id": control_id,
                        "value": options[0], "reply": "\u0130stenen se\u00e7ene\u011fi se\u00e7iyorum.",
                        "utterance": self.utterance,
                    }
                return {
                    "intent": "clarify",
                    "reply": "Bu listedeki hangi se\u00e7ene\u011fi se\u00e7memi istersiniz?",
                    "utterance": self.utterance,
                }
            if control_type in {"button", "action"}:
                if any(word in text.split() for word in {"nerede", "hangisi", "ne", "bul"}):
                    return {
                        "intent": "clarify",
                        "reply": "Kontrol hakk\u0131nda bilgi mi istiyorsunuz, yoksa \u00e7al\u0131\u015ft\u0131rmam\u0131 m\u0131?",
                        "utterance": self.utterance,
                    }
                return {
                    "intent": "click_control", "control_id": control_id,
                    "reply": "\u0130stenen g\u00f6r\u00fcnen kontrol\u00fc \u00e7al\u0131\u015ft\u0131r\u0131yorum.",
                    "utterance": self.utterance,
                }
            if control_type in {"check", "radio"}:
                if any(word in text.split() for word in {"ac", "etkinlestir", "aktiflestir", "sec"}):
                    value = True
                elif any(word in text.split() for word in {"kapat", "pasiflestir", "kaldir"}):
                    value = False
                else:
                    return {
                        "intent": "clarify",
                        "reply": "Bu se\u00e7ene\u011fi a\u00e7mam\u0131 m\u0131, kapatmam\u0131 m\u0131 istersiniz?",
                        "utterance": self.utterance,
                    }
                return {
                    "intent": "set_toggle", "control_id": control_id, "value": value,
                    "reply": "Se\u00e7ene\u011fi g\u00fcncelliyorum.", "utterance": self.utterance,
                }
            if control_type in {"text", "multiline", "number", "date", "time", "datetime"}:
                normalized, source_positions = self._normalized_text_with_map(self.utterance)
                label = matched_label
                start = normalized.find(label)
                tail_start = start + len(label)
                cue = re.match(r"\s*(?:alanina|alana|icin|olarak|degerini|deger)\s*", normalized[tail_start:])
                if cue:
                    tail_start += cue.end()
                tail = normalized[tail_start:]
                end_match = re.search(
                    r"\s+(?:yaz|gir|ekle|olsun|yap|ayarla|olarak(?:\s+(?:yaz|gir))?)\s*[.!?]*$", tail
                )
                value_end = tail_start + end_match.start() if end_match else len(normalized)
                if tail_start < value_end and value_end - 1 < len(source_positions):
                    value = self.utterance[
                        source_positions[tail_start]:source_positions[value_end - 1] + 1
                    ].strip(" \t,.:;!?\"'")
                    if value:
                        return {
                            "intent": "set_field", "control_id": control_id,
                            "value": value[:500], "overwrite": False,
                            "reply": "\u0130stenen alan\u0131 dolduruyorum.",
                            "utterance": self.utterance,
                        }
        source_values = self._extract_explicit_field_values()
        for key, value in tuple(source_values.items()):
            source_values[key] = re.sub(
                r"\s+(?:olarak\s+)?(?:dold(?:ur|un|alim)?|yaz(?:in)?|gir(?:in)?|ekle|olsun|yap(?:in)?|ayarla|kaydet)\s*[.!?]*$",
                "",
                value,
                flags=re.IGNORECASE,
            ).strip()
        supported = {
            str(control.get("id")): control
            for control in self.controls
            if control.get("type") in {"text", "multiline"}
            or (control.get("type") == "combo" and control.get("editable"))
        }
        matched_ids = [str(control.get("id") or "") for control, _label in matches]
        if (
            len(set(matched_ids)) == len(matched_ids)
            and len(matched_ids) >= 2
            and all(control_id in supported and source_values.get(control_id, "").strip() for control_id in matched_ids)
        ):
            return {
                "intent": "set_fields",
                "fields": [
                    {
                        "control_id": control_id,
                        "value": source_values[control_id][:500],
                        "overwrite": False,
                        "operation": "select_option" if supported[control_id].get("type") == "combo" else "set_field",
                    }
                    for control_id in matched_ids
                ],
                "reply": "Birden fazla alan icin soylediginiz degerleri dolduruyorum.",
                "utterance": self.utterance,
            }
        if len(matches) > 1:
            return {
                "intent": "clarify",
                "reply": "Birden fazla g\u00f6r\u00fcnen kontrol e\u015fle\u015fti. Hangisini kullanmam\u0131 istersiniz?",
                "utterance": self.utterance,
            }
        return {
            "intent": "unavailable",
            "reply": (
                "Yerel sohbet modeli kullan\u0131lam\u0131yor. A\u00e7\u0131k men\u00fc ve g\u00f6r\u00fcnen d\u00fc\u011fme adlar\u0131n\u0131 "
                "kullanarak deneyin; veri de\u011fi\u015fikli\u011fi yapmad\u0131m."
            ),
            "utterance": self.utterance,
        }
