### 文章创作 Agent PRD（公众号优先版 / 两次人工确认 / 文本先审图后生）

本文档定义一套可落地的“文章创作Agent”，以公众号为首发平台，围绕“自动化脚本 + 可配置提示词 + 配置文件 + 统一Workflow”落地无人值守写作闭环，并保留两次人工确认（大纲、纯文本）的人机协同停点。生成后的成稿包含配图，可自动上传为公众号草稿。

---

## 1. 目标与范围

- 目标：从 `Materials/` 的输入素材（以语音转文字稿为主）自动产出大纲与90%初稿，文本通过后自动生成配图，并完成“公众号草稿上传”。
- 范围：
  - 包含：目录规范、配置体系、要素提取、记忆检索（自有风格匹配）、公众号爆款模式参考、生成大纲（人工确认A）、分章扩写与事实核查、文本审稿包（人工确认B）、配图（豆包）、转HTML与草稿上传。
  - 不包含：自动发布、社区日报/管理Agent。

成功标准（MVP）：
- 1小时内，从素材到“已上传草稿”。
- 大纲与文本各一次强制人工确认；失败可重试、可恢复。
- 成稿包含配图（封面+每章1图），草稿上传成功率≥95%。

---

## 2. 用户流程（你视角）

1) 将转写稿与素材放入 `Articles/进行中/<文章>/Materials/`（主文件：`transcript.txt/.md`）
2) 运行 `agent outline` 生成大纲 → 人工确认A（看5个标题与章节结构）
3) 运行 `agent draft --text-only` 自动分章扩写+事实核查 → 产出“文本审稿包”
4) 人工确认B（看纯文本与核查报告）
5) 系统自动：生成配图（豆包）→ 插入图片 → 转HTML → 上传公众号草稿
6) 获取草稿ID与预览地址，完成。

---

## 3. 系统架构与模块

- 自动化脚本（双手）：清洗/抽取/格式化/文件生成/公众号API对接。
- 可配置提示词（灵魂）：分层模板（任务要素 + 平台风格 + 记忆样式 + 步骤指令）。
- 配置文件（工具箱）：路径、模型与API、流程开关、阈值。
- 统一Workflow（大脑）：标准化待办与状态机，支持断点续跑与两次人工确认。

---

## 4. 目录结构

```
/
├── Articles/
│   ├── 进行中/
│   │   └── <文章标题>/
│   │       ├── Materials/                # 输入素材（transcript/notes/links/facts）
│   │       ├── article_creation.md       # 人类可读的流程待办（可选）
│   │       ├── workflow_state.json       # 机器可读状态
│   │       ├── extracted_meta.json       # 任务要素
│   │       ├── market_references.json    # 公众号爆款“模式摘要”
│   │       ├── article_structure.md      # 大纲（人工确认A）
│   │       ├── article_writing.md        # 原子化写作剧本
│   │       ├── article_draft_text_only.md# 纯文本成稿（人工确认B）
│   │       ├── verification_reports/     # 事实核查报告
│   │       ├── image_plan.json           # 配图计划（文本通过后生成）
│   │       ├── images/                   # 豆包生成的图片
│   │       ├── article_draft.md          # 含图成稿（配图后生成）
│   │       └── outputs/
│   │           ├── final.md              # 最终导出的Markdown
│   │           └── preview.html          # 预览HTML
│   └── 已完成/
├── Memories/
│   ├── Contents/                         # 自有历史文章（任意格式）
│   ├── Examples/                         # 公众号爆款链接/摘要
│   ├── .ingested/                        # 统一抽取后的文本副本
│   ├── knowledge_dict.json               # 术语字典
│   └── memory_indexing.json              # 索引（元信息）
├── Templates/
│   ├── article_creation.md
│   ├── article_elements_extraction.md
│   ├── platform_styles_lib.json
│   └── prompts/                          # Prompt片段模板（Jinja2）
└── config/
    ├── agent_config.json                 # 全局配置
    ├── wechat_config.json                # 公众号配置
    └── .env.example                      # 密钥样例（实际用 .env）
```

---

## 5. 流程与状态机

阶段与停点：

0) 初始化：创建任务空间与`workflow_state.json`

1) 要素提取（extracted_meta.json）
- 输入：`Materials/`（`transcript.*`为主）
- 输出：主题/受众/目标/关键点/风格/SEO关键词
- 状态：`steps.extract_meta = done`

2) 记忆检索（风格匹配，80/20）
- 自有内容Top2 + 标杆案例Top1-2（来自`Memories/`）
- 状态：`memory_basis` 写入TopN与摘要

3) 公众号爆款模式参考（site白名单）
- 检索域：`mp.weixin.qq.com`（Perplexity检索与模式摘要）
- 产物：`market_references.json`
- 状态：`steps.market_refs = done`

