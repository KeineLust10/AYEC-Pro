from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_context_menu_matches_desktop_action_groups():
    source = (WEB / "customer-context-parity.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "_customers_ui_mixin.py").read_text(encoding="utf-8")
    start = source.index("const groups = [")
    end = source.index("function openPrintView", start)
    groups = source[start:end]
    expected = ["notes", "360", "edit", "service", "invoice", "payment", "whatsapp", "debt-reminder", "excel", "pdf", "print"]

    positions = []
    cursor = 0
    for action in expected:
        position = groups.index(f'"{action}"', cursor)
        positions.append(position)
        cursor = position + len(action) + 2

    desktop_menu = desktop[desktop.index("def populate_customer_menu"):desktop.index("def _on_table_cell_entered")]
    assert positions == sorted(positions)
    assert "if (action === \"notes\") return window.openCustomerNotes(customer);" in source
    assert 'activeGroups[3].push(["Se\\u00e7ilileri Excel Aktar", "selected-excel"])' in source
    assert 'data-customer-context-action="delete"' in source
    for desktop_action in (
        "CustomerNotesDialog",
        "self.open_customer_360",
        "self.create_service",
        "self.create_invoice",
        "self.record_payment",
        "self.send_whatsapp",
        "self.send_debt_reminder",
        "self.export_excel",
        "self.export_pdf",
        "self.print_list",
        'if hasattr(self, "_multi_select") and self._multi_select',
        "self.delete_customer",
    ):
        assert desktop_action in desktop_menu
