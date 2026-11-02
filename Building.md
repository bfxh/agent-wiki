# 构建与测试

## 环境

- Rust 工具链：https://rustup.rs
- Python 3.9+（跑打包脚本）
- Windows 10/11（`SendInput`、命名互斥量、计划任务都是 Windows 专属）

---

## 编译

```bash
git clone git@github.com:bfxh/trit-agent.git && cd trit-agent
cargo build --release
```

产物：`target/release/trit-agent.exe`

**零第三方依赖**——只用 `std` + 手写 FFI。
这是硬约束：项目要能塞进整合包作者的机器、能长期维护、
不能因为某个 crate 停止维护而烂掉。

需要 Win32 / 注册表 / 时间戳时手写 FFI，
注册表走 `reg.exe` 命令行（不用 advapi32，避免 UTF-16 编码坑）。

---

## 测试

```bash
cargo test --release
```

**209 个测试**。覆盖：

| 范围 | 内容 |
|---|---|
| `fsm.rs` | K3 真值表、迟滞不抖、弃权优先 |
| `trit.rs` | 平衡三进制往返 |
| `perceive/` | 日志解析（半行/截断/乱序）、快慢通道补丁合并、墙体方位映射、**协议字段名单与解析器逐字一致** |
| `gather.rs` | 采集门控、挖矿三条地形判据 |
| `behaviors.rs` | 视线闭环自适应等待、感知延迟实测、快通道开关时机 |
| `squad.rs` | 发送失败会重试，不被吞掉 |
| `daemon.rs` | panic 落盘、任务 XML（重启/时限/引号/转义） |
| `act/win32.rs` | 待机期不碰窗口标题、切片 clamp |

### 静态分析

```bash
cargo clippy --release --all-targets
```

标准是 **Error = 0**。

---

## 自检

```bash
target/release/trit-agent.exe selftest
```

9 项，含 200Hz 节拍校验：

```
目标 200 Hz  · 实际 200.5 Hz · 401 拍 / 2.000s
目标 1000 Hz · 实际 1000.5 Hz · 2001 拍 / 2.000s
```

---

## 模拟

不连游戏也能跑整条决策链：

```bash
cargo run --release -- sim              # 战斗决策
cargo run --release -- sim --gather     # 采集
cargo run --release -- sim --mine       # 挖矿
```

```
tick  phase   move strafe yaw pitch atk jump use  strategy   说明
0     idle     0     0     -    0    0   0    0   -          无敌人
2000  engage   +     -     +    0    +   0    0   -          敌人 ≤32 格 → 追
5000  engage   0     -     +    0    0   0    0   feint      敌人 ≤6 格 → 站住（原版没有这一档）
8000  engage   -     -     +    0    0   +    0   ambush     敌人在 10 格 + 苦力怕贴脸 → 规避压过追击
12000 engage   +     +     +    +    +   0    0   -          被墙挡住：想追但走不动 → 低头砍墙  [stuck]
```

---

## 诊断命令

| 命令 | 作用 |
|---|---|
| `trit-agent probe` | 列出候选窗口（标题 + 类名），看认不认得出游戏 |
| `trit-agent status` | 守护进程状态 + 自动重启是否启用 |
| `trit-agent protocol` | 导出传感器协议字段名 |
| `trit-agent protocol --json` | 同上，给脚本读 |
| `trit-agent selftest` | 自检 9 项 |
| `trit-agent init` | 生成默认配置 |

---

## 环境自检（Minecraft 侧）

```bash
cd ../trit-mc
python scripts/check_env.py
```

7 项：AI 本体 / 存档数据包 / 传感器 / 数据包格式 / 模组标签 / 协议 / rrls。

**任何一项红了都会告诉你怎么修。**

---

## 打包（MC 侧）

```bash
cd ../trit-mc
python scripts/build_datapacks.py                        # 只打包
python scripts/build_datapacks.py --install <实例>       # 打包 + 装进实例
python scripts/build_datapacks.py --selftest             # 验证校验器本身有效
```

打包器会自动跑：
- JSON 合法性
- `function` 引用存在性
- 方块标签引用存在性
- **传感器字段名与 Rust 白名单交叉校验**
- 起源包 schema 体检

---

## 端到端验证（不用真游戏）

用**假 GLFW30 窗口**（类名 `GLFW30`）+ `keybd_event` 注入 F8 复现：

```bash
# 1. 造一个类名 GLFW30、标题同整合包的窗口
# 2. 守护进程会挂上它（日志出现「挂上窗口」）
# 3. 注入 F8 → 日志出现「AI 已接管」
# 4. 再注入 F8 → 「已交还控制权」
```

> **必须用 `keybd_event`，不能用 `SendInput`**：
> `SendInput` 注入的按键 `GetAsyncKeyState` 读不到（实测 `0x0000`），
> 而 `keybd_event` 实测能读到 `0x8001 down=true`。
> 真实物理按键不受影响——这是**自动化验证**的问题，不是功能问题。

---

## 目录

```
trit-agent/
  src/
    agent.rs         主循环、状态编排
    fsm.rs           三值状态机
    gather.rs        采集与挖矿
    behaviors.rs     行为组合
    perceive/        协议解析 + 日志尾随
    act/             Win32 注入 + dry 通道
    daemon.rs        后台守护
    squad.rs         共同意识
    strategy.rs      战法
    npc.rs           原版 Goal 的三值重写
    trit.rs          三进制工具
    text.rs          CJK 宽度感知
  docs/
    BOUNDARIES.md    能力边界
    CONTROLS.md      操控方式注册表
  tests/pipeline.rs

trit-mc/
  datapacks/         squad + trit_bridge
  archive/origins/   起源包 + 汉化
  scripts/           打包/装包/自检/诊断
```

---

## 相关

- [[Design-Boundaries]] —— 诚实的边界
- [[Sensor-Protocol]] —— 协议契约与守门测试
- [[Architecture]] —— 模块地图
