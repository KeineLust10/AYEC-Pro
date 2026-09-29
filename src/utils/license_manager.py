# -*- coding: utf-8 -*-

import datetime
import math
import json
import requests
from src.utils.logger import logger

from src.utils.security_manager import SecurityManager

class LicenseManager:
    """
    Yazılım Lisanslama ve Aktivasyon Yönetimi
    - Donanım Kimliği (HWID) oluşturma
    - Lisans Anahtarı Doğrulama
    - Deneme Süresi Kontrolü
    """
    
    def __init__(self, db=None):
        self.db = db
        # SecurityManager'daki SALT ile aynı olmalı
        self.secret_salt = "AYEC_PRO_TEKNİK_SERVIS_2026_SECURE_SALT_!@#"

    def get_hwid(self):
        """Cihaza özel donanım kimliği üretir."""
        return SecurityManager.get_hwid()

    def validate_key(self, license_key):
        """
        Lisans anahtarını doğrular.
        Format: XXXX-XXXX-XXXX-XXXX
        Basit algoritma: Hash tabanlı kontrol (Gerçekte sunucu taraflı olmalı)
        """
        try:
            license_key = license_key.strip().upper()
            if len(license_key) != 19: # 4 chars * 4 groups + 3 dashes
                return False, "Geçersiz format"

            # Demo Key Logic for "Offline" Validation
            # Prefix: PRO- / ENT- / TRL-
            
            if license_key.startswith("DEMO-"):
                return True, "DEMO"
            
            if license_key.startswith("PROX-"):
                return True, "PRO"
                
            if license_key.startswith("ENTX-"):
                return True, "ENTERPRISE"
                
            # Todo: Implement real crypto check
            return False, "Geçersiz Anahtar"
        except Exception as e:
            return False, str(e)

    def create_trial_license(self):
        """Create a 15 day local trial license."""
        start_date = datetime.datetime.now()
        expiry_date = start_date + datetime.timedelta(days=15)
        
        license_data = {
            "license_type": "TRIAL",
            "encrypted_key": "TRIAL-VERSION-AUTO",
            "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "expiry_date": expiry_date.strftime("%Y-%m-%d %H:%M:%S"),
            "hwid": self.get_hwid(),
            "last_check_date": start_date.strftime("%Y-%m-%d %H:%M:%S")
        }
        return license_data

    def check_license_status(self):
        """Start a local 15 day trial only when no license record exists."""
        if not self.db:
            return {"status": "error", "message": "DB bağlantısı yok"}

        # Sütun adlarıyla sorgulama yapmak daha güvenlidir
        cols = self.db._get_table_columns("license_info") if hasattr(self.db, "_get_table_columns") else []
        
        query = "SELECT {columns} FROM license_info ORDER BY id DESC LIMIT 1".format(
            columns=", ".join(cols)
        )
        lic_row = self.db.cursor.execute(query).fetchone()
        
        if not lic_row:
            # First installation creates one local 15 day trial record.
            logger.info("Ilk kurulum algilandi. 15 gunluk deneme suresi baslatiliyor.")
            trial_data = self.create_trial_license()
            
            self.db.cursor.execute(
                "INSERT INTO license_info (encrypted_key, license_type, start_date, expiry_date, last_check_date, hwid) VALUES (?, ?, ?, ?, ?, ?)",
                (trial_data["encrypted_key"], trial_data["license_type"], trial_data["start_date"], 
                 trial_data["expiry_date"], trial_data["last_check_date"], trial_data["hwid"])
            )
            self.db.conn.commit()
            lic_row = self.db.cursor.execute(query).fetchone()

        if not lic_row:
            return {"status": "none", "message": "Lisans oluşturulamadı"}

        # Sütun adlarını ve değerlerini bir sözlükte birleştir
        lic = dict(zip(cols, lic_row))

        lic_type = lic.get("license_type")
        expiry_str = lic.get("expiry_date")
        hwid_db = lic.get("hwid")

        if not expiry_str:
            return {"status": "error", "message": "Lisans son kullanma tarihi bulunamadı."}

        # HWID Check
        current_hwid = self.get_hwid()
        if hwid_db != current_hwid and lic_type != "TRIAL":
             logger.warning(f"HWID Mismatch: DB={hwid_db} / SYS={current_hwid}")

        # Date Check
        try:
            expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                return {"status": "error", "message": f"Geçersiz tarih formatı: {expiry_str}"}
            
        now = datetime.datetime.now()
        last_check = None
        try:
            last_check = datetime.datetime.strptime(str(lic.get("last_check_date") or ""), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            last_check = None
        if last_check and now < last_check - datetime.timedelta(minutes=5):
            return {"status": "expired", "message": "Sistem saati geri alindigi icin lisans dogrulanamadi.", "type": lic_type}
        try:
            self.db.cursor.execute(
                "UPDATE license_info SET last_check_date=? WHERE id=?",
                (now.strftime("%Y-%m-%d %H:%M:%S"), lic.get("id")),
            )
            self.db.conn.commit()
        except Exception:
            logger.warning("License last check timestamp could not be updated.")
        remaining = expiry_date - now
        
        if remaining.total_seconds() <= 0:
            return {"status": "expired", "message": "Lisans süresi dolmuş. Lütfen lisans satın alın.", "type": lic_type}
            
        days_left = max(0, math.ceil(remaining.total_seconds() / 86400))
        return {
            "status": "active", 
            "message": f"Lisans Aktif ({remaining.days} gün kaldı)", 
            "type": lic_type,
            "days_left": days_left,
            "start_date": str(lic.get("start_date") or ""),
            "expiry_date": expiry_str,
        }
    def check_license_online(self, license_key=None):
        """Validate through the shared central signed entitlement endpoint."""
        try:
            client = LicenseApiClient(timeout=15)
            settings = self.db.get_settings() if self.db else {}
            client.configure_scope(
                tenant_id=settings.get("central_tenant_id", ""),
                installation_id=settings.get("central_installation_id", ""),
            )
            result = client.status_for_device(self._license_device_identity())
            return self.apply_server_entitlement(result)
        except Exception as error:
            logger.warning("Central license check deferred: %s", error)
            return False, "Central license check deferred; local state was preserved."

    def apply_server_entitlement(self, payload):
        access = dict(payload.get("access") or {})
        if not access.get("allowed"):
            if self.db.get_setting("license_key", "") == "SERVER-ENTITLEMENT":
                expired_text = (
                    datetime.datetime.now() - datetime.timedelta(seconds=1)
                ).strftime("%Y-%m-%d %H:%M:%S")
                try:
                    self.db.cursor.execute(
                        "UPDATE license_info SET expiry_date=?,last_check_date=? "
                        "WHERE encrypted_key='SERVER-ENTITLEMENT'",
                        (expired_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    )
                    self.db.conn.commit()
                    self.db.set_setting("is_licensed", "0")
                    self.db.set_setting("license_expires", expired_text)
                except Exception:
                    logger.exception("Inactive server entitlement could not be stored.")
            return False, str(access.get("message") or "Lisans henuz etkin degil.")
        license_type = str(access.get("license_type") or "").strip()
        license_start = str(access.get("license_start") or "").strip()
        raw_license_end = str(access.get("license_end") or "").strip()
        if license_type.casefold() in {"", "trial", "demo", "deneme"}:
            return False, "Sunucuda etkin bir lisans bulunamadi."
        is_lifetime = license_type.casefold() in {"lifetime", "suresiz", "sinirsiz"}
        if not raw_license_end and not is_lifetime:
            return False, "Sureli sunucu lisansinin bitis tarih ve saati bulunamadi."

        def normalize_datetime(value, fallback=""):
            text = str(value or "").strip()
            if not text:
                return fallback
            try:
                parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone().replace(tzinfo=None)
                return parsed.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return text.replace("T", " ").replace("+00:00", "")

        now_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        license_start = normalize_datetime(license_start, now_text)
        local_expiry = normalize_datetime(
            raw_license_end,
            "2099-12-31 23:59:59" if is_lifetime else "",
        )
        try:
            self.db.cursor.execute("DELETE FROM license_info")
            self.db.cursor.execute(
                "INSERT INTO license_info (encrypted_key, license_type, hwid, start_date, expiry_date, last_check_date) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "SERVER-ENTITLEMENT", license_type, self.get_hwid(),
                    license_start, local_expiry, now_text,
                ),
            )
            self.db.conn.commit()
            self.db.set_setting("is_licensed", "1")
            self.db.set_setting("license_key", "SERVER-ENTITLEMENT")
            self.db.set_setting(
                "license_code", str(access.get("license_code") or "")
            )
            self.db.set_setting("license_type", license_type)
            self.db.set_setting("license_started", license_start)
            self.db.set_setting("license_expires", "" if is_lifetime else local_expiry)
            self.db.set_setting(
                "license_updated_at", str(access.get("license_updated_at") or "")
            )
        except Exception as error:
            logger.exception("Server entitlement could not be stored: %s", error)
            return False, "Sunucu lisansi yerel kayda yazilamadi."
        return True, "Sunucu lisansi etkinlestirildi."

    def refresh_server_entitlement(self, identifier="", password="", tenant_id=""):
        try:
            from src.utils.license_api_client import LicenseApiClient

            client = LicenseApiClient(timeout=15)
            if identifier and password:
                payload = client.status_for_credentials(identifier, password, tenant_id)
            else:
                payload = client.status_for_device(self._license_device_identity())
            ok, message = self.apply_server_entitlement(payload)
            return ok, message, payload
        except Exception as error:
            logger.info("Server entitlement refresh unavailable: %s", error)
            return False, "Sunucu lisans bilgisine ulasilamadi.", {}

    def _license_device_identity(self):
        identity = {
            "hardware_id": self.get_hwid(),
            "company_name": "",
            "requester_email": "",
        }
        try:
            row = self.db.cursor.execute(
                "SELECT email,company_name FROM registration "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                if hasattr(row, "keys"):
                    identity["requester_email"] = str(row["email"] or "")
                    identity["company_name"] = str(row["company_name"] or "")
                else:
                    identity["requester_email"] = str(row[0] or "")
                    identity["company_name"] = str(row[1] or "")
        except Exception:
            pass
        if not identity["requester_email"]:
            for key in ("company_email", "admin_email", "email"):
                value = str(self.db.get_setting(key, "") or "").strip()
                if value:
                    identity["requester_email"] = value
                    break
        if not identity["company_name"]:
            identity["company_name"] = str(
                self.db.get_setting("company_name", "") or ""
            ).strip()
        return identity

    def start_delayed_license_check(self, callback):
        """5 dakika sonra lisans kontrolünü başlatır"""
        from PyQt6.QtCore import QTimer
        
        # User requested 5 mins (300,000 ms)
        delay_ms = 5 * 60 * 1000 
        
        QTimer.singleShot(delay_ms, lambda: self._run_async_check(callback))
        logger.info(f"🛡️ AYEC Pro Güvenlik Katmanı Aktif. ({5} dk sonra kontrol yapılacak)")

    def _run_async_check(self, callback):
        """İş parçacığında (thread) kontrol yapar ki UI donmasın"""
        import threading
        
        def job():
            # Önce yerel deneme süresi kontrolü (30 GÜN - Kullanıcı isteği: Lisans kontrolü yapılmasın)
            status = self.check_license_status()
            if status['status'] == 'active' and status.get('type') == 'TRIAL':
                logger.info(f"Deneme süreci aktif ({status.get('days_left')} gün). Sunucu kontrolü bypass edildi.")
                return

            license_key = self.db.get_setting("license_key", "TEST-AYEC-2026")
            if not license_key or license_key == "TEST-AYEC-2026": # Allow test if empty
                # Optional: log that we are using test key
                pass
            
            if not license_key:
                # Eğer anahtar yoksa deneme süreci bittiyse kilitle
                if status['status'] == 'expired':
                    callback(False, "Deneme süresi doldu. Lütfen lisans satın alın.")
                    return
                # Hala deneme süresindeyse OK (Zaten yukarıda return edildi ama garanti olsun)
                return

            ok, msg = self.check_license_online(license_key)
            callback(ok, msg)
            
        thread = threading.Thread(target=job, daemon=True)
        thread.start()
