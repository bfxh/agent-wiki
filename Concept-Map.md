# 三进制库概念地图（先读这个）

> 这一页只做一件事：把 `trit` / `trit-core` / `trit-schedule` / `trit-orch` /
> `trit-immune` / `trit-agent` / `repo-tools` / `agent-wiki` 的关系讲清楚。
> 先看一张图，再看“我该读哪个”，最后是术语表。

---

## 1. 一张图

```text
                         bfxh/trit（Rust workspace）
                         ├─ trit-core       三值逻辑内核：Ternary / K3 / Ł3 / B3
                         ├─ sansheng        crates.io 上的发布门面
                         ├─ trit-schedule   静态三值 DAG 调度 + 运行时/检查点
                         ├─ trit-orch       准入/选择/预算/上下文/副作用/轨迹 + 认领/回执/交接（PR #241 已合）
                         ├─ trit-belnap     Belnap 四值（矛盾检测）
                         ├─ trit-policy     策略/门禁
                         ├─ trit-net       网络面
                         └─ ...             其他数值/电路/GPU/训练 crate

bfxh/trit-immune（独立仓 + 单体仓内 crates/trit-immune）
  └─ 安全裁决内核：K3 裁决 + 因果 DAG + 账本 + 舰队 + 坐标 + 门禁 + 回滚

bfxh/trit-agent（Rust）  ←→  bfxh/trit-mc（Minecraft 数据包）
  └─ 三值决策状态机 + 输入注入 + 感知解析

bfxh/repo-tools（Python）      仓库运维：快照/回滚/发布/依赖脱离
bfxh/agent-wiki（本仓）        文档 + 静态站 + 传输层 UI
bfxh/arch-optimize             架构扫描/回归守卫
```

---

## 2. 我该读哪个？

| 你想做的事 | 先读 | 关键类型/命令 | 不要用它做 |
|---|---|---|---|
| 用三值逻辑（K3/Ł3/B3） | `trit-core` | `Ternary::{True,Unknown,False}`、真值表、`&`/`\|` | 不要拿它做调度 |
| 发一个三值库 | `sansheng` | 发布门面/版本 | 不要直接发 workspace 内部 crate |
| 排一个静态 DAG | `trit-schedule` | `Task`、`Dependency`、`Schedule`、`run_resumable` | 不要指望它管认领/权限 |
| 决定“这一轮能不能传” | `trit-orch` | `admit`、`admit_with_claim`、`dependency_gate`、`Plan::select`、`compaction_gate`、`Ledger`、`ClaimStore`、`DeliveryReceipt` | 不要用它执行外部调用 |
| 做安全裁决/仓库治理 | `trit-immune` | `Trit`、`ImmuneDag`、`Journal`、`Fleet`、`policy::decide` | 不要把它当通用调度器 |
| 做 Minecraft 角色托管 | `trit-agent` + `trit-mc` | `fsm.rs`、`Sensor`、`CommandSink` | 不要把它当通用 agent 框架 |
| 仓库自动化（快照/发布） | `repo-tools` | `snapshot.py`、`publish`、`detach` | 不要把它当协议核心 |
| 写文档/看文档 | `agent-wiki` | `*.md`、`wiki.json`、`scripts/build_site.py` | 不要把 HTML 当真相 |

---

## 3. 最容易混的几组

### 3.1 `trit`、`trit-core`、`sansheng`

- **`trit`**：整个 Rust workspace / 仓库名；也可是 CLI 的泛称。
- **`trit-core`**：三值逻辑内核，定义 `Ternary` 和真值表；其他 crate 依赖它。
- **`sansheng`**：发布到 crates.io 的门面 crate；不是另一套逻辑。

### 3.2 `Ternary` 与 `Trit`

- **`Ternary`**：`trit-core` 的通用三值类型，`True/Unknown/False`。
- **`Trit`**：`trit-immune` 的裁决枚举，`Hardened/Unknown/Vulnerable`。
- `trit-immune/compat.rs` 做双向映射与 3×3 同构穷举；**语义对齐，但不是同一个类型**。

### 3.3 `trit-schedule` 与 `trit-orch`

- **`trit-schedule`**：静态 DAG 算法 + 运行时。输入任务图/worker/优先级，输出 makespan/关键路径/延迟。
- **`trit-orch`**：在调度之上加**准入/预算/上下文/副作用/进度**，以及**认领/回执/交接**。它回答“这一轮能不能传、传哪个、传完算不算”。
- 一句话：`trit-schedule` 是“怎么排”，`trit-orch` 是“能不能传/传完算不算”。

### 3.4 `trit-agent` 与 `trit-orch`

