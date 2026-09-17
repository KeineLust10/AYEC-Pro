import sys
import os
from PyQt6.QtCore import QCoreApplication, QTimer

# Adicionar o diretório src ao path para os imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.utils.mail_manager import MailWorker

def test_email():
    app = QCoreApplication(sys.argv)
    
    recipient = "gnnckrk@gmail.com" # Sending to self to test
    subject = "SMTP Test - AYEC Pro"
    body = "<h1>SMTP Testi</h1><p>Yeni uygulama sifresi ile gonderim basarili!</p>"
    
    print(f"Sending test email to {recipient}...")
    worker = MailWorker(recipient, subject, body, is_html=True)
    
    def on_finished(success, msg):
        if success:
            print(f"[OK] Email sent successfully: {msg}")
        else:
            print(f"[FAIL] Email sending failed: {msg}")
        app.quit()

    worker.finished.connect(on_finished)
    worker.start()
    
    # Timeout after 30 seconds
    QTimer.singleShot(30000, lambda: (print("[TIMEOUT] Email test timed out"), app.quit()))
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_email()
