from datetime import datetime

from src.utils.income_tax_tariff_service import (
    IncomeTaxTariffService,
    parse_gib_tariff_text,
)


GIB_2025_TEXT = """
Gelir Vergisi Tarifesi 2025
158.000 TL'ye kadar % 15
330.000 TL'nin 158.000 TL'si icin 23.700 TL, fazlasi % 20
800.000 TL'nin 330.000 TL'si icin 58.100 TL
(ucret gelirlerinde 1.200.000 TL'nin 330.000 TL'si icin 58.100 TL), fazlasi % 27
4.300.000 TL'nin 800.000 TL'si icin 185.000 TL
(ucret gelirlerinde 4.300.000 TL'nin 1.200.000 TL'si icin 293.000 TL), fazlasi % 35
4.300.000 TL'den fazlasinin 4.300.000 TL'si icin 1.410.000 TL, fazlasi % 40
"""


def test_gib_parser_keeps_wage_and_non_wage_thresholds_separate():
    result = parse_gib_tariff_text(GIB_2025_TEXT, expected_year=2025)

    assert result["non_wage"][2] == [800000, 0.27]
    assert result["wage"][2] == [1200000, 0.27]


def test_2026_non_wage_boundaries_use_official_progressive_tariff(tmp_path):
    service = IncomeTaxTariffService(cache_path=str(tmp_path / "tariffs.json"))

    assert service.calculate(190000, 2026, "non_wage")["tax"] == 28500
    assert service.calculate(400000, 2026, "non_wage")["tax"] == 70500
    assert service.calculate(1000000, 2026, "non_wage")["tax"] == 232500
    assert service.calculate(5300000, 2026, "non_wage")["tax"] == 1737500
    assert service.calculate(5400000, 2026, "non_wage")["tax"] == 1777500


def test_2026_wage_boundaries_use_wage_specific_threshold(tmp_path):
    service = IncomeTaxTariffService(cache_path=str(tmp_path / "tariffs.json"))

    assert service.calculate(1500000, 2026, "wage")["tax"] == 367500
    assert service.calculate(5300000, 2026, "wage")["tax"] == 1697500


def test_daily_refresh_is_due_only_on_a_new_day(tmp_path):
    cache_path = tmp_path / "tariffs.json"
    cache_path.write_text(
        '{"updated_at":"2026-07-18T10:00:00","source":"GIB","years":{}}',
        encoding="utf-8",
    )
    service = IncomeTaxTariffService(cache_path=str(cache_path))

    assert service.is_refresh_due(datetime(2026, 7, 18, 23, 59, 59)) is False
    assert service.is_refresh_due(datetime(2026, 7, 19, 0, 0, 1)) is True
