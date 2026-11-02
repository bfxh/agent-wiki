# 配置

配置文件是 `trit-agent.toml`，放在 exe 旁边。

**查找顺序**：exe 旁边 → 安装目录 → 当前工作目录。
相对路径**必须锚定到配置目录**——自启时 cwd 是 `C:\Windows\System32`，
不锚定就永远收不到感知包。

生成一份默认配置：

```bash
target/release/trit-agent.exe init
```

---

## 采集（挖矿/砍树）

```toml
gather = true                # 默认 FALSE：采集会主动改变世界，不该默认开
gather_target = wood         # wood = 砍树，ore = 挖矿
gather_fast_bridge = true    # 干活时按需打开 100ms 快通道（需要 squad_control = chat）
gather_min_hp = 0.65
gather_min_food = 7
gather_night = false         # 夜里不砍
gather_quota = 16            # 一趟采够多少就休息，休息完自动开下一趟
gather_rest_ms = 30000
gather_enter_ms = 2500       # 连续安全多久才允许开工
gather_cooldown_ms = 8000    # 被威胁打断后锁多久
gather_scan_every_ms = 1600  # 插播扫视间隔
gather_scan_ms = 350
gather_reach = 3.2
gather_max_walk = 20.0
gather_max_chop_ms = 25000
```

**`gather = false` 是默认值**，这是有意的：
采集会主动改变世界（砍树、挖矿、破坏方块），
这种副作用不该在你不知情的时候发生。

---

## 共同意识（一个大脑，多个身体）

```toml
squad = true                 # 打开共同意识（默认关）
squad_control = "chat"       # off = 只算不指挥 / dry = 只记录不真发 / chat = 走命令框真发
squad_engage_dist = 12       # 超过这个距离先集合，别各打各的（会被逐个击破）
squad_recall_hp = 0.45       # 低于这个血量且有威胁 → 召回护主
squad_cmd_gap_ms = 1200      # 两条指令的最小间隔
```

`squad_control = "dry"` 是**安全模式**：所有指令只记录不发。
想验证它「打算做什么」而不真的动手时用这个。

---

## 窗口与热键

```toml
window_title = "Minecraft"       # 标题关键字（次要判据）
kill_switch_vk = 119             # F8 的虚拟键码
panic_vk = 120                   # F9 急停
toggle_attack_vk = 117           # F6
toggle_move_vk = 118             # F7
toggle_perspective_vk = 121      # F10
```

**改键位就改虚拟键码**（VK 码）：
F1=112, F2=113, F3=114, F4=115, F5=116, F6=117, F7=118, F8=119,
F9=120, F10=121, F11=122, F12=123。

---

## 行为开关

```toml
restore_first_person = true   # F8 关掉时切回第一视角
focus_pause = true            # 窗口失焦就停手
stop_when_window_gone = true  # 游戏关了自动停
grab_focus_on_start = true    # 接管时抢焦点（后台守护模式会关掉它）
switch_view_on_start = true   # 接管时切视角（后台守护模式会关掉它）
```

> **后台守护模式把最后两个关掉了。**
> 守护进程是常驻的，抢焦点意味着你正在写代码时窗口被游戏抢走；
> 切视角等于在你没玩的时候乱动镜头。

---

## 性能

```toml
tick_hz = 200               # 默认 200，可到 2000
```

200Hz 是实测的最优值。再高收益递减，而且会跟游戏抢主线程。

---

## 感知

```toml
log_path = "E:/MC/MC/profiles/烦人的村民/logs/latest.log"
```

指向游戏实例的 `logs/latest.log`。传感器数据从这条通道来。

**这条路径配错 = AI 永远「没感知」** → 所有票都是 `0` → 永远弃权 → 角色站着不动。
最常见的表现就是这个。

---

## 游戏内聊天指令

不用重启，直接在游戏聊天栏敲：

| 指令 | 作用 |
|---|---|
| `!gather on` / `off` | 开关采集 |
| `!gather reset` | 清配额和冷却 |
| `!gather wood` / `ore` | 换目标 |
| `!gather 8` | 设配额 |
| `!gather night` | 夜里也干 |
| `!gather fast` | 快通道开关 |
| `!gather lag` | **实测感知延迟**（最有用的一条） |
| `!squad on` / `off` | 开关共同意识 |
| `!squad recall` | 立刻召回傀儡和狼 |

---

## 完整模板

仓库里的 `trit-agent.example.toml` 是带注释的完整模板。

---

## 相关

- [[Hotkeys]] —— 键位的行为细节
- [[Troubleshooting]] —— 配置错了会怎么表现
