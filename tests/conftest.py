import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session", autouse=True)
def pipeline():
    """Build the data once per test session (offline-safe: falls back to the committed snapshot)."""
    import build_db, clean, export_app, fetch_cms, findings  # noqa: E401

    fetch_cms.main()
    clean.run()
    build_db.build()
    res = findings.main()
    export_app.main(res)
    return res
