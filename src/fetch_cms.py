"""Download the public CMS "Medicare Telehealth Trends" CSV (no login needed).

If the download fails (offline, URL moved), the committed gzip snapshot of the same
file in data/snapshot/ is used instead, so the pipeline always runs.
"""
from __future__ import annotations

import gzip
import hashlib
import urllib.request

from paths import CMS_PAGE, CMS_URL, RAW_FILE, ROOT, SNAPSHOT


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def main(offline: bool = False) -> str:
    """Make sure data/raw/ holds the CSV. Returns 'download', 'cached' or 'snapshot'."""
    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    if RAW_FILE.exists():
        print(f"[fetch] using cached {RAW_FILE.relative_to(ROOT)}")
        return "cached"
    if not offline:
        try:
            req = urllib.request.Request(CMS_URL, headers={"User-Agent": "Mozilla/5.0 (portfolio fetch script)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if not data.startswith(b"Year,"):
                raise ValueError("response is not the expected CSV")
            RAW_FILE.write_bytes(data)
            print(f"[fetch] downloaded {len(data)/1e6:.1f} MB from CMS (sha256 {sha256(data)})")
            return "download"
        except Exception as exc:  # noqa: BLE001 - any failure falls back to the snapshot
            print(f"[fetch] download failed ({exc}); falling back to the committed snapshot.\n"
                  f"        If the URL moved, get the current CSV link from {CMS_PAGE}")
    data = gzip.decompress(SNAPSHOT.read_bytes())
    RAW_FILE.write_bytes(data)
    print(f"[fetch] restored {RAW_FILE.relative_to(ROOT)} from snapshot (sha256 {sha256(data)})")
    return "snapshot"


if __name__ == "__main__":
    main()
