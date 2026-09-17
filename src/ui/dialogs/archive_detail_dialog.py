# -*- coding: utf-8 -*-

# pyrefly: ignore [missing-import]
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QTabWidget, QScrollArea, QWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPixmap
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import qc, theme_qss
from src.utils.design_system import DesignTokens
from src.utils.logger import logger
import os

class ArchiveDetailDialog(ModernDialog):
    def __init__(self, db, tracking_no, parent=None):
        super().__init__(f"Arşiv Detay - {tracking_no}", parent, width=1200, height=800)
        self.db = db
        self.tracking_no = tracking_no
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(theme_qss("QTabWidget::pane{border:0} QTabBar::tab{padding:8px 16px}"))
        self._init_data()
        self._build_ui()
    
    def _init_data(self):
        try:
            self.db.cursor.execute(
                "SELECT device_brand, device_model, serial_no, entry_date, delivered_at, photo_path, photo_paths "
                "FROM devices WHERE tracking_no=?",
                (self.tracking_no,),
            )
            row = self.db.cursor.fetchone() or [None]*7
            self.brand = row[0] or ""
            self.model = row[1] or ""
            self.serial = row[2] or ""
            self.entry_date = row[3] or ""
            self.delivered_at = row[4] or ""
            self.photo_path = row[5] or ""
            self.photo_paths = row[6] or ""
        except Exception as e:
            logger.warning(f"Archive details device query failed: {e}")
            self.brand = ""
            self.model = ""
            self.serial = ""
            self.entry_date = ""
            self.delivered_at = ""
            self.photo_path = ""
            self.photo_paths = ""
        try:
            self.logs = self.db.get_logs(self.tracking_no) if hasattr(self.db, "get_logs") else []
        except Exception as e:
            logger.warning(f"Archive details logs query failed: {e}")
            self.logs = []
        try:
            self.parts = self.db.get_used_parts(self.tracking_no) if hasattr(self.db, "get_used_parts") else []
        except Exception as e:
            logger.warning(f"Archive details parts query failed: {e}")
            self.parts = []
        self.images_entry = []
        self.images_exit = []
        self.images_other = []
        use_photos = False
        try:
            self.db.cursor.execute("PRAGMA table_info(photos)")
            use_photos = bool(self.db.cursor.fetchall())
        except Exception as e:
            logger.debug(f"Archive details photos table probe failed: {e}")
            use_photos = False
        if use_photos and hasattr(self.db, "get_photos"):
            try:
                rows_entry = self.db.get_photos(self.tracking_no, "Giriş") or []
                rows_exit = self.db.get_photos(self.tracking_no, "İşlem") or []
                for r in rows_entry:
                    pth = r[1]
                    if pth and os.path.exists(pth):
                        self.images_entry.append(pth)
                for r in rows_exit:
                    pth = r[1]
                    if pth and os.path.exists(pth):
                        self.images_exit.append(pth)
            except Exception as e:
                logger.warning(f"Archive details photo list load failed: {e}")
        if not self.images_entry and not self.images_exit:
            paths = []
            if self.photo_path and os.path.exists(self.photo_path):
                paths.append(self.photo_path)
            if self.photo_paths:
                for p in str(self.photo_paths).split(","):
                    p = p.strip()
                    if p and os.path.exists(p):
                        paths.append(p)
            for p in paths:
                lp = p.lower()
                if any(k in lp for k in ["entry", "giris", "before"]):
                    self.images_entry.append(p)
                elif any(k in lp for k in ["exit", "cikis", "after", "islem", "process"]):
                    self.images_exit.append(p)
                else:
                    self.images_other.append(p)
    
    def _build_ui(self):
        container = QFrame()
        container.setStyleSheet(theme_qss("QFrame{background:@surface;border-radius:16px}"))
        lay = QVBoxLayout(container)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        
        info = QFrame()
        info.setStyleSheet(theme_qss(f"background:{DesignTokens.SECONDARY}; border:1px solid {DesignTokens.BORDER}; border-radius:{DesignTokens.RADIUS_LG};"))
        fl = QHBoxLayout(info)
        fl.setContentsMargins(14, 14, 14, 14)
        t1 = QLabel(f"Marka: {self.brand}")
        t1.setFont(QFont(DesignTokens.FONT_FAMILY, 13))
        t2 = QLabel(f"Model: {self.model}")
        t2.setFont(QFont(DesignTokens.FONT_FAMILY, 13))
        t3 = QLabel(f"Seri No: {self.serial}")
        t3.setFont(QFont(DesignTokens.FONT_FAMILY, 13))
        t4 = QLabel(f"Giriş Tarihi: {self.entry_date}")
        t4.setFont(QFont(DesignTokens.FONT_FAMILY, 13))
        fl.addWidget(t1)
        fl.addWidget(t2)
        fl.addWidget(t3)
        fl.addWidget(t4)
        if self.delivered_at:
            t5 = QLabel(f"Teslim Zamanı: {self.delivered_at}")
            t5.setFont(QFont(DesignTokens.FONT_FAMILY, 13))
            fl.addWidget(t5)
        fl.addStretch()
        btn_tech = QPushButton("🛠️ Teknisyen Paneli Formu")
        btn_tech.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tech.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        btn_tech.clicked.connect(self._open_read_only_technician_panel)
        fl.addWidget(btn_tech)
        lay.addWidget(info)
        
        self.tabs.addTab(self._build_logs_tab(), "🕒 İşlem Geçmişi")
        self.tabs.addTab(self._build_parts_tab(), "🔩 Değişen Parçalar")
        self.tabs.addTab(self._build_photos_tab(), "🖼️ Fotoğraflar")
        lay.addWidget(self.tabs, 1)
        self.add_widget(container)

    def _open_read_only_technician_panel(self):
        try:
            row = self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (self.tracking_no,),
            ).fetchone()
            if row:
                from src.utils.system_config import SystemConfig
                is_auto = SystemConfig.get_current_sector(self.db) == "otomotiv" if hasattr(SystemConfig, "get_current_sector") else False
                if is_auto:
                    from src.ui.dialogs.automotive_technician_panel import AutomotiveTechnicianPanel as panel_cls
                else:
                    from src.ui.dialogs.technical_service_technician_panel import TechnicalServiceTechnicianPanel as panel_cls

                panel = panel_cls(self.db, row, self, read_only=True)
                panel.exec()
        except Exception as e:
            logger.error(f"Failed to open read-only technician panel from ArchiveDetailDialog: {e}")

    
    def _build_logs_tab(self):
        w = QFrame()
        layout = QVBoxLayout(w)
        from PyQt6.QtWidgets import QAbstractItemView
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["TARİH", "TÜR", "MESAJ"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        for i, log in enumerate(self.logs or []):
            table.insertRow(i)
            date = str(log[4]) if len(log) > 4 else ""
            typ = str(log[2]) if len(log) > 2 else ""
            msg = str(log[3]) if len(log) > 3 else ""
            item_date = QTableWidgetItem(date)
            item_type = QTableWidgetItem(typ)
            item_msg = QTableWidgetItem(msg)
            if typ == "Customer":
                color = qc("surface_alt")
            elif typ == "System":
                color = qc("surface")
            else:
                color = qc("selection_text")
            for it in [item_date, item_type, item_msg]:
                it.setBackground(color)
            table.setItem(i, 0, item_date)
            table.setItem(i, 1, item_type)
            table.setItem(i, 2, item_msg)
        layout.addWidget(table)
        return w
    
    def _build_parts_tab(self):
        w = QFrame()
        layout = QVBoxLayout(w)
        from PyQt6.QtWidgets import QAbstractItemView
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["PARÇA", "ADET", "FİYAT", "TARİH"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        for i, r in enumerate(self.parts or []):
            table.insertRow(i)
            name = str(r[3]) if len(r) > 3 else ""
            qty_val = r[5] if len(r) > 5 and r[5] is not None else 1
            qty = str(qty_val)
            try:
                price = f"{float(r[4] or 0) * int(qty_val or 1):,.2f}"
            except Exception:
                price = str(r[4]) if len(r) > 4 else ""
            created = str(r[8]) if len(r) > 8 else ""
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem(qty))
            table.setItem(i, 2, QTableWidgetItem(price))
            table.setItem(i, 3, QTableWidgetItem(created))
        layout.addWidget(table)
        return w
    
    def _build_photos_tab(self):
        w = QFrame()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._build_photo_group("Giriş Fotoğrafları", self.images_entry))
        layout.addWidget(self._build_photo_group("Çıkış/İşlem Fotoğrafları", self.images_exit))
        if self.images_other:
            layout.addWidget(self._build_photo_group("Genel", self.images_other))
        return w
    
    def _build_photo_group(self, title, paths):
        grp = QFrame()
        grp.setStyleSheet(theme_qss(f"background:{DesignTokens.SECONDARY}; border:1px solid {DesignTokens.BORDER}; border-radius:{DesignTokens.RADIUS_LG};"))
        vl = QVBoxLayout(grp)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.addWidget(QLabel(title))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        grid = QHBoxLayout(cont)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)
        for p in paths or []:
            lbl = QLabel()
            lbl.setFixedSize(QSize(180, 140))
            lbl.setStyleSheet(theme_qss("background:@surface_alt;border-radius:10px"))
            if os.path.exists(p):
                pix = QPixmap(p).scaled(180, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(pix)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.mousePressEvent = lambda e, path=p: self._open_fullscreen(path)
            grid.addWidget(lbl)
        grid.addStretch()
        cont.setLayout(grid)
        scroll.setWidget(cont)
        vl.addWidget(scroll)
        return grp
    
    def _open_fullscreen(self, path):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dlg.resize(900, 600)
        fr = QFrame()
        fr.setStyleSheet(theme_qss("background:@surface_alt;border-radius:12px"))
        lay = QVBoxLayout(fr)
        img = QLabel()
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(path):
            pix = QPixmap(path).scaled(850, 550, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img.setPixmap(pix)
        lay.addWidget(img)
        btn = QPushButton("Kapat")
        btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        cw = QVBoxLayout(dlg)
        cw.addWidget(fr)
        dlg.exec()


