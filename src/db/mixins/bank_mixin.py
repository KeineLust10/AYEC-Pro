# -*- coding: utf-8 -*-

"""
Bank Mixin
Banka hesap yönetimi ile ilgili database metodları.
"""

from datetime import datetime
import re

from src.utils.logger import logger


class BankMixin:
    """Banka hesap bilgileri icin database metodlari."""
    @staticmethod
    def _is_safe_identifier(value):
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(value or "")))
    """Banka hesap bilgileri için database metodları."""

    def _audit_bank_action(self, action, details):
        try:
            from src.utils.audit_logger import get_audit_logger
            audit = get_audit_logger(self)
            audit.log_action("bank_accounts", action, details)
        except Exception:
            pass

    def add_bank_account(
        self,
        bank_name,
        branch_name,
        account_name,
        account_no,
        iban,
        initial_balance=0.0,
        currency="TRY",
    ):
        """Yeni banka hesabı ekle (legacy+new schema uyumlu)."""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.create_bank_accounts_table()
            cur = self.conn.cursor()

            cur.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in cur.fetchall()]

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

            acc_no_col = pick_col(["account_no", "account_number"])
            if acc_no_col:
                insert_cols.append(acc_no_col)
                values.append(account_no)

            iban_col = pick_col(["iban"])
            if iban_col:
                insert_cols.append(iban_col)
                values.append(iban)

            created_col = pick_col(["created_at", "created"])
            if created_col:
                insert_cols.append(created_col)
                values.append(now)

            currency_col = pick_col(["currency"])
            if currency_col:
                insert_cols.append(currency_col)
                values.append(str(currency or "TRY").upper())

            balance_col = pick_col(["current_balance"])
            if balance_col:
                insert_cols.append(balance_col)
                values.append(float(initial_balance or 0.0))

            if not insert_cols:
                logger.error("Bank add error: bank_accounts table has no expected columns")
                return False

            placeholders = ", ".join(["?"] * len(insert_cols))
            col_list = ", ".join(insert_cols)
            cur.execute(
                f"INSERT INTO bank_accounts ({col_list}) VALUES ({placeholders})",
                tuple(values),
            )
            self.conn.commit()
            self._audit_bank_action("INSERT", f"Yeni hesap: {bank_name} | IBAN: {iban}")
            return True
        except Exception as e:
            logger.error(f"Bank add error: {e}")
            return False

    def get_bank_accounts(self):
        """Tüm banka hesaplarını getir (soft-delete uyumlu)."""
        try:
            self.create_bank_accounts_table()
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in cur.fetchall()]
            deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
            q = "SELECT * FROM bank_accounts"
            if deleted_col:
                q += f" WHERE {deleted_col}=0 OR {deleted_col} IS NULL"
            q += " ORDER BY id DESC"
            cur.execute(q)
            return cur.fetchall() or []
        except Exception as e:
            logger.error(f"Bank list error: {e}")
            return []

    def set_bank_account_active(self, account_id, is_active):
        try:
            self.create_bank_accounts_table()
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in cur.fetchall()]
            col = "is_active" if "is_active" in cols else ("active" if "active" in cols else None)
            if not col or not self._is_safe_identifier(col):
                return False
            cur.execute(
                "UPDATE bank_accounts SET {column}=? WHERE id=?".format(column=col),
                (1 if is_active else 0, account_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Bank active set error: {e}")
            return False

    def update_bank_account(self, account_id, bank_name, branch_name, account_name, account_no, iban, current_balance=None, currency=None):
        try:
            self.create_bank_accounts_table()
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in cur.fetchall()]

            def pick_col(candidates):
                for c in candidates:
                    if c in cols:
                        return c
                return None

            updates = []
            values = []
            mapping = [
                (["bank_name", "bank"], bank_name),
                (["branch_name", "branch_code", "branch"], branch_name),
                (["account_name", "account_holder", "name"], account_name),
                (["account_no", "account_number"], account_no),
                (["iban"], iban),
            ]
            for candidates, val in mapping:
                col = pick_col(candidates)
                if col and self._is_safe_identifier(col):
                    updates.append(f"{col}=?")
                    values.append(val)

            balance_col = pick_col(["current_balance"])
            if balance_col and self._is_safe_identifier(balance_col) and current_balance is not None:
                updates.append(f"{balance_col}=?")
                values.append(float(current_balance))

            currency_col = pick_col(["currency"])
            if currency_col and self._is_safe_identifier(currency_col) and currency is not None:
                updates.append(f"{currency_col}=?")
                values.append(str(currency).upper())

            if not updates:
                return False

            values.append(account_id)
            cur.execute(
                "UPDATE bank_accounts SET {assignments} WHERE id=?".format(
                    assignments=", ".join(updates)
                ),
                tuple(values),
            )
            self.conn.commit()
            self._audit_bank_action("UPDATE", f"Hesap ID {account_id} güncellendi: {bank_name}")
            return True
        except Exception as e:
            logger.error(f"Bank update error: {e}")
            return False

    def delete_bank_account(self, account_id):
        """Banka hesabı sil (soft-delete destekli)."""
        try:
            self.create_bank_accounts_table()
            if hasattr(self, "soft_delete_record"):
                result = self.soft_delete_record("bank_accounts", "id", account_id)
            else:
                deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur = self.conn.cursor()
                cur.execute(
                    "UPDATE bank_accounts SET is_deleted=1, deleted_at=? WHERE id=?",
                    (deleted_at, account_id),
                )
                self.conn.commit()
                result = True
            self._audit_bank_action("DELETE", f"Hesap ID {account_id} silindi")
            return result
        except Exception as e:
            logger.error(f"Bank delete error: {e}")
            return False

    def transfer_between_accounts(self, from_id, to_id, amount, description=""):
        """Hesaplar arası transfer."""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT current_balance FROM bank_accounts WHERE id=?", (from_id,))
            from_row = cur.fetchone()
            if not from_row:
                return False, "Kaynak hesap bulunamadı"
            from_balance = float(from_row[0] or 0)
            if from_balance < amount:
                return False, "Yetersiz bakiye"

            cur.execute("SELECT current_balance FROM bank_accounts WHERE id=?", (to_id,))
            to_row = cur.fetchone()
            if not to_row:
                return False, "Hedef hesap bulunamadı"
            to_balance = float(to_row[0] or 0)

            cur.execute("UPDATE bank_accounts SET current_balance=? WHERE id=?", (from_balance - amount, from_id))
            cur.execute("UPDATE bank_accounts SET current_balance=? WHERE id=?", (to_balance + amount, to_id))
            self.conn.commit()
            self._audit_bank_action("TRANSFER", f"Hesap {from_id} -> {to_id} | Tutar: {amount} | {description}")
            return True, "Transfer başarılı"
        except Exception as e:
            logger.error(f"Bank transfer error: {e}")
            return False, str(e)
