# -*- coding: utf-8 -*-

from src.utils.logger import logger
from datetime import datetime


class ProjectMixin:
    def _safe_identifier(self, value):
        value = str(value or "").strip()
        if not value or not value.replace("_", "").isalnum():
            raise ValueError(f"Unsafe SQL identifier: {value!r}")
        return value

    def create_project_tables(self):
        """Proje yönetimi modülü için gerekli tabloları oluşturur."""
        try:
            # 1. Projeler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    budget REAL DEFAULT 0,
                    status TEXT DEFAULT 'Devam Ediyor', -- Devam Ediyor, Tamamlandı, İptal
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Proje Üniteleri (Blok/Daire/Stok)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    block_name TEXT,
                    floor_no TEXT,
                    unit_no TEXT,
                    status TEXT DEFAULT 'Satılık', -- Satılık, Rezerve, Satıldı, Teslim Edildi
                    price REAL DEFAULT 0,
                    unit_type TEXT,
                    area REAL,
                    unit_price REAL,
                    total_price REAL,
                    customer_id INTEGER, -- Satıldıysa kime satıldı
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            self.cursor.execute("PRAGMA table_info(project_units)")
            cols = {
                r[1] if not isinstance(r, dict) else r["name"]
                for r in self.cursor.fetchall()
            }
            for col_name, col_type in [
                ("unit_type", "TEXT"),
                ("area", "REAL"),
                ("unit_price", "REAL"),
                ("total_price", "REAL"),
                ("parent_unit_id", "INTEGER"),
                ("unit_kind", "TEXT DEFAULT 'Daire'"),
            ]:
                if col_name not in cols:
                    # Validate column name and type to prevent SQL injection
                    if not col_name.replace("_", "").isalnum():
                        logger.error(f"Invalid column name: {col_name}")
                        continue
                    # Validate DDL type
                    allowed_types = ["INTEGER", "TEXT", "REAL", "BLOB", "NULL"]
                    col_type_parts = col_type.upper().split()
                    if not col_type_parts:
                        logger.error(f"Empty DDL type: {col_type}")
                        continue
                    col_type_upper = col_type_parts[0]
                    if not any(allowed in col_type_upper for allowed in allowed_types):
                        logger.error(f"Invalid DDL type: {col_type}")
                        continue
                    self.cursor.execute(
                        "ALTER TABLE project_units ADD COLUMN {column} {ddl}".format(
                            column=self._safe_identifier(col_name),
                            ddl=col_type,
                        )
                    )

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_unit_sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    unit_id INTEGER,
                    buyer_name TEXT,
                    buyer_tc TEXT,
                    buyer_phone TEXT,
                    buyer_email TEXT,
                    buyer_address TEXT,
                    delivery_date TEXT,
                    sales_rep TEXT,
                    notes TEXT,
                    list_price REAL DEFAULT 0,
                    sale_price REAL DEFAULT 0,
                    down_payment_rate REAL DEFAULT 0,
                    down_payment_amount REAL DEFAULT 0,
                    remaining_balance REAL DEFAULT 0,
                    payment_plan TEXT,
                    documents TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(unit_id) REFERENCES project_units(id) ON DELETE CASCADE
                )
            """)

            # 3. Taşeronlar
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS subcontractors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    name TEXT NOT NULL,
                    job_type TEXT, -- Elektrik, Sıva, Boya vb.
                    total_contract_amount REAL DEFAULT 0,
                    contact_info TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # 4. Proje Finansal Hareketleri (Gelir/Gider)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    type TEXT, -- Gelir, Gider
                    category TEXT, -- Malzeme, İşçilik, Satış, Taşeron Ödemesi
                    amount REAL DEFAULT 0,
                    payment_method TEXT, -- Nakit, Banka, Çek
                    date TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'Ödenmedi', -- Ödenmedi, Ödendi
                    paid_date TEXT,
                    ref_table TEXT, -- project_units, subcontractors
                    ref_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Projeler tablosuna yeni kolonlar ekle (yoksa)
            for _col, _ddl in [
                ("cost", "REAL DEFAULT 0"),
                ("payment_method", "TEXT DEFAULT 'Peşin'"),
                ("customer_id", "INTEGER"),
                ("customer_name", "TEXT"),
                ("ref_no", "TEXT"),
                ("is_archived", "INTEGER DEFAULT 0"),
                ("currency", "TEXT DEFAULT 'TRY'"),
                ("exchange_rate", "REAL DEFAULT 1.0"),
                ("contract_path", "TEXT"),
            ]:
                try:
                    self.cursor.execute(
                        "ALTER TABLE projects ADD COLUMN {column} {ddl}".format(
                            column=self._safe_identifier(_col),
                            ddl=_ddl,
                        )
                    )
                except Exception:
                    pass  # Kolon zaten var

            # project_transactions tablosuna döviz kolonları ekle (yoksa)
            for _col, _ddl in [
                ("original_amount", "REAL"),
                ("original_currency", "TEXT DEFAULT 'TRY'"),
                ("exchange_rate", "REAL DEFAULT 1.0"),
            ]:
                try:
                    self.cursor.execute(
                        "ALTER TABLE project_transactions ADD COLUMN {column} {ddl}".format(
                            column=self._safe_identifier(_col),
                            ddl=_ddl,
                        )
                    )
                except Exception:
                    pass

            # 5. Daire-Ürün İlişkisi (Akıllı Ev Kurulum Takibi)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_unit_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    part_id INTEGER,
                    part_name TEXT NOT NULL,
                    part_code TEXT,
                    quantity INTEGER DEFAULT 1,
                    notes TEXT,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(unit_id) REFERENCES project_units(id) ON DELETE CASCADE,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            self.conn.commit()
            logger.info("Project management tables created/verified.")
        except Exception as e:
            logger.error(f"Error creating project tables: {e}")

    # --- PROJECT METHODS ---
    def add_project(self, data):
        try:
            from datetime import datetime as _dt
            from src.utils.currency_helper import CurrencyHelper

            # Proje referans numarası oluştur (Ayarlar > Numara Serisi)
            ref_no = None
            try:
                if hasattr(self, "_get_next_sequence_value"):
                    ref_no = self._get_next_sequence_value(
                        "project_number_prefix", "project_number_next", "PRJ"
                    )
            except Exception as _re:
                logger.warning(f"Project ref_no generation failed: {_re}")

            currency = data.get("currency", "TRY") or "TRY"
            currency = str(currency).upper()
            exchange_rate = float(data.get("exchange_rate", 0) or 0)
            if currency == "TRY":
                exchange_rate = 1.0
            elif exchange_rate <= 0:
                exchange_rate = CurrencyHelper.require_rate(self, currency)

            self.cursor.execute(
                """
                INSERT INTO projects (name, start_date, end_date, budget, cost, payment_method,
                                     customer_id, customer_name, status, description, ref_no,
                                     currency, exchange_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("name"),
                    data.get("start_date"),
                    data.get("end_date"),
                    data.get("budget", 0),
                    data.get("cost", 0),
                    data.get("payment_method", "Peşin"),
                    data.get("customer_id"),
                    data.get("customer_name"),
                    data.get("status", "Devam Ediyor"),
                    data.get("description"),
                    ref_no,
                    currency,
                    exchange_rate,
                ),
            )
            project_id = self.cursor.lastrowid

            # ── Proje Finans sekmesine + global accounting'e otomatik kayıt ─────
            today = _dt.now().strftime("%Y-%m-%d")
            budget = float(data.get("budget", 0) or 0)
            cost = float(data.get("cost", 0) or 0)
            pmethod = data.get("payment_method", "Peşin") or "Peşin"
            pname = data.get("name", "")

            # Döviz dönüşümü: TL değerler
            _sym = {
                "TRY": "₺",
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "AED": "د.إ",
                "CAD": "C$",
                "CHF": "Fr",
            }.get(currency, currency)
            budget_try = budget * exchange_rate if currency != "TRY" else budget
            cost_try = cost * exchange_rate if currency != "TRY" else cost
            _rate_note = (
                f" [{budget:.2f} {_sym} @ {exchange_rate:.4f} = {budget_try:.2f} TL]"
                if currency != "TRY"
                else ""
            )
            _rate_note_cost = (
                f" [{cost:.2f} {_sym} @ {exchange_rate:.4f} = {cost_try:.2f} TL]"
                if currency != "TRY"
                else ""
            )

            # Ödeme şekline göre durum belirle
            _paid_methods = {"Peşin", "Havale / EFT", "Kredi Kartı"}
            pay_status = "Ödendi" if pmethod in _paid_methods else "Ödenmedi"

            # Bütçe (Gelir) → project_transactions tablosuna
            pay_status = "\u00d6denmedi"

            if budget > 0:
                try:
                    budget_transaction_id = self.add_project_transaction(
                        {
                            "project_id": project_id,
                            "type": "Gelir",
                            "category": "Proje Bütçesi",
                            "amount": budget_try,
                            "original_amount": budget if currency != "TRY" else None,
                            "original_currency": currency,
                            "exchange_rate": exchange_rate,
                            "payment_method": pmethod,
                            "date": today,
                            "description": f"Proje bütçesi: {pname}{_rate_note}",
                            "status": pay_status,
                        },
                        commit=False,
                    )
                    if not budget_transaction_id:
                        raise RuntimeError(
                            "Project budget transaction could not be created"
                        )
                except Exception as _fe:
                    raise RuntimeError(
                        f"Budget project transaction failed: {_fe}"
                    ) from _fe

            # Maliyet (Gider) → project_transactions tablosuna
            if cost > 0:
                try:
                    cost_transaction_id = self.add_project_transaction(
                        {
                            "project_id": project_id,
                            "type": "Gider",
                            "category": "Proje Maliyeti",
                            "amount": cost_try,
                            "original_amount": cost if currency != "TRY" else None,
                            "original_currency": currency,
                            "exchange_rate": exchange_rate,
                            "payment_method": pmethod,
                            "date": today,
                            "description": f"Proje maliyeti: {pname}{_rate_note_cost}",
                            "status": pay_status,
                        },
                        commit=False,
                    )
                    if not cost_transaction_id:
                        raise RuntimeError(
                            "Project cost transaction could not be created"
                        )
                except Exception as _fe:
                    raise RuntimeError(
                        f"Cost project transaction failed: {_fe}"
                    ) from _fe

            # ── Müşteri Cari + Borç Kaydı (currency_transactions) ────────────
            customer_id = data.get("customer_id")
            if customer_id and budget > 0:
                debt_created = self.add_currency_transaction(
                    customer_id=customer_id,
                    amount=budget,
                    currency=currency,
                    transaction_type="DEBIT",
                    exchange_rate=exchange_rate,
                    description=f"Proje: {pname} - Kurulum",
                    tracking_no=str(ref_no or f"PRJ-{project_id}"),
                    commit=False,
                )
                if not debt_created:
                    raise RuntimeError("Customer project debt could not be created")

            self.conn.commit()
            return project_id
        except Exception as e:
            logger.error(f"Error adding project: {e}")
            try:
                self.conn.rollback()
            except Exception as rollback_error:
                logger.error("Project rollback failed: %s", rollback_error)
            return None

    def get_projects(self, active_only=False, include_archived=False):
        conditions = []
        if active_only:
            conditions.append("status = 'Devam Ediyor'")
        if not include_archived:
            conditions.append("is_archived = 0")
        query = "SELECT * FROM projects"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        # Tamamlandı ve İptal edilenler sona, aktif olanlar başa
        query += " ORDER BY CASE WHEN status='Devam Ediyor' THEN 0 ELSE 1 END ASC, created_at DESC"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_projects_paginated(
        self,
        limit=30,
        offset=0,
        search_query="",
        active_only=False,
        archived_only=False,
    ):
        limit = max(1, min(int(limit or 30), 200))
        offset = max(0, int(offset or 0))
        conditions = []
        params = []
        if active_only:
            conditions.append("status='Devam Ediyor'")
        if archived_only:
            conditions.append("is_archived=1")
        else:
            conditions.append("is_archived=0")
        if search_query:
            search_like = f"%{str(search_query).strip()}%"
            conditions.append(
                "(name LIKE ? OR customer_name LIKE ? OR ref_no LIKE ?)"
            )
            params.extend([search_like, search_like, search_like])

        where_sql = " WHERE " + " AND ".join(conditions)
        count_row = self.cursor.execute(
            "SELECT COUNT(*) FROM projects" + where_sql,
            tuple(params),
        ).fetchone()
        total = int(count_row[0] or 0) if count_row else 0
        query = (
            "SELECT * FROM projects"
            + where_sql
            + " ORDER BY CASE WHEN status='Devam Ediyor' THEN 0 ELSE 1 END, "
            "created_at DESC LIMIT ? OFFSET ?"
        )
        self.cursor.execute(query, tuple(params + [limit, offset]))
        return self.cursor.fetchall(), total

    def get_archived_projects(self):
        self.cursor.execute(
            "SELECT * FROM projects WHERE is_archived=1 ORDER BY created_at DESC"
        )
        return self.cursor.fetchall()

    def update_project_status(self, project_id, status):
        """Proje durumunu günceller: 'Devam Ediyor', 'Tamamlandı', 'İptal'"""
        try:
            self.cursor.execute(
                "UPDATE projects SET status=? WHERE id=?", (status, project_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating project status: {e}")
            return False

    def archive_project(self, project_id, archived=True):
        """Projeyi arşive taşır veya arşivden çıkarır."""
        try:
            self.cursor.execute(
                "UPDATE projects SET is_archived=? WHERE id=?",
                (1 if archived else 0, project_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error archiving project: {e}")
            return False

    def get_project_details(self, project_id):
        self.cursor.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        return self.cursor.fetchone()

    def delete_project(self, project_id):
        """Projeyi ve ona bağlı tüm verileri (CASCADE) siler."""
        try:
            self.cursor.execute("DELETE FROM projects WHERE id=?", (project_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting project: {e}")
            return False

    # --- UNIT METHODS ---
    def add_project_unit(self, data):
        try:
            self.cursor.execute(
                """
                INSERT INTO project_units (project_id, block_name, floor_no, unit_no, status, price, unit_type, area, unit_price, total_price, description, parent_unit_id, unit_kind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("project_id"),
                    data.get("block_name"),
                    data.get("floor_no"),
                    data.get("unit_no"),
                    data.get("status", "Satılık"),
                    data.get("price", 0),
                    data.get("unit_type"),
                    data.get("area"),
                    data.get("unit_price"),
                    data.get("total_price"),
                    data.get("description"),
                    data.get("parent_unit_id"),
                    data.get("unit_kind", "Daire"),
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding project unit: {e}")
            return None

    def add_project_room(self, project_id, parent_unit_id, room_name):
        try:
            self.cursor.execute(
                "SELECT block_name, floor_no, unit_no FROM project_units WHERE id=?",
                (parent_unit_id,),
            )
            parent = self.cursor.fetchone()
            if not parent:
                return None

            block_name = parent["block_name"] if isinstance(parent, dict) else parent[0]
            floor_no = parent["floor_no"] if isinstance(parent, dict) else parent[1]
            parent_unit_no = (
                parent["unit_no"] if isinstance(parent, dict) else parent[2]
            )

            room_name = str(room_name or "").strip()
            if not room_name:
                return None

            self.cursor.execute(
                """
                SELECT COUNT(*) FROM project_units
                WHERE project_id=? AND parent_unit_id=? AND LOWER(COALESCE(unit_no,''))=LOWER(?)
                """,
                (project_id, parent_unit_id, room_name),
            )
            exists = self.cursor.fetchone()
            exists_count = int(exists[0] if exists else 0)
            if exists_count > 0:
                return None

            return self.add_project_unit(
                {
                    "project_id": project_id,
                    "block_name": block_name,
                    "floor_no": floor_no,
                    "unit_no": room_name,
                    "status": "Bekliyor",
                    "price": 0,
                    "unit_type": parent_unit_no,
                    "area": 0,
                    "unit_price": 0,
                    "total_price": 0,
                    "description": "",
                    "parent_unit_id": parent_unit_id,
                    "unit_kind": "Oda",
                }
            )
        except Exception as e:
            logger.error(f"Error adding project room: {e}")
            return None

    def add_project_unit_sale(self, data):
        try:
            self.cursor.execute(
                """
                INSERT INTO project_unit_sales
                (project_id, unit_id, buyer_name, buyer_tc, buyer_phone, buyer_email, buyer_address,
                 delivery_date, sales_rep, notes, list_price, sale_price, down_payment_rate, down_payment_amount,
                 remaining_balance, payment_plan, documents)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("project_id"),
                    data.get("unit_id"),
                    data.get("buyer_name"),
                    data.get("buyer_tc"),
                    data.get("buyer_phone"),
                    data.get("buyer_email"),
                    data.get("buyer_address"),
                    data.get("delivery_date"),
                    data.get("sales_rep"),
                    data.get("notes"),
                    data.get("list_price", 0),
                    data.get("sale_price", 0),
                    data.get("down_payment_rate", 0),
                    data.get("down_payment_amount", 0),
                    data.get("remaining_balance", 0),
                    data.get("payment_plan"),
                    data.get("documents"),
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding project unit sale: {e}")
            return None

    def get_project_units(self, project_id):
        self.cursor.execute(
            "SELECT * FROM project_units WHERE project_id=? ORDER BY block_name, floor_no, unit_no",
            (project_id,),
        )
        return self.cursor.fetchall()

    def get_project_root_units(self, project_id):
        try:
            self.cursor.execute(
                """
                SELECT *
                FROM project_units
                WHERE project_id=?
                  AND (parent_unit_id IS NULL OR parent_unit_id=0)
                ORDER BY block_name, floor_no, unit_no
                """,
                (project_id,),
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting root project units: {e}")
            return []

    def get_unit_rooms(self, parent_unit_id):
        try:
            self.cursor.execute(
                """
                SELECT *
                FROM project_units
                WHERE parent_unit_id=?
                ORDER BY unit_no
                """,
                (parent_unit_id,),
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting unit rooms: {e}")
            return []

    def update_project_unit_note(self, unit_id, note):
        try:
            self.cursor.execute(
                "UPDATE project_units SET description=? WHERE id=?",
                (note, unit_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating project unit note: {e}")
            return False

    def get_project_unit(self, unit_id):
        try:
            self.cursor.execute("SELECT * FROM project_units WHERE id=?", (unit_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting project unit: {e}")
            return None

    def update_unit_status(self, unit_id, status, customer_id=None):
        try:
            # Önceki durumu ve fiyatı al
            self.cursor.execute(
                "SELECT project_id, block_name, unit_no, price, status FROM project_units WHERE id=?",
                (unit_id,),
            )
            unit = self.cursor.fetchone()
            if not unit:
                return False

            project_id_val, block, no, price, old_status = unit

            if customer_id:
                self.cursor.execute(
                    "UPDATE project_units SET status=?, customer_id=? WHERE id=?",
                    (status, customer_id, unit_id),
                )
            else:
                self.cursor.execute(
                    "UPDATE project_units SET status=? WHERE id=?", (status, unit_id)
                )
            self.conn.commit()

            # --- FINANCIAL TRIGGER ---
            # Eğer "Satıldı" durumuna geçtiyse ve eskiden satıldı değilse -> Gelir Yaz
            if status == "Satıldı" and old_status != "Satıldı":
                desc = f"{block} Blok No:{no} Satış Bedeli"
                # Add to Central Accounting
                if hasattr(self, "add_transaction"):
                    self.add_transaction(
                        t_type="Gelir",
                        category="Daire Satışı",
                        amount=price,
                        description=desc,
                        customer_id=customer_id,
                        project_id=project_id_val,
                    )
                # Add to Project Local Transaction (Mirror)
                self.add_project_transaction(
                    {
                        "project_id": project_id_val,
                        "type": "Gelir",
                        "category": "Konut Satışı",
                        "amount": price,
                        "payment_method": "Nakit",  # Default or ask user?
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "description": desc,
                        "status": "Ödendi",
                        "ref_table": "project_units",
                        "ref_id": unit_id,
                    }
                )

            return True
        except Exception as e:
            logger.error(f"Error updating unit: {e}")
            return False

    # --- SUBCONTRACTOR METHODS ---
    def add_subcontractor(self, data):
        try:
            self.cursor.execute(
                """
                INSERT INTO subcontractors (project_id, name, job_type, total_contract_amount, contact_info)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    data.get("project_id"),
                    data.get("name"),
                    data.get("job_type"),
                    data.get("total_contract_amount", 0),
                    data.get("contact_info"),
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding subcontractor: {e}")
            return None

    def get_subcontractors(self, project_id):
        self.cursor.execute(
            "SELECT * FROM subcontractors WHERE project_id=?", (project_id,)
        )
        return self.cursor.fetchall()

    def get_subcontractors_with_balance(self, project_id):
        """Return project subcontractors and balances in one query."""
        self.cursor.execute(
            """
            SELECT
                s.*,
                COALESCE(s.total_contract_amount, 0)
                - COALESCE(SUM(
                    CASE
                        WHEN pt.type='Gider' AND pt.status='\u00d6dendi'
                        THEN pt.amount
                        ELSE 0
                    END
                ), 0) AS remaining_balance
            FROM subcontractors s
            LEFT JOIN project_transactions pt
              ON pt.ref_table='subcontractors'
             AND pt.ref_id=s.id
            WHERE s.project_id=?
            GROUP BY s.id
            ORDER BY s.id DESC
            """,
            (project_id,),
        )
        return self.cursor.fetchall()

    # --- TRANSACTION METHODS ---
    def add_project_transaction(self, data, commit=True):
        try:
            self.cursor.execute(
                """
                INSERT INTO project_transactions
                (project_id, type, category, amount, payment_method, date, description, status,
                 ref_table, ref_id, original_amount, original_currency, exchange_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("project_id"),
                    data.get("type"),
                    data.get("category"),
                    data.get("amount"),
                    data.get("payment_method"),
                    data.get("date"),
                    data.get("description"),
                    data.get("status", "Ödenmedi"),
                    data.get("ref_table"),
                    data.get("ref_id"),
                    data.get("original_amount"),
                    data.get("original_currency", "TRY"),
                    data.get("exchange_rate", 1.0),
                ),
            )
            project_transaction_id = self.cursor.lastrowid

            # --- FINANCIAL TRIGGER for Expenses ---
            # Eğer bu bir proje gideriyse ve ÖDENDİ ise -> Merkez Kasadan Düş
            # VEYA Gelir ise -> Merkez Kasaya Ekle (Ama yukarıdaki daire satışını duplicate etme!)
            # Duplicate kontrolü: category 'Konut Satışı' ise ve ref_table 'project_units' ise yukarıda zaten ekledik.
            # O yüzden burada sadece MANUAL eklenenleri veya TAŞERON ödemelerini yakalayalım.

            is_duplicate = (
                data.get("category") == "Konut Satışı"
                and data.get("ref_table") == "project_units"
            )

            if not is_duplicate and hasattr(self, "add_transaction"):
                # Sadece 'Ödendi' durumundaysa kasaya yansır
                if data.get("status") == "Ödendi":
                    self.add_transaction(
                        t_type=data.get("type"),
                        category=data.get("category"),
                        amount=data.get("amount"),
                        description=f"{data.get('description')} (Proje: {data.get('project_id')})",
                        project_id=data.get("project_id"),
                        payment_method=data.get("payment_method"),
                        bank_account_id=data.get("bank_account_id"),
                        commit=False,
                    )

            if commit:
                self.conn.commit()
            return project_transaction_id
        except Exception as e:
            logger.error(f"Error adding project transaction: {e}")
            self.conn.rollback()
            return None

    def get_project_transactions(self, project_id, txn_type=None):
        query = "SELECT * FROM project_transactions WHERE project_id=?"
        params = [project_id]
        if txn_type:
            query += " AND type=?"
            params.append(txn_type)
        query += " ORDER BY date DESC"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_subcontractor_balance(self, sub_id):
        """Taşeronun kalan alacağını hesaplar (Toplam Sözleşme - Ödenenler)"""
        try:
            # Sözleşme tutarı
            self.cursor.execute(
                "SELECT total_contract_amount FROM subcontractors WHERE id=?", (sub_id,)
            )
            res = self.cursor.fetchone()
            if not res:
                return 0
            contract_amount = res[0]

            # Yapılan ödemeler (Gider, Kategori=Taşeron Ödemesi, Durum=Ödendi, Ref=subcontractors, RefID=sub_id)
            # Not: Kategori ismi UI'dan tam olarak ne gelirse o olmalı. Burada 'Taşeron Ödemesi' varsayıyoruz.
            # Daha güvenli olması için ref_table ve ref_id kullanıyoruz.
            self.cursor.execute(
                """
                SELECT SUM(amount) FROM project_transactions 
                WHERE ref_table='subcontractors' AND ref_id=? AND type='Gider' AND status='Ödendi'
            """,
                (sub_id,),
            )
            paid_res = self.cursor.fetchone()
            paid_amount = paid_res[0] if paid_res and paid_res[0] else 0

            return contract_amount - paid_amount
        except Exception as e:
            logger.error(f"Error calc sub balance: {e}")
            return 0

    def get_project_currency(self, project_id):
        """Projenin para birimi ve kur bilgisini döndürür: (currency, exchange_rate)"""
        try:
            self.cursor.execute(
                "SELECT COALESCE(currency,'TRY'), COALESCE(exchange_rate, 1.0) FROM projects WHERE id=?",
                (project_id,),
            )
            row = self.cursor.fetchone()
            if row:
                return (row[0] or "TRY", float(row[1] or 1.0))
        except Exception as exc:
            logger.warning(
                "Project currency could not be loaded for project %s: %s",
                project_id,
                exc,
            )
        return ("TRY", 1.0)

    # --- UNIT PRODUCT METHODS (Akıllı Ev Kurulum Takibi) ---
    def add_unit_product(self, data):
        try:
            from src.utils.currency_helper import CurrencyHelper

            project_id = data.get("project_id")
            part_id = data.get("part_id")
            part_name = str(data.get("part_name") or "")
            qty = int(data.get("quantity", 1) or 1)
            if qty <= 0:
                raise ValueError("Unit product quantity must be positive")

            part_currency = "TRY"
            part_rate = 1.0
            original_total = 0.0
            total_cost_try = 0.0
            if part_id:
                self.cursor.execute(
                    """
                    SELECT name, COALESCE(stock, 0),
                           COALESCE(purchase_price, price, 0),
                           COALESCE(currency, 'TRY')
                    FROM parts
                    WHERE id=? AND COALESCE(is_deleted, 0)=0
                    """,
                    (part_id,),
                )
                part_row = self.cursor.fetchone()
                if not part_row:
                    raise ValueError(f"Stock card not found: {part_id}")

                current_stock = int(part_row[1] or 0)
                if current_stock < qty:
                    raise ValueError(
                        f"Insufficient stock for part {part_id}: "
                        f"available={current_stock}, requested={qty}"
                    )

                if not part_name:
                    part_name = str(part_row[0] or "")
                unit_cost = float(part_row[2] or 0)
                part_currency = str(part_row[3] or "TRY").upper()
                original_total = unit_cost * qty
                if part_currency != "TRY":
                    part_rate = CurrencyHelper.require_rate(self, part_currency)
                total_cost_try = round(original_total * part_rate, 4)

            self.cursor.execute(
                """
                INSERT INTO project_unit_products (unit_id, project_id, part_id, part_name, part_code, quantity, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("unit_id"),
                    project_id,
                    part_id,
                    part_name,
                    data.get("part_code"),
                    qty,
                    data.get("notes"),
                ),
            )
            entry_id = self.cursor.lastrowid

            if part_id:
                stock_updated = self.adjust_stock(
                    part_id,
                    -qty,
                    (
                        f"Proje Kullan\u0131m\u0131 "
                        f"(PRJ#:{project_id or 'Bilinmiyor'}): {part_name}"
                    ),
                    "\u00c7\u0131k\u0131\u015f",
                    commit=False,
                )
                if not stock_updated:
                    raise RuntimeError("Project stock movement could not be recorded")

            if project_id and total_cost_try > 0:
                today = datetime.now().strftime("%Y-%m-%d")
                rate_info = ""
                original_amount = None
                if part_currency != "TRY":
                    original_amount = original_total
                    rate_info = (
                        f" [{original_total:.2f} {part_currency} @ "
                        f"{part_rate:.4f} = {total_cost_try:.2f} TL]"
                    )
                self.cursor.execute(
                    """
                    INSERT INTO project_transactions
                    (project_id, type, category, amount, payment_method, date,
                     description, status, ref_table, ref_id,
                     original_amount, original_currency, exchange_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        "Gider",
                        "Malzeme Kullan\u0131m\u0131",
                        total_cost_try,
                        "Stok",
                        today,
                        f"{part_name} x{qty} - Daire kurulumu{rate_info}",
                        "\u00d6dendi",
                        "project_unit_products",
                        entry_id,
                        original_amount,
                        part_currency,
                        part_rate,
                    ),
                )

            self.conn.commit()
            return entry_id
        except Exception as e:
            logger.error(f"Error adding unit product: {e}")
            try:
                self.conn.rollback()
            except Exception as rollback_error:
                logger.error(
                    "Unit product rollback failed: %s",
                    rollback_error,
                )
            return None

    def get_unit_products(self, unit_id):
        try:
            self.cursor.execute(
                "SELECT * FROM project_unit_products WHERE unit_id=? ORDER BY added_at DESC",
                (unit_id,),
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting unit products: {e}")
            return []

    def get_project_unit_products(self, project_id):
        """Return all unit products for a project in one indexed query."""
        try:
            self.cursor.execute(
                """
                SELECT *
                FROM project_unit_products
                WHERE project_id=?
                ORDER BY unit_id, added_at DESC
                """,
                (project_id,),
            )
            return self.cursor.fetchall()
        except Exception as exc:
            logger.error(f"Error getting project unit products: {exc}")
            return []

    def update_unit_product_note(self, entry_id, note):
        """Update only the operational note; financial records stay immutable."""
        try:
            self.cursor.execute(
                "UPDATE project_unit_products SET notes=? WHERE id=?",
                (str(note or ""), entry_id),
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as exc:
            logger.error(f"Error updating unit product note: {exc}")
            return False

    def remove_unit_product(self, entry_id):
        try:
            self.cursor.execute(
                "SELECT part_id, quantity, part_name FROM project_unit_products WHERE id=?",
                (entry_id,),
            )
            row = self.cursor.fetchone()
            if not row:
                return False

            part_id = row["part_id"] if isinstance(row, dict) else row[0]
            qty = row["quantity"] if isinstance(row, dict) else row[1]
            if part_id and qty:
                stock_restored = self.adjust_stock(
                    part_id,
                    qty,
                    f"Proje Urun Iptali (ID:{entry_id})",
                    "Giri\u015f",
                    commit=False,
                )
                if not stock_restored:
                    raise RuntimeError("Project stock restoration failed")

            self.cursor.execute(
                "DELETE FROM project_transactions WHERE ref_table='project_unit_products' AND ref_id=?",
                (entry_id,),
            )

            self.cursor.execute(
                "DELETE FROM project_unit_products WHERE id=?", (entry_id,)
            )
            if self.cursor.rowcount <= 0:
                raise RuntimeError("Project unit product was not deleted")
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing unit product: {e}")
            try:
                self.conn.rollback()
            except Exception as rollback_error:
                logger.error(
                    "Unit product removal rollback failed: %s",
                    rollback_error,
                )
            return False

    def get_unit_product_count(self, unit_id):
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM project_unit_products WHERE unit_id=?", (unit_id,)
            )
            row = self.cursor.fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            logger.error(f"Error counting unit products: {e}")
            return 0

    def get_unit_total_product_count(self, unit_id):
        try:
            self.cursor.execute(
                """
                SELECT COUNT(*)
                FROM project_unit_products
                WHERE unit_id=?
                   OR unit_id IN (
                       SELECT id FROM project_units WHERE parent_unit_id=?
                   )
                """,
                (unit_id, unit_id),
            )
            row = self.cursor.fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            logger.error(f"Error counting recursive unit products: {e}")
            return 0

    def set_unit_install_status(self, unit_id, status):
        """Odanın kurulum durumunu günceller: Bekliyor / Devam Ediyor / Tamamlandı"""
        try:
            self.cursor.execute(
                "UPDATE project_units SET status=? WHERE id=?", (status, unit_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting unit install status: {e}")
            return False

    def get_project_install_summary(self, project_id):
        """Proje kurulum özet istatistiklerini döndürür."""
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM project_units WHERE project_id=?", (project_id,)
            )
            total = int((self.cursor.fetchone() or [0])[0])

            self.cursor.execute(
                "SELECT COUNT(*) FROM project_units WHERE project_id=? AND status='Tamamlandı'",
                (project_id,),
            )
            completed = int((self.cursor.fetchone() or [0])[0])

            self.cursor.execute(
                "SELECT COUNT(*) FROM project_units WHERE project_id=? AND status='Devam Ediyor'",
                (project_id,),
            )
            in_progress = int((self.cursor.fetchone() or [0])[0])

            self.cursor.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM project_unit_products WHERE project_id=?",
                (project_id,),
            )
            total_products = int((self.cursor.fetchone() or [0])[0])

            self.cursor.execute(
                "SELECT COUNT(*) FROM subcontractors WHERE project_id=?", (project_id,)
            )
            team_count = int((self.cursor.fetchone() or [0])[0])

            pct = round((completed / total * 100)) if total > 0 else 0
            return {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "total_products": total_products,
                "team_count": team_count,
                "pct": pct,
            }
        except Exception as e:
            logger.error(f"Error getting install summary: {e}")
            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "total_products": 0,
                "team_count": 0,
                "pct": 0,
            }

    def get_project_financials(self, project_id):
        """Proje Geneli Gelir/Gider Toplamları — ödenen + beklenen ayrımlı."""
        try:

            def _sum(t_type, status=None):
                q = "SELECT SUM(amount) FROM project_transactions WHERE project_id=? AND type=?"
                p = [project_id, t_type]
                if status:
                    q += " AND status=?"
                    p.append(status)
                self.cursor.execute(q, p)
                r = self.cursor.fetchone()
                return float(r[0]) if r and r[0] else 0.0

            income = _sum("Gelir", "Ödendi")
            income_pending = _sum("Gelir", "Ödenmedi")
            expense = _sum("Gider", "Ödendi")
            expense_pending = _sum("Gider", "Ödenmedi")

            return {
                "income": income,
                "income_pending": income_pending,
                "expense": expense,
                "expense_pending": expense_pending,
                "profit": income - expense,
            }
        except Exception as e:
            logger.error(f"Error calc project financials: {e}")
            return {
                "income": 0,
                "income_pending": 0,
                "expense": 0,
                "expense_pending": 0,
                "profit": 0,
            }
