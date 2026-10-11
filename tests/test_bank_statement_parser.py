from decimal import Decimal

import pytest

from src.utils.bank_statement_parser import parse_bank_statement


def test_ofx_statement_preserves_signed_amounts_and_reference():
    text = """OFXHEADER:100
<OFX><BANKTRANLIST>
<STMTTRN><DTPOSTED>20260929120000<TRNAMT>-32400.00<FITID>EXP-44<MEMO>Parts purchase</STMTTRN>
<STMTTRN><DTPOSTED>20260930120000<TRNAMT>15000.00<FITID>INC-45<NAME>Service receipt</STMTTRN>
</BANKTRANLIST></OFX>"""
    rows = parse_bank_statement(text, ".ofx")
    assert [(row["date"], row["amount"], row["reference"]) for row in rows] == [
        ("2026-09-29", Decimal("-32400.00"), "EXP-44"),
        ("2026-09-30", Decimal("15000.00"), "INC-45"),
    ]


def test_mt940_statement_keeps_debit_and_credit():
    text = ":20:STATEMENT\n:61:260929D1850,50NTRFREF-1\n:86:Field fuel\n:61:260930C15000,00NTRFREF-2\n:86:Service income\n"
    rows = parse_bank_statement(text, ".mt940")
    assert rows[0]["amount"] == Decimal("-1850.50")
    assert rows[0]["description"] == "Field fuel"
    assert rows[1]["amount"] == Decimal("15000.00")


def test_statement_without_transactions_is_rejected():
    with pytest.raises(ValueError, match="No statement transactions"):
        parse_bank_statement(":20:EMPTY", ".mt940")
