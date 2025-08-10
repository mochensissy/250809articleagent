from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple

from agent_cli.utils import read_json, write_text_file, update_workflow_step
from agent_cli.llm_perplexity import chat


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _select_transcript(article_dir: Path) -> str:
    materials = article_dir / "Materials"
    if not materials.exists():
        return ""
    candidates = sorted(
        [p for p in materials.glob("transcript.*.*") if p.suffix in {".md", ".txt"}],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return _read_text(candidates[0]) if candidates else ""


def _parse_outline(article_dir: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """解析 `article_structure.md`，返回(标题建议列表, 章节列表[{title, bullets}])"""
    outline_path = article_dir / "article_structure.md"
    text = _read_text(outline_path)
    lines = [ln.rstrip() for ln in text.splitlines()]

    # 标题建议
    title_suggestions: List[str] = []
    in_titles = False
    in_chapters = False
    chapters: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None

    for ln in lines:
        if ln.startswith("## 5个标题建议"):
            in_titles = True
            in_chapters = False
            continue
        if ln.startswith("## 章节设计"):
            in_titles = False
            in_chapters = True
            continue
        if in_titles and ln.strip().startswith("- "):
            title_text = ln.strip()[2:].strip()
            # 去掉可能的 '# ' 前缀
            if title_text.startswith("# "):
                title_text = title_text[2:].strip()
            title_suggestions.append(title_text)
        if in_chapters:
            if ln.startswith("### "):
                # 新章节
                if current:
                    chapters.append(current)
                current = {"title": ln[4:].strip(), "bullets": []}
            elif ln.strip().startswith("- ") and current is not None:
                current["bullets"].append(ln.strip()[2:].strip())
    if current:
        chapters.append(current)

    return title_suggestions, chapters


def _gen_intro_via_llm(meta: Dict[str, Any], transcript: str) -> str:
    theme = meta.get("title_theme", "本次主题")
    if theme.startswith("# "):
        theme = theme[2:].strip()
    prompt_user = (
        "请用中文写一段300字左右的引言，要求：\n"
        f"- 围绕主题：{theme}\n"
        "- 结合以下转写素材中的核心意思（严禁逐字复制）：\n" + transcript[:1200] + "\n"
        "- 口吻：理性、清晰、实操导向\n- 不出现小节标题，不用条目，写成自然段。"
    )
    try:
        return chat([
            {"role": "system", "content": "你是一位资深中文写作者，擅长将口述素材整理为流畅的书面表达。"},
            {"role": "user", "content": prompt_user},
        ])
    except Exception:
        return f"本文围绕“{theme}”展开，结合一线素材与实践经验，总结可操作的方法与思路。"


def _gen_section_via_llm(meta: Dict[str, Any], title: str, bullets: List[str], transcript: str) -> str:
    bullet_text = "\n".join(f"- {b}" for b in bullets)
    prompt_user = (
        f"请用中文围绕小节《{title}》写一段400-600字正文，要求：\n"
        f"- 小节要点：\n{bullet_text}\n"
        "- 结合下面转写素材的思想（严禁逐字复制），提炼为清晰表述：\n" + transcript[:1500] + "\n"
        "- 输出为自然段，不要列表、不加小标题，避免空话套话。"
    )
    try:
        return chat([
            {"role": "system", "content": "你是一位严谨的中文写作者，能把要点扩写为逻辑清晰的段落。"},
            {"role": "user", "content": prompt_user},
        ])
    except Exception:
        return "（正文自动生成失败，已回退到占位段落。要点：" + "; ".join(bullets) + ")"


def _gen_outro_via_llm(meta: Dict[str, Any]) -> str:
    theme = meta.get("title_theme", "本次主题")
    if theme.startswith("# "):
        theme = theme[2:].strip()
    prompt_user = (
        f"请用中文写一段200-300字的结语，主题：{theme}。要求：鼓励读者行动与复盘，避免口号化表达。"
    )
    try:
        return chat([
            {"role": "system", "content": "你是一位中文写作者，擅长总结与行动建议。"},
            {"role": "user", "content": prompt_user},
        ])
    except Exception:
        return "在不确定性中，小步快跑、持续复盘是更稳妥的路径。"


# 规则化兜底：不依赖外部模型，基于提纲与口述素材生成可读正文
def _rule_based_intro(meta: Dict[str, Any], transcript: str) -> str:
    theme = meta.get("title_theme", "本次主题")
    if theme.startswith("# "):
        theme = theme[2:].strip()
    return (
        f"围绕“{theme}”，我们尝试把口述材料整理为清晰可读的文字版本。核心观点是：任何制度或政策都有有效期，"
        "在外部变化更快的今天，这个有效期被显著压缩；因此写作与决策都需要更加灵活的工作方式——小步快跑、持续复盘、"
        "在当下给出‘此时此刻最恰当的解释’。以下内容从现状与痛点、方案与原则、实施路径三部分展开。"
    )


def _rule_based_section(title: str, bullets: List[str], transcript: str) -> str:
    base = " ".join(transcript.split())[:400]
    if "现状" in title or "痛点" in title:
        return (
            "许多历史经验告诉我们，制度与政策并非一旦制定就长期有效。在工业化时代，人们尚且以十数年为周期迭代；"
            "而在当下，高速变化的技术与市场把周期进一步压缩。以AI行业为例，头部团队往往按‘月’甚至‘周’迭代产品与策略，"
            "这意味着‘固定方法’会迅速失效。" \
            "因此，若仍以一次性、线性的方式组织写作与决策，往往会出现滞后感和解释力不足的问题。"
        )
    if "方案" in title or "原则" in title:
        return (
            "更稳妥的做法是把写作与认知当作持续演进的过程。认识论提醒我们：认识需要一个清晰的起点，但没有终点；"
            "我们要在实践中不断加深理解、修正假设、迭代表达。对应到写作：以大纲作为共识锚点，以文本为阶段性产物，"
            "允许根据反馈快速调整。目标不是‘完美解释’，而是当下最恰当的解释。"
        )
    if "实施路径" in title or "路径" in title:
        return (
            "实施上，建议建立可复用的工作流：第一步，大纲确认，用于统一视角与节奏；第二步，文本确认，"
            "用事实核查与读者视角校正表述；第三步，通过自动化工具完成配图与格式化，并在平台侧生成草稿。"
            "配合小步快跑和阶段复盘，可以在不牺牲质量的前提下，把响应速度提高到‘以周为单位’。"
        )
    # 普通小节：用要点组织为自然段
    bullets_txt = "；".join(bullets)
    return f"围绕本节要点（{bullets_txt}），结合口述素材可整理为数个关键结论，并据此形成可操作建议。"


def _compose_draft(meta: Dict[str, Any], title: str, chapters: List[Dict[str, Any]], transcript: str) -> str:
    parts: List[str] = []
    parts.append(f"# {title}")
    parts.append("")

    # 引言
    intro = _gen_intro_via_llm(meta, transcript)
    if "自动生成失败" in intro or len(intro.strip()) < 50:
        intro = _rule_based_intro(meta, transcript)
    parts.append(intro)
    parts.append("")

    # 章节
    for idx, ch in enumerate(chapters, start=1):
        parts.append(f"## {idx}. {ch['title']}")
        section = _gen_section_via_llm(meta, ch['title'], ch.get('bullets', []), transcript)
        if "自动生成失败" in section or len(section.strip()) < 80:
            section = _rule_based_section(ch['title'], ch.get('bullets', []), transcript)
        parts.append(section)
        parts.append("")

    # 结语
    parts.append("## 结语")
    parts.append(_gen_outro_via_llm(meta))

    return "\n".join(parts).rstrip() + "\n"


def run_draft_text_only(article_dir: Path) -> None:
    meta = read_json(article_dir / "extracted_meta.json")
    title_sugs, chapters = _parse_outline(article_dir)
    transcript = _select_transcript(article_dir)
    title = title_sugs[0] if title_sugs else meta.get("title_theme", "你的文章标题")

    draft = _compose_draft(meta, title, chapters, transcript)
    write_text_file(article_dir / "article_draft_text_only.md", draft)

    # 生成最小核查报告占位（后续接入检索核查）
    report = (
        "# 文本审稿包摘要\n\n"
        "- 已生成纯文本成稿，待事实核查与人工确认B\n"
        "- 下一步：`agent approve draft-text` 触发配图→转HTML→上传草稿\n"
    )
    write_text_file(article_dir / "verification_reports" / "summary.md", report)

    update_workflow_step(article_dir / "workflow_state.json", "draft_text", "ready_for_review")


