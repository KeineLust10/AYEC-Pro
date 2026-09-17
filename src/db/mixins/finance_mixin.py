# -*- coding: utf-8 -*-


from src.utils.logger import logger
import sqlite3
from datetime import datetime


class FinanceMixin:
    _finance_schema_initialized = set()

    def _safe_identifier(self, value):
        value = str(value or "").strip()
        if not value or not value.replace("_", "").isalnum():
            raise ValueError(f"Unsafe SQL identifier: {value!r}")
        return value

    def _finance_soft_delete_column(self, table_name):
        table_name = self._safe_identifier(table_name)
        rows = self.conn.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
        if not rows:
            raise sqlite3.OperationalError(
                f"Finance table is unavailable: {table_name}"
            )
        columns = {str(row[1]) for row in rows}
        if "is_deleted" in columns:
            return "is_deleted"
        if "is_archived" in columns:
            return "is_archived"
        return None

    def _finance_active_filter(self, table_name, alias=None):
        deleted_column = self._finance_soft_delete_column(table_name)
        if not deleted_column:
            return ""
        prefix = f"{self._safe_identifier(alias)}." if alias else ""
        return (
            f"({prefix}{deleted_column}=0 OR "
            f"{prefix}{deleted_column} IS NULL)"
        )

    def _finance_schema_key(self):
        db_name = getattr(self, "_db_name", None) or "default"
        try:
            row = self.conn.execute("PRAGMA database_list").fetchone()
            if row and len(row) >= 3 and row[2]:
                return str(row[2])
        except sqlite3.Error as exc:
            logger.debug("Finance schema path lookup failed: %s", exc)
        return str(db_name)

    def create_finance_tables(self):
        """Finans modülü için gerekli tabloları oluşturur."""
        schema_key = self._finance_schema_key()
        if schema_key in type(self)._finance_schema_initialized:
            table_row = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='loans'"
            ).fetchone()
            if table_row:
                return
            type(self)._finance_schema_initialized.discard(schema_key)

        previous_busy_timeout = None
        try:
            try:
                self.cursor.execute("PRAGMA busy_timeout")
                row = self.cursor.fetchone()
                previous_busy_timeout = (
                    int(row[0]) if row and row[0] is not None else None
                )
            except sqlite3.Error as exc:
                logger.debug("Finance busy timeout could not be read: %s", exc)
                previous_busy_timeout = None

            try:
                self.cursor.execute("PRAGMA busy_timeout = 1200")
            except sqlite3.Error as exc:
                logger.debug("Finance busy timeout could not be set: %s", exc)

            # Krediler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_account_id INTEGER, -- Bağlı olduğu banka hesabı
                    bank_name TEXT, -- Banka adı (yedek bilgi)
                    amount REAL,
                    interest_rate REAL,
                    term_months INTEGER,
                    start_date TEXT,
                    total_payment REAL,
                    description TEXT,
                    status TEXT DEFAULT 'Aktif', -- Aktif, Bitmiş, İptal
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Apply every migration independently so one existing column does
            # not prevent the remaining columns from being created.
            loan_columns = {
                row[1] for row in self.cursor.execute("PRAGMA table_info(loans)")
            }
            loan_extensions = {
                "loan_type": "TEXT DEFAULT 'Taksitli'",
                "loan_title": "TEXT",
                "kkdf_rate": "REAL DEFAULT 0",
                "bsmv_rate": "REAL DEFAULT 0",
            }
            for column_name, column_type in loan_extensions.items():
                if column_name not in loan_columns:
                    self.cursor.execute(
                        f"ALTER TABLE loans ADD COLUMN {column_name} {column_type}"
                    )

            # Kredi Ekler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS loan_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loan_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT,
                    notes TEXT,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE
                )
            """)

            # Kredi Taksitleri Tablosu (Enhanced with tax breakdown)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS loan_installments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loan_id INTEGER NOT NULL,
                    installment_no INTEGER NOT NULL,
                    due_date TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    principal_part REAL NOT NULL,
                    interest_part REAL NOT NULL,
                    kkdf_amount REAL DEFAULT 0.0,
                    bsmv_amount REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'Bekliyor',
                    paid_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(loan_id) REFERENCES loans(id) ON DELETE CASCADE
                )
            """)

            # Indexes for performance
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_installments_loan ON loan_installments(loan_id)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_installments_due ON loan_installments(due_date)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_installments_status ON loan_installments(status)"
            )

            # Çek ve Senet Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS checks_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT, -- Çek, Senet
                    direction TEXT, -- Giriş (Alınan), Çıkış (Verilen)
                    portfolio_no TEXT,
                    amount REAL,
                    due_date TEXT,
                    issuer TEXT, -- Keşideci / Borçlu
                    recipient TEXT, -- Alıcı (Biz veya başkası)
                    bank_name TEXT,
                    branch_name TEXT,
                    account_no TEXT,
                    check_no TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'Portföyde', -- Portföyde, Tahsil Edildi, Ciro Edildi, Ödendi, Karşılıksız, İade
                    image_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scheduled Alerts Table (Voice Assistant Time-Based Reminders)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    trigger_time TEXT NOT NULL,
                    is_enabled INTEGER DEFAULT 1,
                    is_critical INTEGER DEFAULT 0,
                    last_triggered TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(alert_type)
                )
            """)

            # Default scheduled alerts (if not exists)
            default_alerts = [
                ("loan_reminder", "11:00", 1, 0),
                ("check_reminder", "11:30", 1, 0),
                ("stock_critical", "15:00", 1, 0),
            ]

            for alert_type, trigger_time, is_enabled, is_critical in default_alerts:
                self.cursor.execute(
                    """
                    INSERT OR IGNORE INTO scheduled_alerts (alert_type, trigger_time, is_enabled, is_critical)
                    VALUES (?, ?, ?, ?)
                """,
                    (alert_type, trigger_time, is_enabled, is_critical),
                )

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS bank_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_account_id INTEGER NOT NULL,
                    card_name TEXT,
                    card_last4 TEXT,
                    card_limit REAL DEFAULT 0,
                    current_debt REAL DEFAULT 0,
                    due_day INTEGER,
                    statement_day INTEGER,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id) ON DELETE CASCADE
                )
            """)

            for index_sql in (
                "CREATE INDEX IF NOT EXISTS idx_loan_installments_due_status ON loan_installments(due_date, status)",
                "CREATE INDEX IF NOT EXISTS idx_checks_notes_date_status ON checks_notes(date, status)",
                "CREATE INDEX IF NOT EXISTS idx_accounting_date_type ON accounting(date, type)",
            ):
                try:
                    self.cursor.execute(index_sql)
                except sqlite3.OperationalError:
                    pass

            self.conn.commit()
            type(self)._finance_schema_initialized.add(schema_key)
            logger.info("Finance tables created/verified successfully.")
        except sqlite3.OperationalError as e:
            try:
                self.conn.rollback()
            except sqlite3.Error as rollback_error:
                logger.error(
                    "Finance schema rollback failed: %s",
                    rollback_error,
                )
            if "locked" in str(e).lower():
                logger.warning("Finance table init skipped due to temporary DB lock.")
                return
            logger.error(f"Error creating finance tables: {e}")
        except Exception as e:
            logger.error(f"Error creating finance tables: {e}")
        finally:
            if previous_busy_timeout is not None:
                try:
                    self.cursor.execute(
                        f"PRAGMA busy_timeout = {max(0, int(previous_busy_timeout))}"
                    )
                except sqlite3.Error as restore_error:
                    logger.warning(
                        "Finance busy timeout could not be restored: %s",
                        restore_error,
                    )

    # --- LOAN METHODS ---
    def add_loan(
        self,
        bank_name=None,
        principal=None,
        interest_rate=None,
        months=None,
        start_date=None,
        loan_type="Taksitli",
        loan_title="Kredi",
        kkdf_rate=0,
        bsmv_rate=0,
        bank_account_id=None,
        total_payment=None,
        description=None,
    ):
        try:
            if isinstance(bank_name, dict):
                data = bank_name
                bank_name = data.get("bank_name")
                principal = (
                    data.get("amount")
                    if data.get("amount") is not None
                    else data.get("principal_amount", principal)
                )
                interest_rate = data.get("interest_rate", interest_rate)
                months = (
                    data.get("term_months")
                    if data.get("term_months") is not None
                    else data.get("installment_count", months)
                )
                start_date = data.get("start_date", start_date)
                loan_type = data.get("loan_type", loan_type)
                loan_title = data.get("loan_title", loan_title)
                kkdf_rate = data.get("kkdf_rate", kkdf_rate)
                bsmv_rate = data.get("bsmv_rate", bsmv_rate)
                bank_account_id = data.get("bank_account_id", bank_account_id)
                total_payment = data.get("total_payment", total_payment)
                description = data.get("description", description)

            if bank_account_id in [None, "", 0, "0"] and bank_name:
                try:
                    self.cursor.execute(
                        "SELECT id FROM bank_accounts WHERE LOWER(bank_name)=LOWER(?) ORDER BY is_active DESC, id DESC LIMIT 1",
                        (bank_name,),
                    )
                    row = self.cursor.fetchone()
                    if row:
                        bank_account_id = row[0]
                except Exception as e:
                    logger.debug(f"Bank account resolution skipped in add_loan: {e}")
                    bank_account_id = None

            self.cursor.execute(
                """
                INSERT INTO loans (
                    bank_account_id, bank_name, amount, interest_rate, term_months, start_date,
                    total_payment, description, loan_type, loan_title, kkdf_rate, bsmv_rate
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    bank_account_id,
                    bank_name,
                    principal,
                    interest_rate,
                    months,
                    start_date,
                    total_payment,
                    description,
                    loan_type,
                    loan_title,
                    kkdf_rate,
                    bsmv_rate,
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding loan: {e}")
            return None

    def update_loan(
        self,
        loan_id,
        bank_name,
        principal,
        interest_rate,
        months,
        start_date,
        description,
        status,
    ):
        try:
            self.cursor.execute(
                """
                UPDATE loans 
                SET bank_name=?, amount=?, interest_rate=?, term_months=?, start_date=?, description=?, status=?
                WHERE id=?
            """,
                (
                    bank_name,
                    principal,
                    interest_rate,
                    months,
                    start_date,
                    description,
                    status,
                    loan_id,
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating loan: {e}")
            return False

    def get_loans(self, active_only=False):
        query = "SELECT * FROM loans"
        where = []
        active_filter = self._finance_active_filter("loans")
        if active_filter:
            where.append(active_filter)
        if active_only:
            where.append("status = 'Aktif'")
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY start_date DESC"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def delete_loan(self, loan_id):
        try:
            return self.soft_delete_record("loans", "id", loan_id)
        except Exception as e:
            logger.error(f"Error deleting loan: {e}")
            return False

    # ===== ADVANCED LOAN TRACKING METHODS =====

    def add_loan_with_installments(self, loan_data, installment_plan):
        """
        Kredi ve tüm taksitlerini tek seferde ekler
        Args:
            loan_data: dict - Kredi bilgileri
            installment_plan: list - LoanCalculator.generate_payment_plan() çıktısı
        Returns:
            loan_id veya None
        """
        try:
            # Krediyi ekle
            self.cursor.execute(
                """
                INSERT INTO bank_loans (bank_name, description, principal_amount, 
                                       interest_rate, installment_count, kkdf_rate, 
                                       bsmv_rate, start_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Aktif')
            """,
                (
                    loan_data.get("bank_name"),
                    loan_data.get("description"),
                    loan_data.get("principal_amount"),
                    loan_data.get("interest_rate"),
                    len(installment_plan),
                    loan_data.get("kkdf_rate", 0.0),
                    loan_data.get("bsmv_rate", 0.0),
                    loan_data.get("start_date"),
                ),
            )

            loan_id = self.cursor.lastrowid

            # Taksitleri toplu ekle
            for inst in installment_plan:
                self.cursor.execute(
                    """
                    INSERT INTO loan_installments 
                    (loan_id, installment_no, due_date, total_amount, principal_part, 
                     interest_part, kkdf_amount, bsmv_amount, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Bekliyor')
                """,
                    (
                        loan_id,
                        inst["installment_number"],
                        inst["due_date"],
                        inst["total_amount"],
                        inst["principal_part"],
                        inst["interest_part"],
                        inst.get("kkdf_amount", 0.0),
                        inst.get("bsmv_amount", 0.0),
                    ),
                )

            self.conn.commit()
            logger.info(
                f"Loan ID {loan_id} added with {len(installment_plan)} installments"
            )
            return loan_id

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error adding loan with installments: {e}")
            return None

    def get_monthly_loan_load(self, year=None, month=None):
        """Belirtilen aydaki toplam kredi yükünü hesaplar"""
        from datetime import datetime

        if not year or not month:
            now = datetime.now()
            year, month = now.year, now.month

        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        self.cursor.execute(
            """
            SELECT 
                COUNT(*) as installment_count,
                SUM(total_amount) as total_amount
            FROM loan_installments
            WHERE due_date >= ? AND due_date < ?
                AND status IN ('Bekliyor', 'Vadesi Geçti')
        """,
            (start_date, end_date),
        )

        result = self.cursor.fetchone()
        return {
            "count": result["installment_count"] or 0,
            "total": result["total_amount"] or 0.0,
        }

    def get_overdue_installments(self):
        """Vadesi geçmiş taksitleri getir"""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")

        self.cursor.execute(
            """
            SELECT i.*, l.bank_name, l.description
            FROM loan_installments i
            JOIN bank_loans l ON i.loan_id = l.id
            WHERE i.due_date < ? AND i.status = 'Bekliyor'
            ORDER BY i.due_date ASC
        """,
            (today,),
        )
        return self.cursor.fetchall()

    def get_upcoming_installments(self, days=7):
        """Yaklaşan taksitleri getir"""
        from datetime import datetime, timedelta

        today = datetime.now()
        future_date = (today + timedelta(days=days)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        self.cursor.execute(
            """
            SELECT i.*, l.bank_name, l.description
            FROM loan_installments i
            JOIN bank_loans l ON i.loan_id = l.id
            WHERE i.due_date BETWEEN ? AND ? 
                AND i.status = 'Bekliyor'
            ORDER BY i.due_date ASC
        """,
            (today_str, future_date),
        )
        return self.cursor.fetchall()

    def pay_installment(self, installment_id):
        """Taksiti öder"""
        from datetime import datetime

        try:
            paid_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.cursor.execute(
                """
                UPDATE loan_installments 
                SET status = 'Ödendi', paid_date = ?
                WHERE id = ?
            """,
                (paid_date, installment_id),
            )

            self.conn.commit()
            logger.info(f"Installment {installment_id} paid")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error paying installment: {e}")
            return False

    def get_loan_installments_by_date(self, target_date):
        """Belirli bir tarihteki taksitleri getir"""
        self.cursor.execute(
            """
            SELECT i.*, l.bank_name, l.description
            FROM loan_installments i
            JOIN bank_loans l ON i.loan_id = l.id
            WHERE i.due_date = ?
            ORDER BY i.total_amount DESC
        """,
            (target_date,),
        )
        return self.cursor.fetchall()

    def get_loan_details(self, loan_id):
        self.cursor.execute("SELECT * FROM loans WHERE id=?", (loan_id,))
        return self.cursor.fetchone()

    # ===== SCHEDULED ALERTS METHODS =====

    def get_scheduled_alerts_by_time(self, time_str):
        """Belirli saatteki aktif uyarıları getir (HH:mm format)"""
        self.cursor.execute(
            """
            SELECT * FROM scheduled_alerts
            WHERE trigger_time = ? AND is_enabled = 1
        """,
            (time_str,),
        )
        return self.cursor.fetchall()

    def get_all_scheduled_alerts(self):
        """Tüm zamanlanmış uyarıları getir"""
        self.cursor.execute("SELECT * FROM scheduled_alerts ORDER BY trigger_time")
        return self.cursor.fetchall()

    def update_scheduled_alert(
        self, alert_type, trigger_time=None, is_enabled=None, is_critical=None
    ):
        """Zamanlanmış uyarıyı güncelle"""
        updates = []
        params = []

        if trigger_time is not None:
            updates.append("trigger_time = ?")
            params.append(trigger_time)

        if is_enabled is not None:
            updates.append("is_enabled = ?")
            params.append(1 if is_enabled else 0)

        if is_critical is not None:
            updates.append("is_critical = ?")
            params.append(1 if is_critical else 0)

        if not updates:
            return

        params.append(alert_type)
        query = "UPDATE scheduled_alerts SET {assignments} WHERE alert_type = ?".format(
            assignments=", ".join(updates)
        )

        self.cursor.execute(query, params)
        self.conn.commit()

    def get_bank_cards(self, bank_account_id):
        query = "SELECT * FROM bank_cards WHERE bank_account_id=?"
        active_filter = self._finance_active_filter("bank_cards")
        if active_filter:
            query += f" AND {active_filter}"
        query += " ORDER BY id DESC"
        self.cursor.execute(query, (bank_account_id,))
        return self.cursor.fetchall()

    def add_bank_card(
        self,
        bank_account_id,
        card_name,
        card_last4,
        card_limit=0,
        current_debt=0,
        due_day=None,
        statement_day=None,
        is_active=True,
    ):
        try:
            self.cursor.execute(
                """
                INSERT INTO bank_cards
                (bank_account_id, card_name, card_last4, card_limit, current_debt, due_day, statement_day, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    bank_account_id,
                    card_name,
                    card_last4,
                    float(card_limit or 0),
                    float(current_debt or 0),
                    due_day,
                    statement_day,
                    1 if is_active else 0,
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding bank card: {e}")
            return None

    def update_bank_card(
        self,
        card_id,
        card_name,
        card_last4,
        card_limit=0,
        current_debt=0,
        due_day=None,
        statement_day=None,
        is_active=True,
    ):
        try:
            self.cursor.execute(
                """
                UPDATE bank_cards
                SET card_name=?, card_last4=?, card_limit=?, current_debt=?, due_day=?, statement_day=?, is_active=?
                WHERE id=?
            """,
                (
                    card_name,
                    card_last4,
                    float(card_limit or 0),
                    float(current_debt or 0),
                    due_day,
                    statement_day,
                    1 if is_active else 0,
                    card_id,
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating bank card: {e}")
            return False

    def delete_bank_card(self, card_id):
        try:
            return self.soft_delete_record("bank_cards", "id", card_id)
        except Exception as e:
            logger.error(f"Error deleting bank card: {e}")
            return False

    def mark_alert_triggered(self, alert_type, triggered_time):
        """Uyarının tetiklendiğini işaretle"""
        self.cursor.execute(
            """
            UPDATE scheduled_alerts
            SET last_triggered = ?
            WHERE alert_type = ?
        """,
            (triggered_time, alert_type),
        )
        self.conn.commit()

    # --- INSTALLMENT METHODS ---
    def add_loan_installment(self, data):
        try:
            self.cursor.execute(
                """
                INSERT INTO loan_installments (loan_id, installment_no, due_date, total_amount, principal_part, interest_part, status)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
                (
                    data.get("loan_id"),
                    data.get("installment_no"),
                    data.get("due_date"),
                    data.get("amount"),  # total_amount
                    data.get("amount"),  # principal_part (simplified)
                    "Bekliyor",
                ),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding installment: {e}")

    def delete_loan_installments(self, loan_id):
        """Krediye ait bekleyen/tüm taksitleri siler"""
        try:
            query = "SELECT id FROM loan_installments WHERE loan_id=?"
            self.cursor.execute(query, (loan_id,))
            rows = self.cursor.fetchall() or []
            ok = True
            for row in rows:
                iid = row[0] if not isinstance(row, dict) else row.get("id")
                if not self.soft_delete_record("loan_installments", "id", iid):
                    ok = False
            return ok
        except Exception as e:
            logger.error(f"Error deleting installments: {e}")
            return False

    def get_loan_installments(self, loan_id):
        query = "SELECT * FROM loan_installments WHERE loan_id=?"
        active_filter = self._finance_active_filter("loan_installments")
        if active_filter:
            query += f" AND {active_filter}"
        query += " ORDER BY due_date ASC"
        self.cursor.execute(query, (loan_id,))
        return self.cursor.fetchall()

    def update_installment_status(self, installment_id, new_status, paid_amount=None):
        """
        Taksit durumunu günceller.
        'Ödendi' yapılıyorsa bakiye entegrasyonu için banka/kasa gideri ekler.
        """
        paid_date = (
            datetime.now().strftime("%Y-%m-%d") if new_status == "Ödendi" else None
        )

        try:
            if new_status == "Ödendi":
                self.cursor.execute(
                    """
                    SELECT i.status, i.total_amount, i.installment_no, l.bank_account_id, l.bank_name
                    FROM loan_installments i
                    JOIN loans l ON l.id = i.loan_id
                    WHERE i.id = ?
                """,
                    (installment_id,),
                )
                row = self.cursor.fetchone()

                if row:
                    current_status = row[0]
                    if current_status != "Ödendi":
                        self.cursor.execute(
                            """
                            UPDATE loan_installments 
                            SET status=?, paid_date=?
                            WHERE id=?
                        """,
                            (new_status, paid_date, installment_id),
                        )
                        self.conn.commit()

                        final_amount = (
                            paid_amount if paid_amount is not None else row[1]
                        )
                        desc = f"Kredi {row[4] or ''} {row[2]}. Taksit Ödemesi"

                        try:
                            self.add_transaction(
                                t_type="Gider",
                                category="Kredi Taksit Ödemesi",
                                amount=final_amount,
                                description=desc,
                                bank_account_id=row[3],
                                payment_method="Banka",
                            )
                        except Exception as e:
                            logger.error(
                                f"Error adding transaction for installment: {e}"
                            )
                        return True

            self.cursor.execute(
                """
                UPDATE loan_installments 
                SET status=?, paid_date=?
                WHERE id=?
            """,
                (new_status, paid_date, installment_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating installment status: {e}")
            return False

    # --- CHECK/NOTE METHODS ---
    def add_check_note(self, data):
        try:
            self.cursor.execute(
                """
                INSERT INTO checks_notes (type, direction, portfolio_no, amount, due_date, issuer, recipient, bank_name, branch_name, account_no, check_no, description, status, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("type"),
                    data.get("direction"),
                    data.get("portfolio_no"),
                    data.get("amount"),
                    data.get("due_date"),
                    data.get("issuer"),
                    data.get("recipient"),
                    data.get("bank_name"),
                    data.get("branch_name"),
                    data.get("account_no"),
                    data.get("check_no"),
                    data.get("description"),
                    data.get("status", "Portföyde"),
                    data.get("image_path"),
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding check/note: {e}")
            return None

    def get_checks_notes(self, status_filter=None):
        query = "SELECT * FROM checks_notes"
        params = []
        active_filter = self._finance_active_filter("checks_notes")
        if active_filter:
            query += f" WHERE {active_filter}"
        if status_filter:
            query += " AND status = ?" if "WHERE" in query else " WHERE status = ?"
            params.append(status_filter)

        query += " ORDER BY due_date ASC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def update_check_status(self, check_id, new_status):
        try:
            self.cursor.execute(
                "UPDATE checks_notes SET status=? WHERE id=?", (new_status, check_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating check status: {e}")
            return False

    # ===== VOICE ASSISTANT QUERY METHODS =====
    def get_total_debt(self):
        """Asistan için toplam borç hesaplaması"""
        try:
            # 1. Kredi Taksitleri (Bekleyen)
            loan_query = "SELECT SUM(total_amount) FROM loan_installments WHERE status = 'Bekliyor'"
            loan_active_filter = self._finance_active_filter("loan_installments")
            if loan_active_filter:
                loan_query += f" AND {loan_active_filter}"
            self.cursor.execute(loan_query)
            loan_debt = self.cursor.fetchone()[0] or 0.0

            # 2. Verilen Çekler/Senetler (Ödenmemiş)
            check_query = "SELECT SUM(amount) FROM checks_notes WHERE direction='Çıkış' AND status NOT IN ('Ödendi', 'İade')"
            check_active_filter = self._finance_active_filter("checks_notes")
            if check_active_filter:
                check_query += f" AND {check_active_filter}"
            self.cursor.execute(check_query)
            check_debt = self.cursor.fetchone()[0] or 0.0

            return float(loan_debt + check_debt)
        except Exception as e:
            logger.error(f"Error calculating total debt: {e}")
            return 0.0

    def get_total_cash(self):
        """Asistan için toplam kasa/banka varlığı - Redundant: Use get_balance instead"""
        return self.get_balance()

    def get_daily_vades(self):
        """Bugün ödenmesi gerekenleri getirir"""
        today = datetime.now().strftime("%Y-%m-%d")
        results = []
        try:
            # 1. Krediler
            loan_filters = [
                value
                for value in (
                    self._finance_active_filter("loan_installments", "i"),
                    self._finance_active_filter("loans", "l"),
                )
                if value
            ]
            loan_where = (
                " AND " + " AND ".join(loan_filters)
                if loan_filters
                else ""
            )
            self.cursor.execute(
                """
                SELECT l.bank_name, i.total_amount, 'Kredi Taksiti' as type 
                FROM loan_installments i
                JOIN loans l ON i.loan_id = l.id
                WHERE i.due_date = ? AND i.status = 'Bekliyor'{loan_where}
                """.format(loan_where=loan_where),
                (today,),
            )
            for row in self.cursor.fetchall():
                results.append({"unvan": row[0], "tutar": row[1], "kategori": row[2]})

            # 2. Çek/Senet
            check_active_filter = self._finance_active_filter("checks_notes")
            check_where = (
                f" AND {check_active_filter}"
                if check_active_filter
                else ""
            )
            self.cursor.execute(
                """
                SELECT recipient, amount, 'Çek/Senet Ödemesi' as type
                FROM checks_notes
                WHERE due_date = ? AND direction='Çıkış' AND status NOT IN ('Ödendi', 'İade'){check_where}
                """.format(check_where=check_where),
                (today,),
            )
            for row in self.cursor.fetchall():
                results.append({"unvan": row[0], "tutar": row[1], "kategori": row[2]})

            return results
        except Exception as e:
            logger.error(f"Error getting daily vades: {e}")
            return []
