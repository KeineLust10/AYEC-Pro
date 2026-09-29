"""Read-only reconciliation report for the AYEC customer ledger.

This tool never changes a database. It compares immutable currency movements,
payment links, stored balances, service parts, and duplicate tracking records.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def _table_exists(conn, name):
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone())


def reconcile(path):
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        result = {"database": str(path), "customers": [], "summary": {}}
        if not _table_exists(conn, "currency_transactions"):
            result["summary"]["error"] = "currency_transactions table is missing"
            return result

        customers = conn.execute(
            "SELECT id, name FROM customers ORDER BY id"
        ).fetchall() if _table_exists(conn, "customers") else []
        for customer in customers:
            cid = int(customer["id"])
            currencies = conn.execute(
                "SELECT DISTINCT currency FROM currency_transactions WHERE customer_id=?",
                (cid,),
            ).fetchall()
            customer_result = {"id": cid, "name": customer["name"], "currencies": []}
            for currency_row in currencies:
                currency = str(currency_row[0] or "TRY").upper()
                ledger = conn.execute(
                    """
                    SELECT
                      COALESCE(SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END), 0) AS debits,
                      COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END), 0) AS credits
                    FROM currency_transactions WHERE customer_id=? AND currency=?
                    """,
                    (cid, currency),
                ).fetchone()
                duplicate_credits = conn.execute(
                    """
                    SELECT tracking_no, COUNT(*) AS count, SUM(amount) AS amount
                    FROM currency_transactions
                    WHERE customer_id=? AND currency=? AND transaction_type='CREDIT'
                      AND COALESCE(tracking_no, '') <> ''
                    GROUP BY tracking_no HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    """,
                    (cid, currency),
                ).fetchall()
                open_debts = conn.execute(
                    """
                    SELECT d.id, d.tracking_no, d.amount,
                           COALESCE(linked.total, 0) AS linked_paid,
                           COALESCE(legacy.total, 0) AS legacy_paid
                    FROM currency_transactions d
                    LEFT JOIN (
                      SELECT debt_txn_id, SUM(amount) AS total
                      FROM payment_debt_links GROUP BY debt_txn_id
                    ) linked ON linked.debt_txn_id=d.id
                    LEFT JOIN (
                      SELECT d2.id, SUM(c.amount) AS total
                      FROM currency_transactions d2
                      JOIN currency_transactions c
                        ON c.customer_id=d2.customer_id AND c.currency=d2.currency
                       AND c.transaction_type='CREDIT'
                       AND (c.tracking_no=d2.tracking_no OR c.tracking_no=d2.tracking_no || '-PAY')
                       AND NOT EXISTS (
                         SELECT 1 FROM payment_debt_links p WHERE p.payment_txn_id=c.id
                       )
                      WHERE d2.transaction_type='DEBIT'
                      GROUP BY d2.id
                    ) legacy ON legacy.id=d.id
                    WHERE d.customer_id=? AND d.currency=? AND d.transaction_type='DEBIT'
                      AND d.amount - COALESCE(linked.total, 0) - COALESCE(legacy.total, 0) > 0.009
                    ORDER BY d.id
                    """,
                    (cid, currency),
                ).fetchall()
                stored = conn.execute(
                    "SELECT balance FROM customer_currency_balances WHERE customer_id=? AND currency=?",
                    (cid, currency),
                ).fetchone() if _table_exists(conn, "customer_currency_balances") else None
                customer_result["currencies"].append({
                    "currency": currency,
                    "debits": float(ledger["debits"] or 0),
                    "credits": float(ledger["credits"] or 0),
                    "ledger_balance": round(float(ledger["credits"] or 0) - float(ledger["debits"] or 0), 2),
                    "stored_balance": float(stored[0]) if stored else None,
                    "balance_mismatch": bool(stored and abs(float(stored[0]) - (float(ledger["credits"] or 0) - float(ledger["debits"] or 0))) > 0.009),
                    "duplicate_credits": [dict(row) for row in duplicate_credits],
                    "open_debts": [dict(row) for row in open_debts],
                })
            result["customers"].append(customer_result)

        result["summary"] = {
            "customer_count": len(result["customers"]),
            "duplicate_credit_groups": sum(
                len(item["duplicate_credits"])
                for customer in result["customers"]
                for item in customer["currencies"]
            ),
            "balance_mismatches": sum(
                int(item["balance_mismatch"])
                for customer in result["customers"]
                for item in customer["currencies"]
            ),
            "open_debt_items": sum(
                len(item["open_debts"])
                for customer in result["customers"]
                for item in customer["currencies"]
            ),
        }
        return result
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Read-only AYEC ledger reconciliation")
    parser.add_argument("database", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.database), ensure_ascii=True, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
