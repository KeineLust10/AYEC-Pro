import io
import json
import math
import os
import re
import tempfile
from datetime import date, datetime

from src.utils.path_helper import PathHelper


GIB_TARIFF_URL = (
    "https://cdn.gib.gov.tr/api/gibportal-file/file/getFileResources?"
    "objectKey=arsiv%2Fyardim-kaynaklar%2Fyararli-bilgiler%2F"
    "gelir-vergisi-tarifeleri%2Fgelir-vergisi-tarifesi-{year}.pdf"
)


FALLBACK_TARIFFS = {
    "2024": {
        "non_wage": [[110000, 0.15], [230000, 0.20], [580000, 0.27], [3000000, 0.35], [None, 0.40]],
        "wage": [[110000, 0.15], [230000, 0.20], [870000, 0.27], [3000000, 0.35], [None, 0.40]],
    },
    "2025": {
        "non_wage": [[158000, 0.15], [330000, 0.20], [800000, 0.27], [4300000, 0.35], [None, 0.40]],
        "wage": [[158000, 0.15], [330000, 0.20], [1200000, 0.27], [4300000, 0.35], [None, 0.40]],
    },
    "2026": {
        "non_wage": [[190000, 0.15], [400000, 0.20], [1000000, 0.27], [5300000, 0.35], [None, 0.40]],
        "wage": [[190000, 0.15], [400000, 0.20], [1500000, 0.27], [5300000, 0.35], [None, 0.40]],
    },
}


def _number(value):
    return int(str(value).replace(".", ""))


def _extract_numbers(text):
    return [_number(value) for value in re.findall(r"\d[\d.]*", text)]


def parse_gib_tariff_text(text, expected_year=None):
    normalized = " ".join(str(text or "").split())
    if expected_year and str(expected_year) not in normalized:
        raise ValueError("GIB tariff year could not be verified")

    matches = list(re.finditer(r"%\s*(15|20|27|35|40)\b", normalized))
    if len(matches) < 4:
        raise ValueError("GIB tariff rates could not be parsed")

    non_wage = []
    wage = []
    previous_end = 0
    for index, match in enumerate(matches):
        rate = int(match.group(1)) / 100.0
        segment = normalized[previous_end:match.start()]
        previous_end = match.end()
        numbers = _extract_numbers(segment)
        if not numbers:
            raise ValueError("GIB tariff threshold could not be parsed")

        lower_segment = segment.lower()
        is_open_ended = "den fazlas" in lower_segment or "dan fazlas" in lower_segment
        if is_open_ended:
            standard_limit = None
            wage_limit = None
        elif index == 0:
            standard_limit = numbers[-1]
            wage_limit = standard_limit
        else:
            standard_limit = numbers[0]
            wage_match = re.search(
                r"gelirlerinde\s+([\d.]+)\s*tl",
                lower_segment,
            )
            wage_limit = _number(wage_match.group(1)) if wage_match else standard_limit

        non_wage.append([standard_limit, rate])
        wage.append([wage_limit, rate])

    _validate_brackets(non_wage)
    _validate_brackets(wage)
    return {"non_wage": non_wage, "wage": wage}


def _validate_brackets(brackets):
    if not brackets or brackets[-1][0] is not None:
        raise ValueError("Tax tariff must end with an open bracket")
    previous = 0
    for limit, rate in brackets:
        if rate <= 0 or rate >= 1:
            raise ValueError("Invalid tax rate")
        if limit is not None:
            if limit <= previous:
                raise ValueError("Tax thresholds are not increasing")
            previous = limit


