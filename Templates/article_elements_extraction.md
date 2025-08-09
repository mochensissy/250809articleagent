# 文章要素提取模板

## 输入
- 主输入：`Materials/transcript.*`
- 辅助输入：`notes.md`、`links.txt`、`facts.json`

## 输出（extracted_meta.json）
- 主题（title_theme）
- 目标受众（target_audience）
- 写作目标（goals[]）
- 关键要点（key_points[]）
- 口吻（tone）
- SEO关键词（seo.primary_keywords[]）
- 平台（platform=wechat_public）

## 规则
- 紧贴主输入，避免凭空扩展
- 关键要点精炼、可直接驱动大纲
- 口吻默认：理性专业，实操为主


