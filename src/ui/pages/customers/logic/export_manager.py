# -*- coding: utf-8 -*-

"""
Export Manager
Müşteri listesi export işlemleri (CSV, Excel, PDF)
"""
import csv
import os
from datetime import datetime
from PyQt6.QtWidgets import QFileDialog, QMessageBox


class ExportManager:
    """Export yönetim sınıfı"""
    
    @staticmethod
    def export_to_csv(customers, parent_widget=None):
        return ExportManager._export_pandas(customers, parent_widget, "xlsx")

    @staticmethod
    def export_to_excel(customers, parent_widget=None):
        return ExportManager._export_pandas(customers, parent_widget, "xlsx")

    @staticmethod
    def _export_pandas(customers, parent_widget, fmt):
        try:
            import pandas as pd
            from PyQt6.QtWidgets import QFileDialog
            from datetime import datetime

            if not customers:
                return False, "Export edilecek müşteri bulunamadı!"
            
            ext = "xlsx"
            filter_str = "Excel Files (*.xlsx)"
            default_filename = f"musteriler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            
            filepath, _ = QFileDialog.getSaveFileName(
                parent_widget,
                f"{ext.upper()}'e Aktar",
                default_filename,
                filter_str
            )
            
            if not filepath:
                return False, "Dosya seçilmedi"

            # Prepare data
            dict_rows = []
            for c in customers:
                # c expected as dict or sqlite3.Row
                d = dict(c) if hasattr(c, "keys") else {
                    "id": c[0], "name": c[1], "phone": c[2], "email": c[3],
                    "type": c[4] if len(c)>4 else "",
                    "address": c[7] if len(c)>7 else "",
                    "company_name": c[9] if len(c)>9 else "",
                }
                dict_rows.append(d)

            df = pd.DataFrame(dict_rows)
            rename_map = {
                "id": "Müşteri No", "name": "Ad Soyad", "company_name": "Firma",
                "phone": "Telefon", "email": "E-posta", "type": "Tür", "address": "Adres"
            }
            df = df.rename(columns=rename_map)
            # Filter columns to only those in rename_map values
            keep_cols = [rename_map[k] for k in rename_map if rename_map[k] in df.columns]
            df = df[keep_cols]

            df.to_excel(filepath, index=False)
            
            return True, f"Dosya başarıyla kaydedildi: {filepath}"
        except Exception as e:
            return False, f"Export hatası: {e}"
