# -*- coding: utf-8 -*-

import os
import time
from urllib.parse import urlparse

import requests


class EInvoiceClient:
    """
    E-Fatura API istemcisi.
    Ozel entegrator API'si ile iletisim kurar.
    """

    def __init__(self, api_key, is_sandbox=True, base_url=""):
        self.api_key = api_key
        self.is_sandbox = is_sandbox
        self.base_url = str(base_url or "").strip().rstrip("/")

    def validate_configuration(self):
        if self.is_sandbox:
            return True, "Sandbox testi yerelde calisir."
        if not self.api_key:
            return False, "API anahtari zorunludur."
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return False, "Canli API adresi HTTPS olmalidir."
        return True, "Yapilandirma gecerli."

    def test_connection(self):
        valid, message = self.validate_configuration()
        if not valid or self.is_sandbox:
            return valid, {"detail": message, "sandbox": self.is_sandbox}
        try:
            response = requests.get(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            if response.status_code >= 500:
                return False, {"detail": f"Sunucu HTTP {response.status_code} hatasi verdi."}
            if response.status_code in (401, 403):
                return False, {"detail": "API anahtari kabul edilmedi."}
            return True, {"detail": f"API sunucusuna ulasildi (HTTP {response.status_code})."}
        except requests.RequestException as exc:
            return False, {"detail": f"Baglanti kurulamadi: {exc}"}

    def send_invoice(self, invoice_json):
        """
        Faturayi API'ye gonderir.
        Return: (success: bool, response: dict)
        """
        if self.is_sandbox:
            return True, {
                "uuid": f"GIB2026{int(time.time())}",
                "status": "TEST_QUEUED",
                "message": "Fatura basariyla kuyruğa alindi (SANDBOX)",
            }

        valid, message = self.validate_configuration()
        if not valid:
            return False, {"error": "Configuration Error", "detail": message}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            resp = requests.post(
                f"{self.base_url}/invoice/send",
                json=invoice_json,
                headers=headers,
                timeout=10,
            )
            if resp.status_code in [200, 201]:
                return True, resp.json()
            return False, {"error": f"HTTP {resp.status_code}", "detail": resp.text}
        except Exception as exc:
            return False, {"error": "Connection Error", "detail": str(exc)}

    def get_status(self, uuid):
        """Fatura durumunu sorgular."""
        if self.is_sandbox:
            return "ONAYLANDI"

    def download_pdf(self, uuid, save_path):
        """PDF'i indirip diske kaydeder."""
        if self.is_sandbox:
            try:
                from reportlab.pdfgen import canvas

                c = canvas.Canvas(save_path)
                c.drawString(100, 800, "AYEC PRO - MOCK E-FATURA")
                c.drawString(100, 780, f"ETTN: {uuid}")
                c.drawString(100, 760, "Bu belge test amaciyla olusturulmustur.")
                c.save()
                return True
            except ImportError:
                with open(save_path, "w", encoding="utf-8") as handle:
                    handle.write("MOCK PDF CONTENT")
                return True