- **`trit-agent`**：Minecraft 领域的智能体（感知/FSM/注入）；有自己的 `trit.rs` 三值工具。
- **`trit-orch`**：通用编排/传输层；不包含 Minecraft 逻辑，也不直接执行输入注入。
- 二者可复用“Unknown 弃权/三值裁决”的语义，但不强行合并。

### 3.5 两个 `trit-immune`

- **单体仓**：`bfxh/trit` 的 `crates/trit-immune`（便于一起跑 CI/发布）。
- **独立仓**：`bfxh/trit-immune`（独立版本/独立 CI）。
- 两份副本内容可能相同（`crate_twin` 会提示），同步靠 `sync-upstream.sh`；**不要以为路径不同就是不同代码**。

### 3.6 `trit-parts` 与 `trit-parts-wiki`

- `trit-parts` 是项目仓；`trit-parts.wiki` 是它的 GitHub Wiki 克隆。
- 本仓 `agent-wiki` 是独立仓 + GitHub Pages，**不是** `.wiki.git`；原因见 [[Docs-As-Artifacts]]。

---

## 4. 术语表

| 术语 | 一句话 | 出处 |
|---|---|---|
| `Ternary` | 三值：`True/Unknown/False` | `trit-core` |
| `Trit` | 免疫裁决：`Hardened/Unknown/Vulnerable` | `trit-immune` |
| K3 | Kleene 三值逻辑；`Unknown` 遇到 `False` 仍是 `False` | `trit-core` |
| Ł3 | Łukasiewicz 三值逻辑 | `trit-core` |
| B3 | Bochvar 三值逻辑 | `trit-core` |
| Belnap FOUR | 四值：真/假/未知/矛盾；矛盾是信息 | `trit-belnap` |
| `Unknown` | 不是“失败”，也不是“通过”；是“需要更多证据” | 全部 |
| `admit` | 四门 K3 AND：依赖/授权/资源/新鲜度 | `trit-orch` |
| `dependency_gate` | `False→True`、`Unknown→Unknown`、`True→evidence` | `trit-orch` |
| `epoch` | 任务定义版本；旧 epoch 的结果自动失效 | `trit-orch` |
| `freshness` | 读数/证据是否属于当前 revision | `trit-orch` |
| `CheckReport` | 验收报告；当前 epoch + 至少一条断言才有效 | `trit-orch` |
| `compaction` | 长上下文压缩：Keep/Prune/Summarize | `trit-orch` |
| `Effect` | 外部副作用六态：Prepared/Sending/Sent/Confirmed/Refuted/Unknown | `trit-orch` |
| `fence` | 单调栅栏；旧执行器不能提交 | `trit-orch` |
| `claim` | 路径认领；谁在写 | `agent_claims.py`（待 Rust 化） |
| `lease` | 认领租约；TTL + 续约 | 待实现 |
| `handoff` | 交接包：目标/状态哈希/决策/证据/下一步 | 本维基 |
| `HLC` | 混合逻辑时钟；跨会话因果序 | `trit-immune` |
| `CRDT` | 无冲突复制数据类型；可交换状态合并 | `trit-immune` |
| `manifest` | 文档清单 `wiki.json`；页面/分组/标签/摘要 | 本仓 |
| `mutation` | 变异测试；必须“指定断言红”才算锁 | 仓库门禁 |
| `module budget` | 单文件行数预算；只减不增 | 仓库门禁 |
| `shadow replay` | 策略只提议、内核照旧决定；用于安全试验 | `trit-orch` |

---

## 5. 推荐阅读路径

### 路径 A：我只想用三值逻辑

`trit-core` 的 `Ternary` + 真值表 → `sansheng` 的发布形态 → 需要矛盾检测再看 `trit-belnap`。

### 路径 B：我想做任务调度

`trit-schedule` 的 `Task/Dependency/Schedule` → `trit-orch` 的 `admit/Plan::select` → [[Coordination]]。

### 路径 C：我想做 agent 的“传输/轮次”

[[Coordination]] → [[Transport-UI]] → `trit-orch` 的 `admission/context/effects` → [[Agent-Interop]]。

### 路径 D：我想做仓库治理/安全裁决

`trit-immune` 的 `Trit/ImmuneDag/Journal/policy` → `repo-tools` 的 snapshot/publish → 本维基的 [[Docs-As-Artifacts]]。

### 路径 E：我想看 Minecraft agent

[[Architecture]] → [[Tri-Value-FSM]] → [[Perception]] → [[Sensor-Protocol]]。

---

## 6. 一句话总结

**`trit` 是工具箱，`trit-core` 是真值，`trit-schedule` 是排程，`trit-orch` 是传输/准入，
`trit-immune` 是裁决/账本，`trit-agent` 是 Minecraft 智能体，`repo-tools` 是仓库运维，`agent-wiki` 是文档。**
先把这条线记住，再看任何单页都不会乱。
