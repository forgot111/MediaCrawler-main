"""抖音评论 CSV 的保存位置和读取方式。"""

import csv
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_OUTPUT_DIR = PROJECT_ROOT / "data" / "douyin" / "csv"
LEGACY_CSV_DIR = PROJECT_ROOT / "F:" / "下载"


def latest_comments_csv() -> Optional[Path]:
    """优先选择新目录中最近生成的评论 CSV，兼容原来的保存目录。"""
    for directory in (CSV_OUTPUT_DIR, LEGACY_CSV_DIR):
        candidates = [p for p in directory.glob("*_comments.csv") if p.is_file()]
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_mtime_ns)
    return None


def read_comments_csv(csv_path: Path) -> List[Dict]:
    """保留评论、视频和用户 ID 的原始字符串，仅转换统计用的数值。"""
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or "评论内容" not in reader.fieldnames:
            raise ValueError("CSV 缺少“评论内容”字段，请选择评论 CSV")
        comments = []
        for row in reader:
            for field in ("点赞数", "子评论数"):
                try:
                    row[field] = int(row.get(field) or 0)
                except (ValueError, TypeError):
                    row[field] = 0
            comments.append(row)
    return comments