4) 生成大纲（article_structure.md）→ 人工确认A（停）
- 状态：`steps.outline = pending_review | approved`

5) 生成写作剧本（article_writing.md）
- 状态：`steps.writing_plan = done`

6) 分章扩写 + 事实核查（文本阶段）
- 每章：写 → 抽取断言 → Perplexity检索验证（白名单域）→ 置信度打分 → 必要改写
- 产物：`article_draft_text_only.md`、`verification_reports/`
- 状态：`steps.draft_text = ready_for_review`

7) 人工确认B（纯文本审稿包，停）
- 通过：`steps.draft_text = approved` → 进入配图
- 退回：你修改文本后再跑 `agent draft --text-only`

8) 配图（文本通过后）
- 生成`image_plan.json` → 豆包生成图片 → 插入 → `article_draft.md`
- 状态：`steps.images = embedded`

9) 草稿上传（公众号）
- Markdown→HTML，上传正文图片获取URL、上传封面素材，`/cgi-bin/draft/add`
- 状态：`steps.wechat_draft = done`

状态文件（示例）：
```json
{
  "current_step": "outline",
  "steps": {
    "extract_meta": "done",
    "market_refs": "done",
    "outline": "pending_review",
    "writing_plan": "",
    "draft_text": "",
    "images": "",
    "wechat_draft": ""
  },
  "checkpoints": { "last_chapter_done": 0 },
  "memory_basis": { "own_top2": ["c001","c014"], "reference_top2": ["e102"] },
  "timestamps": { }
}
```

---

## 6. 数据与文件格式（Schemas）

extracted_meta.json
```json
{
  "title_theme": "AI写作自动化的实践",
  "target_audience": "微信公众号作者",
  "goals": ["降低创作成本","提高频率"],
  "key_points": ["三支柱","工作流","断点续跑"],
  "constraints": ["不抄袭","风格统一"],
  "tone": "理性专业，实操为主",
  "seo": { "primary_keywords": ["AI写作","工作流","公众号"] },
  "platform": "wechat_public",
  "style_refs": { "own_works": [], "reference_examples": [] }
}
```

memory_indexing.json（示意）
```json
{
  "own_works": [
    {"id":"c001","title":"自动化经验","path":"Memories/Contents/a.md","tags":["AI","自动化"],"tone":"理性","keywords":["工作流","Agent"]}
  ],
  "reference_examples": [
    {"id":"e102","title":"爆款标题拆解","path":"Memories/Examples/wechat_links.txt","tone":"吸引","hooks":["反差","悬念"],"structural_patterns":["问题-解决-案例"],"expression_techniques":["金句","列表化"]}
  ]
}
```

market_references.json
```json
{
  "platform": "wechat_public",
  "source_domain_whitelist": ["mp.weixin.qq.com"],
  "queries": ["site:mp.weixin.qq.com AI 自动化 写作 爆款 标题"],
  "candidates": [
    {
      "title": "标题范例",
      "url": "https://mp.weixin.qq.com/...",
      "title_hooks": ["反直觉","数字化对比"],
      "structural_patterns": ["三段论","问题-方案-案例-总结"],
      "expression_techniques": ["比喻","类比","反问"]
    }
  ],
  "summary": {
    "top_title_hooks": ["反差","数字化"],
    "common_structures": ["总-分-总","问题-解决-案例"],
    "common_devices": ["数据支撑","类比解释"]
  }
}
```

workflow_state.json（关键字段已在上节示例）

image_plan.json（文本通过后生成）
```json
{
  "cover": { "prompt": "AI写作自动化/工作流/简洁科技感", "alt": "封面图", "keywords": ["AI","workflow"] },
  "inline": [
    { "anchor_id": "ch1", "prompt": "三支柱示意图", "alt": "三支柱" },
    { "anchor_id": "ch2", "prompt": "工作流流程图", "alt": "流程图" }
  ]
}
```

verification_reports/chapter-XX.json（示意）
```json
{
  "chapter": 1,
  "assertions": [
    {"type":"numeric","text":"阅读量从100到5000","confidence":0.78,"evidence":[{"source":"mp.weixin.qq.com","snippet":"..."}]} 
  ],
  "rewrites": [{"from":"原句","to":"改写句","reason":"证据不足"}]
}
```

wechat_config.json（示意）
```json
{
  "appid": "YOUR_APPID",
  "appsecret": "YOUR_APPSECRET",
  "draft_default": { "author": "你的署名", "digest_policy": "auto_first_paragraph", "show_cover": true }
}
```

---

## 7. 外部接口与规范

文本与检索（Perplexity，默认）：
- 用途：站内检索（`site:mp.weixin.qq.com`）、模式摘要（标题/结构/表达）、分章扩写、事实核查。
- 约束：不落地第三方原文，仅存模式摘要；核查证据仅内部留痕。
- 配置：`TEXT_LLM_PROVIDER=perplexity`、`PERPLEXITY_API_KEY`、可设 `BASE_URL`（OpenAI兼容协议时）。

