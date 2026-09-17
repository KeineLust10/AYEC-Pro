from PIL import Image

from src.utils.professional_proforma import (
    _PDF_METADATA_TITLE,
    _financial_summary_rows,
    _prepare_logo_source,
    _terms,
)


class _Db:
    def __init__(self, settings):
        self.settings = settings

    def get_setting(self, key, default=""):
        return self.settings.get(key, default)


class _Manager:
    def __init__(self, settings):
        self.db = _Db(settings)


def test_custom_offer_terms_follow_selected_currency():
    manager = _Manager(
        {
            "offer_contract": (
                "Fiyat : Amerikan Dolar\u0131 cinsinden verilmi\u015ftir.\n"
                "Odeme : Sipariste yuzde elli pesin."
            )
        }
    )

    terms = _terms(manager, "EUR", 15)

    assert terms.splitlines()[0] == "Fiyat : Teklif tutarlar\u0131 Euro (EUR) cinsindendir."
    assert "Amerikan Dolar\u0131" not in terms
    assert "Odeme : Sipariste yuzde elli pesin." in terms


def test_custom_offer_terms_correct_legacy_fifty_percent_suffix():
    manager = _Manager(
        {"offer_contract": "Odeme : Toplam tutarin %50'i pesin."}
    )

    terms = _terms(manager, "TRY", 15)

    assert "%50'si pesin" in terms
    assert "%50'i pesin" not in terms


def test_pdf_metadata_title_is_ascii_safe():
    assert _PDF_METADATA_TITLE == "FIYAT TEKLIFI"
    assert _PDF_METADATA_TITLE.isascii()


def test_foreign_currency_summary_includes_currency_and_try_blocks():
    rows = _financial_summary_rows(
        (3200, 0, 0.20, 640, 3840),
        "USD",
        totals_try=(136435.20, 0, 0.20, 27287.04, 163722.24),
    )

    assert [row[0] for row in rows[:5]] == [
        "Mal Hizmet Toplam Tutar\u0131",
        "Toplam \u0130skonto",
        "Hesaplanan KDV(%20.00)",
        "Vergiler Dahil Toplam Tutar",
        "\u00d6denecek Tutar",
    ]
    assert all("USD" in row[1] for row in rows[:5])
    assert all("TL" in row[1] for row in rows[5:])


def test_try_summary_does_not_include_foreign_currency_block():
    rows = _financial_summary_rows(
        (3200, 0, 0.20, 640, 3840),
        "TRY",
        totals_try=(3200, 0, 0.20, 640, 3840),
    )

    assert len(rows) == 5
    assert all("USD" not in row[1] for row in rows)
    assert all("TL" in row[1] for row in rows)


def test_dark_logo_is_cropped_and_made_print_safe(tmp_path):
    logo_path = tmp_path / "dark-logo.jpg"
    logo = Image.new("RGB", (400, 200), (0, 0, 0))
    for x in range(100, 300):
        for y in range(70, 130):
            logo.putpixel((x, y), (20, 90, 180))
    logo.save(logo_path, quality=95)

    prepared = _prepare_logo_source(str(logo_path))
    result = Image.open(prepared).convert("RGB")

    assert result.width < logo.width
    assert result.height < logo.height
    assert result.getpixel((0, 0))[0] > 240
