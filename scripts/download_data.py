"""一键下载全部实验数据。

运行：python scripts/download_data.py
数据均来自公开匿名数据源，含多个备用地址，任一成功即可。
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# GMSC 主数据集备用源（均为公开镜像，按顺序尝试）
GMSC_URLS = [
    "https://media.githubusercontent.com/media/KHIRODH06/EXPECTED_CREDIT_LOSS_MODELING_END_TO_END/f71d0e591c6c25a11865d46a0d3cbd7be7c68bbc/cs-training.csv",
    "https://raw.githubusercontent.com/KHIRODH06/EXPECTED_CREDIT_LOSS_MODELING_END_TO_END/main/cs-training.csv",
]

GERMAN_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data"
)


def _download(urls: list[str], dest: Path, min_bytes: int) -> bool:
    if isinstance(urls, str):
        urls = [urls]
    for url in urls:
        try:
            print(f"trying {url}")
            urllib.request.urlretrieve(url, dest)
            if dest.stat().st_size >= min_bytes:
                print(f"saved {dest.name} ({dest.stat().st_size} bytes)")
                return True
        except Exception as exc:  # noqa: BLE001
            print(f"failed: {exc}")
    return False


def fetch_taiwan() -> None:
    """通过 OpenML 获取台湾信用卡数据并保存为 CSV。"""
    dest = DATA / "credit_card_clients.csv"
    if dest.exists():
        print("credit_card_clients.csv already exists")
        return
    from sklearn.datasets import fetch_openml

    ds = fetch_openml(data_id=42477, as_frame=True, parser="auto")
    df = ds.data.copy()
    df["target"] = ds.target.astype(int)
    df.to_csv(dest, index=False)
    print(f"saved {dest.name} ({df.shape})")


def main() -> int:
    ok_gmsc = _download(GMSC_URLS, DATA / "gmsc.csv", min_bytes=5_000_000)
    ok_german = _download(GERMAN_URL, DATA / "german.data", min_bytes=50_000)
    fetch_taiwan()
    if not (ok_gmsc and ok_german):
        print("WARNING: some sources failed; check network or add mirrors")
        return 1
    print("all datasets ready in", DATA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
