import os

files_to_patch = [
    r'src/ui/pages/accounting_dialogs.py',
    r'src/ui/pages/summary_page.py',
    r'src/ui/pages/dashboard_actions_mixin.py',
    r'src/ui/pages/customers/logic/customer_manager.py',
    r'src/ui/widgets/kanban_board.py',
    r'src/ui/pages/stock_page.py',
    r'src/ui/pages/transaction/dialogs/proforma_dialog.py',
    r'src/ui/pages/settings_widgets/job_service_number_widget.py',
    r'src/ui/pages/transaction_page_behaviors.py',
    r'src/utils/pdf_manager.py',
    r'src/utils/pdf_helper.py',
    r'src/ui/pages/quick_sale_page.py',
    r'src/ui/pages/reports_page.py',
    r'src/ui/pages/transaction_page.py',
    r'src/ui/pages/job_service_tracking_page.py',
    r'src/ui/pages/finance/bank_accounts_widget.py',
    r'src/ui/pages/finance/finance_report_page.py',
    r'src/ui/pages/customers_page.py',
    r'src/ui/pages/transaction/logic/price_calculator.py'
]

for fpath in files_to_patch:
    if not os.path.exists(fpath): continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    content = content.replace('{CurrencyHelper.get_symbol()}', '₺')
    
    # We might have f"0.00 ₺" now, let's turn it back to "0.00 ₺" where it makes sense, or keep it. Python evaluates f"0.00 ₺" as "0.00 ₺" anyway.
    content = content.replace('f"0.00 ₺"', '"0.00 ₺"')
    content = content.replace('f"0 ₺"', '"0 ₺"')
    content = content.replace('f" ₺"', '" ₺"')
    content = content.replace('.setSuffix(f" ₺")', '.setSuffix(" ₺")')

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

print('Reverted pseudo currency changes')
