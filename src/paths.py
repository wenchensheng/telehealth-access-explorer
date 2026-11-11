"""Shared paths and constants for the pipeline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CMS_URL = "https://data.cms.gov/sites/default/files/2026-09/TMEDTREND_PUBLIC_260914.csv"
CMS_PAGE = ("https://data.cms.gov/summary-statistics-on-use-and-payments/"
            "medicare-medicaid-service-type-reports/medicare-telehealth-trends")
RAW_FILE = ROOT / "data" / "raw" / "TMEDTREND_PUBLIC_260914.csv"           # git-ignored download
SNAPSHOT = ROOT / "data" / "snapshot" / "TMEDTREND_PUBLIC_260914.csv.gz"  # committed offline copy
CLEAN_FILE = ROOT / "data" / "processed" / "telehealth_clean.csv"
DB_FILE = ROOT / "data" / "processed" / "telehealth.db"
SQL_DIR = ROOT / "sql"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
APP_JSON = DOCS / "data" / "app.json"
ATLAS = DOCS / "data" / "states-albers-10m.json"
LIVE_URL = "https://wenchensheng.github.io/telehealth-access-explorer/"
