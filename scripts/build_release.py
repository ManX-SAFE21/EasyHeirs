#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a reproducible release ZIP of the Easy Heirs plugin and its
SHA-256 checksum.

Reproducible means: the same source tree always produces byte-for-byte the
same ZIP, hence the same SHA-256. This lets anyone rebuild the archive and
check that the published hash matches, independently of who built it. To get
there we sort the file list, zero out per-file timestamps, force fixed
permissions and normalise text files to LF line endings, so nothing machine-,
time- or checkout-specific leaks into the archive.

Usage (from the repository root):

    python scripts/build_release.py

Outputs, into ./dist :
    bal_easy_heirs_v<VERSION>.zip
    bal_easy_heirs_v<VERSION>.zip.sha256

The version is read from bal_easy_heirs/VERSION. The GPG signatures
(.asc / .sig) are produced separately by the release manager with their
own key and passphrase; see RELEASING.md.
"""

import hashlib
import os
import zipfile

# Directory that holds this script -> the repository root is its parent.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT, "bal_easy_heirs")   # the plugin package
DIST_DIR = os.path.join(ROOT, "dist")

# Fixed timestamp baked into every ZIP entry (year, month, day, h, m, s).
# Any constant >= 1980 works; keeping it fixed is what makes builds
# reproducible. It is NOT the release date and has no other meaning.
FIXED_TIME = (2020, 1, 1, 0, 0, 0)

# Files inside the package we never want to ship.
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = (".pyc", ".pyo")

# Text files are normalised to LF before going into the archive. Without this
# the build is only reproducible by accident: git stores LF, but a checkout on
# Windows with core.autocrlf=true writes CRLF to disk, so the same commit would
# produce a different ZIP — and a different SHA-256 — depending on who built
# it. Anything not listed here (the PNG) is copied through byte for byte.
TEXT_SUFFIXES = (".py", ".json", ".md", ".txt", ".svg", ".cfg", ".ini")
TEXT_NAMES = ("VERSION", "LICENSE")

CR, LF = bytes([13]), bytes([10])
CRLF = CR + LF


def read_normalised(path: str) -> bytes:
    """File contents, with CRLF and lone CR turned into LF for text files."""
    with open(path, "rb") as fh:
        data = fh.read()
    name = os.path.basename(path)
    if name in TEXT_NAMES or name.endswith(TEXT_SUFFIXES):
        data = data.replace(CRLF, LF).replace(CR, LF)
    return data


def read_version() -> str:
    """The plugin version, taken from the single source of truth."""
    with open(os.path.join(PKG_DIR, "VERSION"), "r", encoding="utf-8") as f:
        return f.read().strip()


def collect_files() -> list:
    """All shippable files under the package, as (absolute, arcname) pairs,
    sorted so the archive order is deterministic."""
    out = []
    for dirpath, dirnames, filenames in os.walk(PKG_DIR):
        # prune unwanted directories in place so os.walk skips them
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(SKIP_SUFFIXES):
                continue
            full = os.path.join(dirpath, name)
            # arcname keeps the leading "bal_easy_heirs/" that Electrum needs
            arc = os.path.relpath(full, ROOT).replace(os.sep, "/")
            out.append((full, arc))
    return sorted(out, key=lambda pair: pair[1])


def build_zip(zip_path: str, files: list) -> None:
    """Write a deterministic ZIP: fixed order, fixed timestamps, fixed
    permissions, fixed compression."""
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for full, arc in files:
            info = zipfile.ZipInfo(arc, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16   # regular file, rw-r--r--
            z.writestr(info, read_normalised(full))


def sha256_of(path: str) -> str:
    """SHA-256 of a file, read in chunks so large files stay cheap."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    version = read_version()
    os.makedirs(DIST_DIR, exist_ok=True)
    base = f"bal_easy_heirs_v{version}.zip"
    zip_path = os.path.join(DIST_DIR, base)

    files = collect_files()
    build_zip(zip_path, files)

    digest = sha256_of(zip_path)
    # Two spaces between hash and name is the format `sha256sum -c` expects.
    sha_path = zip_path + ".sha256"
    with open(sha_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{digest}  {base}\n")

    print(f"Built {len(files)} files into dist/{base}")
    print(f"SHA-256  {digest}")
    print(f"Wrote    dist/{base}.sha256")
    print()
    print("Next: sign it with your key (see RELEASING.md), for example")
    print(f"  cd dist")
    print(f"  gpg --local-user 206C20114CA96172 --armor --detach-sign {base}")
    print(f"  gpg --local-user 206C20114CA96172 --detach-sign {base}")


if __name__ == "__main__":
    main()
