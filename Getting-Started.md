# 上手

## 前置条件

- Windows 10/11
- Minecraft **1.18.2**（整合包「烦人的村民」已验证）
- Rust 工具链（编译 AI 用）：https://rustup.rs
- Python 3.9+（跑打包脚本用）

**不需要给游戏装任何 mod。** 键鼠注入走 Win32 `SendInput`，直接打进游戏窗口。

---

## 三步

### 1. 装数据包（Minecraft 侧）

数据包提供**传感器**——把游戏状态写进聊天栏，AI 从日志里读回来。
没有它 AI 也能动，但那是盲动。

```bash
git clone git@github.com:bfxh/trit-mc.git
cd trit-mc
python scripts/build_datapacks.py --install "E:/MC/MC/profiles/烦人的村民"
```

> 装完记得回游戏里 `/reload`。新世界还需要 `/datapack enable "file/trit_bridge.zip"`
> —— 详见 [[Data-Packs]] 的「拷进去 ≠ 装上了」。

### 2. 编译 AI（Rust 侧）

```bash
git clone git@github.com:bfxh/trit-agent.git
cd trit-agent
cargo build --release
```

产物：`target/release/trit-agent.exe`

### 3. 自检

```bash
python ../trit-mc/scripts/check_env.py
```

7 项全绿才算就绪。任何一项红了都会告诉你怎么修。

---

## 运行

### 临时用（前台）

双击 `启动AI.bat`，或者：

```bash
cargo run --release -- run
```

会弹一个控制台显示实时状态。**关掉窗口 AI 就停了。**

### 常驻（推荐）

双击 `安装后台.bat`：

- 装开机自启（`HKCU\...\Run`，免管理员）
- 注册 Windows 计划任务（崩溃后自动拉起，每分钟一次）
- 立刻启动一个实例

之后**进游戏直接按 F8**就行，不用开任何窗口。

想彻底卸载：双击 `卸载后台.bat`。

> 详细的原理、为什么用计划任务而不是只靠注册表，看 [[Background-Daemon]]。

---

## 接管

进游戏 → **按 F8**。

- 第一次按：接管，角色开始自己行动
- 再按一次：交还，完全还给你
- **F9**：急停（立刻松手，但不切视角——你还在看它的视角）
- **F10**：切视角

首次接管会自动切到**第三视角**（默认背视）。为什么这么绕，见 [[Hotkeys]]。

---

## 确认它真的活了

接管后聊天栏应该每秒刷一行：

```
<TRIT hp=185 food=17 x=123 y=-601 z=88 h=3 d=6 c=0 w=6 wd=-1 o=4 od=1 t=15200 p=150>
```

看到这行 = 传感器通了 = AI 知道自己在哪、有几个敌人。

看不到这行 → 走 [[Troubleshooting]] 的排查顺序。

---

## 常见问题

**「按 F8 没反应」**
守护进程可能没在跑。查状态：

```bash
target/release/trit-agent.exe status
```

显示「未运行」→ 双击 `安装后台.bat`。
显示「运行中」但按 F8 还没反应 → 可能是另一个进程在抢同一个互斥量，
或者游戏窗口没被认出来（`trit-agent probe` 会列出候选窗口）。

**「AI 站着不动」**
大概率是没感知到血量（未知票权重 > 已知票权重 → 弃权，这是设计）。
查聊天栏有没有 `<TRIT ...>`。

**「游戏崩了」**
走 [[Crash-Troubleshooting]]。

---

## 下一步

- 想知道为什么是三值 → [[Tri-Value-FSM]]
- 想调参数 → [[Configuration]]
- 想接对讲机/语音/第二屏 → [[Control-Channels]]
- 想知道它做不到什么 → [[Design-Boundaries]]
