# -*- coding: utf-8 -*-
"""Unified WhatsApp delivery service for AYEC Pro."""

import urllib.parse
import webbrowser
from typing import Any

from src.utils.logger import logger


class WhatsAppDeliveryError(RuntimeError):
    """Raised when a WhatsApp message cannot be delivered."""


class WhatsAppService:
    MODE_DISABLED = "disabled"
    MODE_CLOUD = "cloud_api"
    MODE_PROVIDER = "provider_api"
    MODE_DESKTOP = "desktop_manual"

    def __init__(self, db):
        self.db = db

    def mode(self) -> str:
        value = str(self.db.get_setting("whatsapp_mode", self.MODE_DISABLED) or "")
        return value if value in {self.MODE_DISABLED, self.MODE_CLOUD, self.MODE_PROVIDER, self.MODE_DESKTOP} else self.MODE_DISABLED

    @staticmethod
    def normalize_phone(value: Any) -> str:
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if digits.startswith("00"):
            digits = digits[2:]
        if digits.startswith("0") and len(digits) == 11:
            digits = "90" + digits[1:]
        elif len(digits) == 10:
            digits = "90" + digits
        if len(digits) < 10:
            return ""
        return "+" + digits

    def render_template(self, template: str, values: dict[str, Any]) -> str:
        company = str(self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro")
        merged = {"firma_adi": company, "company_name": company, **values}
        text = str(template or "")
        for key, value in merged.items():
            text = text.replace("{{" + key + "}}", str(value or ""))
            text = text.replace("{" + key + "}", str(value or ""))
        return text.strip()

    def send(self, phone: str, message: str, template_name: str = "", template_values: list[Any] | None = None) -> dict[str, Any]:
        target = self.normalize_phone(phone)
        if not target:
            raise WhatsAppDeliveryError("Gecerli bir telefon numarasi bulunamadi.")
        if not message.strip():
            raise WhatsAppDeliveryError("Gonderilecek WhatsApp mesaji bos.")
        mode = self.mode()
        if mode == self.MODE_DISABLED:
            raise WhatsAppDeliveryError("WhatsApp gonderimi etkin degil.")
        if mode == self.MODE_CLOUD:
            return self._send_cloud(target, message, template_name, template_values)
        if mode == self.MODE_PROVIDER:
            return self._send_provider(target, message, template_name)
        return self._open_desktop(target, message)

    def _send_cloud(self, phone: str, message: str, template_name: str, template_values: list[Any] | None = None) -> dict[str, Any]:
        token = str(self.db.get_setting("whatsapp_cloud_token", "") or "").strip()
        phone_id = str(self.db.get_setting("whatsapp_cloud_phone_id", "") or "").strip()
        if not token or not phone_id:
            raise WhatsAppDeliveryError("Cloud API icin telefon kimligi ve erisim belirteci gerekli.")
        if not template_name:
            raise WhatsAppDeliveryError("Cloud API gonderiminde onayli sablon adi gerekli.")
        try:
            import requests

            template_payload = {"name": template_name, "language": {"code": "tr"}}
            if template_values:
                template_payload["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(value)} for value in template_values],
                }]
            response = requests.post(
                "https://graph.facebook.com/v20.0/" + phone_id + "/messages",
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone.lstrip("+"),
                    "type": "template",
                    "template": template_payload,
                },
                timeout=20,
            )
            payload = response.json() if response.content else {}
            if response.status_code >= 300:
                raise WhatsAppDeliveryError(str(payload.get("error", {}).get("message") or "Cloud API gonderimi basarisiz."))
            return {"ok": True, "mode": self.MODE_CLOUD, "provider_id": str((payload.get("messages") or [{}])[0].get("id") or "")}
        except WhatsAppDeliveryError:
            raise
        except Exception as error:
            logger.warning("WhatsApp Cloud API error: %s", error)
            raise WhatsAppDeliveryError("Cloud API baglantisi basarisiz.") from error

    def _send_provider(self, phone: str, message: str, template_name: str) -> dict[str, Any]:
        sid = str(self.db.get_setting("twilio_account_sid", "") or "").strip()
        token = str(self.db.get_setting("twilio_auth_token", "") or "").strip()
        sender = str(self.db.get_setting("twilio_whatsapp_from", "") or "").strip()
        if not sid or not token or not sender:
            raise WhatsAppDeliveryError("Saglayici API icin hesap, token ve gonderici gerekli.")
        try:
            import requests

            response = requests.post(
                "https://api.twilio.com/2010-04-01/Accounts/" + sid + "/Messages.json",
                data={
                    "Body": message,
                    "From": sender if sender.startswith("whatsapp:") else "whatsapp:" + sender,
                    "To": "whatsapp:" + phone,
                },
                auth=(sid, token),
                timeout=20,
            )
            payload = response.json() if response.content else {}
            if response.status_code >= 300:
                raise WhatsAppDeliveryError(str(payload.get("message") or "Saglayici API gonderimi basarisiz."))
            return {"ok": True, "mode": self.MODE_PROVIDER, "provider_id": str(payload.get("sid") or "")}
        except WhatsAppDeliveryError:
            raise
        except Exception as error:
            logger.warning("WhatsApp provider API error: %s", error)
            raise WhatsAppDeliveryError("Saglayici API gonderimi basarisiz.") from error

    def _open_desktop(self, phone: str, message: str) -> dict[str, Any]:
        url = "https://wa.me/" + phone.lstrip("+") + "?text=" + urllib.parse.quote(message)
        webbrowser.open(url)
        return {"ok": True, "mode": self.MODE_DESKTOP, "manual_required": True, "url": url}
