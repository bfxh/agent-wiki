# 数据包

> 数据包在独立仓库：**[bfxh/trit-mc](https://github.com/bfxh/trit-mc)**

数据包提供**传感器**——把游戏状态写进聊天栏，AI 从日志里读回来。
没有它 AI 也能动，但那是盲动。

---

## 有什么

```
datapacks/
  squad/             共同意识的执行端：receive 意图 → 改傀儡/狼的 AngryAt
  trit_bridge/       传感器：快慢双通道，把血量/坐标/敌人/原木/矿石/墙体/俯仰角写进聊天
archive/origins/     隔离的起源包（不随状态机打包）
  npc_origins/       给 NPC 挂「起源式」效果（打 tag 生效，默认无副作用）
  summoner_origin/   召唤师起源：3 只战狼 + 铁卫，召唤物会主动打村民和整合包敌对 NPC
  summoner_lang/     召唤师起源的中文名称（资源包）
  origins_zh/        全部汉化（2490 条词条）
```

---

## 装

```bash
git clone git@github.com:bfxh/trit-mc.git && cd trit-mc
python scripts/build_datapacks.py --install "E:/MC/MC/profiles/烦人的村民"
```

打包器会自动校验：JSON 合法性、`function` 引用、方块标签引用、传感器字段名。

---

## ⚠️ 拷进去 ≠ 装上了

这是 MC 侧最大的坑，脚本存在的理由。

### 1. 存档的数据包要单独启用

脚本只是把 zip 复制进 `saves/<世界>/datapacks/`，
而游戏只加载 `level.dat` 里 `Enabled` 表列出的包。**新放进去的默认是禁用。**

进世界后要敲：

```
/datapack list                                   # 方括号 = 未启用，花括号 = 已启用
/datapack enable "file/trit_bridge.zip"
/datapack enable "file/squad.zip"
```

`level.dat` 用脚本查，别靠猜：

```bash
python scripts/save_packs.py status "E:/MC/MC/profiles/烦人的村民"
python scripts/save_packs.py enable "E:/MC/MC/profiles/烦人的村民" --all
```

### 2. 新建的世界里根本没有这些包

数据包是**每个存档一份**的。新建世界时 `saves/<新世界>/datapacks/` 是空目录，
起源列表里当然什么都没有。

装完还得让游戏重新扫一次目录（**退回主菜单再进**），`/datapack enable` 才认得这个 id。

> 这是「我明明装过了」最容易翻车的地方：**装的是旧世界，玩的是新世界。**

### 3. `data modify` 只写已存在的路径

新生实体的 NBT 里没有 `AngryAt`，命令会被**静默拒绝**：
不报错、不写日志、聊天栏也没提示。

必须先造字段再 modify：

```mcfunction
data merge entity @s {AngryAt:[I;0,0,0,0]}
data modify entity @s AngryAt set value [I;1,2,3]
```

同理适用于 `Owner`。

### 4. 资源包和数据包不是一回事

`summoner_lang` 是**资源包**，必须放进 `resourcepacks/` 并在游戏里启用。
数据包里的 `assets/` 不参与加载。

---

## 别照着 1.12 的老资料改选择器

`@e[type=!player,type=!item]`（npc_origins 里在用）**是合法的**：
多个 `type=!` 会 AND 累积，效果是「既不是玩家也不是物品」。

不合法的是多个**正值** `type=cow,type=chicken`（实体不可能同时是牛又是鸡）。

网上流传的「第二个覆盖第一个」出自 Arqade 2015 年的老回答，说的是 1.9 之前的行为；
1.13 重写 `EntitySelectorParser` 之后已经变了。
这条我们查过中英文 wiki 确认，**别再按旧说法去「修」了**。

---

## 起源包会被「照 schema 体检」

打包时会自动跑一次 `validate_origins.py`：

```bash
python archive/origins/scripts/validate_origins.py            # 只查本仓库的 summoner_origin
python archive/origins/scripts/validate_origins.py --all      # 连模组自带的起源一起查
python archive/origins/scripts/validate_origins.py --selftest # 用坏样本验证校验器本身
```

依据不是文档，而是**这套整合包真实注册的 id**——
从 `origins-forge` 和它内嵌的 `apoli` 里那些注册表类把常量池抠出来（380 个 id），
再拿数据包去比对。查四件事：

- `type` 写没写错（`origins:actve_self` 这种，游戏只会静默不加载）
- 必填字段在不在（`active_self` 要 `entity_action`；
  `attribute` 的 `modifier` 要 `attribute`/`operation`/`value`）
- `powers` 引用的文件在不在（跨模组的引用去全局索引查，不误报）
- 起源层的 `replace:true`（**会把别的模组已登记的起源整层顶掉**，选择界面只剩自己的）

`--all` 会拿 origins++ 的 119 个起源 + 1405 个能力跑一遍：全过，说明校验器不会乱报。

---

## 汉化

**2490 / 2490 全译完**（起源 241、能力 2100、容器 10、杂项 139）。

分片写在 `archive/origins/datapacks/origins_zh/_parts/*.json`，
合并后落到 `assets/origins-plus-plus/lang/zh_cn.json`：

```bash
python archive/origins/scripts/merge_zh.py  --mods "E:/MC/MC/profiles/烦人的村民/mods"
python archive/origins/scripts/make_origins_zh.py --mods "E:/MC/MC/profiles/烦人的村民/mods" --inject
```

**为什么分成片 + 按序号回填**：两千多条如果每条都手写
`power.origins-plus-plus.xxx/yyy.name` 这种 key，光 key 就两万多字符，
错一个字母就静默失效。

所以先把英文导出成 `序号<TAB>key<TAB>英文` 的 TSV，
翻译时只写 `序号<TAB>中文`，由 `apply_zh.py` 回填——**序号对不上直接报错，不可能错位**。

TSV 是逐行存的，原文里的换行用 `⏎` 占位，回填时还原成 `\n`
（技能说明里那些换行是 tooltip 排版的一部分）。

**为什么塞进 jar**：模组自带的资源是无条件加载的，
而资源包要在「选项 → 资源包」里手动启用，
且游戏退出时用内存里的列表覆盖 `options.txt`——**运行期改文件无效**。

塞进 jar 只需要重启一次，没有任何手动步骤。模组更新会覆盖掉，重跑上面两条命令即可。

---

## 一键自检

```bash
python scripts/check_env.py
```

7 项：AI 本体 / 存档数据包 / 传感器 / 数据包格式 / 模组标签 / 协议 / rrls。

---

## 相关

- [[Sensor-Protocol]] —— 协议字段表
- [[Crash-Troubleshooting]] —— rrls 崩溃真凶
- [[Perception]] —— 这些数据怎么被用
