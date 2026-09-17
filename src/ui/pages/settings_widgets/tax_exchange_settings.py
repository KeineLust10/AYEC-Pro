from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.design_system import DesignTokens
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.utils.tax_settings import TaxSettings
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success


class TaxExchangeSettingsWidget(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self._build_ui()
        self.load_values()

    @staticmethod
    def _style_numeric_input(spin):
        spin.setFixedWidth(260)
        spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        spin.setStyleSheet(
            theme_qss(
                """
                QDoubleSpinBox {
                    min-height: 38px;
                    padding: 0 38px 0 12px;
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 750;
                }
                QDoubleSpinBox:focus {
                    border-color: @accent;
                }
                QDoubleSpinBox::up-button,
                QDoubleSpinBox::down-button {
                    width: 30px;
                    background: @surface_alt;
                    border-left: 1px solid @border;
                }
                QDoubleSpinBox::up-button {
                    border-top-right-radius: 7px;
                    border-bottom: 1px solid @border;
                }
                QDoubleSpinBox::down-button {
                    border-bottom-right-radius: 7px;
                }
                """
            )
        )

    @staticmethod
    def _style_group(group):
        group.setStyleSheet(
            theme_qss(
                """
                QGroupBox {
                    margin-top: 10px;
                    padding: 18px 14px 14px 14px;
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 12px;
                    font-weight: 800;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 14px;
                    padding: 0 6px;
                    background: @surface;
                }
                QLabel {
                    color: @text;
                    background: transparent;
                    border: none;
                }
                """
            )
        )

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        title = QLabel("KDV ve Kur G\u00fcncelleme")
        title.setStyleSheet(
            theme_qss(
                "font-size: 24px; font-weight: 900; color: @text;"
            )
        )
        root.addWidget(title)

        description = QLabel(
            "Varsay\u0131lan KDV oran\u0131n\u0131 ve kullan\u0131lacak d\u00f6viz "
            "kurlar\u0131n\u0131 tek noktadan y\u00f6netin. Kaydedilen de\u011ferler "
            "sat\u0131\u015f, teklif, proforma ve fatura ekranlar\u0131na "
            "senkronize edilir."
        )
        description.setWordWrap(True)
        description.setStyleSheet(
            theme_qss("font-size: 12px; color: @text_muted;")
        )
        root.addWidget(description)

        vat_group = QGroupBox("KDV G\u00fcncelleme")
        self._style_group(vat_group)
        vat_form = QFormLayout(vat_group)
        vat_form.setSpacing(12)
        vat_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        vat_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.spin_vat = QDoubleSpinBox()
        self.spin_vat.setRange(0, 100)
        self.spin_vat.setDecimals(2)
        self.spin_vat.setSuffix(" %")
        self.spin_vat.setFixedHeight(38)
        self._style_numeric_input(self.spin_vat)
        vat_form.addRow("Varsay\u0131lan KDV:", self.spin_vat)
        self.btn_save_vat = QPushButton(
            "KDV'yi G\u00fcncelle ve Senkronize Et"
        )
        self.btn_save_vat.setFixedHeight(42)
        self.btn_save_vat.setStyleSheet(
            theme_qss(DesignTokens.get_button_qss("success"))
        )
        self.btn_save_vat.clicked.connect(self.save_vat)
        vat_form.addRow("", self.btn_save_vat)
        root.addWidget(vat_group)

        rate_group = QGroupBox("Kur G\u00fcncelleme")
        self._style_group(rate_group)
        rate_form = QFormLayout(rate_group)
        rate_form.setSpacing(12)
        rate_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        rate_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.rate_inputs = {}
        for code in ("USD", "EUR", "GBP"):
            spin = QDoubleSpinBox()
            spin.setRange(0.0001, 999999.0)
            spin.setDecimals(4)
            spin.setSuffix(" \u20ba")
            spin.setFixedHeight(38)
            self._style_numeric_input(spin)
            self.rate_inputs[code] = spin
            rate_form.addRow(f"{code} Sat\u0131\u015f Kuru:", spin)

        rate_actions = QHBoxLayout()
        self.btn_save_rates = QPushButton(
            "Yaz\u0131lan Kurlar\u0131 G\u00fcncelle"
        )
        self.btn_fetch_rates = QPushButton(
            "TCMB'den G\u00fcncel Kurlar\u0131 Al"
        )
        for button, variant in (
            (self.btn_save_rates, "primary"),
            (self.btn_fetch_rates, "secondary"),
        ):
            button.setFixedHeight(42)
            button.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss(variant))
            )
            rate_actions.addWidget(button)
        self.btn_save_rates.clicked.connect(self.save_manual_rates)
        self.btn_fetch_rates.clicked.connect(self.fetch_tcmb_rates)
        rate_form.addRow(rate_actions)
        self.lbl_rate_status = QLabel("")
        self.lbl_rate_status.setWordWrap(True)
        self.lbl_rate_status.setStyleSheet(
            theme_qss("font-size: 11px; color: @text_muted;")
        )
        rate_form.addRow("Son G\u00fcncelleme:", self.lbl_rate_status)
        root.addWidget(rate_group)

        sync_group = QGroupBox("Senkronizasyon ve Yedekleme")
        self._style_group(sync_group)
        sync_layout = QHBoxLayout(sync_group)
        self.btn_sync = QPushButton("Verileri Senkronize Et")
        self.btn_backup = QPushButton("Yedekleme Merkezini A\u00e7")
        for button in (self.btn_sync, self.btn_backup):
            button.setFixedHeight(42)
            button.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss("secondary"))
            )
            sync_layout.addWidget(button)
        self.btn_sync.clicked.connect(self.start_sync)
        self.btn_backup.clicked.connect(self.open_backup)
        root.addWidget(sync_group)
        root.addStretch()

    def load_values(self):
        self.spin_vat.setValue(TaxSettings.get_percent(self.db))
        for code, spin in self.rate_inputs.items():
            rate = ExchangeRateManager.get_current_rate(
                self.db,
                code,
                "selling",
            )
            spin.setValue(float(rate or 1.0))
        self._load_rate_status()

    def _load_rate_status(self):
        try:
            row = self.db.cursor.execute(
                """
                SELECT effective_date, source
                FROM exchange_rates
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
            if row:
                self.lbl_rate_status.setText(
                    f"{row[0] or '-'} | Kaynak: {row[1] or '-'}"
                )
                return
        except Exception:
            pass
        self.lbl_rate_status.setText("Hen\u00fcz kay\u0131tl\u0131 kur yok.")

    def _publish_revision(self):
        revision = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.db.set_setting("financial_defaults_revision", revision)

    def save_vat(self):
        try:
            percent = TaxSettings.set_percent(
                self.db,
                self.spin_vat.value(),
            )
            try:
                self.db.cursor.execute(
                    """
                    UPDATE product_bank_mappings
                    SET default_kdv_rate=?, updated_at=?
                    """,
                    (
                        percent,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                self.db.conn.commit()
            except Exception:
                pass
            self._publish_revision()
            show_success(
                self,
                f"Varsay\u0131lan KDV %{percent:g} olarak senkronize edildi.",
            )
        except Exception as exc:
            show_error(self, f"KDV g\u00fcncellenemedi: {exc}")

    def save_manual_rates(self):
        rates = {
            code: spin.value()
            for code, spin in self.rate_inputs.items()
        }
        if not ExchangeRateManager.save_manual_rates(self.db, rates):
            show_error(self, "Kurlar kaydedilemedi.")
            return
        self._publish_revision()
        self._load_rate_status()
        show_success(self, "Yaz\u0131lan kurlar senkronize edildi.")

    def fetch_tcmb_rates(self):
        self.btn_fetch_rates.setEnabled(False)
        try:
            rates = ExchangeRateManager.fetch_tcmb_rates()
            if not rates:
                show_error(self, "TCMB kurlar\u0131 al\u0131namad\u0131.")
                return
            if not ExchangeRateManager.save_rates_to_db(self.db, rates):
                show_error(self, "TCMB kurlar\u0131 kaydedilemedi.")
                return
            self._publish_revision()
            self.load_values()
            show_success(self, "TCMB kurlar\u0131 g\u00fcncellendi.")
        finally:
            self.btn_fetch_rates.setEnabled(True)

    def start_sync(self):
        if self.main_window and hasattr(
            self.main_window,
            "start_web_sync",
        ):
            self.main_window.start_web_sync(silent=False)
            return
        show_error(self, "Senkronizasyon servisi kullan\u0131lam\u0131yor.")

    def open_backup(self):
        if self.main_window and hasattr(self.main_window, "on_menu_click"):
            self.main_window.on_menu_click(180)
            return
        show_error(self, "Yedekleme merkezi a\u00e7\u0131lamad\u0131.")
