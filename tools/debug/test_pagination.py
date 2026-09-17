import sqlite3
from src.utils.path_helper import PathHelper

db_path = PathHelper.get_db_path('ayecpro.db')
print(f"Connecting to: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    where_sql = "(c.is_deleted = 0 OR c.is_deleted IS NULL)"
    params = []

    count_sql = f"SELECT COUNT(*) FROM customers c WHERE {where_sql}"
    total = int(cur.execute(count_sql, tuple(params)).fetchone()[0])
    print(f"Total counted: {total}")

    data_sql = f"""
        SELECT
            c.*,
            COALESCE(b.balance_try, 0) AS balance_try,
            COALESCE(b.balance_usd, 0) AS balance_usd,
            COALESCE(b.balance_eur, 0) AS balance_eur
        FROM customers c
        LEFT JOIN (
            SELECT
                customer_id,
                SUM(CASE WHEN currency='TRY' THEN balance ELSE 0 END) AS balance_try,
                SUM(CASE WHEN currency='USD' THEN balance ELSE 0 END) AS balance_usd,
                SUM(CASE WHEN currency='EUR' THEN balance ELSE 0 END) AS balance_eur
            FROM customer_currency_balances
            GROUP BY customer_id
        ) b ON b.customer_id = c.id
        WHERE {where_sql}
        ORDER BY c.name
        LIMIT ? OFFSET ?
    """
    data_params = list(params) + [50, 0]
    rows = cur.execute(data_sql, tuple(data_params)).fetchall()
    
    print(f"Rows fetched: {len(rows)}")
    if len(rows) > 0:
        print(f"First row: {dict(rows[0])}")

except Exception as e:
    import traceback
    print(f"Error: {e}\n{traceback.format_exc()}")
finally:
    try:
        conn.close()
    except:
        pass
