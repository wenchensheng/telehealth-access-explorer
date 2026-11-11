"""QR code that opens the live app on a phone (images/qr_live.png)."""
from __future__ import annotations

import qrcode

from paths import LIVE_URL, ROOT


def main() -> None:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=3)
    qr.add_data(LIVE_URL)
    qr.make(fit=True)
    out = ROOT / "images" / "qr_live.png"
    out.parent.mkdir(exist_ok=True)
    qr.make_image(fill_color="#0b3c49", back_color="white").save(out)
    print(f"[qr] {LIVE_URL} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
