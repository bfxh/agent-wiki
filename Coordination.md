# 协调与传输

> 这一页回答三件事：
> 1. 为什么“再发一条消息 / 再加一个钩子”通常不解决问题；
> 2. 调度器到底在调度什么；
> 3. “一轮能传完”与“必须多轮”的判据是什么。

---

## 0. 一句话

调度器调度的不是“任务步长”，而是**传输单元**：
一个意图 / 证据 / 授权包，**能否在这一轮被接收方正确接住**。

接不住，就跑一轮 grounding（读状态、对齐术语、取证、落盘事实），
让下一轮变成“可一轮传”。**不是把动作切碎，也不是把消息发得更多。**

---

## 1. 三类信息

| 类型 | 含义 | 例子 | 传输方式 |
|---|---|---|---|
| `K_prior` | 对方已经知道 | 语言、通用 API、公开约定 | 直接传，成本低 |
| `K_context` | 对方必须读/看/对齐后才知道 | 当前分支、未提交改动、另一个会话的决定 | 先 grounding，再传 |
| `K_unknown` | 现在谁都不知道 | 这个改动会不会回归、对方真实意图 | 先取证/实验，不能猜 |

**短交流**：`K_prior` 足够，`K_context` 很小，意图歧义低。
**长交流**：必须建立 `K_context`，或 `K_unknown` 需要实验。
**混合**：按子目标拆，不要整轮分类。

---

## 2. “1 米 / 2 米”是比喻，不是步长

- **一米**：一个自包含的传输单元。接收方已有必要上下文，一轮能正确理解并执行。
- **两米**：一个不能在一轮里被正确接住的单元。缺前置上下文、缺证据、缺授权，或术语没对齐。
- 它**不是**动作距离、token 长度，也不是 `p(d|C)` 的步长模型。

三种常见误读：

| 说法 | 实际是什么 | 处置 |
|---|---|---|
| 目标一米，却先传两米 | 传了超出目标的单元，接收方可能按错意图执行 | 回退/纠偏，不要“走两步试试” |
| 目标两米，分成两段一米 | 第一段是 grounding，第二段才可被接住 | 第一段必须降 `Unknown`/增证据，否则是纯成本 |
| 两个会话分别说一米/两米 | 意图冲突，不是传输粒度问题 | 先对齐目标，再谈怎么传 |

> 判断标准不是“走了多远”，而是：**接收方能不能复述目标、约束、下一步，并且不需要再问。**

---

## 3. 一轮可传的判据（对齐 `trit-orch`）

一个传输单元 `u` 要在当轮传完，至少要同时满足：

1. **依赖**：`dependencies == True`；`Unknown` 必须先生成取证任务。
2. **授权**：`authorization == True`。
3. **资源**：`resources == True`（worker / cpu / memory / tokens）。
4. **新鲜度**：`freshness == True`（读数/证据/快照属于当前 revision/epoch）。
5. **上下文事实**：能测到 tokens、窗口足够、可回读、承重事实已落盘、逐字约束已固定。
6. **意图歧义**：低于阈值；术语/目标已对齐。
7. **不可逆/高爆炸半径**：已有审批、快照与回滚预案。

前四条就是 `trit-orch/src/admission.rs` 的准入：

```text
admit(dependencies, authorization, resources, freshness)
  = dependencies & authorization & resources & freshness   // K3 AND
```

依赖边的三值语义：

```text
dependency_gate(required, evidence):
  False   -> True        // 可选依赖，不挡
  Unknown -> Unknown     // 未知，延迟，不猜
  True    -> evidence    // 必需依赖，看证据
```

> 注意：`False` 在这里是“可选/不挡”，不是“任务失败”。
> “失败”是裁决的 `-1`，不是依赖的 `False`。

---

## 4. 不能一轮传时：grounding 轮

分轮的唯一正当理由是：**让下一轮变成“一轮可传”**。每一轮至少要完成一项：

- 降低 `Unknown`：读状态、跑探针、验证回读、向对方确认。
- 建立共同术语：对齐概念、给例子、固定字段名。
- 落盘承重事实：把唯一副本写到上下文之外。
- 固定逐字约束：用户原话、红线、不可改的接口。
- 取得授权/新鲜度：谁有权、基于哪个 revision。
- 产出证据：测试、门禁、回执。

**如果一轮什么都没做到，就停止。** 这不是“多轮协调”，是堆轮次。

### 例子：改一个拆过的文件

1. 对方说“把 `pe.rs` 的符号表修了”。
2. 你发现 `pe.rs` 已经拆成 `pe/coff.rs`，锚点/测试也搬了。
3. 这一轮**不要直接改**；先 grounding：确认当前文件、测试位置、变异登记、归属。
4. 下一轮才是“改代码 + 跑门”。

如果跳过第 3 步，就会“正确地修了旧路径”，然后门红、返工、再解释。

---

## 5. `trit-orch` 实际在调度什么

