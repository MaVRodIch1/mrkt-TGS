#!/usr/bin/env python3
"""
Download missing gift images from giftstat CDN.
Скачивает недостающие картинки подарков с CDN giftstat.

Some gifts (e.g. ionicdryer, skystilettos) have wrong or missing images
in api.changes.tg. This script fetches correct images from giftstat's CDN
and saves them to gift_overrides/.

Некоторые подарки (например ionicdryer, skystilettos) имеют неправильные
или отсутствующие картинки в api.changes.tg. Скрипт скачивает правильные
картинки с CDN giftstat и сохраняет в gift_overrides/.

Usage / Запуск:
    python fix_images.py
"""

import os
import urllib.request
import json

OVERRIDES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gift_overrides")

# Slug → giftstat CDN URL
# Картинки, которые не скачиваются или скачиваются неправильно с api.changes.tg
KNOWN_BROKEN_IMAGES = {
    "ionicdryer": "https://ddejfvww7sqtk.cloudfront.net/images/attrs/EQAkqbUwkuFy5sgkgXEGSr9WSxnbslVCc25Ri9BfAEIzXFU-/RVFBa3FiVXdrdUZ5NXNna2dYRUdTcjlXU3huYnNsVkNjMjVSaTlCZkFFSXpYRlUt.webp",
    "skystilettos": "https://ddejfvww7sqtk.cloudfront.net/images/attrs/EQCEVLBbgzL5Ih9bzMkneLi68xzOelYN3NEugm_4gZTpuAFP/RVFDRVZMQmJnekw1SWg5YnpNa25lTGk2OHh6T2VsWU4zTkV1Z21fNGdaVHB1QUZQ.webp",
}


def main():
    os.makedirs(OVERRIDES_DIR, exist_ok=True)

    print(f"Downloading {len(KNOWN_BROKEN_IMAGES)} gift images to {OVERRIDES_DIR}/\n")

    for slug, url in KNOWN_BROKEN_IMAGES.items():
        ext = url.rsplit(".", 1)[-1]  # webp, png, etc.
        path = os.path.join(OVERRIDES_DIR, f"{slug}.{ext}")

        if os.path.exists(path):
            print(f"  · {slug}.{ext} — already exists / уже есть")
            continue

        try:
            print(f"  ↓ {slug}...", end=" ", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            with open(path, "wb") as f:
                f.write(data)
            print(f"OK ({len(data):,} bytes)")
        except Exception as e:
            print(f"FAILED: {e}")
            print(f"    Fix: download manually from giftstat.app and save as {slug}.{ext}")
            print(f"    Решение: скачайте вручную с giftstat.app и сохраните как {slug}.{ext}")

    print(f"\nDone. Restart sticker_pack.py to apply.")
    print(f"Готово. Перезапустите sticker_pack.py для применения.")


if __name__ == "__main__":
    main()
