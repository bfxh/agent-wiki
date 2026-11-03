# 门禁：文档也要能判红

> 这一页回答：文档站怎么保证“不是假绿”。
> 结论：**清单 + 断链 + 传输事件 + 构建 + UI 钩子，全部 fail-closed；并且用负例自测证明每一类错误都能判红。**

---

## 0. 为什么文档也要门禁

- 页面漏登记：导航没有、搜索没有、别人找不到。
- 链接写错：`[[Coordination]]` 变成死链，构建照样“成功”。
- 传输事件字段缺失：UI 徽标显示 9 条，实际只有 7 条能渲染。
- 构建脚本自己坏了：生成 21 页但缺 `site.js`，打开就是白屏。
- 密钥/令牌混进示例：提交到公开仓。

这些都不是“内容问题”，是**判定链问题**。所以门禁先判结构，再判内容。

---

## 1. W1-W12

| 门 | 判据 | 典型反例 |
|---|---|---|
| W1 | `wiki.json` 可解析、`pages` 非空 | JSON 语法错、空清单 |
| W2 | `slug` 唯一、`file` 是 `.md` | 两个页面同 slug |
| W3 | 每个 `file` 存在 | 清单有、文件没了 |
| W4 | 每个 `*.md`（除 `README.md`）都登记 | 新页面忘了加清单 |
| W5 | `title/group/summary/tags` 完整 | 缺摘要、tags 不是数组 |
| W6 | `[[内部链接]]` 目标存在（代码块/行内代码不算） | `[[Nope]]` |
| W7 | 传输事件字段完整、id 唯一、status 非空 | 缺 `status`、bytes 不是整数 |
| W8 | 无明显密钥（GitHub token / API key / 私钥 / AWS key） | 示例里放了真 token |
| W9 | `build_site.py` 构建成功 | 缺 `scripts/site.js` |
| W10 | 每页都有 `tx-badge`/`tx-drawer`/`search-data.js`/`transport-data.js`/`site.js` | 模板漏了抽屉 |
| W11 | 分组连续（同一组不重复出现） | 导航分组来回跳 |
| W12 | 生成的 `search-data.js`/`transport-data.js` 与源一致 | 源 9 条、生成 7 条 |

> 全绿只说明“结构/构建/UI 钩子”没问题；内容是否正确仍要人看。

---

## 2. 怎么跑

```bash
# 1) 负例自测：必须证明每类错误都能判红
python scripts/check_wiki.py --self-test

# 2) 实际检查：清单/断链/传输/构建/UI
python scripts/check_wiki.py --src .

# 3) JSON 输出（给 CI/其他工具）
python scripts/check_wiki.py --src . --json
```

退出码：

- `0`：全绿；
- `1`：有 FAIL；
- `2`：用法错误（`--src` 不是目录）。

输出是逐项 `PASS/FAIL`，最后一行是总结果；任何 FAIL 都打印具体文件/字段，不写“检查失败”四个字了事。

---

## 3. 负例自测

`--self-test` 会临时造一个最小站点，然后逐个注入错误：

| 负例 | 期望 |
|---|---|
| 重复 slug | W2 红 |
| 删掉页面文件 | W3 红 |
| 加一个未登记 md | W4 红 |
| 删掉 `summary` | W5 红 |
| 写 `[[Nope]]` | W6 红 |
| 删掉事件 `status` | W7 红 |
| 放一个假 `ghp_...` | W8 红 |
| 删掉 `scripts/site.js` | W9 红 |
| 分组来回跳 | W11 红 |
| 生成物缺 UI 钩子 | W10 红 |
| 生成物条数不一致 | W12 红 |

**如果某个负例没红，`--self-test` 自己判红。** 这样门禁本身也被测，不是“只测别人”。

---

## 4. CI

`.github/workflows/wiki-gate.yml`：

- `push` 到 `master` / `pull_request` / 手动触发；
- 只读权限（`contents: read`）；
- 先跑 `--self-test`，再跑 `--src .`，最后构建；
- 任何一步非 0，PR 红。

> CI 不负责发布；发布仍然走 `gh-pages`（Pages 源已设为 `gh-pages` 根路径）。
> 门禁只保证“源是自洽的、能构建的、UI 钩子在的”。

---

## 5. 和另外两类门的关系

| 门类 | 例子 | 管什么 |
|---|---|---|
| 文档门（本页） | W1-W12 | 清单/链接/传输/构建/UI |
| 运行时门 | `trit-orch::admit`、`compaction_gate`、`effects::Ledger` | 这一轮能不能传、上下文能不能压、副作用是否确定 |
| 仓库门 | 变异门、module budget、secret scan、必需检查 | 代码/提交/CI 是否可信 |

三层不要混：文档门绿，不代表代码门绿；代码门绿，也不代表文档没断链。

---

## 6. 加新页清单

1. 写 `NewPage.md`。
2. 在 `wiki.json` 加一条：`slug/file/title/group/summary/tags`。
3. 在 `Home.md` 或相关页加 `[[NewPage]]`。
4. 跑 `python scripts/check_wiki.py --src .`。
5. 跑构建，本地打开 `site/index.html`。
6. 提交；CI 会再跑一遍。

> 顺序不能反：**先登记，再写页**；否则 W4 会判红，提醒你“有页面没进清单”。
