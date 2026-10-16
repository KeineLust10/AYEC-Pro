from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_loan_context_actions_use_shared_confirmation_dialogs():
    source = (ROOT / "Web_Arayuzu" / "web" / "loans.js").read_text(encoding="utf-8")
    assert "confirm(" not in source

    assert 'function confirmLoanAction(title, message, submitLabel, action, destructive=false)' in source
    assert 'confirmLoanAction("Krediyi \\u0130ptal Et"' in source
    assert 'Taksit kay\\u0131tlar\\u0131 silinmeyecektir.' in source
    assert 'confirmLoanAction("Krediyi Sil"' in source
    assert 't\\u00fcm taksitlerini silmek istiyor musunuz?' in source
    assert 'confirmLoanAction("Taksiti \\u00d6dendi Olarak \\u0130\\u015faretle"' in source
    assert '"/api/desktop/table/loans"' in source
    assert '`/api/desktop/loan-installments/${encodeURIComponent(id)}/status`' in source