图片（豆包图像API，默认）：
- 用途：生成封面+每章1图。
- 产物：保存至 `images/`，在Markdown中真实嵌入；上传草稿时替换为微信可访问URL。
- 配置：`DOUBAO_IMAGE_API_KEY`、`DOUBAO_IMAGE_API_URL`。

公众号（WeChat Official Account）：
- 获取token：`GET /cgi-bin/token?grant_type=client_credential&appid=xxx&secret=xxx`
- 正文内图片上传：`POST /cgi-bin/media/uploadimg`（返回可用URL）
- 封面/首图素材（永久或临时）：`/cgi-bin/material/add_material`（type=image）
- 新增草稿：`POST /cgi-bin/draft/add`（`articles`结构需包含标题、作者、摘要、内容、封面等）
- 注意：需在公众号后台配置IP白名单；内容为HTML；图片URL必须为微信认可域。

---

## 8. 配置与开关（agent_config.json 建议字段）

```json
{
  "review": { "gate_outline": true, "gate_text": true },
  "verification": { "enabled": true, "strictness": "normal", "source_whitelist": ["mp.weixin.qq.com"] },
  "ingestion": { "trigger": "command", "primary_file_pattern": ["transcript.*.txt","transcript.*.md"] },
  "text_llm": { "provider": "perplexity", "model": "default" },
  "images": { "provider": "doubao", "generate_on_text_approval": true },
  "wechat": { "enabled": true }
}
```

`.env.example`（示意）：
```
PERPLEXITY_API_KEY=
DOUBAO_IMAGE_API_KEY=
DOUBAO_IMAGE_API_URL=
WECHAT_APPID=
WECHAT_APPSECRET=
TEXT_LLM_BASE_URL=
```

---

## 9. 命令行（CLI）与用法

- `agent outline`：读取 `Materials/`，完成要素提取、记忆检索、公众号爆款模式参考，生成 `article_structure.md` 并置 `steps.outline=pending_review`。
- `agent approve outline`：将 `steps.outline=approved`，继续生成写作剧本。
- `agent draft --text-only`：按剧本逐章扩写并事实核查，输出 `article_draft_text_only.md` 与 `verification_reports/`，置 `steps.draft_text=ready_for_review`。
- `agent approve draft-text`：将 `steps.draft_text=approved`，触发 `images → wechat-draft` 自动流程。
- （可选）`agent images`：手动仅执行配图与嵌入。
- （可选）`agent wechat-draft`：手动仅执行转HTML、图片上传与“新增草稿”。

---

## 10. 验收标准

- 时效：≤1小时完成从素材到“新增草稿”。
- 质量：
  - 大纲经你确认后再继续；文本经你确认后再生成配图。
  - 文本事实核查合格（低可信断言被改写或标注复审）。
- 配图：封面+每章1图成功生成与插入。
- 接口：草稿上传成功率≥95%，失败具备重试与错误日志。

---

## 11. 风险与对策

- 事实性偏差：分章核查+必要改写；`strictness` 可调高。
- 外部检索不稳定：Perplexity主用；必要时可加站内检索后备（Bing开关）。
- 公众号接口限制：IP白名单、图片域限制、素材规范严格遵守；失败重试、错误分级日志。
- 合规：不落第三方原文，仅模式摘要；内部保存核查证据，不在成稿展示引用。
- 图片版权：豆包生成视作自制；若后续接图库，需保存许可证信息。

---

## 12. 里程碑

- M0：PRD定稿（本文件）
- M1：目录与配置基线（Templates/、config/、空索引）
- M2：要素提取与记忆检索（含.ingested）
- M3：公众号爆款模式参考 + 大纲生成 + 人工确认A
- M4：写作剧本 + 分章扩写 + 事实核查 + 文本审稿包 + 人工确认B
- M5：配图（豆包） + 转HTML + 公众号草稿上传
- M6：稳定性与回归；模板/风格库完善

---

## 13. 日志与审计

- 记录：流程阶段、检索Query、核查断言与得分、改写痕迹、接口调用状态。
- 产物：`verification_reports/summary.md`、`logs/*.log`（可选）。

---

## 14. 备注（实现细节建议）

- 记忆库格式不限（md/txt/docx/pdf）；统一抽取为 `.ingested/` 文本供检索，不改你原件。
- 默认触发方式为“命令式”；监听模式（watch）可选开关（需常驻进程）。
- 提示词采用分层模板，便于按平台/风格/步骤组合。
- 断点粒度：
  - 强制人工停点：大纲（A）、文本（B）。
  - 内部章节级断点：用于异常恢复，不强制打扰你。


