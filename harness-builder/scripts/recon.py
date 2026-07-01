#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recon.py — 给一个代码仓库做侦察，输出一份结构化报告。

harness 的 agentic search 严重依赖「一个好的起点 context」。这个脚本就是用极低的成本
（不烧模型 context）把仓库的现状摸清楚，作为搭建 / 纠偏方案的事实依据。

用法:
    python recon.py <repo_path> [--json]

只用标准库，跨平台（Windows / macOS / Linux）。不会读取文件全文，只统计行数、扫描结构，
因此在百万行级仓库上也能秒级返回。
"""
import os
import sys
import json
import argparse

# Windows 控制台默认 GBK，强制 UTF-8 输出，避免 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "dist", "build", "out", ".next",
    ".nuxt", "target", "vendor", "__pycache__", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", ".idea", ".vscode", "coverage", ".turbo", ".cache",
    "bin", "obj", ".gradle", "Pods", ".terraform", "bower_components",
}
# 这些目录通常是「生成物 / 构建产物 / 第三方」，纠偏时应建议加入忽略规则
GENERATED_HINT_DIRS = {
    "node_modules", "dist", "build", "out", ".next", "target", "vendor",
    "coverage", "__pycache__", ".turbo", "generated", "gen",
}
LANG_EXT = {
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".py": "Python", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".c": "C", ".h": "C/C++ header",
    ".cc": "C++", ".cpp": "C++", ".hpp": "C++ header", ".cs": "C#",
    ".php": "PHP", ".rb": "Ruby", ".swift": "Swift", ".m": "Objective-C",
    ".scala": "Scala", ".dart": "Dart", ".vue": "Vue", ".svelte": "Svelte",
    ".sql": "SQL", ".sh": "Shell", ".lua": "Lua", ".ex": "Elixir",
}
# 符号歧义高、最该上 LSP 的语言
HIGH_AMBIGUITY_LANGS = {"C", "C++", "C/C++ header", "C++ header", "Java", "PHP"}
MONOREPO_HINTS = [
    "pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json",
    "go.work", "Cargo.toml(workspace)",
]


def count_lines(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def walk_repo(root):
    langs = {}          # lang -> [files, lines]
    total_files = 0
    total_lines = 0
    top_dirs = []
    generated_present = []
    package_jsons = 0
    claude_mds = []     # (relpath, lines)
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if rel == ".":
            top_dirs = sorted([d for d in dirnames if not d.startswith(".")])
            generated_present = sorted(set(dirnames) & GENERATED_HINT_DIRS)
        # 记录命中的生成目录（在被裁剪前），供忽略建议
        for d in list(dirnames):
            if d in GENERATED_HINT_DIRS and os.path.join(rel, d) not in generated_present:
                generated_present.append(os.path.join(rel, d))
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            if fn == "CLAUDE.md":
                claude_mds.append((os.path.relpath(fp, root), count_lines(fp)))
            if fn == "package.json":
                package_jsons += 1
            ext = os.path.splitext(fn)[1].lower()
            lang = LANG_EXT.get(ext)
            if lang:
                lines = count_lines(fp)
                total_files += 1
                total_lines += lines
                entry = langs.setdefault(lang, [0, 0])
                entry[0] += 1
                entry[1] += lines
    return {
        "total_source_files": total_files,
        "total_source_lines": total_lines,
        "languages": langs,
        "top_dirs": top_dirs,
        "generated_present": sorted(set(generated_present)),
        "package_jsons": package_jsons,
        "claude_mds": sorted(claude_mds),
    }


def detect_monorepo(root, scan):
    signals = []
    for hint in MONOREPO_HINTS:
        name = hint.split("(")[0]
        if os.path.exists(os.path.join(root, name)):
            signals.append(name)
    if scan["package_jsons"] > 1:
        signals.append("multiple package.json (%d)" % scan["package_jsons"])
    if "services" in scan["top_dirs"] or "packages" in scan["top_dirs"] or "apps" in scan["top_dirs"]:
        signals.append("workspace-style top dir (services/packages/apps)")
    return signals


def detect_harness(root):
    claude_dir = os.path.join(root, ".claude")
    settings = os.path.join(claude_dir, "settings.json")
    settings_local = os.path.join(claude_dir, "settings.local.json")
    skills_dir = os.path.join(claude_dir, "skills")
    h = {
        "has_git": os.path.isdir(os.path.join(root, ".git")),
        "has_claude_dir": os.path.isdir(claude_dir),
        "has_settings": os.path.isfile(settings),
        "has_settings_local": os.path.isfile(settings_local),
        "has_harness_manifest": os.path.isfile(os.path.join(claude_dir, "HARNESS.md")),
        "skills": [],
        "permissions_deny": [],
        "has_hooks": False,
        "has_mcp": os.path.isfile(os.path.join(root, ".mcp.json")),
        "codebase_map": None,
    }
    if os.path.isdir(skills_dir):
        h["skills"] = sorted(
            d for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))
        )
    for sf in (settings, settings_local):
        if os.path.isfile(sf):
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                perms = (data.get("permissions") or {}).get("deny") or []
                h["permissions_deny"].extend(perms)
                if data.get("hooks"):
                    h["has_hooks"] = True
                if data.get("mcpServers") or data.get("enabledMcpjsonServers"):
                    h["has_mcp"] = True
            except Exception:
                pass
    for cand in ("CODEBASE_MAP.md", "codebase-map.md", "MAP.md", "ARCHITECTURE.md"):
        if os.path.isfile(os.path.join(root, cand)):
            h["codebase_map"] = cand
            break
    return h


def render(root, scan, monorepo, harness):
    L = []
    L.append("# 仓库侦察报告 (harness recon)")
    L.append("")
    L.append("- 路径: `%s`" % os.path.abspath(root))
    L.append("- Git 仓库: %s" % ("✅ 是" if harness["has_git"] else "❌ 否（Claude Code 假设用 Git，非 Git 需额外配置）"))
    L.append("- 源码文件: %d 个，约 %d 行" % (scan["total_source_files"], scan["total_source_lines"]))
    size = scan["total_source_lines"]
    bucket = "小型 (<2万行)" if size < 20000 else "中型 (2万–20万行)" if size < 200000 else "大型 (>20万行，agentic search 起点尤其重要)"
    L.append("- 规模判断: **%s**" % bucket)
    L.append("- Monorepo 信号: %s" % (", ".join(monorepo) if monorepo else "无（看起来是单体仓库）"))
    L.append("")

    L.append("## 语言构成（按行数）")
    langs = sorted(scan["languages"].items(), key=lambda kv: -kv[1][1])
    high_amb = [l for l, _ in langs if l in HIGH_AMBIGUITY_LANGS]
    if langs:
        for lang, (files, lines) in langs:
            flag = "  ⚠️ 符号歧义高，建议上 LSP" if lang in HIGH_AMBIGUITY_LANGS else ""
            L.append("- %s: %d 文件 / %d 行%s" % (lang, files, lines, flag))
    else:
        L.append("- （未识别到常见源码语言）")
    if high_amb:
        L.append("")
        L.append("> 检测到高符号歧义语言（%s）——LSP 是这类仓库「最高价值的投资之一」。" % ", ".join(sorted(set(high_amb))))
    L.append("")

    L.append("## 顶层目录")
    L.append(", ".join("`%s`" % d for d in scan["top_dirs"]) or "（无）")
    L.append("")

    L.append("## 已有的 CLAUDE.md")
    if scan["claude_mds"]:
        for rel, lines in scan["claude_mds"]:
            flag = "  🔴 超过 200 行，需瘦身/分层" if lines > 200 else "  🟡 偏长" if lines > 150 else "  ✅"
            L.append("- `%s` — %d 行%s" % (rel, lines, flag))
    else:
        L.append("- ❌ 没有任何 CLAUDE.md —— 这是搭建的第一层")
    L.append("")

    L.append("## 已有 harness 设施")
    L.append("- `.claude/` 目录: %s" % ("✅" if harness["has_claude_dir"] else "❌"))
    L.append("- `.claude/settings.json`: %s" % ("✅" if harness["has_settings"] else "❌"))
    L.append("- permissions.deny 规则: %s" % (("✅ %d 条" % len(harness["permissions_deny"])) if harness["permissions_deny"] else "❌ 无"))
    L.append("- Hooks: %s" % ("✅ 已配置" if harness["has_hooks"] else "❌ 无"))
    L.append("- Skills: %s" % ((", ".join(harness["skills"])) if harness["skills"] else "❌ 无"))
    L.append("- MCP: %s" % ("✅ 已接入" if harness["has_mcp"] else "—（无；提醒：MCP 应最后才上）"))
    L.append("- 代码库地图: %s" % (("✅ `%s`" % harness["codebase_map"]) if harness["codebase_map"] else "❌ 无"))
    L.append("- harness 清单 `.claude/HARNESS.md`: %s" % ("✅" if harness["has_harness_manifest"] else "❌ 无（搭建收尾时生成）"))
    L.append("")

    if scan["generated_present"]:
        L.append("## 建议忽略的生成/构建/第三方目录")
        L.append(", ".join("`%s`" % d for d in scan["generated_present"]))
        L.append("")

    L.append("## 起点建议（最高 ROI 三件事）")
    L.append("1. CLAUDE.md 砍到 200 行以内 + 分层")
    L.append("2. 在子目录启动 Claude（而非仓库根）")
    L.append("3. %s" % ("装 LSP（检测到高歧义语言）" if high_amb else "按需装 LSP"))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非 markdown")
    args = ap.parse_args()
    root = args.repo_path
    if not os.path.isdir(root):
        print("错误: 路径不存在或不是目录: %s" % root, file=sys.stderr)
        sys.exit(1)
    scan = walk_repo(root)
    monorepo = detect_monorepo(root, scan)
    harness = detect_harness(root)
    if args.json:
        print(json.dumps({"scan": scan, "monorepo": monorepo, "harness": harness}, ensure_ascii=False, indent=2))
    else:
        print(render(root, scan, monorepo, harness))


if __name__ == "__main__":
    main()
