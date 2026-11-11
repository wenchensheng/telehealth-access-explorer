"""Load the tidy CSV into SQLite and run every analysis query in sql/.

Each sql/NN_name.sql (except 00_schema.sql) is executed and its result saved to
reports/sql/NN_name.csv, so the SQL output is reviewable on GitHub without running anything.
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from paths import CLEAN_FILE, DB_FILE, REPORTS, ROOT, SQL_DIR


def connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_FILE)


def query(name: str, con: sqlite3.Connection | None = None) -> pd.DataFrame:
    """Run one analysis query by file stem, e.g. query('01_state_rankings')."""
    own = con is None
    con = con or connect()
    try:
        return pd.read_sql_query((SQL_DIR / f"{name}.sql").read_text(), con)
    finally:
        if own:
            con.close()


def analysis_queries() -> list[str]:
    return sorted(p.stem for p in SQL_DIR.glob("*.sql") if not p.stem.startswith("00_"))


def build() -> None:
    DB_FILE.unlink(missing_ok=True)
    con = connect()
    con.executescript((SQL_DIR / "00_schema.sql").read_text())
    df = pd.read_csv(CLEAN_FILE)
    df.to_sql("telehealth", con, if_exists="append", index=False)
    out = REPORTS / "sql"
    out.mkdir(parents=True, exist_ok=True)
    for name in analysis_queries():
        res = query(name, con)
        res.to_csv(out / f"{name}.csv", index=False)
        print(f"[sql] {name}: {len(res)} rows -> {(out / f'{name}.csv').relative_to(ROOT)}")
    con.close()


if __name__ == "__main__":
    build()
