# trit-agent 维基

**在线版**：https://bfxh.github.io/agent-wiki/

trit-agent 的独立维基。内容用 Markdown 写（`*.md`），构建成静态站点推到 GitHub Pages。

---

## 目录结构

```
.
├── *.md              16 个维基页面（内容源）
├── scripts/
│   └── build_site.py Markdown → HTML 的生成器（零依赖）
└── site/             构建产物（不入库，由 CI/脚本生成）
```

---

## 本地预览

```bash
python scripts/build_site.py --src . --out site
# 然后打开 site/index.html
```

---

## 部署

```bash
python scripts/build_site.py --src . --out site
cd site && git init && git add -A && git commit -m "docs: 更新维基"
git push origin master:gh-pages --force
```

Pages 已在仓库设置里启用（`gh-pages` 分支，根路径）。

---

## 为什么用 GitHub Pages 而不是 GitHub 原生 Wiki

GitHub 原生 Wiki 的 `.wiki.git` 仓库**必须在网页端手工建过第一个页面**才存在：

- REST API `PUT /wiki/pages` → 404
- GraphQL → **完全没有 wiki 相关 mutation**（查过 schema，262 个 mutation 里 0 个）
- `git push` 到 `.wiki.git` → `Repository not found`

这些都实测过了。GitHub 官方就没提供程序化创建首个 wiki 页面的接口。

所以走 Pages：内容还是同一份 Markdown，输出成带侧边导航的 HTML，
而且**能自动构建**——改完 Markdown 跑一条命令就更新。

---

## 生成器说明

`scripts/build_site.py` 是个**零依赖**的 Markdown → HTML 转换器（只用标准库）。

支持：标题、列表、表格、代码块、行内代码、粗体/斜体/删除线、
引用、分割线、链接、`[[内部链接]]`。

处理顺序有讲究：

1. **代码块最先抽走** —— 否则代码里的内容会被当成 Markdown 解析
2. 行内代码其次
3. 然后转义 HTML
4. 最后才做行内格式和链接替换（避免破坏 HTML 实体）

### 页面注册表

页面顺序、侧边栏分组、显示名都在脚本顶部的 `PAGES` / `GROUP_END` 里：

```python
PAGES = [
    ("Home", "首页", "🏠"),
    ("Getting-Started", "上手", "🚀"),
    ...
]
```

加新页面 = 加一行 + 写一个 `.md`。

---

## 页面清单

| 页面 | 内容 |
|---|---|
| `Home` | 首页、仓库地图、目录 |
| `Getting-Started` | 装、跑、按 F8 |
| `Hotkeys` | F8/F9/F10/F6/F7 的行为细节 |
| `Configuration` | 配置项逐条解释 |
| `Background-Daemon` | 后台守护进程、静默死亡那三层坑、计划任务自愈 |
| `Tri-Value-FSM` | 为什么是三值、从 NPC Goal 移植的战术 |
| `Perception` | 两条通道、延迟怎么量的、墙体掩码位序 |
| `Gathering` | 采集门控、挖矿三条判据、视线闭环 |
| `Architecture` | 模块地图与数据流 |
| `Data-Packs` | 数据包、起源包、「拷进去 ≠ 装上了」 |
| `Sensor-Protocol` | 18 个字段、跨仓库契约、守门测试 |
| `Crash-Troubleshooting` | rrls 崩溃真凶（字节码级）、排除法、SRG 速查 |
| `Troubleshooting` | 「没效果」的排查顺序与症状对照表 |
| `Building` | 编译、测试、自检、模拟、端到端验证 |
| `Design-Boundaries` | 诚实的边界、验证到哪一步 |
| `Control-Channels` | 操控方式注册表、哪些路走不通 |

---

## 相关仓库

- **[bfxh/trit-agent](https://github.com/bfxh/trit-agent)** —— Rust 状态机
- **[bfxh/trit-mc](https://github.com/bfxh/trit-mc)** —— Minecraft 侧（数据包）
