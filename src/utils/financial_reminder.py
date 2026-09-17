# -*- coding: utf-8 -*-

"""
Financial Reminder Service - AI Asistan Vade Kontrolü
Kredi, çek ve senet vadelerini kontrol eder ve kullanıcıyı uyarır
"""
from datetime import datetime, timedelta
from src.utils.toast_notification_modern import ModernToast
from src.utils.currency_helper import CurrencyHelper


class FinancialReminderService:
    """
    Finansal vade hatırlatma servisi
    - T-1: 1 gün önce uyarı
    - T-0: Vade günü uyarı
    - T+X: Gecikme uyarısı
    """
    
    def __init__(self, db, parent_widget=None):
        self.db = db
        self.parent = parent_widget
        self.toast = ModernToast(parent_widget) if parent_widget else None

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount,
            db=self.db,
            include_try_reference=include_try_reference,
        )
    
    def check_due_dates(self):
        """Ana vade kontrol metodu - Her saat çağrılır"""
        # Kredi taksitlerini kontrol et
        self.check_loan_installments()
        
        # Çek ve senetleri kontrol et
        self.check_checks_and_notes()
    
    def check_loan_installments(self):
        """Kredi taksit vadelerini kontrol et"""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # T-1: Yarın vadesi gelenler
        upcoming = self.db.get_upcoming_installments(days=1)
        for inst in upcoming:
            due = datetime.strptime(inst['due_date'], '%Y-%m-%d').date()
            if due == tomorrow:
                self._show_loan_tomorrow_warning(inst)
        
        # T-0: Bugün vadesi gelenler
        today_str = today.strftime('%Y-%m-%d')
        today_due = [i for i in self.db.get_loan_installments_by_date(today_str)]
        for inst in today_due:
            if inst['status'] == 'Bekliyor':
                self._show_loan_today_warning(inst)
        
        # T+X: Vadesi geçenler
        overdue = self.db.get_overdue_installments()
        if len(overdue) > 0:
            self._show_loan_overdue_warning(overdue)
    
    def check_checks_and_notes(self):
        """Çek ve senet vadelerini kontrol et"""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Tüm aktif çek/senetleri al
        all_checks = self.db.get_checks_notes(status_filter='Portföyde')
        
        for check in all_checks:
            due = datetime.strptime(check['due_date'], '%Y-%m-%d').date()
            
            # T-1: Yarın
            if due == tomorrow:
                self._show_check_tomorrow_warning(check)
            
            # T-0: Bugün
            elif due == today:
                self._show_check_today_warning(check)
            
            # T+X: Geçmiş
            elif due < today:
                self._show_check_overdue_warning(check)
    
    # === KREDI UYARILARI ===
    
    def _show_loan_tomorrow_warning(self, inst):
        """Yarın vadesi gelen kredi taksiti uyarısı"""
        if not self.toast:
            return
        
        message = (
            f"⏰ Yarın {inst['bank_name']} Taksiti\n"
            f"💰 Tutar: {self._fmt_try(inst['total_amount'])}\n"
            f"📅 Vade: {inst['due_date']}"
        )
        
        self.toast.show_warning(message, duration=5000)
    
    def _show_loan_today_warning(self, inst):
        """Bugün vadesi gelen kredi taksiti uyarısı"""
        if not self.toast:
            return
        
        message = (
            f"🚨 BUGÜN Ödeme Günü!\n"
            f"🏦 {inst['bank_name']}\n"
            f"💰 {self._fmt_try(inst['total_amount'])}"
        )
        
        self.toast.show_error(message, duration=7000)
    
    def _show_loan_overdue_warning(self, overdue_list):
        """Vadesi geçmiş taksitler toplu uyarısı"""
        if not self.toast or len(overdue_list) == 0:
            return
        
        total_overdue = sum(i['total_amount'] for i in overdue_list)
        
        message = (
            f"❌ VADESİ GEÇMİŞ!\n"
            f"📊 {len(overdue_list)} adet taksit\n"
            f"💸 Toplam: {self._fmt_try(total_overdue)}"
        )
        
        self.toast.show_error(message, duration=10000)
    
    # === ÇEK/SENET UYARILARI ===
    
    def _show_check_tomorrow_warning(self, check):
        """Yarın vadesi gelen çek/senet uyarısı"""
        if not self.toast:
            return
        
        message = (
            f"⏰ Yarın Vadesi Dolan {check['type']}\n"
            f"👤 {check['issuer'] or check['recipient']}\n"
            f"💰 {self._fmt_try(check['amount'])}"
        )
        
        self.toast.show_warning(message, duration=5000)
    
    def _show_check_today_warning(self, check):
        """Bugün vadesi gelen çek/senet uyarısı"""
        if not self.toast:
            return
        
        check_no = check.get('check_no', 'N/A')
        message = (
            f"🚨 BUGÜN {check['type']} Vadesi!\n"
            f"🔢 No: {check_no}\n"
            f"💰 {self._fmt_try(check['amount'])}"
        )
        
        self.toast.show_error(message, duration=7000)
    
    def _show_check_overdue_warning(self, check):
        """Vadesi geçmiş çek/senet uyarısı"""
        if not self.toast:
            return
        
        message = (
            f"❌ Vadesi Geçmiş {check['type']}!\n"
            f"👤 {check['issuer'] or check['recipient']}\n"
            f"📅 Vade: {check['due_date']}"
        )
        
        self.toast.show_error(message, duration=10000)
    
    # === HELPER METHODS ===
    
    def get_financial_summary(self):
        """
        Finansal özet döndürür (AI asistan için)
        Returns: dict with total_cash, upcoming_debt, overdue_count
        """
        # Yaklaşan 7 günlük borç
        upcoming = self.db.get_upcoming_installments(days=7)
        upcoming_debt = sum(i['total_amount'] for i in upcoming)
        
        # Vadesi geçenler
        overdue = self.db.get_overdue_installments()
        overdue_count = len(overdue)
        overdue_amount = sum(i['total_amount'] for i in overdue)
        
        # Banka bakiyeleri - aktif hesapların toplam bakiyesi
        total_cash = 0.0
        try:
            self.db.cursor.execute(
                "SELECT COALESCE(SUM(current_balance), 0) FROM bank_accounts WHERE is_active = 1"
            )
            row = self.db.cursor.fetchone()
            total_cash = float(row[0]) if row and row[0] is not None else 0.0
        except Exception:
            pass

        return {
            'total_cash': total_cash,
            'upcoming_7days_debt': upcoming_debt,
            'upcoming_7days_count': len(upcoming),
            'overdue_count': overdue_count,
            'overdue_amount': overdue_amount
        }