class IncomeTaxTariffService:
    CACHE_FILE = "income_tax_tariffs.json"
    FIRST_YEAR = 2013

    def __init__(self, cache_path=None):
        self.cache_path = cache_path or os.path.join(
            PathHelper.get_app_data_dir(), self.CACHE_FILE
        )

    def load(self):
        payload = {
            "updated_at": None,
            "source": "bundled_fallback",
            "years": dict(FALLBACK_TARIFFS),
        }
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                cached = json.load(handle)
            years = cached.get("years") or {}
            for year, tariff in years.items():
                _validate_brackets(tariff["non_wage"])
                _validate_brackets(tariff["wage"])
                payload["years"][str(year)] = tariff
            payload["updated_at"] = cached.get("updated_at")
            payload["source"] = cached.get("source") or "GIB"
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass
        return payload

    def available_years(self):
        return sorted((int(year) for year in self.load()["years"]), reverse=True)

    def get_tariff(self, year=None, income_type="non_wage"):
        payload = self.load()
        years = payload["years"]
        selected_year = str(year or date.today().year)
        if selected_year not in years:
            available = sorted((int(item) for item in years), reverse=True)
            if not available:
                raise ValueError("No income tax tariff is available")
            selected_year = str(available[0])
        kind = "wage" if income_type == "wage" else "non_wage"
        return int(selected_year), years[selected_year][kind], payload

    def calculate(self, tax_base, year=None, income_type="non_wage"):
        selected_year, brackets, payload = self.get_tariff(year, income_type)
        remaining = max(0.0, float(tax_base or 0.0))
        previous_limit = 0.0
        total = 0.0
        breakdown = []
        for upper_limit, rate in brackets:
            width = math.inf if upper_limit is None else float(upper_limit) - previous_limit
            taxable = min(remaining, width)
            if taxable <= 0:
                break
            chunk = taxable * float(rate)
            total += chunk
            breakdown.append(
                {
                    "lower": previous_limit,
                    "upper": upper_limit,
                    "base": taxable,
                    "rate": float(rate),
                    "tax": chunk,
                }
            )
            remaining -= taxable
            if upper_limit is not None:
                previous_limit = float(upper_limit)
        return {
            "year": selected_year,
            "income_type": income_type,
            "tax_base": max(0.0, float(tax_base or 0.0)),
            "tax": total,
            "brackets": breakdown,
            "source": payload.get("source"),
            "source_url": payload["years"][str(selected_year)].get(
                "source_url", GIB_TARIFF_URL.format(year=selected_year)
            ),
            "updated_at": payload.get("updated_at"),
        }

    def is_refresh_due(self, now=None):
        payload = self.load()
        updated_at = payload.get("updated_at")
        if not updated_at:
            return True
        try:
            return datetime.fromisoformat(updated_at).date() < (now or datetime.now()).date()
        except ValueError:
            return True

    def refresh_if_due(self, force=False):
        if not force and not self.is_refresh_due():
            return {"updated": False, "reason": "already_current"}

        import requests
        from pypdf import PdfReader

        years = dict(self.load()["years"])
        fetched = 0
        fetched_years = []
        current_year = date.today().year
        for year in range(self.FIRST_YEAR, current_year + 2):
            try:
                url = GIB_TARIFF_URL.format(year=year)
                response = requests.get(url, timeout=15)
                if response.status_code != 200 or not response.content.startswith(b"%PDF"):
                    continue
                reader = PdfReader(io.BytesIO(response.content))
                text = "\n".join((page.extract_text() or "") for page in reader.pages)
                years[str(year)] = parse_gib_tariff_text(text, expected_year=year)
                years[str(year)]["source_url"] = url
                fetched += 1
                fetched_years.append(year)
            except Exception:
                continue

        if not fetched:
            raise RuntimeError("No GIB income tax tariff could be downloaded")

        payload = {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "source": "Gelir Idaresi Baskanligi (GIB)",
            "years": years,
        }
        self._write_atomic(payload)
        return {
            "updated": True,
            "years": fetched,
            "fetched_years": fetched_years,
            "updated_at": payload["updated_at"],
        }

    def _write_atomic(self, payload):
        directory = os.path.dirname(self.cache_path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix="tax-tariff-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=True, indent=2)
            os.replace(temp_path, self.cache_path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
