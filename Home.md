# trit-agent 维基

用三值决策状态机替你在 Minecraft 里操作角色。Windows / 零第三方依赖 Rust / **不需要给游戏装 mod**。

```
三值决策层   每 5ms 一拍（默认 200Hz，可到 2000Hz）
    ↓ 投票 + 裁决（迟滞 / 弃权）
输入注入层   SendInput 直接打进游戏窗口（键鼠，不是模拟点击）
    ↓
感知回填层   logs/latest.log ← 聊天框 ← 数据包 tellraw
             两条通道：100ms（瞄准/碰撞）+ 1 秒（敌人/资源）
```

能做的事：打怪（借用原版 mob 的 Goal 逻辑 + 《孙子兵法》五条战法）、
一个大脑指挥傀儡和狼、砍树、**挖矿**、**看见墙和台阶**、
F8 一键交还控制权。感知延迟在动手期间压到 100ms 量级。

---

## 仓库地图

| 仓库 | 内容 |
|---|---|
| **[bfxh/trit-agent](https://github.com/bfxh/trit-agent)** | Rust 状态机、输入注入、感知解析、后台守护进程 |
| **[bfxh/trit-mc](https://github.com/bfxh/trit-mc)** | Minecraft 侧：数据包、起源包、打包与诊断脚本 |
| **[bfxh/agent-wiki](https://github.com/bfxh/agent-wiki)** | 本维基 |

两个仓库通过**一条契约**咬合：传感器协议。
数据包往聊天栏打 `<TRIT hp=... food=...>`，Rust 侧从 `logs/latest.log` 读回来。

---

## 目录

### 上手
- [[Getting-Started]] —— 装、跑、按 F8
- [[Hotkeys]] —— 全部按键
- [[Configuration]] —— 配置项逐条解释
- [[Background-Daemon]] —— 后台守护进程（进游戏直接按 F8）

### 原理
- [[Tri-Value-FSM]] —— 为什么是三值而不是「做/不做」
- [[Perception]] —— 两条通道，两个频率
- [[Gathering]] —— 采集：什么时候不该砍
- [[Architecture]] —— 模块地图与数据流

### Minecraft 侧
- [[Data-Packs]] —— 数据包、起源包、装包的那些坑
- [[Sensor-Protocol]] —— 传感器协议字段表
- [[Crash-Troubleshooting]] —— 崩溃排查（含 rrls 真凶）
- [[Troubleshooting]] —— 「还是没有」时的排查顺序

### 开发
- [[Building]] —— 编译、测试、自检
- [[Design-Boundaries]] —— 能力边界（诚实的部分）
- [[Control-Channels]] —— 操控方式注册表 / 想接对讲机看这里

---

## 三分钟速览

```bash
# 1. 装数据包（Minecraft 侧）
git clone git@github.com:bfxh/trit-mc.git && cd trit-mc
python scripts/build_datapacks.py --install "E:/MC/MC/profiles/烦人的村民"

# 2. 编译 AI（Rust 侧）
git clone git@github.com:bfxh/trit-agent.git && cd trit-agent
cargo build --release

# 3. 一键自检
python ../trit-mc/scripts/check_env.py

# 4. 进游戏，按 F8
```

按 F8 接管，再按 F8 交还。**F9 是急停**（不切视角），F10 切视角。

---

## 三十秒速览

进游戏 → **按 F8** → 角色开始自己巡逻、看见墙会绕、见矿会挖。

按 F8 再交还。急了按 F9。

---

## 相关项目

- **[bfxh/trit](https://github.com/bfxh/trit)** —— 三进制工具箱（三值逻辑 K3/Ł3/B3、双导轨位平面、
  三值内核、5 trit/字节打包）。trit-agent 的「为什么是三值」那套理论来自它。
