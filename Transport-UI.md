# 传输层显示 UI

> 目标：把“我发了 / 对方没回 / 到底传了什么”变成**可见、可点开、可核对**的东西。
> 形态：侧边栏一个 **“传输 N”** 徽标；点开是抽屉；每条可展开 payload。
> 数据：本仓 `transport-events.json`（示例）→ `build_site.py` → `transport-data.js` → `site.js`。

---

## 1. 为什么需要它

上一轮的典型对话：

> “我回了。”
> “我没收到。”
> “那你再发一遍。”

这不是谁在撒谎，而是**传输层不可见**：没有消息 ID、没有状态、没有 payload 记录。
UI 的目的不是好看，而是让“传输了什么、到哪一步”可核对。

---

## 2. 界面

```text
┌──────────────────────────────┐
│ 搜索 [____________________]  │
│                              │
│ 🏠 首页                      │
│ 上手                         │
│  ...                         │
│                              │
│ [ 传输 7 ]  ← 点开            │
└──────────────────────────────┘

点击后（右侧抽屉）：

┌────────────────────────────────────────────┐
│ 传输记录（示例）                      [×] │
│ [全部] [Sent] [Delivered] [Read] [Acted]  │
│                                            │
│ 13:20  handoff  179ea139 → dc34ac09        │
│        交接包：trit-re 变异登记             │
│        round 3 · 812 B · Delivered          │
│        ▸ 展开 payload                       │
│                                            │
│ 13:22  claim    179ea139 → *               │
│        claim: crates/trit-re/**             │
│        round 3 · 96 B · Held                │
└────────────────────────────────────────────┘
```

交互：

- 徽标数字 = 事件条数；不是“未读数”（示例数据没有已读状态）。
- 点击徽标打开抽屉；点击遮罩/`Esc`/`×` 关闭。
- 点击一条记录展开/收起 payload。
- 状态下拉筛选；默认“全部”。
- 纯静态，不发网络请求；本地打开 `site/index.html` 也能用。

---

## 3. 事件 schema

```json
{
  "id": "tx-0007",
  "time": "2026-11-03T13:20:00+08:00",
  "from": "session:179ea139",
  "to": "session:dc34ac09",
  "kind": "handoff",
  "round": 3,
  "bytes": 812,
  "status": "delivered",
  "summary": "交接包：trit-re 变异登记",
  "payload": "goal=...\\nbase_commit=0725d92\\nstate_hash=...",
  "evidence": ["commit:0725d92", "file:crates/trit-re/src/pe/coff.rs"]
}
```

字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 事件 ID |
| `time` | 是 | ISO 时间 |
| `from/to` | 是 | `session:*` / `agent:*` / `*`（广播） |
| `kind` | 是 | `handoff/claim/receipt/gate/message` |
| `round` | 否 | 第几轮 |
| `bytes` | 否 | 载荷字节数 |
| `status` | 是 | 见下表 |
| `summary` | 是 | 一行摘要 |
| `payload` | 否 | 可展开的原文（注意脱敏） |
| `evidence` | 否 | commit/file/issue/line 指针 |

状态映射：

| UI 状态 | 来源 |
|---|---|
| `sent` | `Effect::Sent` / 发送日志 |
| `delivered` | 传输层 ack |
| `read` | 读取事件 |
| `acted` | 关联的写/PR/门 |
| `unknown` | `Effect::Unknown` / 超时 |
| `confirmed` | `Effect::Confirmed` |
| `refuted` | `Effect::Refuted` |

> 只有 `acted` 才能说“对方照做了”。`sent` 只说明“我发了”。

---

## 4. 数据从哪来

### 4.1 现在（示例）

- 文件：`transport-events.json`（本仓根目录）。
- 构建：`scripts/build_site.py` 读取它，生成 `site/transport-data.js`：
  ```js
  window.TRANSPORT_EVENTS = [ ... ];
  ```
- 渲染：`scripts/site.js` 读 `window.TRANSPORT_EVENTS`，渲染徽标/抽屉。
- **明确标注“示例数据”**，不是真实会话记录。

### 4.2 以后（真实）

- `trit-orch` 的 `TraceStore` 是 JSONL；每行一个 `TraceStep`。
- 加一个转换器：`TraceStep` + `Effect` → 本页 schema。
- 也可以从 `Progress::RoundReport` 生成“每轮摘要”。
- 不建议直接读原始日志到浏览器：先脱敏、再生成静态 JSON。

---

## 5. 隐私与安全

- 本地静态：不发网络请求。
- payload 要脱敏：token、cookie、私钥、用户路径。
- 只显示“需要知道的”：默认摘要，点开才看 payload。
- 不把 `transport-events.json` 里的敏感内容提交到公开仓；示例用假数据。
- 如果以后接真实数据，走“生成脱敏后的静态 JSON”，不要让浏览器直连内部日志。

---

## 6. 验收

| 项 | 判据 |
|---|---|
| 徽标数字 | 等于 `transport-events.json` 的条数 |
| 点开 | 抽屉出现，列出事件 |
| 展开 | 点击一条，payload 出现/收起 |
| 筛选 | 选 `unknown` 只剩 `unknown` |
| 关闭 | `Esc`/遮罩/`×` 都能关 |
| 无网络 | 断网打开 `site/index.html` 仍可用 |
| 无敏感 | 示例数据不含 token/私钥/真实用户路径 |

---

## 7. 与 `trit-orch` 的对应

| UI 元素 | `trit-orch` 落点 |
|---|---|
| 状态 `sent/sending/prepared` | `Effect::{Prepared,Sending,Sent}` |
| 状态 `unknown` | `Effect::Unknown` + `reconcile` |
| 状态 `confirmed/refuted` | `Effect::{Confirmed,Refuted}` |
| 轮次/选中/挂起 | `Progress::RoundReport` |
| 事件列表 | `TraceStore` / `TraceStep` |
| 为什么没传 | `admission` 的 `BlockReason`、`compaction_gate` 的 `blocks/obligations` |

> UI 不是第二套状态机；它只是把 `trit-orch` 已有的事件/状态**可视化**。
