#!/usr/bin/env python3
"""把 wiki 的 markdown 页面渲染成一个可浏览的维基站点（GitHub Pages）。

为什么不用 GitHub 自带的 Wiki：
GitHub 的 `.wiki.git` 仓库**必须在网页端手工建过第一个页面**才存在，
API / GraphQL / git push 都建不出来（都试过了，返回 404）。
所以这里走 GitHub Pages：内容是同一份 markdown，输出成带侧边导航的 HTML。

用法：
    python scripts/build_site.py            # 从 ../ 的 *.md 生成到 site/
    python scripts/build_site.py --src .. --out site
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import shutil
import sys

# ---------------------------------------------------------------- 页面顺序
# 顺序 = 侧边栏的分组顺序
PAGES = [
    ("Home", "首页", "🏠"),
    ("Getting-Started", "上手", "🚀"),
    ("Hotkeys", "热键", "⌨️"),
    ("Configuration", "配置", "⚙️"),
    ("Background-Daemon", "后台守护进程", "🔧"),
    ("Tri-Value-FSM", "三值状态机", "🎲"),
    ("Perception", "感知", "👁️"),
    ("Gathering", "采集", "🪓"),
    ("Architecture", "架构", "🏗️"),
    ("Data-Packs", "数据包", "📦"),
    ("Sensor-Protocol", "传感器协议", "🔌"),
    ("Crash-Troubleshooting", "崩溃排查", "💥"),
    ("Troubleshooting", "没效果怎么查", "🔍"),
    ("Building", "构建与测试", "🔨"),
    ("Design-Boundaries", "能力边界", "⚖️"),
    ("Control-Channels", "操控方式", "🎛️"),
]

GROUP_END = {
    "Configuration": "上手",
    "Background-Daemon": "上手",
    "Gathering": "原理",
    "Architecture": "原理",
    "Crash-Troubleshooting": "Minecraft 侧",
    "Troubleshooting": "Minecraft 侧",
    "Control-Channels": "开发",
}

GROUPS = ["上手", "原理", "Minecraft 侧", "开发"]

# 页面副标题（显示在大标题下面）
SUBTITLES = {
    "Home": "用三值决策状态机替你在 Minecraft 里操作角色",
    "Getting-Started": "装、跑、按 F8",
    "Hotkeys": "F8 交还 · F9 急停 · F10 切视角",
    "Configuration": "配置项逐条解释",
    "Background-Daemon": "进游戏直接按 F8 —— 装一次，永久有效",
    "Tri-Value-FSM": "为什么不是「做 / 不做」两档",
    "Perception": "两条通道，两个频率",
    "Gathering": "真正难的是「什么时候不该砍」",
    "Architecture": "模块地图与数据流",
    "Data-Packs": "数据包、起源包、装包的那些坑",
    "Sensor-Protocol": "跨仓库的唯一集成点",
    "Crash-Troubleshooting": "不是渲染引擎的问题",
    "Troubleshooting": "每一件事都是静默的",
    "Building": "编译、测试、自检",
    "Design-Boundaries": "知道做不到什么比知道能做什么更有用",
    "Control-Channels": "以后要接对讲机、语音、第二屏的落地清单",
}

# 页面大标题（默认用 PAGES 里的短标签，个别页面另有其名）
PAGE_TITLES = {
    "Home": "trit-agent 维基",
}

# ---------------------------------------------------------------- 样式
CSS = """
:root {
  --bg: #ffffff;
  --bg-soft: #f6f8fa;
  --border: #d0d7de;
  --text: #1f2328;
  --text-dim: #59636e;
  --link: #0969da;
  --accent: #1f6feb;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117;
    --bg-soft: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #9198a1;
    --link: #4493f8;
    --accent: #4493f8;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  font-size: 15px;
  line-height: 1.75;
}
.wrap { display: flex; max-width: 1280px; margin: 0 auto; min-height: 100vh; }
nav {
  width: 264px; flex: 0 0 264px;
  border-right: 1px solid var(--border);
  padding: 26px 18px 60px;
  position: sticky; top: 0; align-self: flex-start;
  max-height: 100vh; overflow-y: auto;
}
nav h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .08em;
         color: var(--text-dim); margin: 22px 0 8px; font-weight: 600; }
nav h2:first-child { margin-top: 0; }
nav a {
  display: block; padding: 5px 10px; margin: 1px 0;
  color: var(--text); text-decoration: none;
  border-radius: 6px; font-size: 14px;
}
nav a:hover { background: var(--bg-soft); }
nav a.on { background: var(--bg-soft); color: var(--accent); font-weight: 600;
           box-shadow: inset 2px 0 0 var(--accent); }
main { flex: 1; min-width: 0; padding: 40px 48px 100px; }
h1 { font-size: 2.1em; margin: 0 0 .4em; padding-bottom: .3em;
     border-bottom: 1px solid var(--border); line-height: 1.25; }
