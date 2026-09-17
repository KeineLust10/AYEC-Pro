# -*- coding: utf-8 -*-

import smtplib
import ssl
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("AYECProLogger")

OFFICIAL_SMTP_SERVER = "srvm07.trwww.com"
OFFICIAL_SMTP_PORT = 465
OFFICIAL_EMAIL = "info@ayecpro.com"
SUPPORT_EMAIL = "destek@ayecpro.com"
LEGACY_PLATFORM_EMAIL = "ayecpro@gmail.com"

class MailWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, recipient, subject, body, is_html=False, attachment_path=None, db=None):
        super().__init__()
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.is_html = is_html
        self.attachment_path = attachment_path
        self.db = db
        
        # Credentials must come from the environment or encrypted app settings.
        self.smtp_server = os.getenv("AYECPRO_SMTP_SERVER", OFFICIAL_SMTP_SERVER)
        self.smtp_port = int(os.getenv("AYECPRO_SMTP_PORT", str(OFFICIAL_SMTP_PORT)))
        self.system_email = os.getenv("AYECPRO_SMTP_EMAIL", OFFICIAL_EMAIL)
        self.app_password = os.getenv("AYECPRO_SMTP_APP_PASSWORD", "")
        self.use_tls = True
        
        if self.db:
            try:
                db_server = self.db.get_setting("smtp_server", "").strip()
                db_port = self.db.get_setting("smtp_port", "").strip()
                db_user = (
                    self.db.get_setting("smtp_email", "").strip()
                    or self.db.get_setting("smtp_user", "").strip()
                )
                db_pass = self.db.get_setting("smtp_password", "").strip()
                db_tls = self.db.get_setting("smtp_use_tls", "1").strip()

                if db_server: self.smtp_server = db_server
                if db_port: self.smtp_port = int(db_port)
                if db_user and db_user.lower() != LEGACY_PLATFORM_EMAIL: self.system_email = db_user
                if db_pass and db_user.lower() != LEGACY_PLATFORM_EMAIL: self.app_password = db_pass
                if db_tls: self.use_tls = db_tls == "1"
            except Exception:
                pass 

        if not self.system_email or not self.app_password:
            try:
                from src.utils.email_manager import EmailManager

                fallback = EmailManager(self.db)
                self.smtp_server = fallback.smtp_server
                self.smtp_port = fallback.smtp_port
                self.system_email = fallback.smtp_user
                self.app_password = fallback.smtp_pass
                self.use_tls = fallback.use_tls
            except Exception:
                pass

    def run(self):
        try:
            if not self.system_email or not self.app_password:
                raise RuntimeError(
                    "SMTP credentials are not configured. "
                    "Use application settings or AYECPRO_SMTP_* variables."
                )
            msg = MIMEMultipart()
            msg['From'] = f"AYEC Pro <{self.system_email}>"
            msg['To'] = self.recipient
            msg['Subject'] = self.subject
            if self.system_email.lower() == OFFICIAL_EMAIL:
                msg['Reply-To'] = SUPPORT_EMAIL
            
            mime_type = 'html' if self.is_html else 'plain'
            msg.attach(MIMEText(self.body, mime_type))

            if self.attachment_path and os.path.exists(self.attachment_path):
                try:
                    with open(self.attachment_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    file_name = os.path.basename(self.attachment_path)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {file_name}",
                    )
                    msg.attach(part)
                except Exception as e:
                    logger.error("Mail attachment error: %s", e)

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=20, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)
                if getattr(self, "use_tls", True):
                    server.starttls(context=ssl.create_default_context())
            server.login(self.system_email, self.app_password)
            server.send_message(msg)
            server.quit()
            
            self.finished.emit(True, "E-posta ba\u015far\u0131yla g\u00f6nderildi.")
            
        except Exception as e:
            self.finished.emit(False, str(e))


