from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFormLayout, QRadioButton, QButtonGroup, QComboBox, QDoubleSpinBox, QSpinBox,
                             QFrame, QGraphicsDropShadowEffect, QFileDialog, QScrollArea, QApplication, QCompleter)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QSize
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.design_system import DesignTokens
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger
from src.ui.widgets.modern_dialog import ModernDialog, NoWheelScrollArea

class AddStockDialog(ModernDialog):
    CATEGORY_BRAND_MAP = {
        "Güvenlik Sistemleri": [
            "Hikvision", "Dahua", "Axis", "Hanwha Vision", "Bosch", "Uniview", "Tiandy",
            "Vivotek", "Avigilon", "Pelco", "Honeywell", "Mobotix", "TVT", "HiLook",
            "Ezviz", "Milesight", "Reolink", "Provision-ISR",
        ],
        "Bilgisayar Bileşenleri": [
            "ASUS", "MSI", "Gigabyte", "ASRock", "Intel", "AMD", "NVIDIA", "Sapphire",
            "PowerColor", "Zotac", "PNY", "Palit", "Gainward", "Corsair", "Kingston", "Samsung",
            "WD", "Western Digital", "Seagate", "Crucial", "G.Skill", "TeamGroup", "ADATA",
            "Apacer", "DeepCool", "Cooler Master", "Noctua", "Arctic", "Thermal Grizzly",
            "Lian Li", "NZXT", "Thermaltake", "be quiet!", "Seasonic", "FSP", "SilverStone",
            "InWin", "Fractal Design", "Phanteks", "XPG",
        ],
        "Akıllı Ev Sistemleri": [
            "WiiHOM", "WiiPro", "TP-Link", "Ubiquiti", "MikroTik", "Ruijie", "Mercusys", "Tenda",
        ],
        "Ağ / Network": [
            "TP-Link", "Ubiquiti", "MikroTik", "Ruijie", "Mercusys", "Tenda",
        ],
    }

    CATEGORY_KEYWORDS = {
        "Güvenlik Sistemleri": [
            "kamera", "nvr", "dvr", "ip kamera", "güvenlik", "guvenlik", "cctv", "dedektör",
            "dedektor", "alarm", "siren", "poe", "bullet", "dome", "ptz", "interkom",
        ],
        "Bilgisayar Bileşenleri": [
            "anakart", "işlemci", "islemci", "cpu", "ram", "ssd", "hdd", "ekran kartı",
            "gpu", "psu", "güç kaynağı", "guc kaynagi", "kasa", "monitör", "monitor",
            "klavye", "mouse", "thermal", "termal", "soğutucu", "sogutucu", "nvme",
        ],
        "Akıllı Ev Sistemleri": [
            "akıllı", "akilli", "zigbee", "gateway", "hub", "termostat", "priz", "röle",
            "role", "perde", "dimmer", "aydınlatma", "aydinlatma", "wiihom", "wiipro",
        ],
        "Ağ / Network": [
            "router", "switch", "modem", "access point", "erişim noktası", "erisim noktasi",
            "network", "ağ", "ag", "ethernet", "cat6", "patch panel",
        ],
        "Sarf Malzeme": [
            "kablo bağı", "kablo bagi", "temizlik", "sprey", "etiket", "bant", "vida", "termal macun",
        ],
        "Aksesuar": [
            "adaptör", "adaptor", "aparat", "mount", "braket", "askı", "aski", "raf", "stand",
        ],
    }

    BUILTIN_BRAND_SUGGESTIONS = [
        # Security / CCTV
        "Hikvision", "Dahua", "Axis", "Hanwha Vision", "Bosch", "Uniview", "Tiandy",
        "Vivotek", "Avigilon", "Pelco", "Honeywell", "Mobotix", "TVT", "TP-Link", "HiLook",
        "Ezviz", "Milesight", "Reolink", "Provision-ISR", "Sony", "Panasonic",
        # PC components
        "ASUS", "MSI", "Gigabyte", "ASRock", "Intel", "AMD", "NVIDIA", "Sapphire",
        "PowerColor", "Zotac", "PNY", "Palit", "Gainward", "Corsair", "Kingston", "Samsung",
        "WD", "Western Digital", "Seagate", "Crucial", "G.Skill", "TeamGroup", "ADATA",
        "Apacer", "DeepCool", "Cooler Master", "Noctua", "Arctic", "Thermal Grizzly",
        "Lian Li", "NZXT", "Thermaltake", "be quiet!", "Seasonic", "FSP", "SilverStone",
        "InWin", "Fractal Design", "Phanteks", "XPG", "Biostar", "Dell", "HP", "Lenovo",
        "Acer", "BenQ", "AOC", "ViewSonic", "Logitech", "Razer", "SteelSeries", "HyperX",
        # Smart home / networking
        "WiiHOM", "WiiPro", "Ubiquiti", "MikroTik", "Ruijie", "Tenda", "Mercusys",
    ]

    def __init__(self, db, parent=None, item_id=None, *args, **kwargs):
        # Backward compatibility:
        # some call sites may still pass an extra positional argument.
        if item_id is None and args:
            item_id = args[0]
        super().__init__(title="Yeni Stok Ekle", parent=parent, width=1080, height=860)
        self.db = db
        self.item_id = item_id
        self._photo_path = None  # seçili fotoğraf yolu
        self.set_footer_visible(False)
        self.resize(1080, 860)
        self.setMinimumSize(1020, 820)
        self.setup_ui()
        self._setup_brand_completer()
        self._load_item_if_edit_mode()
        
        # Entrance Animation
        self.setWindowOpacity(0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()


    def _load_item_if_edit_mode(self):
        if not self.item_id:
            return
        try:
            self.db.cursor.execute("SELECT * FROM parts WHERE id=?", (self.item_id,))
            row = self.db.cursor.fetchone()
            if not row:
                return

            if hasattr(row, 'keys'):
                def val(k, d=None):
                    return row[k] if k in row.keys() else d
            else:
                def val(k, d=None):
                    return d

            self.inp_name.setText(str(val('name', '') or ''))
            self.inp_brand.setText(str(val('brand', '') or ''))
            self.inp_category.setCurrentText(str(val('category', '') or ''))
            self.inp_code.setText(str(val('code', '') or ''))
            self.inp_stock.setValue(int(float(val('stock', 0) or 0)))
            self.inp_min_stock.setValue(int(float(val('min_stock', 0) or 0)))
            self.inp_purchase_price.setValue(float(val('purchase_price', 0) or 0))

            self.inp_price.setValue(float(val('price', 0) or 0))
            self.inp_desc.setText(str(val('description', '') or ''))
            
            # Load Currency
            saved_curr = str(val('currency', 'TRY') or 'TRY')
            if saved_curr == 'USD': self.btn_usd.setChecked(True)
            elif saved_curr == 'EUR': self.btn_eur.setChecked(True)
            else: self.btn_try.setChecked(True)

            # Load Photo
            saved_photo = val('photo_path')
            if saved_photo:
                import os
                if os.path.exists(saved_photo):
                    self._photo_path = saved_photo
                    pix = QPixmap(saved_photo).scaled(
                        QSize(86, 86),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.lbl_photo_preview.setPixmap(pix)
                    self.lbl_photo_preview.setStyleSheet(
                        theme_qss("border: 2px solid @accent; border-radius: 10px; background: @surface_alt;")
                    )
                    self.btn_clear_photo.setVisible(True)

        except Exception as e:
            logger.warning(f"AddStock edit-mode preload failed: {e}")

    def _load_brand_suggestions(self):
        suggestions = set(self.BUILTIN_BRAND_SUGGESTIONS)
        try:
            self.db.cursor.execute(
                "SELECT DISTINCT brand FROM parts WHERE brand IS NOT NULL AND TRIM(brand) != '' ORDER BY brand COLLATE NOCASE"
            )
            for row in self.db.cursor.fetchall() or []:
                value = row["brand"] if hasattr(row, "keys") and "brand" in row.keys() else row[0]
                text = str(value or "").strip()
                if text:
                    suggestions.add(text)
        except Exception as e:
            logger.debug(f"Brand suggestions load from parts failed: {e}")

        try:
            self.db.cursor.execute(
                "SELECT DISTINCT brand FROM device_brands WHERE brand IS NOT NULL AND TRIM(brand) != '' AND COALESCE(is_active,1)=1 ORDER BY brand COLLATE NOCASE"
            )
            for row in self.db.cursor.fetchall() or []:
                value = row["brand"] if hasattr(row, "keys") and "brand" in row.keys() else row[0]
                text = str(value or "").strip()
                if text:
                    suggestions.add(text)
        except Exception as e:
            logger.debug(f"Brand suggestions load from device_brands failed: {e}")

        return sorted(suggestions, key=lambda x: x.lower())

    def _setup_brand_completer(self):
        brand_list = self._ordered_brand_suggestions()
        self.brand_completer = QCompleter(brand_list, self)
        self.brand_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.brand_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.brand_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.inp_brand.setCompleter(self.brand_completer)
        self.inp_brand.editingFinished.connect(self._normalize_brand_input)

    def _ordered_brand_suggestions(self):
        all_suggestions = self._load_brand_suggestions()
        current_category = str(getattr(self, "inp_category", None).currentText() if hasattr(self, "inp_category") else "" or "").strip()
        category_brands = self.CATEGORY_BRAND_MAP.get(current_category, [])
        prioritized = [brand for brand in category_brands if brand in all_suggestions]
        remaining = [brand for brand in all_suggestions if brand not in prioritized]
        return prioritized + remaining

    def _refresh_brand_completer(self):
        if not hasattr(self, "brand_completer"):
            return
        model = self.brand_completer.model()
        if hasattr(model, "setStringList"):
            model.setStringList(self._ordered_brand_suggestions())

    def _smart_brand_case(self, text):
        known_upper = {"asus", "msi", "hp", "lg", "tp-link", "tplink", "amd", "amd", "cpu", "gpu", "ssd", "hdd", "wd"}
        known_mixed = {
            "wiihom": "WiiHOM",
            "wiipro": "WiiPro",
            "tp-link": "TP-Link",
            "tplink": "TP-Link",
            "gskill": "G.Skill",
            "g.skill": "G.Skill",
            "iphone": "iPhone",
        }

        normalized = str(text or "").strip()
        if not normalized:
            return ""

        lookup = normalized.lower()
        if lookup in known_mixed:
            return known_mixed[lookup]
        if lookup in known_upper:
            return normalized.upper().replace("TPLINK", "TP-LINK")

        parts = []
        for word in normalized.split():
            lower_word = word.lower()
            if lower_word in known_mixed:
                parts.append(known_mixed[lower_word])
                continue
            if lower_word in known_upper:
                parts.append(word.upper().replace("TPLINK", "TP-LINK"))
                continue
            if "-" in word:
                parts.append("-".join(piece[:1].upper() + piece[1:].lower() if piece else "" for piece in word.split("-")))
                continue
            parts.append(word[:1].upper() + word[1:].lower())
        return " ".join(parts)

    def _normalize_brand_input(self):
        raw = str(self.inp_brand.text() or "").strip()
        if not raw:
            return

        suggestions = self._ordered_brand_suggestions()
        raw_lower = raw.lower()

        exact = next((item for item in suggestions if item.lower() == raw_lower), None)
        if exact:
            self.inp_brand.setText(exact)
            return

        prefix_match = next((item for item in suggestions if item.lower().startswith(raw_lower)), None)
        if prefix_match:
            self.inp_brand.setText(prefix_match)
            return

        contains_match = next((item for item in suggestions if raw_lower in item.lower()), None)
        if contains_match and len(raw) >= 3:
            self.inp_brand.setText(contains_match)
            return

        self.inp_brand.setText(self._smart_brand_case(raw))

    def _suggest_category(self):
        if not hasattr(self, "inp_category"):
            return
        current = str(self.inp_category.currentText() or "").strip()
        haystack = " ".join([
            str(getattr(self, "inp_name", None).text() if hasattr(self, "inp_name") else "" or ""),
            str(getattr(self, "inp_brand", None).text() if hasattr(self, "inp_brand") else "" or ""),
            str(getattr(self, "inp_code", None).text() if hasattr(self, "inp_code") else "" or ""),
            str(getattr(self, "inp_desc", None).text() if hasattr(self, "inp_desc") else "" or ""),
        ]).lower()

        if not haystack.strip():
            return

        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in haystack)
            if score:
                scores[category] = score

        for category, brands in self.CATEGORY_BRAND_MAP.items():
            brand_score = sum(2 for brand in brands if brand.lower() in haystack)
            if brand_score:
                scores[category] = scores.get(category, 0) + brand_score

        if not scores:
            return

        best_category = max(scores.items(), key=lambda item: item[1])[0]
        if current in {"", "Genel", "Diğer"} or scores.get(current, 0) < scores[best_category]:
            self.inp_category.setCurrentText(best_category)
            self._refresh_brand_completer()

    def setup_ui(self):
        self.setStyleSheet(theme_qss("""
            QLabel { color: @text; background: transparent; }
            QLineEdit, QTextEdit, QComboBox, QAbstractSpinBox {
                color: @text;
                background: @surface;
                border: 1px solid @border;
            }
            QComboBox QAbstractItemView {
                color: @text;
                background: @surface;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
        """))
        # 1. Overlay Layout (for centering and shadow)
        main_layout = self.content_layout
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container Card
        self.container = QFrame()
        self.container.setObjectName("AddStockDialogContainer")
        self.container.setStyleSheet(theme_qss("""
            QFrame#AddStockDialogContainer {
                background-color: @surface;
                border-radius: 0px;
            }
        """))
        
        # Shadow
        self.container.setGraphicsEffect(None)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # --- HEADER ---
        header = QFrame()
        header.setFixedHeight(0)
        header.setStyleSheet("background: transparent; border: none;")
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(35, 0, 25, 0)
        
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size: 42px; background: transparent; border: none;")
        header_layout.addWidget(icon_lbl)
        
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_lbl = QLabel("Yeni Stok Ekle")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_lbl.setStyleSheet(theme_qss("color: @text; background: transparent; border: none;"))
        title_vbox.addWidget(title_lbl)
        
        subtitle_lbl = QLabel("Envanterinize yeni bir ürün veya parça kazandırın")
        subtitle_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; background: transparent; border: none;"))
        title_vbox.addWidget(subtitle_lbl)
        
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(36, 36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface;
                color: @text_muted;
                font-size: 18px;
                border-radius: 18px;
                border: 1px solid @border;
            }
            QPushButton:hover { background: @danger; color: @selection_text; }
        """))
        btn_close.clicked.connect(self.reject)
        header_layout.addWidget(btn_close)
        
        header.setVisible(False)
        container_layout.addWidget(header)
        
        # --- CONTENT ---
        content_frame = QFrame()
        content_frame.setStyleSheet(theme_qss("background-color: @surface; border: none;"))
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 12, 20, 12)
        content_layout.setSpacing(12)
        
        # Styles
        input_style = theme_qss("""
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                padding: 6px 12px;
                border: 1px solid @border;
                border-radius: 12px;
                background: @surface_alt;
                font-size: 13px;
                font-weight: 500;
                color: @text;
                min-height: 24px;
            }
            QSpinBox, QDoubleSpinBox {
                min-height: 42px;
                padding-right: 42px;
            }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 34px;
                background: @accent;
                color: @selection_text;
                border-left: 1px solid @border;
                subcontrol-origin: border;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-position: top right;
                border-top-right-radius: 12px;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-position: bottom right;
                border-bottom-right-radius: 12px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background: @success;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid @accent;
                background-color: @surface;
            }
        """)
        label_style = theme_qss("color: @text; font-size: 12px; font-weight: 700; margin-left: 2px; background: transparent;")
        
        # Row 1: Name + Brand
        r1 = QHBoxLayout()
        r1.setSpacing(16)
        v1 = QVBoxLayout(); v1.setSpacing(8)
        v1.addWidget(QLabel("Ürün Adı", styleSheet=label_style))
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Örn: iPhone 13 Ekran, SSD 500GB...")
        self.inp_name.setStyleSheet(input_style)
        self.inp_name.setMinimumHeight(42)
        self.inp_name.editingFinished.connect(self._suggest_category)
        v1.addWidget(self.inp_name)
        r1.addLayout(v1, 2)

        v1b = QVBoxLayout(); v1b.setSpacing(8)
        v1b.addWidget(QLabel("Marka", styleSheet=label_style))
        self.inp_brand = QLineEdit()
        self.inp_brand.setPlaceholderText("Örn: WiiHOM, ASUS, TP-Link...")
        self.inp_brand.setStyleSheet(input_style)
        self.inp_brand.setMinimumHeight(42)
        self.inp_brand.textEdited.connect(lambda _text: self._refresh_brand_completer())
        v1b.addWidget(self.inp_brand)
        r1.addLayout(v1b, 1)
        content_layout.addLayout(r1)
        
        # Row 2: Category & Code
        r2 = QHBoxLayout()
        r2.setSpacing(16)
        v2_1 = QVBoxLayout(); v2_1.setSpacing(8)
        v2_1.addWidget(QLabel("Kategori", styleSheet=label_style))
        self.inp_category = QComboBox()
        self.inp_category.addItems([
            "Genel", "Güvenlik Sistemleri", "Bilgisayar Bileşenleri",
            "Akıllı Ev Sistemleri", "Ağ / Network", "Yedek Parça",
            "Aksesuar", "Sarf Malzeme", "Diğer"
        ])
        self.inp_category.setEditable(True)
        self.inp_category.setStyleSheet(input_style)
        self.inp_category.setMinimumHeight(42)
        self.inp_category.currentTextChanged.connect(self._refresh_brand_completer)
        v2_1.addWidget(self.inp_category)
        r2.addLayout(v2_1, 1)
        
        v2_2 = QVBoxLayout(); v2_2.setSpacing(8)
        v2_2.addWidget(QLabel("Barkod / Ürün Kodu", styleSheet=label_style))
        self.inp_code = QLineEdit()
        self.inp_code.setPlaceholderText("Barkod okutun veya yazın...")
        self.inp_code.setStyleSheet(input_style)
        self.inp_code.setMinimumHeight(42)
        self.inp_code.editingFinished.connect(self._suggest_category)
        v2_2.addWidget(self.inp_code)
        r2.addLayout(v2_2, 2)
        content_layout.addLayout(r2)
        
        # Row 3: Stock & Min
        r3 = QHBoxLayout()
        r3.setSpacing(16)
        v3_1 = QVBoxLayout(); v3_1.setSpacing(8)
        v3_1.addWidget(QLabel("Mevcut Stok Miktarı", styleSheet=label_style))
        self.inp_stock = QSpinBox()
        self.inp_stock.setRange(0, 100000); self.inp_stock.setValue(1)
        self.inp_stock.setStyleSheet(input_style)
        self.inp_stock.setFixedHeight(42)
        v3_1.addWidget(self.inp_stock)
        r3.addLayout(v3_1, 1)
        
        v3_2 = QVBoxLayout(); v3_2.setSpacing(8)
        v3_2.addWidget(QLabel("Kritik Stok Limiti", styleSheet=label_style))
        self.inp_min_stock = QSpinBox()
        self.inp_min_stock.setRange(0, 10000); self.inp_min_stock.setValue(5)
        self.inp_min_stock.setStyleSheet(input_style)
        self.inp_min_stock.setFixedHeight(42)
        v3_2.addWidget(self.inp_min_stock)
        r3.addLayout(v3_2, 1)
        content_layout.addLayout(r3)
        

        # Currency Selection
        curr_layout = QHBoxLayout()
        curr_layout.setSpacing(10)
        curr_layout.addWidget(QLabel("Birim:", styleSheet=label_style))
        
        self.btn_grp_curr = QButtonGroup(self)
        self.btn_try = QRadioButton(CurrencyHelper.get_symbol(currency_code="TRY"))
        self.btn_usd = QRadioButton("$")
        self.btn_eur = QRadioButton("€")
        
        self.btn_grp_curr.addButton(self.btn_try, 1)
        self.btn_grp_curr.addButton(self.btn_usd, 2)
        self.btn_grp_curr.addButton(self.btn_eur, 3)
        
        # Style radio buttons like modern chips
        chip_style = theme_qss('''
            QRadioButton {
                background: @surface_alt;
                color: @text_muted;
                padding: 6px 14px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid @border;
            }
            QRadioButton::indicator { width: 0; height: 0; }
            QRadioButton:checked {
                background: @accent;
                color: @selection_text;
                border: 1px solid @accent;
            }
            QRadioButton:hover:!checked {
                background: @surface;
                color: @text;
            }
        ''')
        
        for btn in [self.btn_try, self.btn_usd, self.btn_eur]:
            btn.setStyleSheet(chip_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(34)
            curr_layout.addWidget(btn)
        curr_layout.addStretch()
        
        # Get default currency from settings
        default_curr = CurrencyHelper.get_code(self.db)
        if default_curr == "USD":
            self.btn_usd.setChecked(True)
        elif default_curr == "EUR":
            self.btn_eur.setChecked(True)
        else:
            self.btn_try.setChecked(True)
            
        def update_suffixes():
            sym = CurrencyHelper.get_symbol(currency_code="TRY")
            if self.btn_usd.isChecked(): sym = "$"
            elif self.btn_eur.isChecked(): sym = "€"
            self.inp_purchase_price.setSuffix(f" {sym}")
            self.inp_price.setSuffix(f" {sym}")
            
        self.btn_try.toggled.connect(update_suffixes)
        self.btn_usd.toggled.connect(update_suffixes)
        self.btn_eur.toggled.connect(update_suffixes)
        
        content_layout.addLayout(curr_layout)

        # Row 4: Purchase Price & Sales Price
        r4 = QHBoxLayout()
        r4.setSpacing(16)
        v4_1 = QVBoxLayout(); v4_1.setSpacing(8)
        v4_1.addWidget(QLabel("Alış Fiyatı (Birim)", styleSheet=label_style))
        self.inp_purchase_price = QDoubleSpinBox()
        self.inp_purchase_price.setRange(0, 1000000); self.inp_purchase_price.setSuffix(f" {CurrencyHelper.get_symbol(currency_code=CurrencyHelper.get_code(self.db))}")
        self.inp_purchase_price.setStyleSheet(input_style)
        self.inp_purchase_price.setFixedHeight(42)
        v4_1.addWidget(self.inp_purchase_price)
        r4.addLayout(v4_1, 1)
        
        v4_2 = QVBoxLayout(); v4_2.setSpacing(8)
        v4_2.addWidget(QLabel("Satış Fiyatı (Birim)", styleSheet=label_style))
        self.inp_price = QDoubleSpinBox()
        self.inp_price.setRange(0, 1000000); self.inp_price.setSuffix(f" {CurrencyHelper.get_symbol(currency_code=CurrencyHelper.get_code(self.db))}")
        self.inp_price.setStyleSheet(input_style)
        self.inp_price.setFixedHeight(42)
        v4_2.addWidget(self.inp_price)
        r4.addLayout(v4_2, 1)
        content_layout.addLayout(r4)
        
        # Row 5: Desc
        v5 = QVBoxLayout(); v5.setSpacing(8)
        v5.addWidget(QLabel("Ürün Açıklaması / Notlar", styleSheet=label_style))
        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Ürün hakkında detaylı bilgi girin...")
        self.inp_desc.setStyleSheet(input_style)
        self.inp_desc.setMinimumHeight(42)
        self.inp_desc.editingFinished.connect(self._suggest_category)
        v5.addWidget(self.inp_desc)
        content_layout.addLayout(v5)
        
        # Row 5b: Fotoğraf
        photo_row = QHBoxLayout()
        photo_row.setSpacing(14)
        photo_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_photo_preview = QLabel()
        self.lbl_photo_preview.setFixedSize(82, 82)
        self.lbl_photo_preview.setStyleSheet(theme_qss(
            "border: 2px dashed @border; border-radius: 10px; background: @surface_alt;"
        ))
        self.lbl_photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo_preview.setText("📷")
        self.lbl_photo_preview.setStyleSheet(self.lbl_photo_preview.styleSheet() + " font-size: 32px;")

        photo_btns = QVBoxLayout()
        photo_btns.setSpacing(6)
        btn_pick_photo = QPushButton("📂 Fotoğraf Seç")
        btn_pick_photo.setFixedHeight(36)
        btn_pick_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pick_photo.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; border: 1px solid @border; border-radius: 8px; color: @text; font-weight: 600; padding: 0 12px; }"
            "QPushButton:hover { background: @surface; }"
        ))
        btn_pick_photo.clicked.connect(self._pick_photo)

        self.btn_clear_photo = QPushButton("🗑️ Fotoğrafı Kaldır")
        self.btn_clear_photo.setFixedHeight(36)
        self.btn_clear_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_photo.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; border: 1px solid @border; border-radius: 8px; color: @text_muted; padding: 0 12px; }"
            "QPushButton:hover { color: @text; }"
        ))
        self.btn_clear_photo.clicked.connect(self._clear_photo)
        self.btn_clear_photo.setVisible(False)

        photo_label = QLabel("Ürün Fotoğrafı (Opsiyonel)")
        photo_label.setWordWrap(True)
        photo_label.setStyleSheet(label_style)
        photo_btns.addWidget(photo_label)
        photo_btns.addWidget(btn_pick_photo)
        photo_btns.addWidget(self.btn_clear_photo)
        photo_btns.addStretch()

        photo_row.addWidget(self.lbl_photo_preview)
        photo_row.addLayout(photo_btns)
        photo_row.addStretch()
        content_layout.addLayout(photo_row)

        # Row 6: Banka (Gider Fişi İçin)
        v6 = QVBoxLayout(); v6.setSpacing(8)
        v6.addWidget(QLabel("Ödeme Yapılacak Kasa/Banka (Opsiyonel)", styleSheet=label_style))
        self.cmb_bank = QComboBox()
        self.cmb_bank.setStyleSheet(input_style)
        self.cmb_bank.setMinimumHeight(42)
        self.cmb_bank.addItem("Seçiniz...", -1)
        try:
            if hasattr(self.db, 'get_bank_accounts'):
                banks = self.db.get_bank_accounts()
                for b in banks:
                    name = b.get('bank_name', 'Banka') if isinstance(b, dict) else b[1]
                    bid = b.get('id', -1) if isinstance(b, dict) else b[0]
                    self.cmb_bank.addItem(name, bid)
        except Exception as e:
            logger.warning(f"AddStock bank account preload failed: {e}")
        v6.addWidget(self.cmb_bank)
        content_layout.addLayout(v6)
        
        content_layout.addStretch()

        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(theme_qss("""
            QScrollArea {
                background: @surface;
                border: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: @border;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """))
        scroll.setWidget(content_frame)
        container_layout.addWidget(scroll, 1)
        
        # --- FOOTER ---
        footer = QFrame()
        footer.setFixedHeight(74)
        footer.setStyleSheet(theme_qss("""
            QFrame {
                background-color: transparent;
                border-top: 1px solid @border;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """))
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 8, 20, 8)
        footer_layout.setSpacing(15)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedSize(140, 50)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface;
                color: @text_muted;
                border: 1px solid @border;
                border-radius: 14px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: @surface_alt; color: @text; }
        """))
        btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(btn_cancel)
        
        footer_layout.addStretch()
        
        btn_save = QPushButton("✅ Ürünü Kaydet")
        btn_save.setFixedSize(200, 50)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss("""
            QPushButton {
                background: @success;
                color: @selection_text;
                border: none;
                border-radius: 14px;
                font-weight: 700;
                font-size: 15px;
            }
            QPushButton:hover { background: @accent_hover; }
        """))
        self.btn_save = btn_save
        btn_save.clicked.connect(self.save)
        footer_layout.addWidget(btn_save)
        
        container_layout.addWidget(footer)
        
        main_layout.addWidget(self.container)

    def _pick_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Fotoğraf Seç", "",
            "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._photo_path = path
            pix = QPixmap(path).scaled(
                QSize(86, 86),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_photo_preview.setPixmap(pix)
            self.lbl_photo_preview.setStyleSheet(
                theme_qss("border: 2px solid @accent; border-radius: 10px; background: @surface_alt;")
            )
            self.btn_clear_photo.setVisible(True)

    def _clear_photo(self):
        self._photo_path = None
        self.lbl_photo_preview.clear()
        self.lbl_photo_preview.setText("📷")
        self.lbl_photo_preview.setStyleSheet(
            theme_qss("border: 2px dashed @border; border-radius: 10px; background: @surface_alt; font-size: 32px;")
        )
        self.btn_clear_photo.setVisible(False)

    def save(self):
        # Disable button to prevent double clicks
        self.btn_save.setEnabled(False)
        self.btn_save.setText("⏳ Kaydediliyor...")
        QApplication.processEvents()

        name = self.inp_name.text().strip()
        if not name:
            show_warning(self, "Lütfen ürün adı giriniz!")
            self.btn_save.setEnabled(True)
            self.btn_save.setText("✅ Ürünü Kaydet")
            return
            
        category = self.inp_category.currentText()
        brand = self.inp_brand.text().strip()
        code = self.inp_code.text()
        stock = self.inp_stock.value()
        min_stock = self.inp_min_stock.value()

        purchase_price = self.inp_purchase_price.value()
        price = self.inp_price.value()
        desc = self.inp_desc.text()
        
        currency = 'TRY'
        if self.btn_usd.isChecked(): currency = 'USD'
        elif self.btn_eur.isChecked(): currency = 'EUR'
        
        bank_id = self.cmb_bank.currentData()
        
        if self.item_id:
            ok = self.db.update_part(self.item_id, name, category, stock, price, desc, min_stock, code, None, purchase_price, currency, photo_path=self._photo_path, brand=brand)
            part_id = self.item_id if ok else None
        else:
            part_id = self.db.add_part(name, category, stock, price, desc=desc, min_stock=min_stock, code=code, purchase_price=purchase_price, currency=currency, photo_path=self._photo_path, brand=brand)

        if part_id:
            # ... existing success logic ...
            finance_warning = None
            if not self.item_id and purchase_price > 0 and stock > 0:
                try:
                    total_cost = purchase_price * stock
                    b_id = None if bank_id == -1 else bank_id
                    pm_method = "Banka/Kasa" if b_id else "Nakit"
                    self.db.add_transaction(
                        t_type="Gider",
                        category="Stok Alımı",
                        amount=total_cost,
                        description=f"Stok Alımı: {stock} x {name}",
                        bank_account_id=b_id,
                        payment_method=pm_method,
                        currency=currency,
                        original_amount=total_cost,
                        selected_services=[{
                            "kind": "stock_purchase",
                            "name": name,
                            "quantity": stock,
                            "unit_price": purchase_price,
                            "currency": currency,
                            "line_total": total_cost,
                        }]
                    )
                except Exception as e:
                    logger.error("AddStockDialog bank slip transaction error: %s", e)
                    finance_warning = str(e)
            try:
                parent_page = self.parent() if callable(getattr(self, "parent", None)) else None
                main_window = getattr(parent_page, "main_window", None) or getattr(self.window(), "main_window", None)
                if main_window and hasattr(main_window, "stock_updated"):
                    main_window.stock_updated.emit()
                    for page_index in (40, 101):
                        page = getattr(main_window, "pages", {}).get(page_index)
                        if page and hasattr(page, "refresh_data"):
                            page.refresh_data()
            except Exception:
                pass
            if finance_warning:
                show_warning(self, f"Stok kaydedildi ancak finans fisine yazilamadi: {finance_warning}")
            else:
                if self.item_id:
                    show_success(self, "Stok karti guncellendi.")
                else:
                    show_success(self, "Stok karti ve finans kaydi olusturuldu.")
            self.accept()
        else:
            show_error(self, "Stok kartı eklenirken bir hata oluştu.")
            self.btn_save.setEnabled(True)
            self.btn_save.setText("✅ Ürünü Kaydet")
    
    def get_data(self):
        return {
            "name": self.inp_name.text(),
            "category": self.inp_category.currentText(),
            "code": self.inp_code.text(),
            "stock": self.inp_stock.value(),
            "min_stock": self.inp_min_stock.value(),
            "purchase_price": self.inp_purchase_price.value(),
            "price": self.inp_price.value(),
            "desc": self.inp_desc.text()
        }
