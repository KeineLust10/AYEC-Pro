# -*- coding: utf-8 -*-

import smtplib
import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import threading
import logging
from src.utils.theme_colors import tc

OFFICIAL_SMTP_SERVER = "srvm07.trwww.com"
OFFICIAL_SMTP_PORT = 465
OFFICIAL_EMAIL = "info@ayecpro.com"
SUPPORT_EMAIL = "destek@ayecpro.com"
LEGACY_PLATFORM_EMAIL = "ayecpro@gmail.com"

try:
    from src.utils.logger import logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("EmailManager")


class EmailManager:
    """Manages email sending operations (SMTP)."""

    def __init__(self, db=None):
        self.db = db
        self.smtp_server = os.getenv("AYECPRO_SMTP_SERVER", OFFICIAL_SMTP_SERVER)
        self.smtp_port = int(os.getenv("AYECPRO_SMTP_PORT", str(OFFICIAL_SMTP_PORT)))
        self.smtp_user = os.getenv("AYECPRO_SMTP_EMAIL", "")
        self.smtp_pass = os.getenv("AYECPRO_SMTP_APP_PASSWORD", "")
        self.use_tls = True
        self.smtp_security = "ssl" if self.smtp_port == 465 else "starttls"
        self.smtp_timeout = 15
        self.smtp_sender_name = ""
        self.smtp_auth_required = True
        self.smtp_auto_bcc = False
        self.smtp_archive_email = ""

        if self.db:
            self._load_config()

    def _load_config(self):
        try:
            db_server = self.db.get_setting("smtp_server", "").strip()
            db_port = self.db.get_setting("smtp_port", "").strip()
            db_user = (
                self.db.get_setting("smtp_email", "").strip()
                or self.db.get_setting("smtp_user", "").strip()
            )
            from src.utils.secure_setting_store import SecureSettingStore

            db_pass = SecureSettingStore.get(self.db, "smtp_password", "").strip()
            db_tls = self.db.get_setting("smtp_use_tls", "1").strip()
            configured_security = self.db.get_setting("smtp_security", "").strip().lower()
            configured_timeout = self.db.get_setting("smtp_timeout", "15").strip()
            configured_auth = self.db.get_setting("smtp_auth_required", "1").strip()
            configured_bcc = self.db.get_setting("smtp_auto_bcc", "0").strip()
            self.smtp_sender_name = self.db.get_setting("smtp_sender_name", "").strip()
            self.smtp_archive_email = self.db.get_setting("smtp_archive_email", "").strip() or self.db.get_setting("company_email", "").strip()
            try:
                self.smtp_timeout = max(5, min(60, int(configured_timeout or 15)))
            except (TypeError, ValueError):
                self.smtp_timeout = 15
            self.smtp_auth_required = configured_auth.lower() not in ("0", "false", "no")
            self.smtp_auto_bcc = configured_bcc.lower() in ("1", "true", "yes")

            if db_server: self.smtp_server = db_server
            if db_port: self.smtp_port = int(db_port)
            self.smtp_security = configured_security or ("ssl" if self.smtp_port == 465 else ("starttls" if db_tls == "1" else "none"))
            if db_user and db_user.lower() != LEGACY_PLATFORM_EMAIL: self.smtp_user = db_user
            if db_pass and db_user.lower() != LEGACY_PLATFORM_EMAIL: self.smtp_pass = db_pass
            if db_tls: self.use_tls = db_tls == "1"
        except Exception as e:
            logger.error(f"Error loading SMTP config: {e}")

    def send_email(self, to_email, subject, body, is_html=False):
        if not to_email or "@" not in str(to_email):
            logger.debug("Invalid recipient email: %s", to_email)
            return False
        thread = threading.Thread(target=self._send_email_thread, args=(to_email, subject, body, is_html))
        thread.start()
        return True

    def _send_email_thread(self, to_email, subject, body, is_html):
        try:
            if self.smtp_auth_required and (not self.smtp_user or not self.smtp_pass):
                logger.warning("SMTP credentials missing. Email not sent.")
                return

            msg = MIMEMultipart()
            msg['From'] = formataddr((self.smtp_sender_name, self.smtp_user)) if self.smtp_sender_name else self.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject
            if self.smtp_user.lower() == OFFICIAL_EMAIL:
                msg['Reply-To'] = SUPPORT_EMAIL

            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

            if self.smtp_security == "ssl":
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout)
                if self.smtp_security == "starttls":
                    server.starttls(context=ssl.create_default_context())

            if self.smtp_auth_required:
                server.login(self.smtp_user, self.smtp_pass)
            recipients = [to_email]
            if self.smtp_auto_bcc and self.smtp_archive_email and self.smtp_archive_email.lower() != str(to_email).lower():
                recipients.append(self.smtp_archive_email)
            server.sendmail(self.smtp_user, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")

    def send_new_service_email(self, to_email, customer_name, tracking_no, device_name):
        """Yeni servis kaydı açıldığında müşteriye e-posta gönderir."""
        if not to_email:
            return
        subject = f"Servis Kaydınız Oluşturuldu — Takip No: {tracking_no}"
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: {tc('text')};">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid {tc('border')}; border-radius: 10px;">
                <h2 style="color: {tc('accent')};">Sayın {customer_name},</h2>
                <p>Cihazınız / aracınız için servis kaydı başarıyla oluşturulmuştur.</p>
                <div style="background-color: {tc('surface_alt')}; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p style="margin: 5px 0;"><strong>Takip Numarası:</strong> {tracking_no}</p>
                    <p style="margin: 5px 0;"><strong>Cihaz / Araç:</strong> {device_name}</p>
                </div>
                <p>Servis durumunu takip etmek için işletmemiz ile iletişime geçebilirsiniz.</p>
                <p style="font-size: 12px; color: {tc('text_muted')}; margin-top: 30px;">AYEC Pro Otomatik Bilgilendirme Sistemi</p>
            </div>
        </body>
        </html>
        """
        self.send_email(to_email, subject, html_body, is_html=True)

    def send_delivery_email(self, to_email, customer_name, tracking_no, device_name, total_amount=None):
        """Cihaz teslim edildiğinde müşteriye e-posta gönderir."""
        if not to_email:
            return
        subject = f"Servis Teslim Bilgilendirmesi — Takip No: {tracking_no}"
        tut_str = f"<p style='margin: 5px 0;'><strong>Toplam Tutar:</strong> {total_amount}</p>" if total_amount else ""
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: {tc('text')};">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid {tc('border')}; border-radius: 10px;">
                <h2 style="color: {tc('accent')};">Sayın {customer_name},</h2>
                <p>{tracking_no} takip numaralı {device_name or 'cihazınız'} servis işlemlerinin ardından teslim edilmiştir.</p>
                <div style="background-color: {tc('surface_alt')}; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p style="margin: 5px 0;"><strong>Takip Numarası:</strong> {tracking_no}</p>
                    <p style="margin: 5px 0;"><strong>Durum:</strong> Teslim Edildi</p>
                    {tut_str}
                </div>
                <p>Bizimle çalıştığınız için teşekkür ederiz!</p>
                <p style="font-size: 12px; color: {tc('text_muted')}; margin-top: 30px;">AYEC Pro Otomatik Bilgilendirme Sistemi</p>
            </div>
        </body>
        </html>
        """
        self.send_email(to_email, subject, html_body, is_html=True)


    def send_welcome_email(self, to_email, company_name, username):
        subject = "AYEC Pro'ya Hos Geldiniz!"

        html_body = f"""
        <html>
        <body style=\"font-family: Arial, sans-serif; color: {tc('text')};\">
            <div style=\"max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid {tc('border')}; border-radius: 10px;\">
                <h1 style=\"color: {tc('accent')};\">AYEC Pro'ya Hos Geldiniz!</h1>
                <p>Sayin <strong>{company_name}</strong> yetkilisi,</p>
                <p>AYEC Pro Servis Yönetim Sistemi kurulumunuz basariyla tamamlandi.</p>

                <div style=\"background-color: {tc('surface_alt')}; padding: 15px; border-radius: 5px; margin: 20px 0;\">
                    <h3 style=\"margin-top: 0;\">Hesap Bilgileriniz:</h3>
                    <p><strong>Kullanici Adi:</strong> {username}</p>
                    <p><strong>Lisans Durumu:</strong> Deneme Surumu (Trial)</p>
                </div>

                <p>Uygulamayi kullanmaya baslamak icin asagidaki kaynaklardan yararlanabilirsiniz:</p>
                <ul>
                    <li><a href=\"#\">Kullanim Kilavuzu</a></li>
                    <li><a href=\"#\">Video Egitimler</a></li>
                    <li><a href=\"#\">Destek Merkezi</a></li>
                </ul>

                <p>Sorulariniz icin bizimle iletisime gecmekten cekinmeyin.</p>

                <p style=\"font-size: 12px; color: {tc('text_muted')}; margin-top: 30px;\">
                    © 2026 AYEC - AYEC Pro<br>
                    Bu e-posta otomatik olarak olusturulmustur.
                </p>
            </div>
        </body>
        </html>
        """

        self.send_email(to_email, subject, html_body, is_html=True)

    def test_connection(self):
        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=20, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)
                if self.use_tls:
                    server.starttls(context=ssl.create_default_context())
            server.login(self.smtp_user, self.smtp_pass)
            server.quit()
            return True, "Baglanti Basarili"
        except Exception as e:
            return False, str(e)
