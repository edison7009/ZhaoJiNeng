"""Mirror Chinese HTML (index/all/models/ranking) into whichclaw/ with translation.

One maintenance truth: you edit the Chinese HTML, run this, and the English
site picks up the same structural change with every known Chinese string
swapped for its English equivalent. If you introduce NEW Chinese text, the
script prints how many CJK characters remain in each output file — add a
mapping to TRANSLATIONS and rerun.

The override CSS block (full-width nav, tab spacing, lang switch) lives in
both Chinese and English HTML as an `!important` block, so it survives the
copy — no special handling needed here.

Run directly:   python sync_html.py
As part of:     python sync.py skills   (automatically chained)
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).parent
PAGES = ["index.html", "all.html", "models.html", "ranking.html"]

# Keep long phrases before their substrings. When adding new strings, prepend
# to the list so the longer match wins first.
TRANSLATIONS: list[tuple[str, str]] = [
    # ---- head metadata ----
    ('lang="zh-CN"', 'lang="en"'),
    ("hi@zhaojineng.com", "hi@whichclaw.com"),
    ("zhaojineng.com", "whichclaw.com"),
    ("\u627e\u6280\u80fd \u2014 \u9f99\u867e OpenClaw\u4e2d\u6587\u6280\u80fd\u5e93",
     "WhichClaw \u2014 AI Agent Skills Directory"),
    ("\u5168\u90e8\u6280\u80fd \u2014 \u627e\u6280\u80fd \u00b7 \u9f99\u867e OpenClaw\u4e2d\u6587\u6280\u80fd\u5e93",
     "All Skills \u2014 WhichClaw"),
    ("\u5927\u6a21\u578b\u6392\u884c\u699c \u2014 \u627e\u6280\u80fd \u00b7 \u9f99\u867e OpenClaw\u4e2d\u6587\u6280\u80fd\u5e93",
     "LLM Rankings \u2014 WhichClaw"),
    ("\u5168\u7403\u9f99\u867e\u6392\u884c\u699c \u2014 \u627e\u6280\u80fd \u00b7 \u9f99\u867e OpenClaw\u4e2d\u6587\u6280\u80fd\u5e93",
     "Global Agent Rankings \u2014 WhichClaw"),
    ("\u9f99\u867e Agent \u751f\u6001\u6392\u884c\u699c\uff0c\u8ffd\u8e2a Star \u589e\u957f\u3001\u8d21\u732e\u8005\u6d3b\u8dc3\u5ea6\u548c\u9879\u76ee\u53d1\u5c55\u8d8b\u52bf\u3002",
     "A leaderboard of AI agents across GitHub \u2014 stars, contributors, commits."),
    ("\u5168\u7403\u5927\u8bed\u8a00\u6a21\u578b\u5b9e\u529b\u699c\uff0c\u6309\u4eca\u65e5\u3001\u672c\u5468\u3001\u672c\u6708\u4e09\u4e2a\u7ef4\u5ea6\u8ffd\u8e2a\u6a21\u578b\u8c03\u7528\u70ed\u5ea6\u3002",
     "A global LLM leaderboard by day, week, and month."),
    ("\u5b9e\u65f6\u8ffd\u8e2a\u5168\u7403\u9876\u7ea7\u5927\u8bed\u8a00\u6a21\u578b (LLM) \u7684\u8c03\u7528\u91cf\u4e0e\u70ed\u5ea6\u8d8b\u52bf\u3002",
     "A global LLM leaderboard by day, week, and month."),

    # ---- footer + business contact ----
    ("\u5546\u52a1\u5408\u4f5c\uff1a", "Business: "),
    ("\u627e\u6280\u80fd (whichclaw.com)", "WhichClaw (whichclaw.com)"),
    ("GitHub API \u6bcf\u5c0f\u65f6\u540c\u6b65", "Synced hourly via GitHub API"),

    # ---- nav ----
    ('>\u627e\u6280\u80fd<', '>WhichClaw<'),
    ('alt="\u627e\u6280\u80fd"', 'alt="WhichClaw"'),
    ("\u5b98\u65b9\u63a8\u8350", "Featured"),
    ("\u5168\u90e8\u6280\u80fd", "All Skills"),
    ("\u63a2\u7d22\u5168\u90e8\u6280\u80fd", "Explore All Skills"),
    ("\u5168\u7403 <span>\u9f99\u867e\u6392\u884c\u699c</span>", "Global <span>Agent Rankings</span>"),
    ("\u5168\u7403 <span>\u5927\u6a21\u578b\u6392\u884c\u699c</span>", "Global <span>LLM Rankings</span>"),
    ("\u5168\u7403\u9f99\u867e\u5b9e\u65f6\u6392\u540d", "Agent Rankings"),
    ("\u9f99\u867e\u6392\u884c\u699c", "Agent Rankings"),
    ("\u5927\u6a21\u578b\u6392\u884c\u699c", "LLM Rankings"),
    ('class="badge-soon">\u63a8\u8350</span>', 'class="badge-soon">Hot</span>'),

    # ---- index hero ----
    ('\u517b\u597d\u9f99\u867e Agent\uff0c<br>\u5148<span>\u627e\u6280\u80fd\uff01</span>',
     'Use Agent,<br>find <span>skills</span> first!'),
    ('\u517b\u597d\u9f99\u867eClaw\uff0c<br>\u5148<span>\u627e\u6280\u80fd\uff01</span>',
     'Use Agent,<br>find <span>skills</span> first!'),
    ("\u4e3a\u4e2d\u56fd\u9f99\u867e\u517b\u6b96\u6237\u6253\u9020\u4e2d\u6587 Skills \u793e\u533a",
     "Every AI agent skill, in one place"),
    ("\u7cbe\u9009\u63a8\u8350\uff0c\u9ad8\u901f\u4e0b\u8f7d\u4f53\u9a8c\uff0c\u8f7b\u677e\u67e5\u627e ClawHub 3.4\u4e07 \u4e2a AI Skills",
     "Hand-picked skills. Fast downloads. Browse 25k+ AI agent skills."),
    ("\u67e5\u770b\u7cbe\u9009\u699c\u5355", "View Featured"),
    ("\u4ece ClawHub \u751f\u6001\u4e2d\u7cbe\u9009\u6700\u503c\u5f97\u5b89\u88c5\u7684 50 \u4e2a AI Skills\uff0c\u56fd\u5185\u76f4\u8fde\u955c\u50cf\uff0c\u4e00\u952e\u52a0\u901f\u5b89\u88c5\u3002",
     "Top 50 AI agent skills, hand-picked from the ecosystem. One click to install."),

    # ---- all.html header + categories ----
    ("\u6d4f\u89c8 ClawHub \u751f\u6001\u4e2d\u7684\u6240\u6709 AI \u6280\u80fd\uff0c\u652f\u6301\u5206\u7c7b\u7b5b\u9009\u4e0e\u641c\u7d22",
     "Browse every AI agent skill, with search and category filters."),
    ("\u641c\u7d22\u6280\u80fd\u540d\u79f0\u6216\u529f\u80fd\u63cf\u8ff0\uff08\u652f\u6301\u4e2d\u82f1\u6587\uff09...",
     "Search skills by name or description\u2026"),
    (">\u5168\u90e8<", ">All<"),
    ("AI \u667a\u80fd", "AI Intelligence"),
    ("\u5f00\u53d1\u5de5\u5177", "Developer Tools"),
    ("\u6548\u7387\u63d0\u5347", "Productivity"),
    ("\u6570\u636e\u5206\u6790", "Data Analysis"),
    ("\u5185\u5bb9\u521b\u4f5c", "Content Creation"),
    ("\u5b89\u5168\u5408\u89c4", "Security & Compliance"),
    ("\u901a\u8baf\u534f\u4f5c", "Communication"),
    ('\ud83e\udd9e \u5168\u90e8 AI Skills', '\ud83e\udd9e All AI Skills'),

    # ---- loading + empty states ----
    ("\u6b63\u5728\u52a0\u8f7d\u6280\u80fd\u5e93\u6570\u636e\uff0c\u8bf7\u7a0d\u5019...", "Loading skills library\u2026"),
    ("\u52a0\u8f7d\u699c\u5355\u6570\u636e\u4e2d...", "Loading leaderboard\u2026"),
    ("\u52a0\u8f7d\u699c\u5355\u6570\u636e\u4e2d\u2026", "Loading leaderboard\u2026"),
    ("\u52a0\u8f7d\u4e2d...", "Loading\u2026"),
    ("\u52a0\u8f7d\u4e2d\u2026", "Loading\u2026"),
    ("\u6570\u636e\u52a0\u8f7d\u4e2d\u2026", "Loading\u2026"),
    ("\u6570\u636e\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u5237\u65b0\u91cd\u8bd5\u3002", "Failed to load. Please refresh."),
    ("\u6570\u636e\u52a0\u8f7d\u5931\u8d25", "Failed to load"),
    ("\u8bf7\u5237\u65b0\u9875\u9762\u91cd\u8bd5\u3002", "Please refresh to retry."),
    ("\u7f51\u7edc\u6216\u89e3\u6790\u9519\u8bef", "Network or parse error"),
    ("\u2014 \u5df2\u52a0\u8f7d\u5168\u90e8\u6570\u636e \u2014", "\u2014 All loaded \u2014"),
    ("\u672a\u627e\u5230\u76f8\u5173\u6280\u80fd", "No skills match"),
    ("\u5c1d\u8bd5\u66f4\u6362\u641c\u7d22\u8bcd\uff0c\u6216\u6eda\u52a8\u5230\u5e95\u90e8\u52a0\u8f7d\u66f4\u591a\u70ed\u95e8\u5e93", "Try a different search."),
    ("\u5c1d\u8bd5\u66f4\u6362\u641c\u7d22\u8bcd\u6216\u5206\u7c7b", "Try a different search or category."),
    ("\u5168\u5e93\u52a0\u8f7d\u4e2d", "Loading"),
    ("\u8be5\u5468\u671f\u6682\u65e0\u6570\u636e\u3002", "No data for this period."),
    ("\u6682\u65e0\u6392\u540d\u6570\u636e", "No data yet."),
    ("\u5171 ${allSkills.length.toLocaleString()} \u4e2a\u6280\u80fd",
     "${allSkills.length.toLocaleString()} skills"),
    ("\u5339\u914d\u5230 ${filteredSkills.length.toLocaleString()} \u4e2a\u6280\u80fd",
     "${filteredSkills.length.toLocaleString()} matches"),

    # ---- modal ----
    ("\u8bf7\u5b89\u88c5\u8fd9\u4e2a\u6280\u80fd ", "Install this skill: "),
    ("\u590d\u5236\u7ed9 AI Agent\uff0c\u81ea\u52a8\u8bc6\u522b\u5e76\u5b89\u88c5", "Paste to your AI Agent to install."),
    (">\u590d\u5236<", ">Copy<"),
    (">\u5df2\u590d\u5236<", ">Copied<"),
    (">\u5173\u95ed<", ">Close<"),
    ("\u590d\u5236\u6210\u529f", "Copied"),
    ("\u590d\u5236\u5931\u8d25", "Copy failed"),
    ("\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f", "Copied to clipboard"),
    ("\u8bf7\u624b\u52a8\u590d\u5236", "Please copy manually"),
    ("btn.textContent = '\u590d\u5236'", "btn.textContent = 'Copy'"),
    ("|| '\u6682\u65e0\u8be6\u7ec6\u63cf\u8ff0'", "|| 'No description yet'"),
    ("|| '\u6682\u65e0\u63cf\u8ff0\u4fe1\u606f'", "|| 'No description'"),
    ("|| '\u6700\u8fd1\u66f4\u65b0'", "|| 'Recently updated'"),

    # ---- index hero card + stat chips ----
    ("\u6b63\u5728\u83b7\u53d6\u6280\u80fd\u4fe1\u606f...", "Loading skill info\u2026"),
    ("\u6b63\u5728\u540c\u6b65\u6700\u65b0\u6280\u80fd\u6570\u636e...", "Syncing latest skill data\u2026"),
    ("\u2605 \u5b98\u65b9\u8ba4\u8bc1\u63a8\u8350", "\u2605 Official"),
    ("\u26a1 \u52a0\u901f\u4e0b\u8f7d", "\u26a1 Fast Install"),
    ("\u2713 \u5b89\u5168\u5ba1\u8ba1", "\u2713 Audited"),
    ("\u7cbe\u9009\u6280\u80fd Top 50", "Featured Top 50"),
    ("\u2b50\ufe0f \u6536\u85cf\u8bc4\u5206", "\u2b50\ufe0f Rating"),
    ("\ud83d\udce5 \u7d2f\u8ba1\u4e0b\u8f7d", "\ud83d\udce5 Downloads"),
    ("\ud83d\udce6 \u6d3b\u8dc3\u96c6\u6210", "\ud83d\udce6 Active Installs"),
    ("\u5b89\u88c5\u65b9\u5f0f", "How to Install"),
    ("\u628a\u4e0b\u9762\u8fd9\u53e5\u8bdd\u590d\u5236\u7ed9 AI Agent\uff1a", "Copy this to your AI Agent:"),
    ("\u9002\u7528\u6240\u6709\u5e73\u53f0 \u00b7 AI \u4f1a\u81ea\u52a8\u8bc6\u522b\u5e76\u4e0b\u8f7d\u5b89\u88c5",
     "Works on any platform \u2014 your agent will detect and install."),
    ("\u9002\u7528\u6240\u6709\u5e73\u53f0 &middot; AI \u4f1a\u81ea\u52a8\u8bc6\u522b\u5e76\u4e0b\u8f7d\u5b89\u88c5",
     "Works on any platform &middot; your agent will detect and install"),
    ("'\u7efc\u5408\u589e\u5f3a'", "'Skill'"),
    ("\u2014 \u5df2\u5c55\u793a\u5168\u90e8\u7cbe\u9009\u6280\u80fd \u2014", "\u2014 All featured loaded \u2014"),

    # ---- models period ----
    (">\u4eca\u65e5<", ">Today<"),
    (">\u672c\u5468<", ">This Week<"),
    (">\u672c\u6708<", ">This Month<"),
    ("\u4eca\u65e5 (24h)", "Today"),
    ("\u672c\u5468 (7d)", "This Week"),
    ("\u672c\u6708 (30d)", "This Month"),
    ("\u6570\u636e\u66f4\u65b0\u4e8e", "Updated"),
    ("Top 20 \u00b7 \u6309 OpenRouter token \u8c03\u7528\u91cf\u6392\u5e8f", "Top 20"),
    ('id="periodLabel">\u672c\u5468</span>', 'id="periodLabel">This Week</span>'),
    ('id="periodLabel">\u4eca\u65e5</span>', 'id="periodLabel">Today</span>'),
    ('id="periodLabel">\u672c\u6708</span>', 'id="periodLabel">This Month</span>'),
    ("'zh-CN', { hour12: false }", "'en-US', { hour12: false }"),
    ("'zh-CN'", "'en-US'"),
    ("PERIOD_LABEL = { day: '\u4eca\u65e5', week: '\u672c\u5468', month: '\u672c\u6708' }",
     "PERIOD_LABEL = { day: 'Today', week: 'This Week', month: 'This Month' }"),

    # ---- ranking summary cards + table ----
    # Emoji stripped on EN side: English labels (ECOSYSTEM STARS,
    # 7D GROWTH, TOP GROWTH) are long enough that the leading emoji
    # pushes them onto two lines inside the summary cards. CN labels
    # are short, so emojis still fit there.
    (" \u9886\u8dd1\u8005", "LEADER"),
    ("\u2b50 \u751f\u6001\u603b\u6536\u85cf", "ECOSYSTEM STARS"),
    ("\ud83d\udcc8 7\u65e5\u751f\u6001\u589e\u957f", "7D GROWTH"),
    ("\ud83d\ude80 7\u65e5\u6700\u5feb\u589e\u957f", "TOP GROWTH"),
    ("\u8ffd\u8e2a ", "Across "),
    (" \u4e2a\u9879\u76ee", " tracked repos"),
    (">\u6392\u540d<", ">RANK<"),
    (">\u9879\u76ee<", ">PROJECT<"),
    (">7\u65e5\u6536\u85cf<", ">7D STARS<"),
    (">7\u65e5\u8d21\u732e\u8005<", ">7D CONTRIBS<"),
    (">7\u65e5\u63d0\u4ea4<", ">7D COMMITS<"),
    (">\u53d8\u5316<", ">CHANGE<"),
    (">\u603b\u6536\u85cf \u2193<", ">TOTAL STARS \u2193<"),
    (">\u4e0a\u5347<", ">Rising<"),
    (">\u4e0b\u964d<", ">Cooling<"),
    ("\u521a\u521a\u66f4\u65b0", "Just updated"),
    ("\u5206\u949f\u524d\u66f4\u65b0", " min ago"),
    ("\u5c0f\u65f6\u524d\u66f4\u65b0", " h ago"),
    ("\u6570\u636e\u5df2\u5237\u65b0", "Data refreshed"),
    ("'Stars', '\u6536\u85cf'", "'Stars', 'stars'"),
    ("'stars', '\u6536\u85cf'", "'stars', 'stars'"),
    ("'over 7 days', '\uff087\u5929\uff09'", "'over 7 days', '(7d)'"),

    # ---- TAG_MAP / CAT_MAP values ----
    ("'automation':'\u81ea\u52a8\u5316'", "'automation':'Automation'"),
    ("'browser':'\u6d4f\u89c8\u5668'", "'browser':'Browser'"),
    ("'headless':'\u65e0\u5934\u6a21\u5f0f'", "'headless':'Headless'"),
    ("'web':'\u7f51\u9875'", "'web':'Web'"),
    ("'memory':'\u8bb0\u5fc6'", "'memory':'Memory'"),
    ("'persistence':'\u6301\u4e45\u5316'", "'persistence':'Persistence'"),
    ("'long-term':'\u957f\u671f'", "'long-term':'Long-term'"),
    ("'copywriting':'\u6587\u6848\u5199\u4f5c'", "'copywriting':'Copywriting'"),
    ("'marketing':'\u8425\u9500'", "'marketing':'Marketing'"),
    ("'seo':'SEO\u4f18\u5316'", "'seo':'SEO'"),
    ("'productivity':'\u6548\u7387'", "'productivity':'Productivity'"),
    ("'assistant':'\u52a9\u624b'", "'assistant':'Assistant'"),
    ("'business':'\u5546\u52a1'", "'business':'Business'"),
    ("'documents':'\u6587\u6863'", "'documents':'Documents'"),
    ("'framework':'\u6846\u67b6'", "'framework':'Framework'"),
    ("'security':'\u5b89\u5168'", "'security':'Security'"),
    ("'identity':'\u8eab\u4efd'", "'identity':'Identity'"),
    ("'templates':'\u6a21\u677f'", "'templates':'Templates'"),
    ("'team':'\u56e2\u961f'", "'team':'Team'"),
    ("'workspace':'\u5de5\u4f5c\u533a'", "'workspace':'Workspace'"),
    ("'persona':'\u89d2\u8272'", "'persona':'Persona'"),
    ("'sales':'\u9500\u552e'", "'sales':'Sales'"),
    ("'proactive':'\u4e3b\u52a8\u578b'", "'proactive':'Proactive'"),
    ("'production':'\u751f\u4ea7'", "'production':'Production'"),
    ("'proposals':'\u63d0\u6848'", "'proposals':'Proposals'"),
    ("'code':'\u4ee3\u7801'", "'code':'Code'"),
    ("'deploy':'\u90e8\u7f72'", "'deploy':'Deploy'"),
    ("'data':'\u6570\u636e'", "'data':'Data'"),
    ("'search':'\u641c\u7d22'", "'search':'Search'"),
    ("'llm':'\u5927\u8bed\u8a00\u6a21\u578b'", "'llm':'LLM'"),
    ("'chat':'\u804a\u5929'", "'chat':'Chat'"),
    ("'model':'\u6a21\u578b'", "'model':'Model'"),
    ("'dev':'\u5f00\u53d1'", "'dev':'Dev'"),
    ("'tool':'\u5de5\u5177'", "'tool':'Tool'"),
    ("'prompt':'\u63d0\u793a\u8bcd'", "'prompt':'Prompt'"),
    ("'prompt engineering':'\u63d0\u793a\u5de5\u7a0b'", "'prompt engineering':'Prompt Engineering'"),
    ("'self-improving':'\u81ea\u6211\u4f18\u5316'", "'self-improving':'Self-improving'"),
    ("'setup-wizard':'\u5b89\u88c5\u5411\u5bfc'", "'setup-wizard':'Setup Wizard'"),
    ("'meeting-notes':'\u4f1a\u8bae\u8bb0\u5f55'", "'meeting-notes':'Meeting Notes'"),
    ("'never-forget':'\u6c38\u4e0d\u9057\u5fd8'", "'never-forget':'Never Forget'"),
    ("'long-running':'\u6301\u7eed\u8fd0\u884c'", "'long-running':'Long-running'"),
    ("'in-chat-commands':'\u804a\u5929\u547d\u4ee4'", "'in-chat-commands':'In-chat Commands'"),
    ("'cost-saving':'\u8282\u7701\u6210\u672c'", "'cost-saving':'Cost-saving'"),
    ("'context-protection':'\u4e0a\u4e0b\u6587\u4fdd\u62a4'", "'context-protection':'Context-protection'"),
    ("'client-proposals':'\u5ba2\u6237\u63d0\u6848'", "'client-proposals':'Client Proposals'"),
    ("'closing-deals':'\u6210\u5355'", "'closing-deals':'Closing Deals'"),
    ("'reliable-agent':'\u53ef\u9760Agent'", "'reliable-agent':'Reliable Agent'"),
    ("'starter-packs':'\u5165\u95e8\u5305'", "'starter-packs':'Starter Packs'"),
    ("'zero-terminal':'\u96f6\u7ec8\u7aef'", "'zero-terminal':'Zero Terminal'"),
    ("'heartbeat':'\u5fc3\u8df3\u68c0\u6d4b'", "'heartbeat':'Heartbeat'"),
    ("'ambient-monitoring':'\u73af\u5883\u76d1\u63a7'", "'ambient-monitoring':'Ambient Monitoring'"),
    ("'presets':'\u9884\u8bbe'", "'presets':'Presets'"),
    ("'escalation':'\u5347\u7ea7\u5904\u7406'", "'escalation':'Escalation'"),
    ("'clawdbot':'\u673a\u5668\u4eba'", "'clawdbot':'Bot'"),
    ("'ai-persona':'AI\u89d2\u8272'", "'ai-persona':'AI Persona'"),
    ("'advisor':'\u987e\u95ee'", "'advisor':'Advisor'"),
    ("'cro':'\u8f6c\u5316\u4f18\u5316'", "'cro':'CRO'"),
    ("'ai-intelligence': 'AI\u667a\u80fd'", "'ai-intelligence': 'AI Intelligence'"),
    ("'developer-tools': '\u5f00\u53d1\u5de5\u5177'", "'developer-tools': 'Developer Tools'"),
    ("'productivity': '\u6548\u7387\u63d0\u5347'", "'productivity': 'Productivity'"),
    ("'data-analysis': '\u6570\u636e\u5206\u6790'", "'data-analysis': 'Data Analysis'"),
    ("'content-creation': '\u5185\u5bb9\u521b\u4f5c'", "'content-creation': 'Content Creation'"),
    ("'security-compliance': '\u5b89\u5168\u5408\u89c4'", "'security-compliance': 'Security & Compliance'"),
    ("'communication-collaboration': '\u901a\u8baf\u534f\u4f5c'", "'communication-collaboration': 'Communication'"),
    ('data-cat="AI\u667a\u80fd"', 'data-cat="AI Intelligence"'),
    ('data-cat="\u5f00\u53d1\u5de5\u5177"', 'data-cat="Developer Tools"'),
    ('data-cat="\u6548\u7387\u63d0\u5347"', 'data-cat="Productivity"'),
    ('data-cat="\u6570\u636e\u5206\u6790"', 'data-cat="Data Analysis"'),
    ('data-cat="\u5185\u5bb9\u521b\u4f5c"', 'data-cat="Content Creation"'),
    ('data-cat="\u5b89\u5168\u5408\u89c4"', 'data-cat="Security & Compliance"'),
    ('data-cat="\u901a\u8baf\u534f\u4f5c"', 'data-cat="Communication"'),
    ("|| '\u901a\u7528'", "|| 'General'"),
    ("'\u641c\u7d22\u7ed3\u679c'", "'Search Results'"),
    (" + ' \u6280\u80fd'", " + ' skills'"),

    # ---- language switches (footer + nav right) — rewrite direction ZH->EN ----
    ('<a href="https://whichclaw.com/" style="color:var(--text-secondary);text-decoration:none;">English</a>',
     '<a href="https://zhaojineng.com/" style="color:var(--text-secondary);text-decoration:none;">\u4e2d\u6587</a>'),
    ('<a href="https://whichclaw.com/all.html" style="color:var(--text-secondary);text-decoration:none;">English</a>',
     '<a href="https://zhaojineng.com/all.html" style="color:var(--text-secondary);text-decoration:none;">\u4e2d\u6587</a>'),
    ('<a href="https://whichclaw.com/ranking.html" style="color:inherit;text-decoration:none;">English</a>',
     '<a href="https://zhaojineng.com/ranking.html" style="color:inherit;text-decoration:none;">\u4e2d\u6587</a>'),
    ('<a href="https://whichclaw.com/" class="nav-lang" hreflang="en">English</a>',
     '<a href="https://zhaojineng.com/" class="nav-lang" hreflang="zh-CN">\u4e2d\u6587</a>'),
    ('<a href="https://whichclaw.com/all.html" class="nav-lang" hreflang="en">English</a>',
     '<a href="https://zhaojineng.com/all.html" class="nav-lang" hreflang="zh-CN">\u4e2d\u6587</a>'),
    ('<a href="https://whichclaw.com/models.html" class="nav-lang" hreflang="en">English</a>',
     '<a href="https://zhaojineng.com/models.html" class="nav-lang" hreflang="zh-CN">\u4e2d\u6587</a>'),
    ('<a href="https://whichclaw.com/ranking.html" class="nav-lang" hreflang="en">English</a>',
     '<a href="https://zhaojineng.com/ranking.html" class="nav-lang" hreflang="zh-CN">\u4e2d\u6587</a>'),

    # ---- logo implementation: Chinese <img logo.png> -> English CSS wordmark ----
    ('<img src="./logo.png" alt="WhichClaw" style="height:24px;width:auto;">',
     '<span style="font-family:\'Inter\',-apple-system,BlinkMacSystemFont,sans-serif;font-weight:800;font-size:22px;letter-spacing:-0.04em;line-height:1;display:inline-block;"><span style="color:#111">Which</span><span style="background:linear-gradient(90deg,#D94025 0%,#f5734a 100%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:#D94025">Claw</span></span>'),
    ('<img src="./logo.png" alt="\u627e\u6280\u80fd" style="height:24px;width:auto;">',
     '<span style="font-family:\'Inter\',-apple-system,BlinkMacSystemFont,sans-serif;font-weight:800;font-size:22px;letter-spacing:-0.04em;line-height:1;display:inline-block;"><span style="color:#111">Which</span><span style="background:linear-gradient(90deg,#D94025 0%,#f5734a 100%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:#D94025">Claw</span></span>'),
]


def translate(text: str) -> str:
    for src, dst in TRANSLATIONS:
        if src:
            text = text.replace(src, dst)
    return text


def main() -> None:
    for fn in PAGES:
        src = HERE / fn
        dst = HERE / "whichclaw" / fn
        if not src.exists():
            print(f"  skip {fn} (source missing)")
            continue
        text = src.read_text(encoding="utf-8")
        text = translate(text)
        dst.write_text(text, encoding="utf-8")
        remaining = len(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", text))
        tag = "OK" if remaining == 0 else f"WARN {remaining} CN chars"
        print(f"  whichclaw/{fn}: {tag}")


if __name__ == "__main__":
    main()
