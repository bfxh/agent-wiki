# 排查：没效果

> 不是崩溃的话看这篇。崩溃见 [[Crash-Troubleshooting]]。

**每一件事都是静默的**：包没启用、`data modify` 写不进去、模组 jar 被更新覆盖、
`allowCommands=0` 让 `/function` 直接被拒——**游戏一律不报错**。

所以排查的唯一入口是那条自检命令：

```bash
python scripts/check_env.py
```

（在 bfxh/trit-mc 仓库里，7 项全绿才算就绪）

---

## 排查顺序

### 1. AI 进程在跑吗

```bash
target/release/trit-agent.exe status
```

- 「未运行」→ 双击 `安装后台.bat`（见 [[Background-Daemon]]）
- 「运行中」但按 F8 没反应 → 有第二个实例在抢同一个互斥量，
  或者游戏窗口没被认出来

### 2. 认得出游戏窗口吗

```bash
target/release/trit-agent.exe probe
```

会列出候选窗口的 `标题 [类名]`——光看标题根本分不清启动器和游戏。

> 整合包的窗口标题是 `Annoying Villagers - Annoying Villagers`，
> **整串没有 "Minecraft"**。真正决定匹配的是**类名** `GLFW30`。

### 3. 传感器有数据吗

接管后看游戏聊天栏，应该每秒刷一行：

```
<TRIT hp=185 food=17 x=123 y=-601 z=88 h=3>
```

**看不到这行 = 感知断了**，AI 会一直弃权（这是设计，不是 bug）。

逐条查：

| 检查 | 怎么查 |
|---|---|
| 包装了吗 | `ls saves/*/datapacks/trit_bridge.zip` |
| 启用了吗 | 游戏里 `/datapack list`，花括号才是启用 |
| 是当前世界吗 | 新建世界的 `datapacks/` 是空的 |
| 标签作废了吗 | `check_env.py` 的 [5] 项 |
| 字段名对吗 | `check_env.py` 的 [6] 项 |

### 4. 配置文件对吗

```bash
grep log_path trit-agent.toml
```

指向的文件必须存在（游戏至少启动过一次才会生成 `logs/latest.log`）。

**这条路径配错 = AI 永远「没感知」** → 所有票都是 `0` → 永远弃权 → 角色站着不动。
这是最常见的表现。

### 5. 感知延迟正常吗

游戏里敲：

```
!gather lag
```

会显示实测的感知间隔和「等多久」。异常值（比如装了快通道还是 1400ms）
说明快通道没开或数据包没更新。

---

## 症状对照表

| 症状 | 最可能的原因 |
|---|---|
| 按 F8 没反应 | 进程没在跑 / 有第二个实例抢互斥量 |
| 角色站着不动 | 没有感知数据（查聊天栏有没有 `<TRIT`） |
| 角色动了但撞墙 | 「看见墙」是近似的，漏了某个方块（`stuck` 检测会兜底） |
| 一直原地转圈 | 墙体位序写反了（yaw 往右加，位 1 是正右方） |
| 挖矿挖不动 | 没换工具（木镐挖钻石矿会掉） |
| 挖矿挖错东西 | 判据不全（岩浆/矿石分类靠 `#trit_bridge:ores` 标签） |
| 夜里不干活 | `gather_night = false`（默认） |
| 干活干一半停了 | 配额用完（`gather_quota`）或血量/饥饿不够 |
| 宠物乱跑 | 只删了 `AngryAt` 没清 `AngerTime`，或反过来 |
| 看不到宠物被指挥 | `squad = true` 且 `squad_control = "chat"` |
| AI 不理 `/function` | `allowCommands=0`，或者世界没开作弊 |
| 窗口切出去 AI 就停 | `focus_pause = true`（默认，行为正确） |
| 鼠标转太快/太慢 | `look_gain`，默认 1.35 是按灵敏度 0.5 估的 |
| 改了代码没生效 | exe 比源码旧，重新 `cargo build --release` |

---

## 数据包侧的那些坑

详见 [[Data-Packs]] 的「拷进去 ≠ 装上了」。摘要：

1. 拷进 `saves/<世界>/datapacks/` **≠ 启用**——要 `/datapack enable`
2. 新建的世界是空的——**装的是旧世界，玩的是新世界**
3. `data modify` 只写已存在的路径——新实体要先 `data merge` 造字段
4. 资源包和数据包不是一回事——`summoner_lang` 要放 `resourcepacks/`

---

## 崩溃了

见 [[Crash-Troubleshooting]]。

---

## 相关

- [[Building]] —— 编译与自检
- [[Configuration]] —— 每个配置项的行为
