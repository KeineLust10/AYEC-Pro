# accounting_dialogs.py - Facade module for backward compatibility
# This file re-exports all dialog classes from the accounting_dialogs package

from .accounting_dialogs import (
    TransactionDetailsDialog,
    AddIncomeDialog,
    AddExpenseDialog,
    AddTransferDialog,
    TaxAnalysisDialog,
)

__all__ = [
    "TransactionDetailsDialog",
    "AddIncomeDialog",
    "AddExpenseDialog",
    "AddTransferDialog",
    "TaxAnalysisDialog",
]
