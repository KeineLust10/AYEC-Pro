# -*- coding: utf-8 -*-
"""
src/utils/barcode_manager.py
Servis etiketi ve barkod yazdırma yöneticisi.

Özellikler:
- Code128 barkod içeren servis etiketi PDF oluşturur
- Windows varsayılan yazıcısına doğrudan gönderir
  (ya da PDF kaydeder ve kullanıcının seçtiği yazıcıya açar)
- A4 sayfasına 4 etiket yan yana, 6x4 grid şeklinde 24 etiket sığar
- Herhangi bir USB / ağ yazıcısı ile çalışır (sürücü kurulu olması yeter)
"""

import os
import sys
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

from src.utils.logger import logger


# ---------------------------------------------------------------------------
# Etiket boyutları (mm cinsinden)
# ---------------------------------------------------------------------------
LABEL_W_MM = 62          # Etiket genişliği
LABEL_H_MM = 29          # Etiket yüksekliği
LABELS_PER_ROW = 3       # Satır başına etiket adedi (A4'te)
LABELS_PER_COL = 8       # Sütun başına etiket adedi (A4'te)
MARGIN_MM = 8            # Sayfa kenar boşluğu


def _mm(val):
    """mm → ReportLab point dönüşümü (1 mm = 2.8346 pt)."""
    return val * 2.8346


