"""Download the files that are shipped as `.url` placeholders and check them.

Every `<name>.url` file holds the download address, the size and the SHA-256 of
`<name>`. This script walks the given folders (default: the whole
gaussian-process-regression folder), downloads each missing file next to its
placeholder and keeps it only when size and SHA-256 match.

Usage (needs network once):
    python offline-RCGP/scripts/fetch_url_files.py               # everything
    python offline-RCGP/scripts/fetch_url_files.py RCGP-main     # one folder
    python offline-RCGP/scripts/fetch_url_files.py --list        # show only
"""
import argparse
import configparser
import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]


def read_placeholder(path: Path):
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    cp.read(path, encoding="utf-8")
    url = cp.get("InternetShortcut", "URL")
    size = cp.getint("File", "SizeBytes", fallback=-1)
    digest = cp.get("File", "SHA256", fallback="").lower()
    return url, size, digest


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dst: Path, size: int, digest: str) -> bool:
    tmp = dst.with_name(dst.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "fetch-url-files/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    ok = (size < 0 or tmp.stat().st_size == size) and (not digest or sha256_of(tmp) == digest)
    if ok:
        tmp.replace(dst)
    else:
        tmp.unlink()
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="*", help="folders relative to the gaussian-process-regression folder")
    ap.add_argument("--list", action="store_true", help="list placeholders without downloading")
    args = ap.parse_args()
    roots = [BASE / f for f in args.folders] or [BASE]
    bad = 0
    for root in roots:
        for ph in sorted(root.rglob("*.url")):
            url, size, digest = read_placeholder(ph)
            dst = ph.with_suffix("")
            rel = dst.relative_to(BASE)
            if dst.is_file() and (not digest or sha256_of(dst) == digest):
                print(f"ok      {rel}")
                continue
            if args.list:
                print(f"missing {rel}  <- {url}")
                continue
            try:
                good = fetch(url, dst, size, digest)
            except OSError as exc:
                good = False
                print(f"error   {rel}: {exc}")
            print(f"{'fetched' if good else 'FAILED '} {rel}")
            bad += 0 if good else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
