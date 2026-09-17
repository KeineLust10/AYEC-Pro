from src.utils.logger import logger


class LabelMixin:
    def create_label_tables(self):
        """Create live labels and sector preset tables."""
        try:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_labels (
                    key_name TEXT PRIMARY KEY,
                    default_value TEXT,
                    current_value TEXT,
                    category TEXT DEFAULT 'Global',
                    description TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sector_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sector_name TEXT,
                    key_name TEXT,
                    preset_value TEXT,
                    UNIQUE(sector_name, key_name)
                )
                """
            )

            self.conn.commit()
            logger.info("Label and Preset tables created/verified.")
            self._seed_presets()
        except Exception as e:
            logger.error(f"Error creating label tables: {e}")

    def _seed_presets(self):
        """Insert missing sector presets from src.utils.sector_presets."""
        try:
            from src.utils.sector_presets import PRESETS

            for sector, mappings in PRESETS.items():
                for key, val in mappings.items():
                    self.cursor.execute(
                        """
                        INSERT OR IGNORE INTO sector_presets (sector_name, key_name, preset_value)
                        VALUES (?, ?, ?)
                        """,
                        (sector, key, val),
                    )

            self.conn.commit()
            logger.info("Sector presets seeded successfully.")
        except Exception as e:
            logger.error(f"Error seeding presets: {e}")

    def get_all_labels(self):
        try:
            self.cursor.execute("SELECT key_name, current_value, default_value FROM app_labels")
            rows = self.cursor.fetchall()
            labels_dict = {}
            for row in rows:
                key, current, default = row
                labels_dict[key] = current if current else default
            return labels_dict
        except Exception as e:
            logger.error(f"Error getting labels: {e}")
            return {}

    def get_label_details(self, category=None):
        try:
            query = "SELECT key_name, default_value, current_value, category, description FROM app_labels"
            params = []
            if category:
                query += " WHERE category = ? OR category = 'Global'"
                params.append(category)

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            return [
                {
                    "key": row[0],
                    "default": row[1],
                    "current": row[2],
                    "category": row[3],
                    "description": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting label details: {e}")
            return []

    def update_label(self, key, new_value):
        try:
            self.cursor.execute(
                "UPDATE app_labels SET current_value = ?, updated_at = CURRENT_TIMESTAMP WHERE key_name = ?",
                (new_value, key),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating label {key}: {e}")
            return False

    def reset_label(self, key):
        try:
            self.cursor.execute(
                "UPDATE app_labels SET current_value = NULL, updated_at = CURRENT_TIMESTAMP WHERE key_name = ?",
                (key,),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting label {key}: {e}")
            return False

    def get_preset_data(self, sector_name):
        try:
            self.cursor.execute(
                "SELECT key_name, preset_value FROM sector_presets WHERE sector_name = ?",
                (sector_name,),
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting preset data for {sector_name}: {e}")
            return []

    def register_label(self, key, default_value, category="Global", description=""):
        try:
            self.cursor.execute("SELECT key_name FROM app_labels WHERE key_name = ?", (key,))
            if self.cursor.fetchone():
                return

            self.cursor.execute(
                """
                INSERT INTO app_labels (key_name, default_value, category, description)
                VALUES (?, ?, ?, ?)
                """,
                (key, default_value, category, description),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error registering label {key}: {e}")
