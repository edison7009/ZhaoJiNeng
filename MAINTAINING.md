# 维护手册

本站所有数据榜单都由本地 Python 脚本生成后 commit 到仓库，push 到 `main` 即上线。三条工作流统一入口：`python sync.py`。

## 快速开始

```bash
pip install -r requirements.txt      # 首次，或 aiohttp 缺失时
python sync.py                       # 刷新全部三条流
git add -A && git commit -m "data: refresh" && git push origin main
```

## 入口脚本

```bash
python sync.py                 # 全量（skills + models + ranking + whichclaw）
python sync.py skills          # 仅 skills（含英文数据自动同步）
python sync.py models          # 仅大模型排行榜
python sync.py ranking         # 仅龙虾排行榜
python sync.py whichclaw       # 仅英文站数据筛选（models + ranking 之后跑）
python sync_html.py            # 手动：把中文 HTML 镜像到英文站（见下方 §4）
```

单步也可以直接跑对应脚本——`sync.py` 只是编排器。

---

## 中英双站一图看懂

```
           ┌────── 中文站 zhaojineng.com ──────┐   ┌────── 英文站 whichclaw.com ──────┐
           │                                  │   │                                 │
  data  →  │ skills.json (25MB)               │──►│ public/skills.json (14.6MB 筛英文) │
           │ public/featured.json             │──►│ public/featured.json              │
           │ public/skills_pages/*.json       │──►│ public/skills_pages/*.json        │
           │ public/models_ranking.json       │──►│ public/models_ranking.json (mirror) │
           │ public/ranking_snapshot.json     │──►│ public/ranking_snapshot.json (mirror) │
           │                                  │   │                                 │
  html  →  │ index/all/models/ranking.html    │── sync_html.py（手动）──►│ 同四个 HTML    │
           └──────────────────────────────────┘   └─────────────────────────────────┘
                    改什么 → 跑什么
                    ─────────────────────────────────────────
                    改 skill 数据  → python sync.py skills    （自动双站）
                    改榜单数据    → python sync.py models/ranking
                    改 HTML 结构/文案 → 改中文 + python sync_html.py（见 §4）
```

---

## 三条工作流

### 1. Skills（全站技能库）

| 项目 | 内容 |
|---|---|
| 脚本 | `scratch_sync.py` → `generate_pages.py` |
| 数据源 | `https://lightmake.site/api/skills`（腾讯 SkillHub 后端，需要 Referer/Origin 头） |
| 产物 | `skills.json`（≈25 MB 全量）<br>`public/featured.json`（top 50 精选）<br>`public/skills_pages/*.json`（50 条/页，685 页，分页懒加载用） |
| 消费方 | [all.html](all.html) 首屏加载 `skills_pages/1.json`，后台 hydrate 其余<br>[index.html](index.html) 读 `public/featured.json` 做"精选推荐" |
| 频率 | 按需（用户新增/更新技能后） |

### 2. 大模型排行榜

| 项目 | 内容 |
|---|---|
| 脚本 | `sync_openrouter_models.py` |
| 数据源 | `https://openrouter.ai/rankings?view={day\|week\|month}` 的 SSR 内联数据 + `https://openrouter.ai/api/v1/models`（模型元数据）+ 首页作者头像 |
| 产物 | `public/models_ranking.json`（全本地相对路径，零外链）<br>`public/models_icons/*.{svg,png,jpg}`（作者头像，幂等落盘） |
| 消费方 | [models.html](models.html) |
| 频率 | 每天 1 次建议；OpenRouter 排名数据实时性高，太久不更新榜单会失真 |
| 无须鉴权 | 标准库 urllib 即可 |

### 3. 龙虾排行榜

| 项目 | 内容 |
|---|---|
| 脚本 | `ranking_sync.py` |
| 数据源 | GitHub REST API（`api.github.com/repos/{owner}/{repo}`、`/commits`、`/stats/contributors`） |
| 产物 | `public/ranking_snapshot.json`（ranking.html 直接 fetch）<br>`public/ranking_history/<YYYY-MM-DD>.json`（每次归档，供下次算 7 日 delta） |
| 消费方 | [ranking.html](ranking.html) 优先读 snapshot，失败兜底到 `RANKING_DATA` 硬编码 |
| 频率 | 每 3-7 天；7 日 delta 靠对比 `ranking_history/` 里 ≥6 天前的快照，所以第一次跑 delta 会是 `—`，至少跑两次间隔 7 天才完整 |
| 限流 | 未带 token 时 GitHub API 每小时 60 次（11 repo × 3 请求 = 33 次，单次跑不限流，但连续 debug 会踩）；设 `GITHUB_TOKEN` 环境变量提升到 5000/hr |

