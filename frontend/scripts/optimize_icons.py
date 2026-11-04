# bs"d - lehagdil torah velahadir
"""Make sure every icon in frontend/icons/orig_icons has an optimized copy in frontend/icons/optimized.

Just run (needs Pillow: pip install pillow):
    python frontend/scripts/optimize_icons.py

Originals are never modified. Existing optimized files that are newer than their original are skipped;
optimized files whose original was deleted are removed. Optimization: EXIF rotation, metadata stripped,
downscaled to fit MAX_SIZE (never upscaled), re-encoded (JPEG flattened onto white).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"
ORIG_DIR = ICONS_DIR / "orig_icons"
OPTIMIZED_DIR = ICONS_DIR / "optimized"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE = (1200, 1200)
QUALITY = 85


def optimize(src: Path, dst: Path) -> None:
    with Image.open(src) as opened:
        img = ImageOps.exif_transpose(opened)
        img.load()
    img.thumbnail(MAX_SIZE, Image.LANCZOS)

    ext = src.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "LA", "P"):
            rgba = img.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel("A"))
            img = flat
        else:
            img = img.convert("RGB")
        img.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    elif ext == ".png":
        img.save(dst, "PNG", optimize=True)
    else:
        img.save(dst, "WEBP", quality=QUALITY, method=6)


def main() -> None:
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    originals = {p.name: p for p in ORIG_DIR.iterdir() if p.suffix.lower() in EXTENSIONS}

    for name, src in sorted(originals.items()):
        dst = OPTIMIZED_DIR / name
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            print(f"{name}: up to date")
            continue
        optimize(src, dst)
        print(f"{name}: {src.stat().st_size / 1024:.0f}KB -> {dst.stat().st_size / 1024:.0f}KB")

    for stale in OPTIMIZED_DIR.iterdir():
        if stale.suffix.lower() in EXTENSIONS and stale.name not in originals:
            stale.unlink()
            print(f"{stale.name}: removed (no original)")


if __name__ == "__main__":
    main()
