"""Fill data/cache/data/<dataset>/ from data/uci/ so the UCI experiments run without network.

The RCGP UCI benchmark reads <cache_dir>/data/<dataset>/<file name of the download URL>
and only downloads when that file is missing. This script places the four UCI files
under every dataset variant (plain, _asymmetric, _focused, _uniform).

Usage:  python scripts/prepare_data.py
"""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "uci"
CACHE = ROOT / "data" / "cache" / "data"

FILES = {
    "boston": ("housing.data", "baadf72995725d76efe787b664e1f083388c79ba21ef9a7990d87f774184735a"),
    "concrete": ("Concrete_Data.xls", "710076c66b9ca3f8050e7942f3dcbdbe04013534daeb0077ffd3079a52d8e0c4"),
    "energy": ("ENB2012_data.xlsx", "0089fcffc1415e41e2ff63730cca5280efe54fc43d722dfde1b0aaa808e35dc4"),
    "yacht": ("yacht_hydrodynamics.data", "00dfecc0fc01ddd4c90b558a3ac11b246df8ebcfea130724223475a9a67f0ea1"),
}
VARIANTS = ("", "_asymmetric", "_focused", "_uniform")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    written = 0
    for name, (fname, digest) in FILES.items():
        src = SRC / fname
        if not src.is_file():
            raise SystemExit(f"missing {src}")
        if sha256(src) != digest:
            raise SystemExit(f"SHA-256 mismatch: {src}")
        for variant in VARIANTS:
            dst = CACHE / f"{name}{variant}" / fname
            if dst.is_file() and sha256(dst) == digest:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            written += 1
    print(f"cache ready: {CACHE} ({written} files written, {len(FILES) * len(VARIANTS)} expected)")


if __name__ == "__main__":
    main()
