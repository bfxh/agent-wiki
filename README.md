# trit-agent 维基

**在线版**：https://bfxh.github.io/agent-wiki/

trit-agent 的独立维基。内容用 Markdown 写（`*.md`），构建成静态站点推到 GitHub Pages。

---

## 目录结构

```
.
├── *.md              21 个维基页面（内容源）
├── wiki.json         页面清单：slug/file/title/group/icon/summary/tags
├── transport-events.json  传输层 UI 的示例事件（本地静态，非真实日志）
├── scripts/
│   ├── build_site.py Markdown → HTML 的生成器（零依赖）
│   ├── check_wiki.py 文档门禁 W1-W12（零依赖，带负例自测）
│   └── site.js       搜索 + 传输层抽屉（零依赖）
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

### 页面清单（`wiki.json`）

页面顺序、侧边栏分组、标题、摘要、标签、文件名都在 `wiki.json` 里：

```json
{
  "slug": "Coordination",
  "file": "Coordination.md",
  "title": "协调与传输",
  "group": "原理",
  "icon": "🔀",
  "summary": "一轮能传什么，什么时候必须多轮",
  "tags": ["原理", "协调", "传输", "调度"]
}
```

加新页面 = 加一条清单 + 写一个 `.md`。构建器会 fail-closed 校验：

- slug 唯一；
- 每个 `file` 存在；
- 每个 `*.md`（除 `README.md`）都登记；
- `[[内部链接]]` 目标存在（代码块/行内代码里的示例不算）；
- `transport-events.json` 字段完整。

### 门禁（W1-W12）

```bash
# 负例自测：必须证明每类错误都能判红
python scripts/check_wiki.py --self-test

# 实际检查：清单/孤儿/断链/元数据/传输事件/密钥/构建/UI/分组/生成数据
python scripts/check_wiki.py --src .

# JSON 输出
python scripts/check_wiki.py --src . --json
```

- 任何 FAIL 都打印具体文件/字段；退出码 1。
- `--self-test` 会造 11 个负例；如果某个负例没红，自测自己判红。
- CI：`.github/workflows/wiki-gate.yml`，push/PR 都跑自测 + 门禁 + 构建。

### 搜索与传输层 UI

- **搜索**：侧边栏输入框，按标题/摘要/标签/正文过滤，纯本地 `search-data.js`。
- **传输徽标**：侧边栏“传输 N”；N = `transport-events.json` 的事件条数。
- **抽屉**：点徽标打开；列出 from→to、类型、轮次、字节、状态；点一条展开 payload；可按状态筛选；`Esc` 关闭。
- **无网络可用**：数据以 `window.TRANSPORT_EVENTS` 内嵌，不 fetch、不请求后端。
- **示例数据**：`transport-events.json` 是演示，不是真实会话日志；以后从 `trit-orch` 的 `TraceStore` 转换。

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
| `Coordination` | 协调与传输：一轮能传什么，什么时候必须多轮 |
| `Concept-Map` | 三进制概念地图：trit / trit-schedule / trit-orch / trit-immune / trit-agent |
| `Agent-Interop` | 跨智能体通讯：信封、能力握手、四态回执 |
| `Transport-UI` | 传输层 UI：徽标、抽屉、事件 schema |
| `Docs-As-Artifacts` | 文档即工件：清单、渲染、发布 |
| `Gate` | 文档门禁 W1-W12：清单/断链/传输/构建/UI |

---

## 相关仓库

- **[bfxh/trit-agent](https://github.com/bfxh/trit-agent)** —— Rust 状态机
- **[bfxh/trit-mc](https://github.com/bfxh/trit-mc)** —— Minecraft 侧（数据包）
