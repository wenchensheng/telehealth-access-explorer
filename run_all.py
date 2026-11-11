"""One command for the whole pipeline:

fetch CMS CSV -> clean + data-quality checks -> SQLite + SQL queries -> findings ->
app JSON (docs/data/app.json) -> QR code -> execute the analysis notebook.

Usage:  python run_all.py                 # everything
        python run_all.py --offline       # use the committed CMS snapshot, no download
        python run_all.py --skip-notebook
Then:   python -m http.server -d docs 8000   and open http://localhost:8000
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import build_db, clean, export_app, fetch_cms, findings, make_qr  # noqa: E402,E401


def execute_notebook(path: Path) -> None:
    import nbformat
    from nbclient import NotebookClient

    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(path.parent)}}).execute()
    for cell in nb.cells:  # drop per-run timestamps so re-runs give clean diffs
        cell.get("metadata", {}).pop("execution", None)
    nbformat.write(nb, path)
    print(f"[notebook] executed {path.relative_to(ROOT)} (outputs saved)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="skip the download and use data/snapshot/")
    ap.add_argument("--skip-notebook", action="store_true")
    args = ap.parse_args()
    t0 = time.perf_counter()
    fetch_cms.main(offline=args.offline)
    clean.run()
    build_db.build()
    res = findings.main()
    export_app.main(res)
    make_qr.main()
    if not args.skip_notebook:
        execute_notebook(ROOT / "notebooks" / "analysis.ipynb")
    print(f"[done] pipeline finished in {time.perf_counter() - t0:.1f}s. "
          f"Preview: python -m http.server -d docs 8000")


if __name__ == "__main__":
    main()
