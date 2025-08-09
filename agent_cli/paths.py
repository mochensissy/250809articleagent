from __future__ import annotations

from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_ONGOING = ROOT / "Articles" / "进行中"


def resolve_article_dir(article_title: Optional[str]) -> Path:
    if article_title:
        return ARTICLES_ONGOING / article_title
    # 默认取“进行中”下最新修改的目录
    if not ARTICLES_ONGOING.exists():
        raise FileNotFoundError("找不到 Articles/进行中 目录，请先创建任务目录")
    candidates = [p for p in ARTICLES_ONGOING.iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError("进行中目录为空，请先创建文章任务目录")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def ensure_article_dirs(article_dir: Path) -> None:
    (article_dir / "Materials").mkdir(parents=True, exist_ok=True)
    (article_dir / "verification_reports").mkdir(parents=True, exist_ok=True)


