# -*- coding: utf-8 -*-

from src.ui.pages.stock_page import StockPage


class TechnicalStockPage(StockPage):
    def _detect_automotive_mode(self):
        return False

    def _normalize_ui_texts(self):
        super()._normalize_ui_texts()
        self.hero_title.setText("Stok Yönetimi")
        self.hero_subtitle.setText(
            "Envanter, hareketler ve ürün girişlerini teknik servis operasyonu içinde yönetin."
        )
        self.hero_badge.setText("TEKNİK SERVİS STOK")
        self.tabs.setTabText(0, "📦 Stok Durumu")
        self.tabs.setTabText(1, "📋 Stok Hareketleri")
        if hasattr(self, "tab_guide"):
            self.tabs.setTabText(
                self.tabs.indexOf(self.tab_guide), "❓ Nasıl Kullanılır?"
            )
        if hasattr(self, "search_inp"):
            self.search_inp.setPlaceholderText("🔍 Ürün adı veya barkod ile ara...")
        if hasattr(self, "btn_critical"):
            self.btn_critical.setText("⚠️ Kritik Stoklar")
        if hasattr(self, "stock_empty_state"):
            try:
                self.stock_empty_state.set_title("Ürün Yok")
                self.stock_empty_state.set_message(
                    "Envanter boş veya kriterlere uyan ürün bulunamadı."
                )
            except Exception:
                pass
