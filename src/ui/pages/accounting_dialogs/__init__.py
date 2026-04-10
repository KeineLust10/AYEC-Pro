# accounting_dialogs package - Modularized accounting dialogs
# This module provides dialog classes for accounting operations

from .transaction_details_dialog import TransactionDetailsDialog
from .add_income_dialog import AddIncomeDialog
from .add_expense_dialog import AddExpenseDialog
from .add_transfer_dialog import AddTransferDialog
from .tax_analysis_dialog import TaxAnalysisDialog

__all__ = [
    "TransactionDetailsDialog",
    "AddIncomeDialog",
    "AddExpenseDialog",
    "AddTransferDialog",
    "TaxAnalysisDialog",
]
