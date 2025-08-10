"""
命令行入口（CLI）。

提供基础命令：
- agent outline: 读取最新或指定文章任务，生成 extracted_meta.json、market_references.json 与 article_structure.md，并将步骤置为待审。
- agent approve-outline: 将大纲审核通过并生成写作剧本雏形。

运行示例：
  python agent.py outline --article "示例文章"
  python agent.py approve-outline --article "示例文章"
"""
from __future__ import annotations

import typer
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import os

from agent_cli.outline import run_outline
from agent_cli.paths import resolve_article_dir, ensure_article_dirs
from agent_cli.utils import update_workflow_step, write_text_file
from agent_cli.draft import run_draft_text_only


app = typer.Typer(help="文章创作Agent命令行工具")

# 预加载 .env（项目根目录）
ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT/".env", override=False)


@app.command()
def outline(article: Optional[str] = typer.Option(None, help="文章标题（默认选择最新一条进行中任务）")) -> None:
    """生成大纲：extracted_meta.json、market_references.json、article_structure.md，并置待审。"""
    article_dir = resolve_article_dir(article)
    ensure_article_dirs(article_dir)
    run_outline(article_dir)
    typer.echo(f"[outline] 大纲已生成，待审路径：{article_dir / 'article_structure.md'}")


@app.command("approve-outline")
def approve_outline(article: Optional[str] = typer.Option(None, help="文章标题（默认选择最新一条进行中任务）")) -> None:
    """大纲通过审核，写入状态并生成写作剧本雏形。"""
    article_dir = resolve_article_dir(article)
    workflow_path = article_dir / "workflow_state.json"
    update_workflow_step(workflow_path, "outline", "approved")

    writing_plan_path = article_dir / "article_writing.md"
    if not writing_plan_path.exists():
        write_text_file(
            writing_plan_path,
            """# 写作剧本（雏形）\n\n- [ ] 第1章：按已确认大纲展开\n- [ ] 第2章：……\n\n提示：运行 `agent draft --text-only` 进入文本扩写与事实核查阶段。\n""",
        )
    update_workflow_step(workflow_path, "writing_plan", "done")
    typer.echo(f"[approve-outline] 已通过大纲并生成写作剧本雏形：{writing_plan_path}")

    # 同步Checklist勾选“人工确认A”与“生成写作剧本”
    checklist = article_dir / "article_creation.md"
    if checklist.exists():
        try:
            text = checklist.read_text(encoding="utf-8")
            text = text.replace("- [ ] 2. 人工确认A", "- [x] 2. 人工确认A")
            text = text.replace("- [ ] 3. 生成写作剧本（`article_writing.md`）", "- [x] 3. 生成写作剧本（`article_writing.md`）")
            checklist.write_text(text, encoding="utf-8")
        except Exception:
            pass


@app.command("draft")
def draft_text_only(article: Optional[str] = typer.Option(None, help="文章标题（默认选择最新一条进行中任务）"), text_only: bool = typer.Option(True, "--text-only", help="仅生成纯文本成稿（不含配图）")) -> None:
    """按剧本与大纲扩写纯文本成稿，并生成审稿包摘要。"""
    article_dir = resolve_article_dir(article)
    run_draft_text_only(article_dir)
    typer.echo(f"[draft] 已产出纯文本成稿与审稿包：{article_dir}")


if __name__ == "__main__":
    app()


