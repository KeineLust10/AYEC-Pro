# -*- coding: utf-8 -*-

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.path_helper import PathHelper


class DatabaseLegacyPart2Mixin:
    def add_bank_account(self, bank_name, branch_name, account_name, account_no, iban, initial_balance=0.0):
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.create_bank_accounts_table()

            self.cursor.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in self.cursor.fetchall()]

            def pick_col(candidates):
                for c in candidates:
                    if c in cols:
                        return c
                return None

            insert_cols = []
            values = []

            bank_col = pick_col(["bank_name", "bank"])
            if bank_col:
                insert_cols.append(bank_col)
                values.append(bank_name)

            branch_col = pick_col(["branch_name", "branch_code", "branch"])
            if branch_col:
                insert_cols.append(branch_col)
                values.append(branch_name)

            acc_name_col = pick_col(["account_name", "account_holder", "name"])
            if acc_name_col:
                insert_cols.append(acc_name_col)
                values.append(account_name)

            acc_no_col = pick_col(["account_no", "account_number", "account_no"])
            if acc_no_col:
                insert_cols.append(acc_no_col)
                values.append(account_no)

            iban_col = pick_col(["iban"])
            if iban_col:
                insert_cols.append(iban_col)
                values.append(iban)

            created_col = pick_col(["created_at"])
            if created_col:
                insert_cols.append(created_col)
                values.append(now)

            balance_col = pick_col(["current_balance"])
            if balance_col:
                insert_cols.append(balance_col)
                values.append(initial_balance or 0.0)

            if not insert_cols:
                return False

            placeholders = ", ".join(["?"] * len(insert_cols))
            col_list = ", ".join(insert_cols)
            self.cursor.execute(
                f"INSERT INTO bank_accounts ({col_list}) VALUES ({placeholders})",
                tuple(values),
            )
            self.conn.commit()
            
            # --- EKSİK KAPATMA / FİNANS KAYDI ---
            try:
                account_id = self.cursor.lastrowid
                init_bal = float(initial_balance or 0.0)
                if init_bal > 0:
                    desc_str = f"Hesap Açılış Bakiyesi: {bank_name} - {account_name}"
                    try:
                        self.add_transaction_extended(
                            type="Gelir",
                            category="Sermaye / Açılış",
                            amount=init_bal,
                            description=desc_str,
                            date=now.split(" ")[0],
                            payment_method="Banka",
                            bank_account_id=account_id
                        )
                    except Exception:
                        self.add_transaction(
                            t_type="Gelir",
                            category="Sermaye / Açılış",
                            amount=init_bal,
                            description=desc_str,
                            payment_method="Banka",
                            currency="TRY"
                        )
            except Exception as e:
                logger.warning(f"Opening balance transaction failed: {e}")

            try:
                from src.utils.audit_logger import get_audit_logger
                audit = get_audit_logger(self)
                audit.log_action("bank_accounts", "INSERT", f"{bank_name} | {account_name} | {account_no} | {iban} | {initial_balance or 0.0}")
            except Exception as e:
                logger.warning(f"Audit log failed for bank add: {e}")
            return True
        except Exception as e:
            logger.error(f"Bank add error: {e}")
            return False


    def get_bank_accounts(self):
        self.create_bank_accounts_table()
        self.cursor.execute("PRAGMA table_info(bank_accounts)")
        cols = [r[1] for r in self.cursor.fetchall()]
        deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
        query = "SELECT * FROM bank_accounts"
        if deleted_col:
            query += f" WHERE {deleted_col}=0 OR {deleted_col} IS NULL"
        query += " ORDER BY id DESC"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        def idx(name):
            try:
                return cols.index(name)
            except ValueError:
                return None

        def pick(row, *names):
            for n in names:
                i = idx(n)
                if i is None:
                    continue
                v = row[i]
                if v is None:
                    continue
                s = str(v).strip()
                if s != "":
                    return v
            for n in names:
                i = idx(n)
                if i is None:
                    continue
                v = row[i]
                if v is not None:
                    return v
            return None

        out = []
        for r in rows:
            rid = pick(r, "id")
            bank = pick(r, "bank_name", "bank")
            branch = pick(r, "branch_name", "branch_code", "branch")
            acc_name = pick(r, "account_name", "account_holder", "name")
            acc_no = pick(r, "account_no", "account_number", "account_no")
            iban = pick(r, "iban")
            balance = pick(r, "current_balance")
            is_active = pick(r, "is_active", "active")
            created_at = pick(r, "created_at", "created")
            try:
                is_active_val = int(is_active) if is_active is not None else 1
            except Exception:
                is_active_val = 1
            try:
                balance_val = float(balance) if balance is not None else 0.0
            except Exception:
                balance_val = 0.0
            out.append((rid, bank, branch, acc_name, acc_no, iban, balance_val, is_active_val, created_at))

        return out


    def set_bank_account_active(self, account_id, is_active):
        try:
            self.create_bank_accounts_table()
            self.cursor.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in self.cursor.fetchall()]
            col = "is_active" if "is_active" in cols else ("active" if "active" in cols else None)
            if not col:
                return False
            safe_col = self._safe_identifier(col)
            self.cursor.execute(
                "UPDATE bank_accounts SET {column_name}=? WHERE id=?".format(column_name=safe_col),
                (1 if is_active else 0, account_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Bank active set error: {e}")
            return False


    def update_bank_account(self, account_id, bank_name, branch_name, account_name, account_no, iban, current_balance=None):
        try:
            self.create_bank_accounts_table()
            self.cursor.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in self.cursor.fetchall()]

            def pick_col(candidates):
                for c in candidates:
                    if c in cols:
                        return c
                return None

            updates = []
            values = []

            bank_col = pick_col(["bank_name", "bank"])
            if bank_col:
                # Validate column name to prevent SQL injection
                if not bank_col.replace('_', '').isalnum():
                    logger.error(f"Invalid bank column name: {bank_col}")
                    return False
                updates.append(f"{self._safe_identifier(bank_col)}=?")
                values.append(bank_name)

            branch_col = pick_col(["branch_name", "branch_code", "branch"])
            if branch_col:
                # Validate column name to prevent SQL injection
                if not branch_col.replace('_', '').isalnum():
                    logger.error(f"Invalid branch column name: {branch_col}")
                    return False
                updates.append(f"{self._safe_identifier(branch_col)}=?")
                values.append(branch_name)

            acc_name_col = pick_col(["account_name", "account_holder", "name"])
            if acc_name_col:
                # Validate column name to prevent SQL injection
                if not acc_name_col.replace('_', '').isalnum():
                    logger.error(f"Invalid account name column name: {acc_name_col}")
                    return False
                updates.append(f"{self._safe_identifier(acc_name_col)}=?")
                values.append(account_name)

            acc_no_col = pick_col(["account_no", "account_number", "account_no"])
            if acc_no_col:
                # Validate column name to prevent SQL injection
                if not acc_no_col.replace('_', '').isalnum():
                    logger.error(f"Invalid account number column name: {acc_no_col}")
                    return False
                updates.append(f"{self._safe_identifier(acc_no_col)}=?")
                values.append(account_no)

            iban_col = pick_col(["iban"])
            if iban_col:
                # Validate column name to prevent SQL injection
                if not iban_col.replace('_', '').isalnum():
                    logger.error(f"Invalid IBAN column name: {iban_col}")
                    return False
                updates.append(f"{self._safe_identifier(iban_col)}=?")
                values.append(iban)

            balance_col = pick_col(["current_balance"])
            if balance_col and current_balance is not None:
                # Validate column name to prevent SQL injection
                if not balance_col.replace('_', '').isalnum():
                    logger.error(f"Invalid balance column name: {balance_col}")
                    return False
                updates.append(f"{self._safe_identifier(balance_col)}=?")
                values.append(current_balance)

            if not updates:
                return False

            # Validate all update clauses to prevent SQL injection
            for update in updates:
                if not update.replace('_', '').replace('=', '').replace('?', '').isalnum():
                    logger.error(f"Invalid update clause: {update}")
                    return False

            values.append(account_id)
            self.cursor.execute(
                "UPDATE bank_accounts SET {assignments} WHERE id=?".format(
                    assignments=", ".join(updates)
                ),
                tuple(values),
            )
            self.conn.commit()
            try:
                from src.utils.audit_logger import get_audit_logger
                audit = get_audit_logger(self)
                audit.log_action("bank_accounts", "UPDATE", f"ID {account_id} güncellendi")
            except Exception as e:
                logger.warning(f"Audit log failed for bank update: {e}")
            return True
        except Exception as e:
            logger.error(f"Bank update error: {e}")
            return False


    def delete_bank_account(self, account_id):
        self.create_bank_accounts_table()
        details = ""
        try:
            self.cursor.execute("SELECT bank_name, account_holder, account_number, iban FROM bank_accounts WHERE id=?", (account_id,))
            row = self.cursor.fetchone()
            if row:
                details = f"{row[0]} | {row[1]} | {row[2]} | {row[3]}"
        except Exception:
            details = ""
        self.soft_delete_record("bank_accounts", "id", account_id)
        try:
            from src.utils.audit_logger import get_audit_logger
            audit = get_audit_logger(self)
            audit.log_action("bank_accounts", "DELETE", f"ID {account_id} {details}".strip())
        except Exception as e:
            logger.warning(f"Audit log failed for bank delete: {e}")


    def get_bank_account_by_id(self, account_id):
        try:
            self.create_bank_accounts_table()
            query = "SELECT * FROM bank_accounts WHERE id=?"
            try:
                cols = self._get_table_columns("bank_accounts")
                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                if deleted_col:
                    query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            except Exception:
                pass
            self.cursor.execute(query, (account_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Bank get error: {e}")
            return None


    def update_bank_balance(self, account_id, delta, cursor=None):
        try:
            if cursor is None:
                self.create_bank_accounts_table()
            cur = cursor or self.conn.cursor()
            cur.execute("SELECT current_balance FROM bank_accounts WHERE id=?", (account_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Bank account not found: {account_id}")
            current = 0.0
            try:
                current = float(row[0] or 0)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid bank balance for account {account_id}"
                ) from exc
            new_balance = current + float(delta or 0)
            cur.execute("UPDATE bank_accounts SET current_balance=? WHERE id=?", (new_balance, account_id))
            if cur.rowcount != 1:
                raise RuntimeError(
                    f"Bank balance update affected {cur.rowcount} rows"
                )
            if cursor is None:
                self.conn.commit()
            return new_balance
        except Exception as e:
            logger.error(f"Bank balance update error: {e}")
            return None


    def add_bank_transfer(self, from_account_id, to_account_id, amount, description="", date=None, payment_method=None):
        try:
            if from_account_id == to_account_id:
                return False
            amount_val = float(amount or 0)
            if amount_val <= 0:
                return False
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(accounting)")
            cols = [r[1] for r in cur.fetchall()]
            def has_col(name):
                return name in cols
            insert_cols = ["type", "category", "amount", "description", "date", "created_at"]
            if has_col("payment_method"):
                insert_cols.append("payment_method")
            if has_col("bank_account_id"):
                insert_cols.append("bank_account_id")
            if has_col("related_account_id"):
                insert_cols.append("related_account_id")
            
            # Validate all column names to prevent SQL injection
            for col in insert_cols:
                if not col.replace('_', '').isalnum():
                    logger.error(f"Invalid column name in INSERT: {col}")
                    return False
            
            placeholders = ", ".join(["?"] * len(insert_cols))
            col_list = ", ".join(self._safe_identifier(col) for col in insert_cols)
            def build_values(category, bank_id, related_id):
                values = ["Transfer", category, amount_val, description, date, created]
                if has_col("payment_method"):
                    values.append(payment_method or "Banka")
                if has_col("bank_account_id"):
                    values.append(bank_id)
                if has_col("related_account_id"):
                    values.append(related_id)
                return values
            cur.execute(
                "INSERT INTO accounting ({columns}) VALUES ({placeholders})".format(
                    columns=col_list,
                    placeholders=placeholders,
                ),
                tuple(build_values("Transfer Çıkış", from_account_id, to_account_id)),
            )
            cur.execute(
                "INSERT INTO accounting ({columns}) VALUES ({placeholders})".format(
                    columns=col_list,
                    placeholders=placeholders,
                ),
                tuple(build_values("Transfer Giriş", to_account_id, from_account_id)),
            )
            self.update_bank_balance(from_account_id, -amount_val, cursor=cur)
            self.update_bank_balance(to_account_id, amount_val, cursor=cur)
            self.conn.commit()
            try:
                from src.utils.audit_logger import get_audit_logger
                logger_obj = get_audit_logger(self)
                logger_obj.log_action("bank_accounts", "TRANSFER", f"{from_account_id} -> {to_account_id} | {amount_val}")
            except Exception as e:
                logger.warning(f"Audit log failed for bank transfer: {e}")
            return True
        except Exception as e:
            logger.error(f"Bank transfer error: {e}")
            return False



    def get_setting(self, key, default=""):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = self.cursor.fetchone()
        return row[0] if row else default


    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()


    def _get_next_sequence_value(self, prefix_key, counter_key, default_prefix):
        try:
            prefix = self.get_setting(prefix_key, default_prefix)
        except Exception:
            prefix = default_prefix
        try:
            raw = self.get_setting(counter_key, "1")
            current = int(raw) if str(raw).isdigit() else 1
        except Exception:
            current = 1
        next_val = current + 1
        try:
            self.set_setting(counter_key, str(next_val))
        except Exception:
            pass
        return f"{prefix}{current}"


    def get_next_job_number(self):
        return self._get_next_sequence_value("job_number_prefix", "job_number_next", "JOB")


    def get_next_service_number(self):
        return self._get_next_sequence_value("service_number_prefix", "service_number_next", "SRV")


    def get_next_reference_number(self):
        return self._get_next_sequence_value("reference_number_prefix", "reference_number_next", "REF")


    def get_templates(self):
        self.cursor.execute("SELECT * FROM whatsapp_templates")
        return self.cursor.fetchall()


    def add_template(self, name, content):
        self.cursor.execute("INSERT INTO whatsapp_templates (name, content) VALUES (?, ?)", (name, content))
        self.conn.commit()


    def delete_template(self, t_id):
        self.cursor.execute("DELETE FROM whatsapp_templates WHERE id=?", (t_id,))
        self.conn.commit()



    def create_customers_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT,
                type TEXT, -- Bireysel, Kurumsal
                tax_id TEXT,
                tax_no TEXT,
                address TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()
    

    def update_customers_schema(self):
        """Customers tablosuna yeni kolonlar ekle"""
        customer_columns = [
            ("phone2", "TEXT"),
            ("company_name", "TEXT"),
            ("tc_no", "TEXT"),
            ("tax_number", "TEXT"),
            ("tax_no", "TEXT"),
            ("tax_office", "TEXT"),
            ("district", "TEXT"),
            ("city", "TEXT"),
            ("neighborhood", "TEXT"),
            ("street", "TEXT"),
            ("zip_code", "TEXT"),
            ("notes", "TEXT"),
            ("term_days", "INTEGER DEFAULT 0"),
            ("limit_amount", "REAL DEFAULT 0"),
            ("sms_enabled", "INTEGER DEFAULT 1"),
            ("is_problematic", "INTEGER DEFAULT 0"),
            ("latitude", "REAL DEFAULT 0"),
            ("longitude", "REAL DEFAULT 0"),
            ("service_type", "TEXT"),
            ("commission_rate", "REAL DEFAULT 0"),
            ("is_deleted", "INTEGER DEFAULT 0")
        ]
        
        try:
            self.cursor.execute("PRAGMA table_info(customers)")
            existing_cols = [row[1] for row in self.cursor.fetchall()]
            
            for col_name, col_type in customer_columns:
                if col_name not in existing_cols:
                    logger.info(f"Customers tablosuna kolon ekleniyor: {col_name}")
                    safe_col = self._safe_identifier(col_name)
                    self.cursor.execute(
                        "ALTER TABLE customers ADD COLUMN {column_name} {col_type}".format(
                            column_name=safe_col,
                            col_type=col_type,
                        )
                    )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Customers schema update error: {e}")


    def add_customer(self, data):
        try:
            keys = ", ".join(self._safe_identifier(key) for key in data.keys())
            values_ph = ", ".join(["?"] * len(data))
            values = tuple(data.values())
            sql = "INSERT INTO customers (" + keys + ") VALUES (" + values_ph + ")"
            self.cursor.execute(sql, values)
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Customer add error: {e}")
            return None


    def get_customer_id_by_name(self, name):
        try:
            q = f"%{str(name).strip()}%"
            self.cursor.execute("SELECT id FROM customers WHERE name LIKE ? ORDER BY id LIMIT 1", (q,))
            row = self.cursor.fetchone()
            return row[0] if row else None
        except Exception:
            return None


    def get_customer_financial_summary(self, customer_id):
        try:
            return self.get_customer_balance(customer_id)
        except Exception:
            return 0.0


    def get_customer_loyalty_score(self, customer_id):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM devices WHERE customer_id = ?", (customer_id,))
            count = int(self.cursor.fetchone()[0] or 0)
            self.cursor.execute("""
                SELECT SUM(try_equivalent) FROM currency_transactions
                WHERE customer_id = ? AND transaction_type = 'DEBIT'
            """, (customer_id,))
            total = float(self.cursor.fetchone()[0] or 0.0)
            if total <= 0:
                self.cursor.execute("SELECT tracking_no, labor_cost FROM devices WHERE customer_id = ?", (customer_id,))
                devices = self.cursor.fetchall()
                for tno, labor in devices:
                    total += float(labor or 0.0)
                    self.cursor.execute("SELECT SUM(price) FROM used_parts WHERE tracking_no = ?", (tno,))
                    p = self.cursor.fetchone()[0] or 0.0
                    total += float(p or 0.0)
                self.cursor.execute("SELECT SUM(total_amount) FROM customer_services WHERE customer_id = ?", (customer_id,))
                s = self.cursor.fetchone()[0] or 0.0
                total += float(s or 0.0)
            score = (count // 2) + (int(total) // 5000)
            if score <= 0:
                return 1
            return min(int(score), 5)
        except Exception:
            return 1


    def get_discount_advice(self, customer_id):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM devices WHERE customer_id = ?", (customer_id,))
            total_services = int(self.cursor.fetchone()[0] or 0)
            self.cursor.execute("""
                SELECT SUM(try_equivalent) FROM currency_transactions
                WHERE customer_id = ? AND transaction_type = 'DEBIT'
            """, (customer_id,))
            total_spent = float(self.cursor.fetchone()[0] or 0.0)
            if total_spent <= 0:
                self.cursor.execute("SELECT tracking_no, labor_cost FROM devices WHERE customer_id = ?", (customer_id,))
                devices = self.cursor.fetchall()
                for tno, labor in devices:
                    total_spent += float(labor or 0.0)
                    self.cursor.execute("SELECT SUM(price) FROM used_parts WHERE tracking_no = ?", (tno,))
                    p = self.cursor.fetchone()[0] or 0.0
                    total_spent += float(p or 0.0)
                self.cursor.execute("SELECT SUM(total_amount) FROM customer_services WHERE customer_id = ?", (customer_id,))
                s = self.cursor.fetchone()[0] or 0.0
                total_spent += float(s or 0.0)
            if total_services >= 5 or total_spent >= 10000:
                return "VIP", "Bu müşterimiz çok sadık. %15'e kadar indirim yapmanızda bir sakınca görmüyorum."
            elif total_services >= 2:
                return "Standart", "Bu müşterimiz düzenli geliyor. %5 veya %10'luk bir jest yapabilirsiniz."
            else:
                return "Yeni", "Bu müşterimizin ilk işlemleri. İndirim yerine bir sonraki işlem için kupon verebiliriz."
        except Exception:
            return "Bilinmiyor", "Analiz yapılamadı."


    def delete_customer(self, customer_id):
        try:
            return self.soft_delete_record("customers", "id", customer_id)
        except Exception as e:
            logger.error(f"Customer delete error: {e}")
            return False


    def get_customer_history_summary(self, customer_name):
        """Müşteriye özel özet istatistikler ve geçmiş bilgisi getirir."""
        try:
            # 1. Temel Sayılar
            self.cursor.execute("""
                SELECT COUNT(*), SUM(price), MAX(entry_date) 
                FROM devices 
                WHERE customer_name = ?
            """, (customer_name,))
            job_count, total_spend, last_visit = self.cursor.fetchone()
            
            if not job_count:
                return None
                
            # 2. Cihaz Geçmişi (Tekrar eden cihaz var mı?)
            self.cursor.execute("""
                SELECT device_brand, device_model, COUNT(*) as visit_count 
                FROM devices 
                WHERE customer_name = ?
                GROUP BY device_brand, device_model
                ORDER BY visit_count DESC
            """, (customer_name,))
            device_history = self.cursor.fetchall()
            
            # 3. Son 3 İşlem
            self.cursor.execute("""
                SELECT device_brand, device_model, status, entry_date 
                FROM devices 
                WHERE customer_name = ?
                ORDER BY entry_date DESC LIMIT 3
            """, (customer_name,))
            recent_jobs = self.cursor.fetchall()
            
            return {
                "name": customer_name,
                "job_count": job_count,
                "total_spend": total_spend or 0,
                "last_visit": last_visit,
                "device_history": device_history,
                "recent_jobs": recent_jobs
            }
        except Exception as e:
            logger.error(f"Customer history summary error: {e}")
            return None


    def get_customer_history(self, customer_name):
        # Müşteriye ait cihaz geçmişini getir
        try:
            self.cursor.execute("SELECT * FROM devices WHERE customer_name=? ORDER BY entry_date DESC", (customer_name,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Customer history error: {e}")
            return []


    def update_parts_schema(self):
        # Parts tablosuna yeni kolonlar ekle
        try:
            self.cursor.execute("PRAGMA table_info(parts)")
            cols = [row[1] for row in self.cursor.fetchall()]
            
            if "part_name" not in cols:
                # name varsa part_name'i name'den al, yoksa boş ekle
                if "name" in cols:
                    self.cursor.execute("ALTER TABLE parts ADD COLUMN part_name TEXT")
                    self.cursor.execute("UPDATE parts SET part_name = name")
                else:
                    self.cursor.execute("ALTER TABLE parts ADD COLUMN part_name TEXT")
            if "name" not in cols:
                if "part_name" in cols:
                    self.cursor.execute("ALTER TABLE parts ADD COLUMN name TEXT")
                    self.cursor.execute("UPDATE parts SET name = part_name")
                else:
                    self.cursor.execute("ALTER TABLE parts ADD COLUMN name TEXT")

            if "shelf_number" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN shelf_number TEXT")
            if "code" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN code TEXT")
            if "category" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN category TEXT DEFAULT 'Genel'")
            if "description" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN description TEXT")
            if "created_at" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN created_at TEXT")
            if "min_stock" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN min_stock INTEGER DEFAULT 5")
            if "purchase_price" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN purchase_price REAL DEFAULT 0")
            if "currency" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN currency TEXT DEFAULT 'TRY'")
            if "is_deleted" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN is_deleted INTEGER DEFAULT 0")
            if "deleted_at" not in cols:
                self.cursor.execute("ALTER TABLE parts ADD COLUMN deleted_at TEXT")
            self.conn.commit()
        except Exception as e:
            logger.error(f"Parts schema update error: {e}")


    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT UNIQUE,
                customer_name TEXT,
                device_brand TEXT,
                device_model TEXT,
                serial_no TEXT,
                fault_category TEXT,
                urgency TEXT,
                status TEXT,
                entry_date TEXT,
                estimated_date TEXT,
                price REAL DEFAULT 0,
                device_type TEXT,
                imei TEXT,
                pattern_lock TEXT,
                customer_type TEXT,
                customer_tax_id TEXT,
                customer_contact TEXT,
                fault_description TEXT,
                photo_path TEXT,
                device_password TEXT,
                approval_status TEXT DEFAULT 'Bekleme'
            )
        """)
        self.conn.commit()


    def get_part_by_barcode(self, barcode):
        """Barkoda göre parça/ürün bul"""
        try:
            self.cursor.execute("SELECT * FROM parts WHERE barcode=? OR code=?", (barcode, barcode))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Part by barcode error: {e}")
            return None


    def create_parts_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                part_name TEXT,
                stock INTEGER,
                price REAL,
                purchase_price REAL DEFAULT 0,
                currency TEXT DEFAULT 'TRY',
                code TEXT,
                barcode TEXT,
                category TEXT DEFAULT 'Genel'
            )
        """)
        # Ensure backwards compatibility for both name and part_name
        self.update_parts_schema()

    # Combined add_part moved to line ~2659 for consistency with StockMixin


    def get_all_parts(self):
        try:
            query = "SELECT * FROM parts"
            try:
                cols = self._get_table_columns("parts")
                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                if deleted_col:
                    query += f" WHERE {deleted_col}=0 OR {deleted_col} IS NULL"
            except Exception:
                pass
            query += " ORDER BY name"
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get parts: {e}")
            return []


    def get_part_by_barcode(self, barcode):
        try:
            query = "SELECT * FROM parts WHERE code = ?"
            params = [barcode]
            try:
                cols = self._get_table_columns("parts")
                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                if deleted_col:
                    query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            except Exception:
                pass
            self.cursor.execute(query, params)
            part = self.cursor.fetchone()
            if not part:
                # Fallback to ID search
                if barcode.isdigit():
                    query = "SELECT * FROM parts WHERE id = ?"
                    params = [barcode]
                    try:
                        cols = self._get_table_columns("parts")
                        deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                        if deleted_col:
                            query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
                    except Exception:
                        pass
                    self.cursor.execute(query, params)
                    part = self.cursor.fetchone()
            return part
        except Exception as e:
            logger.error(f"Part lookup by barcode failed for {barcode}: {e}")
            return None


    def create_logs_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_tracking_no TEXT,
                log_type TEXT, -- 'Customer' or 'Technician' or 'System'
                message TEXT,
                created_at TEXT,
                user TEXT
            )
        """)
        # LoggingMixin 'logs' tablosunu kullanıyor - uyumluluk için oluştur
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                log_type TEXT,
                message TEXT,
                user TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()


    def create_report_tables(self):
        # Randevu Tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                phone TEXT,
                date TEXT,
                time TEXT,
                description TEXT,
                status TEXT DEFAULT 'Bekliyor', -- Bekliyor, Tamamlandı, İptal
                created_at TEXT
            )
        """)
        
        # Hatırlatıcı Tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                message TEXT,
                due_date TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        self.conn.commit()

        # Kullanılan Parçalar (Maliyet Takibi)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS used_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                part_id INTEGER,
                part_name TEXT,
                price REAL,
                quantity INTEGER DEFAULT 1,
                purchase_price_snapshot REAL DEFAULT 0,
                created_at TEXT
            )
        """)
        
        # Test Sonuçları
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                test_name TEXT,
                result TEXT, -- Geçti, Kaldı, Test Edilmedi, veya ölçüm değeri
                note TEXT,
                technician TEXT,
                test_date TEXT
            )
        """)
        self.conn.commit()


    def add_device_test(self, tracking_no, test_name, result, note="", technician=""):
        try:
            test_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO device_tests (tracking_no, test_name, result, note, technician, test_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tracking_no, test_name, result, note, technician, test_date))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add device test error: {e}")
            return False


    def get_device_tests(self, tracking_no):
        try:
            self.cursor.execute("SELECT test_name, result, note, test_date FROM device_tests WHERE tracking_no=? ORDER BY id DESC", (tracking_no,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Device tests fetch error for {tracking_no}: {e}")
            return []


