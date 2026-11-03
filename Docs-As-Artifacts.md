# 文档即工件：谁管理、谁渲染、谁发布

> 这一页解决“东西太多、无法管理”的问题。
> 结论：**HTML 只是渲染器，不是真相；真相是 Markdown + `wiki.json` 清单。**
> 管理文档的是“代替 Git 的那个软件”（编排/仓库治理层），不是前端。

---

## 1. 问题

- 页面一多，靠硬编码导航就会漏、会重、会找不到。
- 只靠 HTML 手改，改完就丢源；只靠 Markdown，又没有索引/搜索/分组。
- 多个智能体同时写文档，没有清单就会“你写你的、它写它的”。

---

## 2. 四层

```text
源        Markdown（*.md）+ wiki.json（清单）
  ↓
管理      trit-orch / 仓库治理层：索引、链接、版本、冲突、发布
  ↓
渲染      scripts/build_site.py：Markdown → HTML（零依赖）
  ↓
远端      GitHub Pages（或本地 site/index.html）
```

- **源**：唯一真相；人和智能体只改这里。
- **管理**：负责“有哪些页、属于哪组、谁负责、是否过期、链接是否断”。
- **渲染**：只做格式转换；不拥有内容、不做业务判断。
- **远端**：静态产物；可重建、可丢弃。

---

## 3. `wiki.json` 清单

```json
{
  "title": "trit-agent 维基",
  "subtitle": "...",
  "pages": [
    {
      "slug": "Coordination",
      "file": "Coordination.md",
      "title": "协调与传输",
      "group": "原理",
      "icon": "🔀",
      "summary": "一轮能传什么，什么时候必须多轮",
      "tags": ["原理", "协调", "传输", "调度"]
    }
  ]
}
```

字段：

| 字段 | 作用 |
|---|---|
| `slug` | 输出 HTML 文件名/内部链接目标 |
| `file` | 源 Markdown 文件 |
| `title` | 导航显示名 |
| `group` | 侧边栏分组 |
| `icon` | 导航图标（可选） |
| `summary` | 副标题/搜索摘要 |
| `tags` | 搜索/筛选 |

### 校验规则（建议进门禁）

1. `wiki.json` 能解析；`slug` 唯一。
2. 每个 `file` 存在；每个 `*.md`（除 `README.md`）都在清单里。
3. `[[内部链接]]` 的目标存在。
4. 每个页面有 `title/group/summary/tags`。
5. `transport-events.json` 能解析；事件字段完整。

---

## 4. 生命周期

```text
draft -> review -> published -> stale -> archived
```

- `draft`：可以没有完整链接；不进导航。
- `review`：至少一个 owner 看过；链接/命令可执行。
- `published`：进导航、进搜索。
- `stale`：超过 N 天没更新，或依赖的 commit/版本已变；页面顶部显示提示。
- `archived`：不再维护；保留链接，标注“已归档”。

> 清单里建议加 `status`、`owner`、`updated`、`source_commit` 四个字段；
> 现在先保持最小（slug/file/title/group/icon/summary/tags），后续再扩。

---

## 5. 可管理性：分组、标签、搜索

- **分组**：按“上手 / 原理 / Minecraft 侧 / 开发”分，不要按文件名堆。
- **标签**：跨组检索（如 `三值`、`调度`、`传输`、`排障`）。
- **搜索**：`build_site.py` 生成 `search-data.js`，前端按标题/摘要/标签/正文过滤。
- **先读**：`Home.md` + [[Concept-Map]] 给两条路径（用三值 / 做调度 / 做 agent）。
- **去重**：同一主题只留一页；重复页合并，不并行维护。

---

## 6. 多智能体写文档

- **单写者**：同一页同一时间一个写者；用 claim/lease。
- **清单先行**：新增页先改 `wiki.json`，再写 `.md`；否则渲染器不知道。
- **冲突检测**：
  - 路径重叠：同一 `file`。
  - 内容重叠：同一标题/同一段落/同一命令。
  - 语义重叠：同一主题的两个页（合并，不并存）。
- **交接包**：目标、状态哈希、已定决策、未决问题、下一步；见 [[Coordination]]。
- **回执**：`Sent/Delivered/Read/Acted`；不要用“我写了”代替“渲染出来了”。

---

## 7. 发布

```bash
python scripts/build_site.py --src . --out site
# 本地看
python -m http.server 8000 --directory site
# 打开 http://localhost:8000/
```

- GitHub Pages 可以指向 `gh-pages` 分支（本仓已有在线版）。
- 也可以把 `site/` 作为 CI 产物上传；不要让 CI 直接改 `.md`。
- 发布前跑校验：清单、链接、transport JSON、HTML 生成。
- **不要手改 `site/`**：它是产物；下次构建会被覆盖。

---

## 8. 验收门

| 门 | 判据 | 反例 |
|---|---|---|
| D1 | `wiki.json` 可解析、slug 唯一 | 重复 slug → 红 |
| D2 | 每个 `file` 存在、每个 md 在清单里 | 孤儿页 → 红 |
| D3 | `[[链接]]` 都能解析 | 断链 → 红 |
| D4 | 每页有 title/group/summary/tags | 缺字段 → 红 |
| D5 | `transport-events.json` 字段完整 | 缺 status → 红 |
| D6 | `build_site.py` 生成 0 缺失 | 缺页 → 红 |
| D7 | 本地 `file://` 打开可用（无 fetch） | 依赖网络 → 红 |

---

## 9. 与“代替 Git 的那个软件”的关系

- **它管理**：清单、链接、版本、冲突、发布、过期标记。
- **HTML 不管理**：只渲染；不拥有内容；不做裁决。
- **GitHub 是远端**：镜像/Pages，不是唯一真相。
- **智能体只改源**：`*.md` + `wiki.json`；渲染产物可随时重建。

> 一句话：**文档是工件，清单是索引，HTML 是视图。**
> 不要把视图当真相，也不要把“能打开”当成“管理好了”。