追踪的 repo 列表在 `ranking_sync.py` 顶部 `TRACKED` 数组里，要加/删项目改那里即可（也要同步 `ranking.html` 的 `PROJECT_*` 映射）。

### 4. WhichClaw（英文站 whichclaw.com）

| 项目 | 内容 |
|---|---|
| 脚本 | `sync_whichclaw.py` |
| 数据源 | 6 份 `awesome-claude-skills` GitHub README.md（ComposioHQ/hesreallyhim/sickn33/VoltAgent/travisvn/BehiSecc），通过 `raw.githubusercontent.com` 抓取；无鉴权 |
| 产物 | `whichclaw/public/skills.json`（去重后 ~300 条）<br>`whichclaw/public/featured.json`（top 50）<br>`whichclaw/public/skills_pages/*.json`（分页）<br>**Mirror**：`whichclaw/public/models_ranking.json`、`ranking_snapshot.json`、`models_icons/`、`ico/` + 根部 `ico.png`、`logo.png` |
| 消费方 | [whichclaw/index.html](whichclaw/index.html) / [all.html](whichclaw/all.html) / [models.html](whichclaw/models.html) / [ranking.html](whichclaw/ranking.html) |
| 频率 | 每周 1 次；awesome 列表更新不频繁，跑太勤意义不大 |
| 无须鉴权 | 标准库 urllib 即可 |
| 排序 | 出现在越多 awesome 列表 = `score` 越高；同一个 URL 会被 dedupe，合并 `sources` 数组 |

⚠️ **顺序依赖**：`whichclaw/public/models_ranking.json` 和 `ranking_snapshot.json` 是从顶层 `public/` mirror 过去的，所以 `sync.py` 默认先跑 models/ranking 再跑 whichclaw（stage 顺序就是这样）。如果单独跑 `python sync.py whichclaw` 而没先更新 models/ranking，mirror 的就是上次的旧数据。

### 4. 英文 HTML 镜像（`sync_html.py`）

| 项目 | 内容 |
|---|---|
| 脚本 | `sync_html.py` |
| 输入 | `index.html`、`all.html`、`models.html`、`ranking.html`（中文站根目录） |
| 输出 | `whichclaw/index.html` 等 4 个对应文件 |
| 触发方式 | **手动**，不在 `sync.py` 链路里（破坏性覆盖，自动跑会踩掉已调好的英文） |
| 翻译字典 | 脚本顶部 `TRANSLATIONS` 数组，长条目在前，短条目在后 |

**典型流程**（改了中文 HTML 想同步到英文）：
```bash
# 1) 改完中文 HTML (index/all/models/ranking)
# 2) 镜像到英文站
python sync_html.py
#    whichclaw/index.html:  OK
#    whichclaw/all.html:    WARN 12 CN chars   ← 说明字典没覆盖到
# 3) 如果提示 WARN，Grep 出残留中文
grep -oE '[\u4e00-\u9fff]+' whichclaw/all.html | sort -u
# 4) 把新中文 → 英文 的映射补到 sync_html.py 的 TRANSLATIONS 最前
# 5) 再跑一次 python sync_html.py 直到全部 OK
# 6) commit + push
```

**什么情况 _不_ 需要跑**：
- 只改了数据（skills/models/ranking JSON）—— `python sync.py skills` 自动处理英文数据
- 只改了英文独有文案（比如 whichclaw hero badge）—— 直接改英文文件
- 只改了 CSS override（nav 布局之类全局样式）—— 已经用 `!important` 块保护，两边都生效

---

## 常见坑

- **aiohttp 缺失**：`pip install -r requirements.txt`。
- **Windows 终端输出乱码**：日志里的 `—` 在 CMD 下可能显示成 `??`，但写入的 JSON 文件是 UTF-8 clean。可忽略。
- **skills.json 特别大（25 MB）**：不要 `git add` 后又 revert；push 一次 delta 可能几 MB，多次折腾会撑大 git 仓库。
- **龙虾榜 stats/contributors 首次返回 202**：GitHub 后台在算，脚本会把该字段写成 `0`；再跑一次一般就有了。
- **OpenRouter 换页面结构**：`sync_openrouter_models.py` 的 `extract_ranking_data` 用正则从 RSC payload 里抠 `rankingData`；如果 OpenRouter 改了前端，这里会 raise。改正则即可，数据源没变。

---

## 部署

静态站托管在 Cloudflare Pages，绑定 `main` 分支。push 后 1-2 分钟生效。**不要开分支**——直接推 main。

本项目相关的个人偏好与历史背景记录在 `~/.claude/projects/d--ZhaoJiNeng/memory/` 的 auto-memory 系统里，新会话启动时会自动加载。
