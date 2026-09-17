# -*- coding: utf-8 -*-

import sqlite3
import threading
from datetime import datetime

import requests
from PyQt6.QtCore import QThread

from src.utils.logger import logger
from src.utils.path_helper import PathHelper


class TelegramWorker(QThread):
    def __init__(self, token, db_path):
        super().__init__()
        self.token = token
        self.db_path = db_path
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.running = True
        self._stop_event = threading.Event()

    def log(self, msg):
        try:
            log_file = PathHelper.get_log_path("bot_debug.txt")
            with open(log_file, "a", encoding="utf-8") as handle:
                handle.write(f"{datetime.now()}: {msg}\n")
            logger.info(msg)
        except Exception as exc:
            logger.error("Telegram worker log write error: %s", exc)

    def _pause(self, seconds):
        self._stop_event.wait(seconds)

    def run(self):
        self.log("Telegram Worker Started")
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            while self.running and not self._stop_event.is_set():
                try:
                    updates = self.get_updates()
                    for update in updates:
                        self.offset = update["update_id"] + 1

                        if "message" in update:
                            self.process_message(cursor, conn, update["message"])
                        elif "edited_message" in update:
                            self.process_message(cursor, conn, update["edited_message"])

                    self._pause(2)
                except Exception as exc:
                    self.log(f"Telegram cycle error: {exc}")
                    self._pause(5)
        except Exception as exc:
            self.log(f"Telegram connection failed: {exc}")
        finally:
            if conn:
                conn.close()
            self.log("Telegram Worker Stopped")

    def stop(self):
        self.running = False
        self._stop_event.set()
        self.wait()

    def get_updates(self):
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self.offset, "timeout": 10}
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
            self.log(f"API Error: {data}")
        except Exception as exc:
            self.log(f"Network Error: {exc}")
        return []

    def process_message(self, cursor, conn, message):
        user = message.get("from", {})
        username = user.get("username")

        txt = message.get("text", "")
        self.log(f"Mesaj alindi: {username} - Text: {txt[:20]}...")

        edited_message = message.get("edited_message") or {}
        location = message.get("location") or edited_message.get("location")

        if location:
            lat = location.get("latitude")
            lng = location.get("longitude")
            self.log(f"Konum tespit edildi: {lat}, {lng} (User: {username})")

            if username:
                self.update_location(cursor, conn, username, lat, lng)
            else:
                self.log("Kullanici adi yok. Ayarlardan gizlilik veya username bilgisini kontrol edin.")
        else:
            self.log("Mesajda konum yok.")

    def update_location(self, cursor, conn, username, lat, lng):
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            query = """
                UPDATE personnel
                SET lat=?, lng=?, last_seen=?, status='Gorevde'
                WHERE telegram_username = ? OR telegram_username = ?
            """
            username_clean = username.replace("@", "").lower()
            username_at = f"@{username_clean}"

            cursor.execute(query, (lat, lng, now, username_at, username_clean))
            if cursor.rowcount > 0:
                conn.commit()
                self.log(f"Veritabani guncellendi: {username}")
            else:
                self.log(
                    f"Database eslesme hatasi: '{username}' bulunamadi. Personel kartina '{username_at}' ekleyin."
                )
        except Exception as exc:
            self.log(f"DB update error: {exc}")
