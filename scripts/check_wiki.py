#!/usr/bin/env python3
"""文档门禁：清单、孤儿页、断链、元数据、传输事件、敏感信息、构建、UI 钩子。

用法：
    python scripts/check_wiki.py --src .
    python scripts/check_wiki.py --src . --json
    python scripts/check_wiki.py --self-test

设计原则：
- fail closed：任何一项不满足就非 0；
- 负例自测：--self-test 必须证明每一类错误都能判红；
- 只读：检查器不改源文件；构建写到临时目录。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

MANIFEST = "wiki.json"
REQUIRED_PAGE = ("slug", "file", "title", "group", "summary", "tags")
REQUIRED_EVENT = ("id", "time", "from", "to", "kind", "status", "summary")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
WIKI_LINK = re.compile(r"\[\[([^\]|]+)")
SEARCH_MARK = '"slug": "'
TRANSPORT_PREFIX = "window.TRANSPORT_EVENTS = "
SECRET_PATTERNS = (
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("api_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
)


@dataclass(frozen=True)
class Finding:
    gate: str
    ok: bool
    message: str


def load_pages(src: Path, findings: list[Finding]) -> list[dict]:
    path = src / MANIFEST
    if not path.is_file():
        findings.append(Finding("W1", False, f"缺 {MANIFEST}"))
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(Finding("W1", False, f"{MANIFEST} 解析失败：{exc}"))
        return []
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        findings.append(Finding("W1", False, f"{MANIFEST} 没有 pages"))
        return []
    findings.append(Finding("W1", True, f"{MANIFEST} 可解析，{len(pages)} 页"))
    return pages


def check_manifest(src: Path, pages: list[dict], findings: list[Finding]) -> list[str]:
    slugs: list[str] = []
    seen: set[str] = set()
    for position, page in enumerate(pages):
        if not isinstance(page, dict):
            findings.append(Finding("W2", False, f"pages[{position}] 不是对象"))
            continue
        slug = page.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            findings.append(Finding("W2", False, f"pages[{position}] slug 为空"))
            continue
        if slug in seen:
            findings.append(Finding("W2", False, f"slug 重复：{slug}"))
        else:
            seen.add(slug)
            slugs.append(slug)
        file_name = page.get("file")
        if not isinstance(file_name, str) or not file_name.endswith(".md"):
            findings.append(Finding("W2", False, f"{slug} 的 file 不是 .md：{file_name!r}"))

    if len(slugs) == len(seen):
        findings.append(Finding("W2", True, f"slug 唯一：{len(slugs)} 个"))

    texts: dict[str, str] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        slug = page.get("slug")
        file_name = page.get("file")
        if not isinstance(slug, str) or not isinstance(file_name, str):
            continue
        path = src / file_name
        if not path.is_file():
            findings.append(Finding("W3", False, f"缺文件：{file_name}（slug={slug}）"))
            continue
        texts[slug] = path.read_text(encoding="utf-8")
    if texts:
        findings.append(Finding("W3", True, f"文件存在：{len(texts)} 个"))

    registered = {
        page.get("file")
        for page in pages
        if isinstance(page, dict) and isinstance(page.get("file"), str)
    }
    md_files = {path.name for path in src.glob("*.md")} - {"README.md"}
    orphans = sorted(md_files - registered)
    if orphans:
        findings.append(Finding("W4", False, f"未登记页面：{', '.join(orphans)}"))
    else:
        findings.append(Finding("W4", True, f"无孤儿页（{len(md_files)} 个 md）"))

    bad_meta: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        slug = str(page.get("slug") or "?")
        for key in REQUIRED_PAGE:
            value = page.get(key)
            if key == "tags":
                if not isinstance(value, list) or not all(
                    isinstance(tag, str) and tag.strip() for tag in value
                ):
                    bad_meta.append(f"{slug}.tags")
                continue
            if not isinstance(value, str) or not value.strip():
                bad_meta.append(f"{slug}.{key}")
    if bad_meta:
        findings.append(Finding("W5", False, f"元数据缺失/为空：{', '.join(bad_meta)}"))
    else:
        findings.append(Finding("W5", True, "元数据完整（title/group/summary/tags）"))

    bad_links: list[str] = []
    for slug, text in texts.items():
        scan = FENCE.sub(" ", text)
        scan = INLINE_CODE.sub(" ", scan)
        for target in WIKI_LINK.findall(scan):
            if target not in seen:
                bad_links.append(f"{slug}->[[{target}]]")
    if bad_links:
        findings.append(Finding("W6", False, f"断链：{', '.join(sorted(set(bad_links)))}"))
    else:
        findings.append(Finding("W6", True, "内部链接均可解析"))

    groups = [
        page.get("group", "")
        for page in pages
        if isinstance(page, dict) and page.get("slug") != "Home"
    ]
    closed: set[str] = set()
    previous = ""
    bad_group = ""
    for group in groups:
        if group != previous:
            if group in closed:
                bad_group = str(group)
                break
            if previous:
                closed.add(previous)
            previous = group
    if bad_group:
        findings.append(Finding("W11", False, f"分组不连续：{bad_group}"))
    else:
        findings.append(Finding("W11", True, "分组连续"))

    return slugs


def check_transport(src: Path, findings: list[Finding]) -> list[dict]:
    path = src / "transport-events.json"
    if not path.is_file():
        findings.append(Finding("W7", False, "缺 transport-events.json"))
        return []
    try:
        events = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(Finding("W7", False, f"transport-events.json 解析失败：{exc}"))
        return []
    if not isinstance(events, list):
        findings.append(Finding("W7", False, "transport-events.json 顶层不是数组"))
        return []

    problems: list[str] = []
    ids: set[str] = set()
    for position, event in enumerate(events):
        if not isinstance(event, dict):
            problems.append(f"[{position}] 不是对象")
            continue
        missing = [key for key in REQUIRED_EVENT if key not in event]
        if missing:
            problems.append(f"[{position}] 缺 {','.join(missing)}")
        event_id = event.get("id")
        if isinstance(event_id, str):
            if event_id in ids:
                problems.append(f"[{position}] id 重复：{event_id}")
            ids.add(event_id)
        if not isinstance(event.get("status"), str) or not event.get("status", "").strip():
            problems.append(f"[{position}] status 为空")
        for key in ("round", "bytes"):
            if key in event and not isinstance(event[key], int):
                problems.append(f"[{position}] {key} 不是整数")

    if problems:
        findings.append(Finding("W7", False, "传输事件问题：" + "; ".join(problems)))
    else:
        findings.append(Finding("W7", True, f"传输事件合法：{len(events)} 条"))
    return events


def scan_secrets(src: Path, findings: list[Finding]) -> None:
    paths = [src / "transport-events.json"] + sorted(src.glob("*.md"))
    hits: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.name}:{name}")
    if hits:
        findings.append(Finding("W8", False, "疑似密钥：" + ", ".join(hits)))
    else:
        findings.append(Finding("W8", True, "未发现明显密钥"))


def run_build(src: Path, out: Path) -> tuple[int, str]:
    script = src / "scripts" / "build_site.py"
    if not script.is_file():
        return 127, "缺 scripts/build_site.py"
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        [sys.executable, str(script), "--src", str(src), "--out", str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def check_generated(
    out: Path, slugs: list[str], events: list[dict], findings: list[Finding]
) -> None:
    missing: list[str] = []
    for slug in slugs:
        path = out / f"{slug}.html"
        if not path.is_file():
            missing.append(f"{slug}.html")
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        for marker in (
            'id="tx-badge"',
            'id="tx-drawer"',
            'src="search-data.js"',
            'src="transport-data.js"',
            'src="site.js"',
        ):
            if marker not in html:
                missing.append(f"{slug}.html 缺 {marker}")
    if not (out / "index.html").is_file():
        missing.append("index.html")
    if missing:
        findings.append(Finding("W10", False, "构建产物/UI 钩子缺失：" + "; ".join(missing)))
    else:
        findings.append(Finding("W10", True, f"UI 钩子齐全：{len(slugs)} 页"))

    data_problems: list[str] = []
    search_path = out / "search-data.js"
    if not search_path.is_file():
        data_problems.append("缺 search-data.js")
    else:
        text = search_path.read_text(encoding="utf-8", errors="replace")
        for slug in slugs:
            if SEARCH_MARK + slug + '"' not in text:
                data_problems.append(f"search-data.js 缺 {slug}")
    transport_path = out / "transport-data.js"
    if not transport_path.is_file():
        data_problems.append("缺 transport-data.js")
    else:
        text = transport_path.read_text(encoding="utf-8", errors="replace")
        if not text.startswith(TRANSPORT_PREFIX):
            data_problems.append("transport-data.js 格式不对")
        else:
            raw = text[len(TRANSPORT_PREFIX) :].strip()
            if raw.endswith(";"):
                raw = raw[:-1].strip()
            try:
                generated = json.loads(raw)
            except json.JSONDecodeError:
                data_problems.append("transport-data.js 不是合法 JSON")
            else:
                if len(generated) != len(events):
                    data_problems.append(
                        f"transport-data.js 条数 {len(generated)} != {len(events)}"
                    )
    if data_problems:
        findings.append(Finding("W12", False, "生成数据不一致：" + "; ".join(data_problems)))
    else:
        findings.append(Finding("W12", True, "search/transport 数据与源一致"))


def check(src: Path, build: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    pages = load_pages(src, findings)
    if not pages:
        return findings
    slugs = check_manifest(src, pages, findings)
    events = check_transport(src, findings)
    scan_secrets(src, findings)
    if build:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "site"
            rc, output = run_build(src, out)
            if rc != 0:
                tail = output.strip().splitlines()[-8:]
                findings.append(
                    Finding("W9", False, "构建失败：" + " | ".join(tail))
                )
            else:
                findings.append(Finding("W9", True, "构建成功"))
                check_generated(out, slugs, events, findings)
    return findings


def print_findings(findings: list[Finding], as_json: bool) -> int:
    failed = [finding for finding in findings if not finding.ok]
    if as_json:
        payload = {
            "ok": not failed,
            "findings": [
                {"gate": finding.gate, "ok": finding.ok, "message": finding.message}
                for finding in findings
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for finding in findings:
            print(f"{'PASS' if finding.ok else 'FAIL'} {finding.gate} {finding.message}")
        print(f"结果：{'PASS' if not failed else 'FAIL'}（{len(failed)} 项失败）")
    return 0 if not failed else 1


# ---------------------------------------------------------------- 负例自测

def write_valid_fixture(root: Path) -> None:
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    base = Path(__file__).resolve().parent
    shutil.copy2(base / "build_site.py", root / "scripts" / "build_site.py")
    shutil.copy2(base / "site.js", root / "scripts" / "site.js")
    (root / MANIFEST).write_text(
        json.dumps(
            {
                "title": "Fixture",
                "pages": [
                    {
                        "slug": "Home",
                        "file": "Home.md",
                        "title": "首页",
                        "group": "首页",
                        "icon": "",
                        "summary": "home",
                        "tags": ["home"],
                    },
                    {
                        "slug": "A",
                        "file": "A.md",
                        "title": "A",
                        "group": "原理",
                        "icon": "",
                        "summary": "a",
                        "tags": ["a"],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "Home.md").write_text("# Home\n\n[[A]]\n", encoding="utf-8")
    (root / "A.md").write_text("# A\n\ntext\n", encoding="utf-8")
    (root / "transport-events.json").write_text(
        json.dumps(
            [
                {
                    "id": "tx-1",
                    "time": "2026-11-03T00:00:00+08:00",
                    "from": "a",
                    "to": "b",
                    "kind": "handoff",
                    "status": "sent",
                    "summary": "x",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def mutate_manifest(root: Path, mutate) -> None:
    path = root / MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def teardown_ok(root: Path, expected_gate: str, build: bool = False) -> bool:
    findings = check(root, build=build)
    failed = {finding.gate for finding in findings if not finding.ok}
    return expected_gate in failed


def self_test() -> int:
    cases: list[tuple[str, str, Callable[[Path], None]]] = []

    def case_dup(root: Path) -> None:
        def mutate(data):
            data["pages"].append(dict(data["pages"][1]))

        mutate_manifest(root, mutate)

    def case_missing_file(root: Path) -> None:
        (root / "A.md").unlink()

    def case_orphan(root: Path) -> None:
        (root / "Orphan.md").write_text("# Orphan\n", encoding="utf-8")

    def case_meta(root: Path) -> None:
        def mutate(data):
            del data["pages"][1]["summary"]

        mutate_manifest(root, mutate)

    def case_link(root: Path) -> None:
        (root / "A.md").write_text("# A\n\n[[Nope]]\n", encoding="utf-8")

    def case_event(root: Path) -> None:
        path = root / "transport-events.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        del data[0]["status"]
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def case_secret(root: Path) -> None:
        path = root / "transport-events.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data[0]["payload"] = "ghp_" + "A" * 36
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def case_groups(root: Path) -> None:
        def mutate(data):
            data["pages"].extend(
                [
                    {
                        "slug": "B",
                        "file": "B.md",
                        "title": "B",
                        "group": "上手",
                        "icon": "",
                        "summary": "b",
                        "tags": ["b"],
                    },
                    {
                        "slug": "C",
                        "file": "C.md",
                        "title": "C",
                        "group": "原理",
                        "icon": "",
                        "summary": "c",
                        "tags": ["c"],
                    },
                ]
            )

        mutate_manifest(root, mutate)
        (root / "B.md").write_text("# B\n", encoding="utf-8")
        (root / "C.md").write_text("# C\n", encoding="utf-8")

    def case_no_site_js(root: Path) -> None:
        (root / "scripts" / "site.js").unlink()

    cases.extend(
        [
            ("W2 duplicate slug", "W2", case_dup),
            ("W3 missing file", "W3", case_missing_file),
            ("W4 orphan page", "W4", case_orphan),
            ("W5 missing metadata", "W5", case_meta),
            ("W6 broken link", "W6", case_link),
            ("W7 bad event", "W7", case_event),
            ("W8 secret", "W8", case_secret),
            ("W11 group not contiguous", "W11", case_groups),
            ("W9 missing site.js", "W9", case_no_site_js),
        ]
    )

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "valid"
        root.mkdir()
        write_valid_fixture(root)
        findings = check(root, build=True)
        bad = [finding for finding in findings if not finding.ok]
        if bad:
            failures.append("valid fixture should pass: " + "; ".join(f.message for f in bad))

    for name, expected, mutate in cases:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case"
            root.mkdir()
            write_valid_fixture(root)
            mutate(root)
            build = expected == "W9"
            try:
                ok = teardown_ok(root, expected, build=build)
            except Exception as exc:  # noqa: BLE001 - self-test must report, not crash
                failures.append(f"{name}: exception {exc}")
                continue
            if not ok:
                failures.append(f"{name}: gate {expected} did not fail")

    # W10/W12 直接测生成物，不依赖构建脚本的变异。
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir)
        (out / "Home.html").write_text("<!doctype html><html></html>", encoding="utf-8")
        (out / "index.html").write_text("x", encoding="utf-8")
        findings: list[Finding] = []
        check_generated(out, ["Home"], [{"id": "tx-1"}], findings)
        failed = {finding.gate for finding in findings if not finding.ok}
        if "W10" not in failed:
            failures.append("W10 generated hooks did not fail")
        if "W12" not in failed:
            failures.append("W12 generated data did not fail")

    if failures:
        for failure in failures:
            print(f"FAIL self-test {failure}")
        print(f"self-test FAIL（{len(failures)} 项）")
        return 1
    print(f"PASS self-test：{len(cases) + 2} 个负例全部按预期判红，正例通过")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=".", help="文档源目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--self-test", action="store_true", help="跑负例自测")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    src = Path(args.src).resolve()
    if not src.is_dir():
        print(f"FAIL 用法：--src 不是目录：{src}", file=sys.stderr)
        return 2
    return print_findings(check(src), args.json)


if __name__ == "__main__":
    sys.exit(main())
