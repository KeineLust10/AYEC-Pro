# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_CANDIDATES = ["ayecpro.db", "ayecpro.db", "ayec_pro.db"]
OUT_FILE = ROOT / "docs" / "DB_SCHEMA_ANALYSIS.md"


def pick_db() -> Path:
    for name in DB_CANDIDATES:
        p = ROOT / name
        if p.exists() and p.stat().st_size > 0:
            return p
    raise FileNotFoundError("No SQLite DB found in candidates.")


def main() -> int:
    db_path = pick_db()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Veritabanı Şema Analizi\n\n")
        f.write(f"- Kaynak DB: `{db_path.name}`\n")
        f.write(f"- Toplam tablo: **{len(tables)}**\n\n")

        f.write("## Tablo Envanteri\n")
        for table in tables:
            cols = cur.execute(f"PRAGMA table_info('{table}')").fetchall()
            idxs = cur.execute(f"PRAGMA index_list('{table}')").fetchall()
            f.write(f"### `{table}`\n")
            f.write(f"- Kolon sayısı: {len(cols)}\n")
            if idxs:
                f.write(f"- Index sayısı: {len(idxs)}\n")
                for i in idxs:
                    idx_name = i[1]
                    idx_cols = [c[2] for c in cur.execute(f"PRAGMA index_info('{idx_name}')").fetchall()]
                    f.write(f"- `{idx_name}` -> {', '.join(idx_cols)}\n")
            else:
                f.write("- Index sayısı: 0\n")
            f.write("- Kolonlar:\n")
            for c in cols:
                # c: cid, name, type, notnull, dflt_value, pk
                f.write(
                    f"  - `{c[1]}` `{c[2] or 'TEXT'}` "
                    f"{'NOT NULL' if c[3] else 'NULL'} "
                    f"{'PK' if c[5] else ''}\n"
                )
            f.write("\n")

        f.write("## Web Optimizasyon Önerileri\n")
        f.write("- Sorgu ağırlıklı alanlara birleşik index ekleyin (örn. `devices(status, created_at)`).\n")
        f.write("- Soft-delete yaklaşımı olan tablolarda `is_active` + tarih alanı indexleyin.\n")
        f.write("- Audit ve log tablolarını zaman bazlı partition/archival stratejisine taşıyın.\n")
        f.write("- API pagination için liste endpointlerinde `ORDER BY + LIMIT/OFFSET` standardize edin.\n")
        f.write("- Raporlama için ağır join'ler adına materialized snapshot/job tablosu tasarlayın.\n")

    conn.close()
    print(f"generated: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

