# -*- coding: utf-8 -*-
"""
src/utils/error_handler.py
Uygulama geneli hata yönetimi ve özel istisna sınıfları.

transaction_page.py ve diğer modüller tarafından import edilir.
"""

from src.utils.logger import logger


class ValidationError(Exception):
    """Form doğrulama hatası. Kullanıcıya gösterilecek mesajları taşır."""

    def __init__(self, message: str, field: str = ""):
        super().__init__(message)
        self.message = message
        self.field = field

    def __str__(self):
        if self.field:
            return f"[{self.field}] {self.message}"
        return self.message


class DatabaseError(Exception):
    """Veritabanı işlemi hatası."""

    def __init__(self, message: str, query: str = ""):
        super().__init__(message)
        self.message = message
        self.query = query


class PermissionError(Exception):
    """Yetki hatası."""

    def __init__(self, message: str = "Bu işlem için yetkiniz bulunmuyor."):
        super().__init__(message)
        self.message = message


def handle_error(error: Exception, context: str = "", show_traceback: bool = False) -> str:
    """
    Hataları merkezi olarak işler ve log kaydı oluşturur.

    Args:
        error: Yakalanan istisna
        context: Hatanın oluştuğu bağlam (örn: "TransactionPage.save_transaction")
        show_traceback: True ise tam traceback loglanır

    Returns:
        Kullanıcıya gösterilebilecek hata mesajı
    """
    if show_traceback:
        import traceback
        logger.error(f"[{context}] {type(error).__name__}: {error}\n{traceback.format_exc()}")
    else:
        logger.error(f"[{context}] {type(error).__name__}: {error}")

    if isinstance(error, ValidationError):
        return str(error)
    if isinstance(error, PermissionError):
        return error.message
    if isinstance(error, DatabaseError):
        return f"Veritabanı hatası: {error.message}"

    return f"Beklenmeyen bir hata oluştu: {type(error).__name__}"
