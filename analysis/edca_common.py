"""Shared constants and utilities for EDCA result analysis."""

import sqlite3
import pandas as pd

AC_ORDER = ["AC_VO", "AC_VI", "AC_BE", "AC_BK"]

AC_COLORS = dict(zip(AC_ORDER, ["#e74c3c", "#3498db", "#2ecc71", "#95a5a6"]))

_AC_MAP = {"vosta": "AC_VO", "vista": "AC_VI", "besta": "AC_BE", "bksta": "AC_BK",
           "voice": "AC_VO", "video": "AC_VI", "background": "AC_BK"}


def classify_ac(module_name: str) -> str:
    lower = module_name.lower()
    return next((ac for kw, ac in _AC_MAP.items() if kw in lower), "AC_BE")


def query_sqlite(db_path: str, query: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()
