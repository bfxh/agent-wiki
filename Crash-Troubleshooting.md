# 崩溃排查

> **不是渲染引擎的问题。**
> 本文记录的两个真实崩溃都是 **Java 空指针（NullPointerException）**，
> 跟 GPU / 驱动 / 光影 / 材质渲染完全无关。

---

## 一键诊断

```bash
python scripts/diagnose_crash.py          # 诊断最近一次崩溃
python scripts/diagnose_crash.py --all    # 列出所有历史崩溃
```

（在 bfxh/trit-mc 仓库里）

输出包含：崩溃点栈帧、是否已进世界、`<TRIT>` 条数、守护进程时间线、
**按崩溃时刻判定 AI 有无接管**。

---

## 真凶：rrls

整合包「The Annoying Villagers by PugilistSteve42834」自带的
**rrls**（Remove Reloading Screen，作者 dimadencep），
藏在 `mods/TheAnnoyingVillagersByPugilist_Steve_4_28 (34).jar` 里。

### 崩溃链（字节码级钉死）

`rrls-common.mixins.json` → `MinecraftClientMixin`：

```java
@Redirect(method = {"tick", "handleInputEvents"},
          at = @At(value = "FIELD", target = "...Minecraft;overlay:..."))
private Overlay fixOverlayUsage(Minecraft mc) {
    return Rrls.tryGetOverlay(mc.overlay);
}
```

`Rrls.tryGetOverlay` 字节码原文：

```
if (overlay instanceof SplashAccessor && splash.isAttached())
    return null;      // ← 这里
return overlay;
```

原版 `Minecraft.runTick()` 靠 `overlay == null` 判断「现在不该处理按键」。
rrls 在加载界面还挂着时返回 null，把这条判断**反转**了：

```
正常：  加载界面挂着 -> overlay != null -> 跳过 handleKeybinds
有 rrls：加载界面挂着 -> overlay == null -> 照样跑 handleKeybinds
                                        -> this.player 还是 null -> NPE
```

所以崩溃发生在**进世界之前**（`player == null`）。

### 为什么栈里看不到它

崩溃栈 5 帧全是原版帧。这正是**定位的线索**：

> 因为它用 mixin 的 `@Redirect` **改写了控制流**，
> 不是插入代码——处理器返回后 vanilla 继续执行，
> 所以栈里只剩 vanilla 帧，没有 mod 帧。

顺着这个线索去查 mixin 的 **refmap**（mixin 目标写在 refmap/json 里，
**不在 class 常量池**——搜常量池是找不到的），全量扫描后
只有 `Rrls-common-refmap.json` 同时映射 `m_91279_`（handleKeybinds）
和 `m_91398_`（runTick）。

### 为什么 `rrls.toml` 的 `enabled = false` 没用

`config/rrls.toml` 里有 `enabled = true`，看着像开关。
但那是 AutoConfig 的配置项，只影响模组自己的配置逻辑——
`fixOverlayUsage` 方法体里**没有任何 enabled 判断**
（字节码只有一条 `getfield f_91081_` → `tryGetOverlay` → `areturn`），
mixin 该注入还是注入。

**唯一可靠的办法是不让这个 jar 被 Forge 加载。**

### 处置

```bash
python scripts/toggle_rrls.py status    # 查看
python scripts/toggle_rrls.py disable   # 禁用（防崩溃）
python scripts/toggle_rrls.py enable    # 恢复
```

- 改名成 `.jar.disabled`（Forge 只加载 `.jar` 结尾的文件）
- **先备份**到 `mods/.trit-agent-backup/`，不是删除，可还原
- 自动扫描含 rrls 的 jar，不写死文件名（整合包更新后编号会变）
- 该 jar 里**只有 rrls**，禁用它零副作用

代价只是加载/资源重载时会短暂显示原版进度条界面。

---

## 第二次崩溃：AI 干没干？

**没有。** 这是教科书级的干净对照：

| 时刻 | 事件 |
|---|---|
| 19:20:22 | 守护进程启动 |
| 19:21:52 | 守护进程最后一条日志 |
| 19:22:31 | **ModLauncher 启动**（游戏才开始） |
| 19:23:13 | 崩溃 |

崩溃时守护进程**已经死了 90 秒**，进程根本不存在，**零按键注入**。

对比第一次崩溃：守护进程当时是活着的（怀疑它待机时改窗口标题）。
那次已经修了——**待机期完全不碰窗口标题**，
`update_badge()` / `refresh_badge()` 只在接管时才写。
新增回归测试 `idle_agent_never_touches_the_window_title` 锁住这条。

---

## 排除法：怎么确认不是别的 mod

字节码级排查用到的手段，记下来省得重复：

| 手段 | 用途 |
|---|---|
| `javap -c -p` | 反汇编字节码 |
| `javap -l -p` | 行号表（定位到 Minecraft.java:1836） |
| `javap -v` | mixin 注解 |
| 搜 class 常量池 | 找引用了某字段/方法的类 |
| 搜 mixin refmap | **找谁在改写控制流**（栈里看不到 mod 时用这个） |

被逐一排除的候选（各有 null 保护或不碰 handleKeybinds）：
Iris / Oculus、ExtraSounds、CombatRoll、BetterCombat、
WeaponMaster、ShieldExp、Guns、PassiveShield。

---

## SRG 映射速查

调试时用得上：

| SRG | Yarn | 含义 |
|---|---|---|
| `m_91279_` | `handleKeybinds` | 按键处理 |
| `m_91398_` | `runTick` | 每 tick 主循环 |
| `m_91383_` | `tick(boolean)` | |
| `f_91074_` | `Minecraft.player` | 玩家实体 |
| `f_91081_` | `Minecraft.overlay` | 当前界面 |
| `f_91080_` | `Minecraft.screen` | |
| `m_6117_()` | `public boolean` | |

---

## 如果还崩

rrls 排除后如果还崩，说明有第二个元凶。跑：

```bash
python scripts/diagnose_crash.py
```

把输出发出来。诊断脚本会给出：崩溃点栈帧、mod 名单、
以及**按崩溃时刻判定 AI 有无接管**的结论。

---

## 相关

- [[Troubleshooting]] —— 不是崩溃，是「没效果」
- [[Data-Packs]] —— 数据包侧的坑
- [[Background-Daemon]] —— 守护进程为什么曾经静默死亡
