#!/usr/bin/env python3
"""Validate OCR/import output against a private regression manifest.

The guard is read-only. It never changes source documents or application data.
Keep private invoice files outside the repository and reference them from a local
manifest.
"""

import argparse
import json
import sys
from pathlib import Path


def _matches(expected, actual):
    for key, value in expected.items():
        if key.endswith("_contains"):
            actual_key = key[: -len("_contains")]
            if str(value).casefold() not in str(actual.get(actual_key, "")).casefold():
                return False
        elif actual.get(key) != value:
            return False
    return True


def validate_result(case, result):
    """Return human-readable contract failures for one parsed document."""
    failures = []
    rows = result.get("rows") or []
    metadata = result.get("metadata") or {}

    minimum = int(case.get("min_rows", 0))
    maximum = case.get("max_rows")
    if len(rows) < minimum:
        failures.append(f"row count {len(rows)} is below {minimum}")
    if maximum is not None and len(rows) > int(maximum):
        failures.append(f"row count {len(rows)} is above {maximum}")

    for key, value in (case.get("metadata") or {}).items():
        if metadata.get(key) != value:
            failures.append(
                f"metadata {key!r}: expected {value!r}, got {metadata.get(key)!r}"
            )

    for expected_row in case.get("rows", []):
        if not any(_matches(expected_row, row) for row in rows):
            failures.append(f"expected row was not found: {expected_row!r}")

    forbidden_names = [
        str(value).casefold() for value in case.get("forbidden_name_contains", [])
    ]
    for row in rows:
        name = str(row.get("name", "")).casefold()
        for value in forbidden_names:
            if value in name:
                failures.append(f"forbidden summary row was imported: {row!r}")

    return failures


def run_manifest(manifest_path):
    from src.utils.stock_import_parser import StockImportParser

    manifest_path = Path(manifest_path).resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    if not cases:
        return ["manifest has no cases"]

    failures = []
    for index, case in enumerate(cases, start=1):
        name = case.get("name") or f"case-{index}"
        source = Path(case["source"])
        if not source.is_absolute():
            source = manifest_path.parent / source
        if not source.is_file():
            failures.append(f"{name}: source does not exist: {source}")
            continue
        try:
            result = StockImportParser.parse_file(source)
        except Exception as exc:
            failures.append(f"{name}: parser error: {exc}")
            continue
        failures.extend(f"{name}: {item}" for item in validate_result(case, result))
    return failures


def main():
    parser = argparse.ArgumentParser(description="Run OCR regression contracts")
    parser.add_argument("manifest", help="Path to the local JSON manifest")
    args = parser.parse_args()

    failures = run_manifest(args.manifest)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("OCR regression contracts passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
