from src.ui.pages.offer_pages import _filter_offer_rows


def test_offer_filters_match_status_and_currency_aliases():
    rows = [
        {"status": "Onayland\u0131", "currency_code": "TRY"},
        {"status": "pending", "currency_code": "USD"},
        {"status": "Reddedildi", "currency_code": "EUR"},
        {"status": "draft", "currency_code": "TRY"},
    ]

    assert _filter_offer_rows(rows, "accepted", "all") == [rows[0]]
    assert _filter_offer_rows(rows, "pending", "USD") == [rows[1]]
    assert _filter_offer_rows(rows, "rejected", "all") == [rows[2], rows[3]]
    assert _filter_offer_rows(rows, "all", "TRY") == [rows[0], rows[3]]
