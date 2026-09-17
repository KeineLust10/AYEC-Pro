# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self, db):
        self.db = db

    def send_email(self, to_email, subject, body):
        smtp_server = self.db.get_setting("smtp_server")
        smtp_port = self.db.get_setting("smtp_port")
        smtp_email = self.db.get_setting("smtp_email")
        smtp_password = self.db.get_setting("smtp_password")

        if not all([smtp_server, smtp_port, smtp_email, smtp_password]):
            return False, "SMTP ayarları eksik. Lütfen Ayarlar menüsünden yapılandırın."

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
            server.login(smtp_email, smtp_password)
            text = msg.as_string()
            server.sendmail(smtp_email, to_email, text)
            server.quit()
            return True, "E-posta başarıyla gönderildi."
        except Exception as e:
            return False, f"E-posta gönderme hatası: {str(e)}"
