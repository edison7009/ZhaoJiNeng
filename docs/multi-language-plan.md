# 找技能 多语言扩展计划

> 通过多语言版本的 Find Skills 站群，以极低成本为 EchoBird.ai 引流全球 SEO 长尾流量。

---

## ✅ 为什么值得做

| 优势 | 分析 |
|------|------|
| **成本极低** | 每个站只是翻译 `skills.json` + 改几段 HTML 文字，Cloudflare Pages 免费托管 |
| **长尾 SEO** | 每个语言版本独立域名 = 独立搜索引擎收录，小语种竞争少容易排前 |
| **积少成多** | 20+ 语言 × 每天几十个 UV = 每天几百～几千曝光给 EchoBird.ai |
| **技能数据现成** | 1.3 万技能的描述翻译一次就行，后续同步脚本自动跑 |
| **品牌矩阵** | 多国站点反链 → 提升 echobird.ai 的域名权重 (DA) |

---

## 📋 执行方案

### 域名规划

```
find-skills.com        → 英文版（主站）
jp.find-skills.com     → 日本語
kr.find-skills.com     → 한국어
de.find-skills.com     → Deutsch
fr.find-skills.com     → Français
es.find-skills.com     → Español
pt.find-skills.com     → Português
ru.find-skills.com     → Русский
...
zhaojineng.com         → 中文版（已完成 ✅）
```

### 每个站点结构

1. 同一套 `index.html` + `all.html` 模板
2. 翻译后的 `skills.json`（description 字段翻译）
3. 页面文字本地化（hero 标题、按钮、提示）
4. 顶部导航 → **echobird.ai**（核心引流点）

---

## ⚠️ 注意事项

| 项目 | 说明 |
|------|------|
| **翻译质量** | 用 AI 批量翻译 1.3 万条 description 即可，不需要人工 |
| **更新同步** | GitHub Actions 自动拉新数据 → 翻译 → 部署 |
| **域名成本** | 用一个域名 + 子域名（如 `find-skills.com`），每年只花一个域名的钱 |
| **节奏控制** | 先做 5-8 个流量大的语言（英/日/韩/德/法/西/葡/俄），验证效果再扩展 |

---

## 📊 投入产出分析

**投入：**
- 1 个域名 ≈ ¥80/年
- AI 翻译 1.3 万条 × 8 语言 ≈ ¥50（API 费用）
- Cloudflare Pages 托管 = 免费
- GitHub Actions 自动化 = 免费

**产出：**
- 多语言 SEO 长尾流量
- echobird.ai 全球品牌曝光
- 多站点反链提升主站域名权重

---

## 🚀 执行步骤

### Phase 1：英文主站（验证模型）

- [ ] 注册 `find-skills.com` 域名
- [ ] 基于 `zhaojineng.com` 模板创建英文版
- [ ] 翻译 `skills.json` 中的 `description` 字段为英文
- [ ] 页面文字本地化（hero、按钮、提示等）
- [ ] 部署到 Cloudflare Pages
- [ ] 提交 Google Search Console 收录
- [ ] 观察 2-4 周流量数据

### Phase 2：扩展高流量语言

- [ ] 日语版 `jp.find-skills.com`
- [ ] 韩语版 `kr.find-skills.com`
- [ ] 德语版 `de.find-skills.com`
- [ ] 法语版 `fr.find-skills.com`
- [ ] 西班牙语版 `es.find-skills.com`
- [ ] 葡萄牙语版 `pt.find-skills.com`
- [ ] 俄语版 `ru.find-skills.com`

### Phase 3：自动化流水线

- [ ] GitHub Actions 定时同步最新 `skills.json`
- [ ] AI 自动翻译新增技能描述
- [ ] 自动部署到各语言子域名

---

## 🔗 数据源

| 资源 | URL |
|------|-----|
| 技能索引 | `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills.json` |
| 技能下载 | `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills/{slug}.zip` |
| CLI 安装 | `https://skillhub-1251783334.cos.ap-guangzhou.myqcloud.com/install/install.sh` |

---

> **总结：** 性价比极高的引流策略。先搞一个英文版 `find-skills.com` 测试效果，跑通了就批量铺开。
