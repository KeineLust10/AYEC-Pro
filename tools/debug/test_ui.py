import sys
import os

sys.path.insert(0, r"c:\Users\Pc\Desktop\yapay zeka\AYEC Pro")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.db.database import Database
from ModernDesktopApp import ModernDesktopApp

app = QApplication(sys.argv)
db = Database()

main_win = ModernDesktopApp(db=db)
main_win.showMaximized()

def capture_and_inspect():
    main_win.grab().save(r"C:\Users\Pc\.gemini\antigravity\brain\bf9998f0-936e-49f8-b563-086df4850e8a\screenshot.png")
    app.quit()

QTimer.singleShot(3000, capture_and_inspect)
app.exec()
