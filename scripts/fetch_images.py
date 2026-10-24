#!/usr/bin/env python3
"""
Download every artwork image listed in assets/images.json and write two
web-sized copies into assets/img/.

Runs on GitHub's servers via .github/workflows/fetch-images.yml, so the
images move from Shopify into this repository without anyone downloading
anything by hand. It can also be run locally:  python3 scripts/fetch_images.py

Already-present images are skipped, so re-running is cheap and safe.
"""

import json, os, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets" / "images.json"

FULL_PX = 2000      # long edge of the large copy shown on a work page
THUMB_PX = 1000     # long edge of the grid copy
QUALITY = 82

UA = {"User-Agent": "Mozilla/5.0 (ENJZ site build; +https://enjzworks.art)"}


def magick(*args):
    """ImageMagick 7 uses `magick`, 6 uses `convert`."""
    for exe in ("magick", "convert"):
        try:
            subprocess.run([exe, *args], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            continue
        except subprocess.CalledProcessError as e:
            print("   ! imagemagick:", e.stderr.decode()[:200])
            return False
    print("   ! ImageMagick not found")
    return False


def download(url, dest, attempts=3):
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r, open(dest, "wb") as f:
                f.write(r.read())
            return dest.stat().st_size > 1024
        except Exception as e:
            print(f"   retry {i+1}/{attempts}: {e}")
            time.sleep(2 * (i + 1))
    return False


def main():
    items = json.loads(MANIFEST.read_text())
    tmp = ROOT / ".img-tmp"
    tmp.mkdir(exist_ok=True)

    done = skipped = failed = 0
    for n, it in enumerate(items, 1):
        full = ROOT / it["full"]
        thumb = ROOT / it["thumb"]
        if full.exists() and thumb.exists():
            skipped += 1
            continue

        full.parent.mkdir(parents=True, exist_ok=True)
        raw = tmp / f"raw-{n}"
        print(f"[{n}/{len(items)}] {it['full']}")

        if not download(it["url"], raw):
            print("   ! download failed")
            failed += 1
            continue

        ok = magick(str(raw), "-auto-orient", "-colorspace", "sRGB", "-strip",
                    "-resize", f"{FULL_PX}x{FULL_PX}>", "-quality", str(QUALITY),
                    "-interlace", "Plane", str(full))
        ok = magick(str(raw), "-auto-orient", "-colorspace", "sRGB", "-strip",
                    "-resize", f"{THUMB_PX}x{THUMB_PX}>", "-quality", str(QUALITY - 2),
                    "-interlace", "Plane", str(thumb)) and ok

        raw.unlink(missing_ok=True)
        if ok:
            done += 1
        else:
            failed += 1

    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()

    mb = sum(p.stat().st_size for p in (ROOT / "assets" / "img").rglob("*.jpg")) / 1e6 \
        if (ROOT / "assets" / "img").exists() else 0
    print(f"\nfetched {done} · already present {skipped} · failed {failed}")
    print(f"images on disk: {mb:.1f} MB")
    return 1 if failed and not done else 0


if __name__ == "__main__":
    sys.exit(main())
