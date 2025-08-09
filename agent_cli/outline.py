from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agent_cli.utils import read_json, write_json, write_text_file, update_workflow_step


def _load_agent_config(root: Path) -> Dict[str, Any]:
    cfg_path = root / "config" / "agent_config.json"
    return read_json(cfg_path)


def _select_primary_materials(article_dir: Path) -> Dict[str, str]:
    materials_dir = article_dir / "Materials"
    if not materials_dir.exists():
        return {"transcript": ""}
    # 选最新的 transcript.*.txt / .md
    candidates = sorted(
        [p for p in materials_dir.glob("transcript.*.*") if p.suffix in {".txt", ".md"}],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    transcript_content = candidates[0].read_text(encoding="utf-8") if candidates else ""
    return {"transcript": transcript_content}


def _make_extracted_meta(article_dir: Path) -> Dict[str, Any]:
    mats = _select_primary_materials(article_dir)
    transcript = mats.get("transcript", "").strip()
    # 极简占位实现：从转写首行猜测主题
    title_theme = transcript.splitlines()[0][:50] if transcript else "待定主题"
    meta = {
        "title_theme": title_theme,
        "target_audience": "微信公众号作者",
        "goals": ["降低创作成本", "提高更新频率"],
        "key_points": [],
        "constraints": ["不抄袭", "风格统一"],
        "tone": "理性专业，实操为主",
        "seo": {"primary_keywords": []},
        "platform": "wechat_public",
        "style_refs": {"own_works": [], "reference_examples": []},
    }
    write_json(article_dir / "extracted_meta.json", meta)
    return meta


def _make_market_references(article_dir: Path, extracted_meta: Dict[str, Any]) -> Dict[str, Any]:
    # 占位：生成一个包含 site:mp.weixin.qq.com 的示例查询与空候选
    theme = extracted_meta.get("title_theme", "")
    queries = [f"site:mp.weixin.qq.com {theme} 爆款 标题 结构"] if theme else ["site:mp.weixin.qq.com AI 写作 自动化"]
    market = {
        "platform": "wechat_public",
        "source_domain_whitelist": ["mp.weixin.qq.com"],
        "queries": queries,
        "candidates": [],
        "summary": {"top_title_hooks": [], "common_structures": [], "common_devices": []},
    }
    write_json(article_dir / "market_references.json", market)
    return market


def _render_outline(article_dir: Path, extracted_meta: Dict[str, Any], market: Dict[str, Any]) -> None:
    # 简化：直接输出一个基础大纲，后续再接Jinja模板与LLM生成
    title = extracted_meta.get("title_theme", "你的文章标题")
    content = f"""# 文章大纲（候选）\n\n## 5个标题建议\n- {title}\n- {title}（加强版1）\n- {title}（加强版2）\n- {title}（数字钩子）\n- {title}（反差钩子）\n\n## 章节设计\n### 第一章 现状与痛点\n- 目标：让读者共鸣\n- 要点：创作成本高、频率低\n\n### 第二章 方案与原则\n- 目标：传达方法论\n- 要点：脚本+提示词+配置+Workflow\n\n### 第三章 实施路径\n- 目标：可复制落地\n- 要点：目录、状态机、两次人工确认\n"""
    write_text_file(article_dir / "article_structure.md", content)


def run_outline(article_dir: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _ = _load_agent_config(root)

    # 若不存在统一待办清单，则从模板拷贝一份
    checklist = article_dir / "article_creation.md"
    tmpl = root / "Templates" / "article_creation.md"
    if not checklist.exists() and tmpl.exists():
        checklist.write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")

    meta = _make_extracted_meta(article_dir)
    market = _make_market_references(article_dir, meta)
    _render_outline(article_dir, meta, market)

    update_workflow_step(article_dir / "workflow_state.json", "outline", "pending_review")

    # 在 checklist 中标记“生成大纲”完成（简单替换方框为已勾选）
    try:
        text = checklist.read_text(encoding="utf-8")
        text = text.replace("- [ ] 1. 生成大纲（`article_structure.md`）", "- [x] 1. 生成大纲（`article_structure.md`）")
        checklist.write_text(text, encoding="utf-8")
    except Exception:
        pass


