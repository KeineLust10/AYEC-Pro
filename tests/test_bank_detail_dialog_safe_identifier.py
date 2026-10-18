import pytest

from src.ui.dialogs.bank_detail_dialog import BankDetailDialog


def test_bank_detail_table_identifier_accepts_known_schema_name():
    assert BankDetailDialog._safe_identifier("bank_accounts") == "bank_accounts"


@pytest.mark.parametrize("name", ["bank_accounts; DROP TABLE users", "name space", "", "1table"])
def test_bank_detail_table_identifier_rejects_unsafe_names(name):
    with pytest.raises(ValueError, match="Invalid database identifier"):
        BankDetailDialog._safe_identifier(name)