| 组件 | 管什么 | 对应本页的哪一步 |
|---|---|---|
| `admission` | 依赖/授权/资源/新鲜度的 K3 准入 | 这一轮能不能传 |
| `dependency_gate` | `True/False/Unknown` 依赖语义 | `Unknown` 延迟，不猜 |
| `context::compaction_gate` | Keep / Prune / Summarize | 放不下时，先压缩还是先补证 |
| `selection` | 当前 epoch、新鲜、前驱已结算、容量允许的任务 | 这一轮传哪个 |
| `effects::Ledger` | Prepared/Sending/Sent/Confirmed/Refuted/Unknown | 传输副作用；未知不盲重试 |
| `progress::Progress` | 每轮 selected/held/denied/inflight/settled | 传了多少、卡在哪 |
| `shadow::TraceStore` | 轨迹/影子回放 | 事后看“到底传了什么” |

关键语义：

- **`Unknown` 不是通过**：上下文压缩闸门在缺少 tokens/可回读/事实落盘时停在 `Keep`，不批准有损摘要。
- **`Unknown` 不是失败**：副作用已发出但结果不明时进入 `Unknown`，先对账，不盲重试。
- **`0` 不是空**：`CheckReport` 只有在“当前 epoch + 至少一条断言 + 结果确定”时才给 `True/False`，否则 `Unknown`。

### 5.1 现状：协调原语已落地（`feat/orchestration-core`）

`trit-orch` 现在已有：

| 原语 | API | 语义 |
|---|---|---|
| 认领/租约 | `ClaimStore::claim/renew/release/state_of/gate` | 路径前缀、TTL、fencing、Contested/Expired |
| 第五门 | `admit_with_claim(deps, auth, res, fresh, claim)` | 四门 K3 AND 再与 claim 做 K3 AND |
| 通讯回执 | `DeliveryReceipt` + `ReceiptLedger` | Sent→Delivered→Read→Acted；Rejected/Expired 终止 |
| 交接包 | `HandoffPacket` + `handoff_gate` | 结构/过期/状态哈希三值判定 |
| 测试 | `tests/coordination.rs` | 14 条；含 `admit_with_claim` 243 组 |
| 变异 | `scripts/orch_mutants.py` | 过期续约、旧 fence、前缀冲突、未覆盖、回执跳级、Acted 终止、交接哈希/过期 |

注意：`evidence::Receipt` 是**执行回执**（exit/断言数），
`receipt::DeliveryReceipt` 是**通讯回执**（Sent→Acted）。两者不要混。

> 干净分支 `feat/trit-orch-coordination`（PR #241）已全绿，基于最新 `main`；
> 旧 `feat/orchestration-core` 保留（含 GPU/texture 等改动）。
> CLI 适配还没接。

---

## 6. 跨会话 / 跨智能体

仅靠“发消息”不够。至少需要：

1. **认领/租约**：谁在写哪个路径；`fencing` 防旧写者复活。
2. **交接包**：目标、基提交、状态哈希、已定决策、未决问题、认领、证据、下一步、过期时间。
3. **四态回执**：`Sent / Delivered / Read / Acted`；超时记 `Unknown`，不写“对方没回”。
4. **钩子预算**：每事件最多 N 次调用，去重/合并，禁止递归；钩子只是提醒，不是协议。
5. **权限**：跨会话只能 propose，目标 accept 才执行；不可逆动作要人。

详见 [[Agent-Interop]]。

---

## 7. 传输层 UI

站点侧边栏有一个 **“传输 N”** 徽标：

- `N` = 当前事件条数；
- 点开是抽屉，列出 `from → to`、类型、轮次、字节数、状态、摘要；
- 点某条展开 payload；
- 可按状态筛选；
- 纯本地静态数据，不发网络请求。

详见 [[Transport-UI]]。

---

## 8. 文档不是 HTML

- **HTML 只是渲染器**，不是真相。
- 真相是 Markdown + `wiki.json` 清单（slug/file/title/group/tags/summary）。
- “代替 Git 的那个软件”负责管理文档：索引、链接、版本、冲突、发布；HTML 只消费。
- 详见 [[Docs-As-Artifacts]]。

---

## 9. 验收门

| 门 | 判据 | 反例 |
|---|---|---|
| T1 | 四门任一 `Unknown` 不得当轮派发 | `Unknown` 直接传 → 红 |
| T2 | 每个 grounding 轮必须降 `Unknown` 或增证据 | 纯聊天轮 → 红 |
| T3 | `Effect::Unknown` 不得盲重试 | 重发导致重复副作用 → 红 |
| T4 | 跨会话交接必须有状态哈希 + 回执 | 只发不等 → 红 |
| T5 | 钩子必须有预算/去重/禁止递归 | 钩子风暴 → 红 |
| T6 | UI 徽标数字必须等于事件条数 | 数字对不上 → 红 |

---

## 10. FAQ

**Q：为什么不直接把全部上下文都发过去？**
A：上下文窗口有限，中间信息会被忽略；摘要会丢细节；对方还要花成本读。先给“最小充分集”，比“全量倾倒”更可靠。

**Q：为什么不加一个钩子让对方知道？**
A：钩子解决“提醒”，不解决“接住”。没有认领、回执、幂等，提醒只会变成更多轮次。

**Q：调度器不就是排任务吗？**
A：排任务是其中一层。它还要决定“能不能这一轮传、传哪个、上下文够不够、传完算不算、坏了怎么对账”。

**Q：怎么判断一轮能不能传？**
A：让对方复述目标、约束、下一步；如果复述准确且不需要追问，就是可一轮传。否则先 grounding。
