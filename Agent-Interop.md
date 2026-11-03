# 跨智能体通讯：信封、能力、回执

> 目标：能和别的智能体/宿主协作，但**不共享内部实现**。
> 只在通讯层约定：信封、能力、回执、幂等、超时。
> 对应实现：`trit-orch::effects` 的六态台账；本页是协议层说明书。

---

## 0. 边界

- **共享**：消息信封、能力名、内容类型、回执状态、幂等键、过期时间。
- **不共享**：对方的内部任务模型、调度算法、账本格式、模型/工具实现。
- **不直接操控**：一个智能体不能命令另一个智能体执行写操作；只能 propose，目标 accept 后才执行。

---

## 1. 信封

```json
{
  "v": 1,
  "id": "msg-01J...",
  "idempotency_key": "handoff:trit-re:0007",
  "from": {
    "agent": "qoder/179ea139",
    "role": "worker",
    "capabilities": ["read:repo", "write:src/trit-re"]
  },
  "to": {
    "agent": "qoder/dc34ac09",
    "role": "reviewer"
  },
  "intent": "review",
  "content_type": "application/json",
  "body": { "...": "..." },
  "refs": [
    "commit:0725d92",
    "file:crates/trit-re/src/pe/coff.rs",
    "issue:232"
  ],
  "sent_at": "2026-11-03T13:20:00+08:00",
  "deadline": "2026-11-03T13:35:00+08:00",
  "reply_to": "msg-01J...",
  "signature": null
}
```

字段说明：

| 字段 | 必填 | 作用 |
|---|---|---|
| `v` | 是 | 协议版本；不兼容要拒绝，不要猜 |
| `id` | 是 | 消息 ID |
| `idempotency_key` | 是 | 去重；重复投递不重复执行 |
| `from/to` | 是 | 身份 + 能力；不是“命令” |
| `intent` | 是 | `propose/accept/reject/query/reply/handoff/claim` |
| `content_type` | 是 | `text/markdown` / `application/json` / `application/jsonl` |
| `body` | 是 | 载荷；大小有上限 |
| `refs` | 否 | 证据指针：commit/file/issue/line |
| `deadline` | 否 | 过期后不得直接执行，只能当线索 |
| `reply_to` | 否 | 线程/因果链 |
| `signature` | 否 | 需要时签名；不默认强制 |

---

## 2. 握手与能力

连接建立时交换：

```json
{
  "v": 1,
  "agent": "qoder/179ea139",
  "capabilities": [
    {"scope": "repo:bfxh/trit", "actions": ["read"]},
    {"scope": "path:crates/trit-re/**", "actions": ["read", "write", "claim"]},
    {"scope": "pr:232", "actions": ["review", "comment"]}
  ],
  "content_types": ["text/markdown", "application/json"],
  "receipt_modes": ["sent", "delivered", "read", "acted"],
  "limits": {"max_body_bytes": 262144, "max_hops": 2}
}
```

规则：

- 能力是**最小集**，不是“全权”。
- 能力有作用域（repo/path/PR/工具），不是全局开关。
- 能力可过期；过期后需要重新握手。
- 不支持的能力 → 拒绝，不降级成“试试看”。

---

## 3. 投递语义

- **at-least-once**：允许重复，不允许静默丢失。
- **去重**：接收方按 `idempotency_key` 去重。
- **顺序**：用 HLC/因果向量；只保证同一路径的因果序，不追求全局全序。
- **超时**：状态记 `Unknown`，不是 `NotSent`/`NotRead`；不要写“对方没回”。
- **回执四态**：

| 状态 | 含义 | 证据 |
|---|---|---|
| `Sent` | 已发出 | 发送日志 |
| `Delivered` | 对方进程收到 | 传输层 ack |
| `Read` | 对方读过 | 读取事件 |
| `Acted` | 对方据此行动 | 关联的写/PR/门 |

> 只有 `Acted` 才能说“对方照做了”。`Sent` 只说明“我发了”。

---

## 4. 与 `trit-orch::effects` 的映射

`trit-orch` 已经有外部副作用的六态台账：

| `Effect` | 含义 | 对应通讯层 |
|---|---|---|
| `Prepared` | 意图已落账，尚未发送 | 准备发送 |
| `Sending` | 发送标记已落盘，可能已发生 | 正在发送 |
| `Sent` | 调用已被受理 | `Sent` |
| `Confirmed` | 外部确认发生 | `Delivered/Read/Acted` 的合并结果 |
| `Refuted` | 外部确认未发生 | 可重试 |
| `Unknown` | 可能已发生，但结果不明 | 必须先对账，不盲重试 |

关键规则（沿用 `effects.rs`）：

- `may_retry` 只允许 `None` 或 `Refuted`。
- `Prepared/Sending/Sent/Unknown/Confirmed` 都不能再 `prepare`。
- `fence` 单调；旧执行器的提交会被拒绝。
- `dispatch_ready` 要求同 epoch 且 `Prepared`。

**建议扩展**：在 `Effect` 之上加通讯四态（`Delivered/Read/Acted`），
但底层仍以 `Ledger` 为准；不要把四态做成第二套账。

---

## 5. 权限

- 跨智能体**只能 propose**：`intent=propose`，目标 `accept/reject`。
- 目标接受后才产生写/合并/发布动作。
- 不可逆动作（删除、force push、发布、权限变更）必须人类确认 + 快照。
- 能力越界 → 拒绝并记录；不要“先做了再说”。

---

## 6. 适配器：MCP / A2A 类协议

- **MCP**：适合“工具/资源”面（读文件、跑命令、查数据），**不是**智能体会话协议。
- **A2A/ACP 类**：可作为上层适配器；核心只依赖本页的信封/能力/回执。
- 适配器负责：
  - 把本页信封映射到对方协议；
  - 把对方的回执映射回 `Sent/Delivered/Read/Acted/Unknown`；
  - 不做语义决策（谁该写、能不能合并由编排层决定）。
- 原则：**核心不绑定任何单一协议**；适配器坏了，核心仍可用。

---

## 7. 安全

- 不信任 payload：长度、类型、字段、路径都要校验。
- 不把 secret 放进 `body`；用引用/句柄。
- `refs` 只放可公开/可回读的指针；敏感信息走安全通道。
- 跨智能体默认不共享工作区路径；需要时显式授权。
- 记录所有跨智能体动作，便于回放/追责。

---

## 8. 测试矩阵

| 场景 | 期望 |
|---|---|
| 重复投递同一 `idempotency_key` | 副作用至多一次 |
| 消息乱序 | 按 HLC/因果序处理，不覆盖新状态 |
| 超时无回执 | `Unknown`，不写“没回” |
| 对方能力不足 | 拒绝，不降级 |
| 旧 fence 写 | 拒绝 |
| 伪造能力 | 拒绝 + 记录 |
| 大 payload | 拒绝/分片，不静默截断 |
| 适配器不可用 | 核心仍能本地运行 |

---

## 9. 最小落地顺序

1. 定义信封 JSON + 能力名 + 四态回执。
2. 在 `trit-orch` 外包一层 `interop` 适配器；底层用 `Effects::Ledger`。
3. 两个假智能体跑通：正常、重复、乱序、超时、越权。
4. 接一个真实宿主（Qoder/ZCode/其他）做只读握手。
5. 再做写能力；不可逆动作先不开放。

> 先只读、再 propose、最后才 accept 写。不要一上来就给跨智能体写权限。