.subtitle { color: var(--text-dim); font-size: 1.05em; margin: 0 0 1.6em;
            padding-bottom: 1em; border-bottom: 1px solid var(--border); }
h2 { font-size: 1.45em; margin: 1.9em 0 .7em; padding-bottom: .3em;
     border-bottom: 1px solid var(--border); }
h3 { font-size: 1.15em; margin: 1.6em 0 .5em; }
p, li { margin: .7em 0; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
code {
  background: var(--bg-soft); border: 1px solid var(--border);
  padding: .12em .38em; border-radius: 5px;
  font-family: ui-monospace, SFMono-Regular, "Cascadia Code", Consolas, monospace;
  font-size: .87em;
}
pre {
  background: var(--bg-soft); border: 1px solid var(--border);
  padding: 15px 17px; border-radius: 8px; overflow-x: auto; line-height: 1.55;
}
pre code { background: none; border: none; padding: 0; font-size: 13px; }
table { border-collapse: collapse; margin: 1.1em 0; display: block; overflow-x: auto; max-width: 100%; }
th, td { border: 1px solid var(--border); padding: 7px 13px; text-align: left; }
th { background: var(--bg-soft); font-weight: 600; }
tr:nth-child(2n) td { background: color-mix(in srgb, var(--bg-soft) 45%, transparent); }
blockquote {
  margin: 1.1em 0; padding: .1em 1em; color: var(--text-dim);
  border-left: 3px solid var(--border);
}
hr { border: none; border-top: 1px solid var(--border); margin: 2em 0; }
img { max-width: 100%; }
.pager { display: flex; justify-content: space-between; gap: 14px;
         margin-top: 52px; padding-top: 20px; border-top: 1px solid var(--border); }
.pager a { padding: 11px 15px; border: 1px solid var(--border); border-radius: 8px;
           background: var(--bg-soft); font-size: 14px; }
.pager a:hover { border-color: var(--accent); text-decoration: none; }
.pager .next { margin-left: auto; }
.meta { color: var(--text-dim); font-size: 13px; margin-top: 40px; }
.badge { display:inline-block; padding:1px 8px; border-radius:20px;
         background: var(--bg-soft); border:1px solid var(--border);
         font-size:12px; color: var(--text-dim); }
"""


def md_to_html(md: str) -> str:
    """够用的 markdown → HTML。

    不引第三方库：只需要标题/列表/表格/代码块/强调/链接/引用/分隔线。
    顺序有讲究——**代码块最先抽走**，否则里面的内容会被当成 markdown 解析。
    """
    blocks: list[str] = []
    out: list[str] = []

    # 1. 抽出围栏代码块
    def _fence(m: re.Match) -> str:
        lang = m.group(1) or ""
        body = m.group(2)
        cls = f' class="language-{html.escape(lang)}"' if lang else ""
        blocks.append(f"<pre><code{cls}>{html.escape(body)}</code></pre>")
        return f"\x00BLOCK{len(blocks) - 1}\x00"

    text = re.sub(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", _fence, md, flags=re.S)

    # 2. 抽出行内代码
    codes: list[str] = []

    def _inline(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00CODE{len(codes) - 1}\x00"

    text = re.sub(r"`([^`\n]+)`", _inline, text)

    # 3. 转义 HTML
    text = html.escape(text, quote=False)

    # 4. 逐行处理
    lines = text.split("\n")
    i = 0
    in_ul = False
    in_ol = False
    in_table = False
    table_rows: list[list[str]] = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def close_table() -> None:
        nonlocal in_table
        if not in_table:
            return
        out.append("<table>")
        header, *body = table_rows
        out.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in header) + "</tr></thead>")
        if body:
            out.append("<tbody>" + "".join(
                "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body
            ) + "</tbody>")
        out.append("</table>")
        in_table = False
        table_rows.clear()

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # 表格行
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                i += 1  # 分隔行
                continue
            if not in_table:
                close_lists()
                in_table = True
                table_rows = []
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            close_table()

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_lists()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{m.group(2)}</h{lvl}>")
            i += 1
            continue

        # 分隔线
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", line):
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        # 引用
        if line.startswith("> "):
            close_lists()
            buf = [line[2:]]
            i += 1
            while i < len(lines) and lines[i].startswith("> "):
                buf.append(lines[i][2:])
                i += 1
            out.append(f"<blockquote>{'<br>'.join(buf)}</blockquote>")
            continue

        # 列表
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", raw)
        if m:
            indent, marker, content = m.groups()
            ordered = marker[0].isdigit()
            if ordered and not in_ol:
                close_lists()
                out.append("<ol>")
                in_ol = True
            elif not ordered and not in_ul:
                close_lists()
                out.append("<ul>")
                in_ul = True
            elif ordered != in_ol:
                close_lists()
                out.append("<<ol>>" if ordered else "<ul>")
                if ordered:
                    in_ol = True
                else:
                    in_ul = True
            out.append(f"<li>{content}</li>")
            i += 1
            continue

        # 空行
        if not line:
            close_lists()
            i += 1
            continue

        # 段落
        close_lists()
        buf = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^\s*([-*+]|\d+\.)\s+", lines[i]
        ) and not lines[i].startswith(">") and not lines[i].startswith("|") \
            and not re.match(r"^#{1,6}\s", lines[i]):
            buf.append(lines[i].rstrip())
            i += 1
        out.append(f"<p>{'<br>'.join(buf)}</p>")

    close_lists()
    close_table()

    result = "\n".join(out)

    # 5. 行内格式（必须在转义之后做，避免破坏实体）
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)
    result = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", result)
    result = re.sub(r"~~(.+?)~~", r"<del>\1</del>", result)

    # 6. 链接：[[Page]] 内部链接 / [text](url) 外部链接
    #    内部链接显示**中文页名**，不是英文文件名 —— 首页那种
    #    "Getting-Started —— 装、跑、按 F8" 读起来别扭。
    page_labels = {n: lbl for n, lbl, _ in PAGES}

    def _wiki_link(m: re.Match) -> str:
        target = m.group(1)
        label = m.group(2)
        if label is None:
            label = page_labels.get(target, target)
        href = target if target.lower().endswith(".html") else target + ".html"
        return f'<a href="{html.escape(href)}">{html.escape(label)}</a>'

    result = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", _wiki_link, result)

    def _ext_link(m: re.Match) -> str:
        href, label = m.group(1), m.group(2)
        return f'<a href="{href}" target="_blank" rel="noopener">{label}</a>'

    result = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", _ext_link, result)

    # 7. 还原代码
    result = re.sub(r"\x00BLOCK(\d+)\x00", lambda m: blocks[int(m.group(1))], result)
    result = re.sub(r"\x00CODE(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))])}</code>", result)

    return result


def nav_html(current: str) -> str:
    """侧边栏导航。"""
    parts = ['<nav>', f'<a href="Home.html" class="{"on" if current == "Home" else ""}">🏠 首页</a>']
    seen: set[str] = set()
    for name, label, icon in PAGES:
        if name == "Home":
            continue
        group = GROUP_END.get(name)
        if group and group not in seen:
            if seen:
                parts.append("</div>")
            parts.append(f"<h2>{group}</h2><div>")
            seen.add(group)
        cls = "on" if current == name else ""
        parts.append(f'<a href="{name}.html" class="{cls}">{icon} {label}</a>')
    if seen:
        parts.append("</div>")
    parts.append("</nav>")
    return "\n".join(parts)


def page_html(name: str, title: str, body_md: str) -> str:
    idx = next((i for i, p in enumerate(PAGES) if p[0] == name), None)
    prev_link = ""
    next_link = ""
    if idx is not None and idx > 0:
        p = PAGES[idx - 1]
        prev_link = f'<a href="{p[0]}.html">← {p[1]}</a>'
    if idx is not None and idx < len(PAGES) - 1:
        p = PAGES[idx + 1]
        next_link = '<a class="next" href="{}.html">{} →</a>'.format(p[0], p[1])

    # 页面大标题（markdown 的一级标题被剥掉了，这里补一个带副标题的）
    subtitle = SUBTITLES.get(name, "")
    head_title = PAGE_TITLES.get(name, title)
    head = f"<h1>{html.escape(head_title)}</h1>"
    if subtitle:
        head += f'<p class="subtitle">{html.escape(subtitle)}</p>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · trit-agent 维基</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="wrap">
{nav_html(name)}
<main>
{head}
{md_to_html(body_md)}
<div class="pager">{prev_link}{next_link}</div>
<div class="meta">
  <span class="badge">trit-agent 维基</span>
  <span class="badge">bfxh/agent-wiki</span>
  <span class="badge">Rust · Minecraft · 零依赖</span>
</div>
</main>
</div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".", help="markdown 所在目录")
    ap.add_argument("--out", default="site", help="输出目录")
    args = ap.parse_args()

    src = pathlib.Path(args.src).resolve()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    for name, label, _ in PAGES:
        f = src / f"{name}.md"
        if not f.is_file():
            missing.append(name)
            continue
        md = f.read_text(encoding="utf-8")
        # 去掉 markdown 里的一级标题（页面标题已经在 <title> 和 h1 里）
        md = re.sub(r"^#\s+.*\n+", "", md, count=1)
        (out / f"{name}.html").write_text(page_html(name, label, md), encoding="utf-8")

    if missing:
        print(f"[!!] 缺页面: {', '.join(missing)}")

    (out / "style.css").write_text(CSS, encoding="utf-8")

    # 搜索索引（给未来的搜索框用）
    index = {
        name: {"title": label, "icon": icon}
        for name, label, icon in PAGES
    }
    (out / "search-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 首页额外做一个 index.html 别名
    (out / "index.html").write_text(
        (out / "Home.html").read_text(encoding="utf-8"), encoding="utf-8"
    )

    print(f"生成 {len(PAGES)} 个页面 -> {out}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
