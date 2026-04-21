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
python sync.py                 # 全量（skills + models + ranking）
python sync.py skills          # 仅 skills（scratch_sync + generate_pages）
python sync.py models          # 仅大模型排行榜
python sync.py ranking         # 仅龙虾排行榜
```

单步也可以直接跑对应脚本——`sync.py` 只是编排器。

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
