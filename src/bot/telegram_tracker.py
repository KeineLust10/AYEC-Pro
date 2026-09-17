import os
import sqlite3
import sys
import threading
from datetime import datetime

import requests

from src.utils.logger import logger

# --- CONFIGURATION ---
# 1. Telegram Bot Token'inizi buraya yapistirin
# Ornek: "123456789:ABCdefGHIjklMNOpqrsTUVwx_yz"
BOT_TOKEN = "BURAYA_TOKEN_YAZIN"

# 2. Veritabani yolu (otomatik bulmaya calisir)
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ayecpro.db",
)


class TelegramLocationTracker:
    def __init__(self, token, db_path):
        self.token = token
        self.db_path = db_path
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.conn = None
        self.cursor = None
        self._stop_event = threading.Event()

    def connect_db(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info("Veritabanina baglanildi: %s", self.db_path)
        except Exception as exc:
            logger.error("Veritabani hatasi: %s", exc)
            sys.exit(1)

    def _pause(self, seconds):
        self._stop_event.wait(seconds)

    def get_updates(self):
        """Telegram'dan yeni mesajlari al."""
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self.offset, "timeout": 30}
        try:
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
            logger.error("Telegram update error: %s", data)
        except Exception as exc:
            logger.error("Telegram baglanti hatasi: %s", exc)
            self._pause(5)
        return []

    def process_message(self, message):
        """Mesaji isle ve konumu kaydet."""
        user = message.get("from", {})
        username = user.get("username")
        edited_message = message.get("edited_message") or {}
        location = message.get("location") or edited_message.get("location")

        if location:
            lat = location.get("latitude")
            lng = location.get("longitude")
            logger.info("Konum geldi: %s (%s, %s)", username, lat, lng)
            if username:
                self.update_personnel_location(username, lat, lng)
            else:
                logger.warning("Kullanici adi yok, veritabani eslesmesi yapilamadi.")
        else:
            logger.info("Mesaj: %s - %s", message.get("text", "Icerik yok"), username)

    def update_personnel_location(self, username, lat, lng):
        """Veritabaninda personeli guncelle."""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            query = """
                UPDATE personnel
                SET lat=?, lng=?, last_seen=?, status='Gorevde'
                WHERE telegram_username = ? OR telegram_username = ?
            """
            username_clean = username.replace("@", "")
            username_at = f"@{username_clean}"
            self.cursor.execute(query, (lat, lng, now, username_at, username_clean))

            if self.cursor.rowcount > 0:
                self.conn.commit()
                logger.info("Personel guncellendi: %s", username)
            else:
                logger.warning(
                    "Eslesen personel bulunamadi: %s (Personel kartina Telegram kullanici adini ekleyin)",
                    username,
                )
        except Exception as exc:
            logger.error("Veritabani guncelleme hatasi: %s", exc)

    def run(self):
        logger.info("Telegram bot takip servisi baslatiliyor...")
        self.connect_db()
        logger.info("Telegram mesajlari dinleniyor...")

        while not self._stop_event.is_set():
            updates = self.get_updates()
            for update in updates:
                self.offset = update["update_id"] + 1
                if "message" in update:
                    self.process_message(update["message"])
                elif "edited_message" in update:
                    self.process_message(update["edited_message"])
            self._pause(1)


if __name__ == "__main__":
    if BOT_TOKEN == "BURAYA_TOKEN_YAZIN":
        logger.error("Lutfen dosyayi acip BOT_TOKEN kismina Telegram tokeninizi yapistirin.")
    else:
        tracker = TelegramLocationTracker(BOT_TOKEN, DB_PATH)
        tracker.run()
