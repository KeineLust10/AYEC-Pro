# -*- coding: utf-8 -*-
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens

class PartnersPageStyleMixin:
    def apply_theme_styles(self):
        self.lbl_title.setStyleSheet(theme_qss("color: @text; font-size: 24px; font-weight: 800; background: transparent; border: none;"))
        self.lbl_sub.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; background: transparent; border: none;"))
        self.sidebar.setStyleSheet(theme_qss("background: transparent;"))
        self.workspace.setStyleSheet(theme_qss("background: transparent;"))
        for frame in (self.partner_hero, self.shipment_card):
            frame.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 18px;"))
        self.partner_name.setStyleSheet(theme_qss("color: @text; font-size: 26px; font-weight: 800; background: transparent; border: none;"))
        for lbl in (self.partner_meta, self.partner_scorecard, self.lbl_shipments_sub, self.lbl_total):
            lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; background: transparent; border: none;"))
        self.lbl_shipments_title.setStyleSheet(theme_qss("color: @text; font-size: 16px; font-weight: 700; background: transparent; border: none;"))
        self.partner_list.setStyleSheet(theme_qss(
            "QListWidget { background: @surface; border: 1px solid @border; border-radius: 16px; padding: 8px; }"
            "QListWidget::item { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 12px; padding: 12px; margin: 0 0 8px 0; }"
            "QListWidget::item:selected { background: @accent; color: @selection_text; border: none; }"
            "QListWidget::item:hover { border-color: @accent; }"
        ))
        table_qss = theme_qss(
            "QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; }"
            "QHeaderView::section { background: @surface_alt; color: @text; padding: 12px; font-weight: 700; border: none; }"
            "QTableWidget::item { color: @text; padding: 10px; border-bottom: 1px solid @border; }"
            "QTableWidget::item:selected { background: @accent; color: @selection_text; border: none; outline: none; }"
        )
        for t in (self.shipment_table, self.history_table): t.setStyleSheet(table_qss)
        self.empty_label.setStyleSheet(theme_qss("color: @text_muted; padding: 18px;"))
        self.history_empty_label.setStyleSheet(theme_qss("color: @text_muted; padding: 18px;"))
        self.partner_tabs.setStyleSheet(theme_qss(
            "QTabWidget::pane { border: none; background: transparent; }"
            "QTabBar::tab { background: @surface_alt; color: @text; padding: 10px 16px; border-radius: 12px; margin-right: 6px; border: 1px solid @border; font-weight: 700; }"
            "QTabBar::tab:selected { background: @accent; color: @selection_text; border: none; }"
        ))
        sum_qss = theme_qss("color: @text; background: transparent; border: none; line-height: 1.5;")
        for lbl in (self.notes_summary, self.finance_summary, self.documents_summary, self.timeline_summary, self.trends_summary):
            lbl.setStyleSheet(sum_qss)
        self.finance_card.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 14px;"))
        self.finance_commission.setStyleSheet(theme_qss("color: @text; font-size: 14px; font-weight: 700; background: transparent; border: none;"))
        self.finance_contact.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; background: transparent; border: none;"))
        btn_qss = theme_qss(DesignTokens.get_button_qss("primary"))
        for btn in (self.btn_add_partner, self.btn_add_shipment, self.btn_documents, self.btn_docs_center, self.btn_edit_partner, self.btn_more, self.btn_open_notes, self.btn_open_finance, self.btn_open_documents):
            btn.setStyleSheet(btn_qss)
        for card in (self.stat_total, self.stat_active, self.stat_done, self.stat_last):
            card.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 14px;"))
            card._value_label.setStyleSheet(theme_qss("color: @text; font-size: 22px; font-weight: 800; background: transparent; border: none;"))
            card._title_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 700; background: transparent; border: none;"))
        aux_qss = theme_qss(
            "QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; }"
            "QHeaderView::section { background: @surface_alt; color: @text; padding: 10px; font-weight: 700; border: none; }"
            "QTableWidget::item { color: @text; padding: 8px; border-bottom: 1px solid @border; }"
            "QTableWidget::item:selected { background: @accent; color: @selection_text; border: none; outline: none; }"
        )
        for t in (self.documents_table, self.timeline_table, self.trend_table): t.setStyleSheet(aux_qss)

    def refresh_theme(self): self.apply_theme_styles()