class BarcodeManager:
    """
    Servis etiketi PDF oluşturur ve varsayılan yazıcıya gönderir.

    Kullanım:
        bm = BarcodeManager()
        ok, msg = bm.print_service_label({
            "tracking_no": "SRV-2025-001",
            "customer_name": "Ahmet Yılmaz",
            "device_info": "Samsung Galaxy S21",
            "entry_date": "2025-06-30",
        })
    """

    def __init__(self):
        self._reportlab_ok = self._check_reportlab()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def print_service_label(self, label_data: dict) -> tuple[bool, str]:
        """
        Servis etiketi PDF oluşturur ve yazıcıya gönderir.

        Args:
            label_data: {tracking_no, customer_name, device_info, entry_date}

        Returns:
            (success: bool, message: str)
        """
        if not self._reportlab_ok:
            return False, (
                "Etiket yazdırma için 'reportlab' kütüphanesi gereklidir.\n"
                "Lütfen yöneticinizle iletişime geçin."
            )

        try:
            pdf_path = self._build_label_pdf(label_data)
            return self._send_to_printer(pdf_path)
        except Exception as e:
            logger.error(f"BarcodeManager.print_service_label: {e}")
            return False, f"Etiket oluşturma hatası: {e}"

    def save_label_pdf(self, label_data: dict, save_path: str) -> tuple[bool, str]:
        """
        Etiketi PDF dosyasına kaydeder (yazdırmadan).

        Args:
            label_data: {tracking_no, customer_name, device_info, entry_date}
            save_path: Kaydedilecek PDF dosya yolu

        Returns:
            (success: bool, message: str)
        """
        if not self._reportlab_ok:
            return False, "reportlab kütüphanesi bulunamadı."
        try:
            self._build_label_pdf(label_data, output_path=save_path)
            return True, f"Etiket kaydedildi: {save_path}"
        except Exception as e:
            logger.error(f"BarcodeManager.save_label_pdf: {e}")
            return False, f"PDF kaydetme hatası: {e}"

    def print_barcode(self, barcode_value: str, label_text: str = "") -> tuple[bool, str]:
        """Tekil barkod yazdırır."""
        label_data = {
            "tracking_no": barcode_value,
            "customer_name": label_text,
            "device_info": "",
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
        }
        return self.print_service_label(label_data)

    # ------------------------------------------------------------------
    # PDF Oluşturma
    # ------------------------------------------------------------------

    def _build_label_pdf(self, label_data: dict, output_path: str = None) -> str:
        """
        Barkodlu servis etiketi PDF'i oluşturur.

        Returns:
            Oluşturulan PDF'in tam yolu
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.graphics.barcode import code128
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderPDF

        tracking_no   = str(label_data.get("tracking_no", "")).strip() or "UNKNOWN"
        customer_name = str(label_data.get("customer_name", "")).strip() or "—"
        device_info   = str(label_data.get("device_info", "")).strip() or "—"
        entry_date    = str(label_data.get("entry_date", datetime.now().strftime("%Y-%m-%d")))

        # Geçici PDF dosyası veya belirtilen yol
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf",
                prefix=f"etiket_{tracking_no}_",
                delete=False,
                dir=tempfile.gettempdir(),
            )
            tmp.close()
            output_path = tmp.name

        # Etiket boyutları (pt cinsinden)
        lw = _mm(LABEL_W_MM)   # Etiket genişliği
        lh = _mm(LABEL_H_MM)   # Etiket yüksekliği

        # A4 boyutlarında tek etiket sayfası oluştur
        # (tek etiket ortalanmış olarak)
        page_w, page_h = A4

        c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))

        # Sayfa ortasına etiket yerleştir
        x = (page_w - lw) / 2
        y = (page_h - lh) / 2

        self._draw_single_label(
            c, x, y, lw, lh,
            tracking_no, customer_name, device_info, entry_date
        )

        c.save()
        logger.info(f"BarcodeManager: Etiket PDF oluşturuldu → {output_path}")
        return output_path

    def _draw_single_label(
        self, c, x, y, lw, lh,
        tracking_no, customer_name, device_info, entry_date
    ):
        """Tek bir etiketi canvas üzerine çizer."""
        from reportlab.lib import colors
        from reportlab.graphics.barcode import code128
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderPDF

        # Arka plan (beyaz kutu + çerçeve)
        c.setFillColorRGB(1, 1, 1)
        c.setStrokeColorRGB(0.3, 0.3, 0.3)
        c.setLineWidth(0.5)
        c.roundRect(x, y, lw, lh, radius=_mm(1.5), fill=1, stroke=1)

        # ── Şirket logosu / başlık çizgisi ──────────────────────────
        header_h = _mm(5.5)
        c.setFillColorRGB(0.08, 0.16, 0.30)   # Koyu lacivert
        c.roundRect(x, y + lh - header_h, lw, header_h,
                    radius=_mm(1.5), fill=1, stroke=0)

        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x + _mm(2), y + lh - _mm(4), "AYEC PRO  ·  Servis Etiketi")

        # ── Takip No (büyük font) ─────────────────────────────────
        c.setFillColorRGB(0.05, 0.05, 0.05)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + _mm(2), y + lh - _mm(9), tracking_no)

        # ── Müşteri adı ───────────────────────────────────────────
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(x + _mm(2), y + lh - _mm(13), f"Müşteri: {customer_name}")

        # ── Cihaz bilgisi ─────────────────────────────────────────
        device_text = device_info[:32] + ".." if len(device_info) > 32 else device_info
        c.drawString(x + _mm(2), y + lh - _mm(17), f"Cihaz: {device_text}")

        # ── Giriş tarihi ──────────────────────────────────────────
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(x + _mm(2), y + _mm(2), f"Giriş: {entry_date}")

        # ── Code128 Barkod ────────────────────────────────────────
        barcode_val = tracking_no[:20]   # Code128 için max 20 karakter
        try:
            bc = code128.Code128(
                barcode_val,
                barHeight=_mm(7),
                barWidth=0.9,
                humanReadable=False,
                quiet=False,
            )
            # Barkodu etiketin sağ tarafına çiz
            bc_w = bc.width
            bc_x = x + lw - bc_w - _mm(2)
            bc_y = y + _mm(1.5)
            bc.drawOn(c, bc_x, bc_y)

            # Barkodun altına takip no küçük yazı
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.3, 0.3, 0.3)
            c.drawCentredString(bc_x + bc_w / 2, y + _mm(0.3), barcode_val)
        except Exception as e:
            # Barkod oluşturma başarısız olursa sadece metni yaz
            logger.warning(f"BarcodeManager barkod çizim hatası: {e}")
            c.setFont("Helvetica-Bold", 8)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(x + lw - _mm(30), y + _mm(5), tracking_no)

    # ------------------------------------------------------------------
    # Yazıcıya Gönderme
    # ------------------------------------------------------------------

    def _send_to_printer(self, pdf_path: str) -> tuple[bool, str]:
        """
        PDF'i Windows'ta varsayılan yazıcıya gönderir.
        Ayrıca PDF'i Adobe Reader / sistem görüntüleyicisinde açarak
        kullanıcının yazıcı seçmesine izin verir.
        """
        if not os.path.exists(pdf_path):
            return False, f"PDF dosyası oluşturulamadı: {pdf_path}"

        try:
            if sys.platform == "win32":
                # Windows: Varsayılan PDF uygulamasıyla aç
                # (Kullanıcı Print butonuna basarak yazıcıya gönderir)
                os.startfile(pdf_path, "print")
                logger.info(f"BarcodeManager: PDF yazdırma isteği gönderildi → {pdf_path}")
                return True, f"Etiket yazdırma diyaloğu açıldı."
            else:
                # Linux / macOS
                subprocess.Popen(["lp", pdf_path])
                return True, "Etiket kuyruğa alındı."
        except Exception as e:
            # startfile başarısız olursa dosyayı aç
            try:
                os.startfile(pdf_path)
                return True, "Etiket PDF açıldı — lütfen yazıcıya gönderin."
            except Exception as e2:
                logger.error(f"BarcodeManager._send_to_printer: {e2}")
                return False, f"Yazıcıya gönderilirken hata: {e2}"

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------

    @staticmethod
    def _check_reportlab() -> bool:
        try:
            import reportlab  # noqa
            from reportlab.graphics.barcode import code128  # noqa
            return True
        except ImportError:
            return False
