from src.ui.dialogs.stock_import_preview_dialog import StockImportPreviewDialog
from src.utils.stock_import_parser import StockImportParser


def test_invoice_table_reads_code_unit_and_skips_summary_rows():
    header = [
        "S\u0131ra No",
        "\u00dcr\u00fcn Kod",
        "Mal Hizmet",
        "Miktar",
        "Birim Fiyat",
        "KDV Oran\u0131",
        "KDV Tutar\u0131",
        "Tutar",
    ]
    rows = StockImportParser._parse_table_rows(
        [
            header,
            [
                "9",
                "SPD-\n9524S4L",
                "SUPREMA 2MP DOME KAMERA",
                "20Adet",
                "20USD",
                "%20,00",
                "80,00USD",
                "400,00USD",
            ],
            [None, "Toplam \u0130skonto", "0,00USD", "", "", "", "", ""],
        ]
    )

    assert len(rows) == 1
    assert rows[0]["code"] == "SPD-9524S4L"
    assert rows[0]["unit"] == "Adet"
    assert rows[0]["stock"] == 20
    assert rows[0]["purchase_price"] == 20.0
    assert rows[0]["currency"] == "USD"


def test_invoice_metadata_reads_seller_company_before_buyer():
    text = (
        "KEDACOM B\u0130L\u0130\u015e\u0130M A.\u015e KEDACOM\n"
        "Vergi Dairesi: \u015e\u0130\u015eL\u0130\n"
        "SAYIN\n"
        "ALICI ADI\n"
        "Fatura No: INV-1\n"
    )

    metadata = StockImportParser._extract_document_metadata(text)

    assert metadata["supplier_company"] == "KEDACOM B\u0130L\u0130\u015e\u0130M A.\u015e"
    assert metadata["invoice_no"] == "INV-1"


def test_technical_stock_preview_hides_irrelevant_columns():
    assert "compatible_models" not in StockImportPreviewDialog.TECH_FIELDS
    assert "condition" not in StockImportPreviewDialog.TECH_FIELDS
    assert "code" in StockImportPreviewDialog.TECH_FIELDS
    assert "supplier" in StockImportPreviewDialog.TECH_FIELDS
