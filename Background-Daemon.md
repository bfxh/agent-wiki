# 后台守护进程

> **进游戏直接按 F8** —— 这是整套东西的最终形态。

---

## 为什么要有守护进程

热键是**进程里注册的全局钩子**。进程不在，F8 就是死的。

之前的设计是「双击 `启动AI.bat` → 开一个黑窗口 → 切到游戏 → 按 F8」。
问题是那个黑窗口一关就没了，而且切窗口的动作本身就会丢焦点。

守护进程把它变成：**装一次，永久有效，进游戏按 F8 就行**。

---

## 它做什么

```
守护进程（常驻，无窗口）
    ↓ 等游戏窗口出现（每 30 秒报一次状态）
    ↓ 找到窗口（按类名 GLFW* + 标题关键字）
    ↓ 挂上，但不接管 —— 等你按 F8
    ↓ 你按 F8 → 接管
    ↓ 游戏关了 → 松手，回到等待
```

**关键设计：守护模式不自动接管。**
前台模式是「双击就开跑」，守护模式是「按 F8 才接管」——
后者才符合「直接按 F8 就可以」。

而且守护进程：

- **不抢焦点**（`grab_focus_on_start = false`）
- **不自动切视角**（`switch_view_on_start = false`）

理由同上：守护进程是常驻的，抢焦点意味着你正在写代码时窗口被游戏抢走。

---

## 静默死亡：一个查了三层的坑

### 现象

守护进程 19:20:22 启动，19:21:52 之后日志直接断掉、进程消失。
用户按键时**根本没有任何进程在监听 F8**。

但外部**没有任何痕迹**：

- Windows 事件日志无记录
- WER 无崩溃转储
- Defender 无误杀记录

### 三层叠加的「静默」

1. **守护进程是 `windows_subsystem = "windows"` 编译的** —— 没有控制台。
   Rust 默认的 panic 处理往 stderr 打印，而 GUI 子系统的 stderr 指向无效句柄，
   **一个字都出不来**。
2. **release profile 是 `panic = "abort"`** —— panic 直接终止进程，
   `catch_unwind` 也拦不住。
3. 进程消失后没有任何外部痕迹。

排查过程排除了所有其他可能：

| 假设 | 怎么排除的 |
|---|---|
| 窗口枚举切片越界 panic | 探针实测 `GetClassNameW` 在缓冲区不足时返回**实际拷贝数**（buf16 对 24 字符类名返回 15），不是 MSDN 说的「所需长度」 |
| 被父进程树连带杀掉 | 跨工具调用的子进程存活实验：心跳持续增长，**不成立** |
| 访问违例 | 事件日志 + WER 转储，**无记录** |
| Defender 误杀 | Defender 事件日志，**无记录** |

结论：只剩「panic 且无处输出」这一条路。

### 修法

**1. panic 落盘**

`install_panic_hook()` 把 panic 现场（消息 + 文件行号 + 线程）写进
`trit-agent-daemon.log`。这是唯一能抓住它的时机。

**2. release 改 `panic = "unwind"`**

abort 下 `catch_unwind` 无效；unwind 换来的是
「某一轮跑炸了，守护进程照样活着，F8 继续有效」。

**3. 循环级 panic 隔离**

「跑一轮」整体抽成 `run_one_round()`，主循环用 `catch_unwind` 包住。
panic 只炸掉当前这一轮（最多丢一两秒），下一轮重新挂窗口即可——
相比「守护进程彻底死掉」这个代价可忽略。

---

## 自愈：死了要能自己回来

光「不崩」不够，得**崩了还有人拉起来**。

### 计划任务

注册 Windows 计划任务 `trit-agent-daemon`：

- `LogonTrigger` —— 登录即启动
- **每分钟重复触发** —— 主力
- `RestartOnFailure`（间隔 1 分钟，999 次）
- `ExecutionTimeLimit = PT0S` —— **不限运行时长**
  （默认值是「任务运行 3 天后强制终止」，对常驻守护是颗定时炸弹）
- `MultipleInstancesPolicy = IgnoreNew` —— 不重复起
- `DisallowStartIfOnBatteries = false` —— 笔记本拔电源也继续跑
- `RunLevel = LeastPrivilege` —— 不用管理员

### 「每分钟重复触发」为什么是主力

实测发现：**`RestartOnFailure` 在外部强杀时不触发**。
`LastTaskResult` 变成 `0xFFFFFFFF`（`SCHED_S_TASK_HAS_NOT_RUN`）——
任务计划程序没把强杀当成「失败」。

而「每分钟重复触发」不依赖退出码：daemon 靠命名互斥量保证单实例，
已经在跑时新实例立刻退出（`IgnoreNew` 也跳过重复启动）。

**实测：连续强杀 3 次，全部在 1 分钟内复活**
（20:10:01 / 20:11:01 / 20:12:01 / 20:13:01，间隔精确到秒）。

### 两套并存

`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 保留着，互为备份。

但注意：注册表指向的**必须是 `%LOCALAPPDATA%\trit-agent\` 里的副本**，
不能指向 `target/release`——`cargo clean` 会删掉，自启就静默失效了。

---

## 日志在哪

```
%LOCALAPPDATA%\trit-agent\trit-agent-daemon.log
```

格式：`[2026-11-02 20:10:01] 等待游戏窗口……`

> 时间戳是**本地时间**。早期版本用的是 `SystemTime::now()`（UTC），
> 比崩溃报告和 MC 日志差 8 小时——排查时这条证据就废了。

---

## 查状态

```bash
target/release/trit-agent.exe status
```

```
守护进程: 运行中
自动重启: 已启用（计划任务 trit-agent-daemon）
日志: C:\Users\...\AppData\Local\trit-agent\trit-agent-daemon.log
最近日志:
  [2026-11-02 20:10:01] 等待游戏窗口（按窗口类名 GLFW* 匹配）……
```

> 「自动重启」这一行很重要。
> 只说「未运行」会让人以为彻底没救了——实际上死了会被拉起来。

---

## 停掉

```bash
target/release/trit-agent.exe stop
```

`stop` 会置位命名停机事件（`Global\trit-agent-stop`），
守护进程在**主循环**里查这个信号。

> 这个信号事件必须是**手动复位**的：
> 自动复位会被第一个等待者吃掉，而停机信号有两个查询点（主循环 + 外层循环）。
>
> 命名对象的权限位用错也**不会报错，只会静默失败**：
> `OpenMutexW` 必须用 `SYNCHRONIZE`（`EVENT_MODIFY_STATE` 是事件的位），
> 否则「进程明明在跑但 status 说没跑」。

---

## 排错表

| 现象 | 原因 | 怎么办 |
|---|---|---|
| status 说未运行，但进程在 | 互斥量权限位用错 | 查 `OpenMutexW` 的 `SYNCHRONIZE` |
| 按 F8 没反应，status 说运行中 | 有第二个实例在抢 | `status` 会报；停掉前台那个 |
| 日志停在某一行，之后没了 | panic（历史 bug） | 现在会落盘，看日志里有没有 `!!! 守护进程 panic` |
| 自启不生效 | 注册表指向 `target/release` | 必须指向 `%LOCALAPPDATA%\trit-agent\` 的副本 |
| 配置读不到 | 相对路径没锚定 | 配置查找顺序：exe 旁边 → 安装目录 → cwd |

---

## 相关

- [[Hotkeys]] —— F8 的行为细节
- [[Troubleshooting]] —— 通用排查顺序