def send_registration_emails_async(data, db=None):
    """
    Yeni müşteri kaydı oluştuğunda:
    1. Müşterinin e-posta adresine Hoş Geldin maili gönderir.
    2. Notify the official support mailbox about the new registration.
    """
    from datetime import datetime
    company_name = data.get("company_name") or data.get("company") or "Belirtilmedi"
    full_name = data.get("full_name") or data.get("authorized_person") or data.get("username") or "Sayın Yetkili"
    user_email = data.get("email") or ""
    phone = data.get("phone") or "Belirtilmedi"
    purpose = data.get("purpose") or data.get("current_sector") or "Genel"
    license_info = data.get("license") or "Deneme Sürümü (Trial)"
    reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    admin_emails = [SUPPORT_EMAIL]
    if db:
        try:
            custom_admin = db.get_setting("admin_notification_email", "").strip()
            if custom_admin and "@" in custom_admin and custom_admin.lower() != LEGACY_PLATFORM_EMAIL and custom_admin not in admin_emails:
                admin_emails.append(custom_admin)
        except Exception:
            pass

    # -------------------------------------------------------------
    # 1. MÜŞTERİYE GÖNDERİLECEK HOŞ GELDİN MAİLİ
    # -------------------------------------------------------------
    if user_email and "@" in user_email:
        customer_html = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head><meta charset="UTF-8">
        <style>
          body{{font-family:'Segoe UI',Arial,sans-serif;background:#0F172A;margin:0;padding:0;color:#F8FAFC;}}
          .wrap{{max-width:600px;margin:30px auto;background:#1E293B;border-radius:16px;overflow:hidden;border:1px solid #334155;}}
          .header{{background:linear-gradient(135deg,#2563EB,#4F46E5);padding:36px;text-align:center;}}
          .header h1{{color:#FFFFFF;margin:0;font-size:26px;font-weight:800;}}
          .header p{{color:#E2E8F0;margin:6px 0 0;font-size:14px;}}
          .body{{padding:32px;}}
          .card{{background:#0F172A;border-radius:12px;padding:20px;border:1px solid #334155;margin:20px 0;}}
          .card-title{{color:#60A5FA;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;}}
          .row{{display:flex;justify-content:space-between;border-bottom:1px solid #334155;padding:8px 0;font-size:13px;}}
          .row:last-child{{border-bottom:none;}}
          .row-label{{color:#94A3B8;}}
          .row-val{{color:#F8FAFC;font-weight:600;}}
          .badge{{background:rgba(16,185,129,0.2);color:#34D399;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;}}
          .footer{{text-align:center;padding:20px;border-top:1px solid #334155;font-size:12px;color:#64748B;}}
        </style>
        </head>
        <body>
        <div class="wrap">
          <div class="header">
            <h1>AYEC Pro Servis Takip</h1>
            <p>Aramıza Hoş Geldiniz! 🎉</p>
          </div>
          <div class="body">
            <p style="font-size:16px;font-weight:600;color:#F8FAFC;">Sayın {full_name},</p>
            <p style="color:#CBD5E1;font-size:14px;line-height:1.6;">
              <strong style="color:#60A5FA;">{company_name}</strong> firması için AYEC Pro kaydınız başarıyla tamamlanmıştır.
              İşletmenizi dijitalleştirmek ve tüm servis süreçlerinizi tek noktadan yönetmek için sisteminiz kullanıma hazırdır.
            </p>
            <div class="card">
              <div class="card-title">Kayıt & İrtibat Bilgileri</div>
              <div class="row"><span class="row-label">Firma Adı</span><span class="row-val">{company_name}</span></div>
              <div class="row"><span class="row-label">Yetkili</span><span class="row-val">{full_name}</span></div>
              <div class="row"><span class="row-label">E-posta</span><span class="row-val">{user_email}</span></div>
              <div class="row"><span class="row-label">Telefon</span><span class="row-val">{phone}</span></div>
              <div class="row"><span class="row-label">Kullanım Amacı</span><span class="row-val">{purpose}</span></div>
              <div class="row"><span class="row-label">Durum</span><span class="row-val"><span class="badge">✓ Aktif Kayıt</span></span></div>
            </div>
            <p style="color:#94A3B8;font-size:13px;">
              Giriş bilgilerinizi ve şifrenizi güvenli bir yerde saklayınız. Herhangi bir sorunuzda destek ekibimizle iletişime geçebilirsiniz.
            </p>
          </div>
          <div class="footer">
            © 2026 AYEC Pro — Tüm Hakları Saklıdır.<br>
            Destek: <a href="mailto:destek@ayecpro.com" style="color:#60A5FA;">destek@ayecpro.com</a><br>
            <a href="https://www.ayecpro.com">www.ayecpro.com</a>
          </div>
        </div>
        </body>
        </html>
        """
        w_cust = MailWorker(
            recipient=user_email,
            subject=f"\U0001f389 AYEC Pro Kayd\u0131n\u0131z Ba\u015far\u0131yla Olu\u015fturuldu \u2014 {company_name}",
            body=customer_html,
            is_html=True,
            db=db,
        )
        w_cust.start()
        # Thread referansını canlı tut
        if not hasattr(MailWorker, "_active_threads"):
            MailWorker._active_threads = []
        MailWorker._active_threads.append(w_cust)

    # -------------------------------------------------------------
    # 2. YÖNETİCİYE GÖNDERİLECEK YENİ KAYIT BİLDİRİM MAİLİ
    # -------------------------------------------------------------
    admin_html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head><meta charset="UTF-8">
    <style>
      body{{font-family:'Segoe UI',Arial,sans-serif;background:#0F172A;margin:0;padding:0;color:#F8FAFC;}}
      .wrap{{max-width:600px;margin:30px auto;background:#1E293B;border-radius:16px;overflow:hidden;border:2px solid #EAB308;}}
      .header{{background:linear-gradient(135deg,#CA8A04,#EAB308);padding:30px;text-align:center;color:#0F172A;}}
      .header h1{{margin:0;font-size:24px;font-weight:800;}}
      .body{{padding:32px;}}
      .card{{background:#0F172A;border-radius:12px;padding:20px;border:1px solid #334155;margin:20px 0;}}
      .row{{display:flex;justify-content:space-between;border-bottom:1px solid #334155;padding:10px 0;font-size:13px;}}
      .row:last-child{{border-bottom:none;}}
      .row-label{{color:#94A3B8;font-weight:600;}}
      .row-val{{color:#F8FAFC;font-weight:700;}}
    </style>
    </head>
    <body>
    <div class="wrap">
      <div class="header">
        <h1>🔔 YENİ MÜŞTERİ KAYDI BİLDİRİMİ</h1>
        <p style="margin:4px 0 0;font-size:13px;font-weight:600;">AYEC Pro Sistem Bildirimi</p>
      </div>
      <div class="body">
        <p style="font-size:15px;color:#F8FAFC;">Yeni bir müşteri AYEC Pro yazılımına kayıt oldu!</p>
        <div class="card">
          <div class="row"><span class="row-label">Firma Adı:</span><span class="row-val">{company_name}</span></div>
          <div class="row"><span class="row-label">Yetkili / Ad Soyad:</span><span class="row-val">{full_name}</span></div>
          <div class="row"><span class="row-label">E-posta:</span><span class="row-val">{user_email}</span></div>
          <div class="row"><span class="row-label">Telefon:</span><span class="row-val">{phone}</span></div>
          <div class="row"><span class="row-label">Sektör / Kullanım:</span><span class="row-val">{purpose}</span></div>
          <div class="row"><span class="row-label">Lisans Bilgisi:</span><span class="row-val">{license_info}</span></div>
          <div class="row"><span class="row-label">Kayıt Tarihi:</span><span class="row-val">{reg_time}</span></div>
        </div>
      </div>
    </div>
    </body>
    </html>
    """

    for admin_email in admin_emails:
        if admin_email and "@" in admin_email:
            w_admin = MailWorker(
                recipient=admin_email,
                subject=f"\U0001f514 YEN\u0130 KAYIT B\u0130LD\u0130R\u0130M\u0130: {company_name} ({full_name})",
                body=admin_html,
                is_html=True,
                db=db,
            )
            w_admin.start()
            if not hasattr(MailWorker, "_active_threads"):
                MailWorker._active_threads = []
            MailWorker._active_threads.append(w_admin)
