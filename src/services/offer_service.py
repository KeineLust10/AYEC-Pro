class OfferService:
    def __init__(self, db):
        self.db = db
        self.ensure_schema()

    def ensure_schema(self):
        offer_columns = {
            str(row[1])
            for row in self.db.cursor.execute(
                "PRAGMA table_info(offers)"
            ).fetchall()
        }
        if offer_columns and "created_by" not in offer_columns:
            self.db.cursor.execute("ALTER TABLE offers ADD COLUMN created_by TEXT")
        self.db.conn.commit()

    def offers(self, search=""):
        query = """
            SELECT o.*, COALESCE(GROUP_CONCAT(oi.description, ', '), '') AS items
            FROM offers o
            LEFT JOIN offer_items oi ON oi.offer_id=o.id
        """
        params = []
        if str(search or "").strip():
            term = f"%{str(search).strip()}%"
            query += """
                WHERE o.offer_no LIKE ?
                   OR o.customer_name LIKE ?
                   OR o.company_name LIKE ?
                   OR oi.description LIKE ?
            """
            params.extend([term, term, term, term])
        query += " GROUP BY o.id ORDER BY o.created_at DESC, o.id DESC"
        return self.db.cursor.execute(query, params).fetchall()

    def offer_summary(self):
        row = self.db.cursor.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN LOWER(status) IN (
                       'draft', 'pending', 'waiting', 'beklemede'
                   ) THEN 1 ELSE 0 END),
                   SUM(CASE WHEN LOWER(status) IN (
                       'accepted', 'approved', 'onaylandi'
                   ) THEN 1 ELSE 0 END),
                   SUM(CASE WHEN LOWER(status) IN (
                       'rejected', 'declined', 'reddedildi'
                   ) THEN 1 ELSE 0 END),
                   COALESCE(SUM(total_try), 0)
            FROM offers
            """
        ).fetchone()
        return tuple(row or (0, 0, 0, 0, 0))

    def monthly_offer_trend(self):
        return self.db.cursor.execute(
            """
            SELECT substr(created_at, 1, 7) AS month_key,
                   COUNT(*) AS offer_count,
                   COALESCE(SUM(total_try), 0) AS total_amount,
                   GROUP_CONCAT(
                       DISTINCT COALESCE(NULLIF(company_name, ''), customer_name, '-')
                   ) AS customer_names,
                   GROUP_CONCAT(
                       DISTINCT COALESCE(NULLIF(TRIM(created_by), ''), '-')
                   ) AS creator_names
            FROM offers
            WHERE created_at >= date('now', '-11 months', 'start of month')
            GROUP BY month_key
            ORDER BY month_key DESC
            """
        ).fetchall()

    def customer_offer_distribution(self):
        return self.db.cursor.execute(
            """
            SELECT COALESCE(NULLIF(company_name, ''), customer_name, '-'),
                   COUNT(*) AS offer_count,
                   COALESCE(SUM(total_try), 0) AS total_amount
            FROM offers
            GROUP BY 1
            ORDER BY offer_count DESC, total_amount DESC, 1
            LIMIT 20
            """
        ).fetchall()

    def personnel_offer_distribution(self):
        return self.db.cursor.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(created_by), ''), '-') AS creator_name,
                   COUNT(*) AS offer_count,
                   COALESCE(SUM(total_try), 0) AS total_amount,
                   MAX(created_at) AS latest_offer_at
            FROM offers
            GROUP BY creator_name
            ORDER BY offer_count DESC, total_amount DESC,
                     latest_offer_at DESC, creator_name
            LIMIT 20
            """
        ).fetchall()
