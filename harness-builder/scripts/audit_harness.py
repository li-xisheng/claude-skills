#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_harness.py — 给一个已有 harness 的仓库做「机械体检」。

把能机械查的东西（行数、漂移、有无）交给脚本，省下模型 context 去做真正需要判断的事
（Goodhart 化、过度显形、过期——这些请对照 references/audit-checklist.md 和
references/judgment-and-taste.md 由人/模型判断）。

用法:
    python audit_harness.py <repo_path> [--json]

只用标准库，跨平台。退出码: 0=无 FAIL, 1=有 FAIL（便于挂进 CI / hook）。
"""
import os
import re
import sys
import json
import argparse

# Windows 控制台默认 GBK，强制 UTF-8 输出，避免 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", "out", ".next", "target",
    "vendor", "__pycache__", ".venv", "venv", "coverage", ".turbo", "bin", "obj",
}
LINE_SOFT = 150
LINE_HARD = 200
# 「应当落 S4/Project Taste、不该写成硬量化目标」的 Goodhart 高风险信号。
# 用宽松匹配：关键词与数字之间允许「必须 / 不得超过」等词。
GOODHART_PATTERNS = [
    (re.compile(r"覆盖率.{0,8}\d{1,3}\s*%|coverage.{0,8}\d{1,3}\s*%?", re.I),
     "覆盖率硬目标（S2 量化指标，Goodhart 高风险——AI 会刷 assert True）"),
    (re.compile(r"(函数|方法|文件|行数|lines?).{0,8}(不超过|不得超过|超过|[<≤]=?|大于|小于).{0,4}\d+\s*行?", re.I),
     "行数/长度硬上限（会被拆函数绕过、可读性反而塌）"),
    (re.compile(r"圈复杂度|cyclomatic", re.I),
     "圈复杂度硬目标（量化指标当目标，易被规避）"),
]


def count_lines(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def find_claude_mds(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        if "CLAUDE.md" in filenames:
            found.append(os.path.join(dirpath, "CLAUDE.md"))
    return sorted(found)


REF_PATTERN = re.compile(r"`([^`\n]+\.[A-Za-z0-9]{1,6})`|\]\(([^)]+\.[A-Za-z0-9]{1,6})\)")


def check_path_drift(md_path, root):
    """从 CLAUDE.md 里抽出引用的相对路径，检查是否还存在（漂移检测）。"""
    text = read_text(md_path)
    base = os.path.dirname(md_path)
    drift = []
    for m in REF_PATTERN.finditer(text):
        ref = m.group(1) or m.group(2)
        if not ref or ref.startswith(("http://", "https://", "#")):
            continue
        ref = ref.split("#")[0].strip()
        if not ref or any(c in ref for c in "*<>|"):
            continue
        # 只校验看起来像仓库内相对路径的引用
        if ref.startswith("/") or ":" in ref:
            continue
        # 跳过「故意提及但本就不该/不一定存在」的引用：.env 系列密钥文件、secrets 目录
        # （它们常被 gitignore、本地不存在；被 CLAUDE.md 引用恰恰是为了叮嘱别碰，不是漂移）
        ref_name = os.path.basename(ref)
        if ref_name.startswith(".env") or "/secrets/" in ("/" + ref + "/"):
            continue
        cand = os.path.normpath(os.path.join(base, ref))
        cand_root = os.path.normpath(os.path.join(root, ref))
        if not (os.path.exists(cand) or os.path.exists(cand_root)):
            drift.append(ref)
    return sorted(set(drift))


def scan_goodhart(md_path):
    text = read_text(md_path)
    hits = []
    for pat, label in GOODHART_PATTERNS:
        if pat.search(text):
            hits.append(label)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = args.repo_path
    if not os.path.isdir(root):
        print("错误: 路径不存在: %s" % root, file=sys.stderr)
        sys.exit(2)

    checks = []  # (level, title, detail)   level in PASS/WARN/FAIL/INFO

    claude_mds = find_claude_mds(root)
    has_root_md = os.path.isfile(os.path.join(root, "CLAUDE.md"))

    # 1. 行数
    if not claude_mds:
        checks.append(("FAIL", "CLAUDE.md 缺失", "仓库里没有任何 CLAUDE.md，harness 第一层未搭"))
    for md in claude_mds:
        rel = os.path.relpath(md, root)
        n = count_lines(md)
        if n > LINE_HARD:
            checks.append(("FAIL", "CLAUDE.md 过长", "`%s` 有 %d 行（>200），Claude 开始忽略指令的概率显著上升，需瘦身/分层" % (rel, n)))
        elif n > LINE_SOFT:
            checks.append(("WARN", "CLAUDE.md 偏长", "`%s` 有 %d 行（>150），逼近上限，建议「删除测试」狠删" % (rel, n)))
        else:
            checks.append(("PASS", "CLAUDE.md 长度健康", "`%s` %d 行" % (rel, n)))

    # 2. 分层
    if has_root_md and len(claude_mds) == 1:
        checks.append(("WARN", "未分层", "只有根 CLAUDE.md，没有子目录 CLAUDE.md。大库应分层：根放指针，子目录放细节"))
    elif len(claude_mds) > 1:
        checks.append(("PASS", "已分层", "存在 %d 个 CLAUDE.md（含子目录）" % len(claude_mds)))

    # 3. 路径漂移
    drift_total = 0
    for md in claude_mds:
        drift = check_path_drift(md, root)
        if drift:
            drift_total += len(drift)
            checks.append(("FAIL", "CLAUDE.md 引用漂移", "`%s` 引用了已不存在的路径: %s" % (os.path.relpath(md, root), ", ".join(drift))))
    if claude_mds and drift_total == 0:
        checks.append(("PASS", "无引用漂移", "CLAUDE.md 里引用的路径都还存在"))

    # 4. Goodhart 信号
    for md in claude_mds:
        hits = scan_goodhart(md)
        for h in hits:
            checks.append(("WARN", "可能的 Goodhart 化规则", "`%s`: %s" % (os.path.relpath(md, root), h)))

    # 5. 权限边界
    settings = os.path.join(root, ".claude", "settings.json")
    if os.path.isfile(settings):
        try:
            data = json.loads(read_text(settings))
        except Exception:
            data = {}
        deny = (data.get("permissions") or {}).get("deny") or []
        if deny:
            checks.append(("PASS", "权限边界", "permissions.deny 有 %d 条" % len(deny)))
        else:
            checks.append(("WARN", "权限边界薄弱", ".claude/settings.json 没有 permissions.deny 规则"))
    else:
        checks.append(("WARN", "无 settings.json", "缺少 .claude/settings.json，权限/忽略规则无法被团队共享"))

    # 6. 地图
    has_map = any(os.path.isfile(os.path.join(root, c)) for c in ("CODEBASE_MAP.md", "codebase-map.md", "MAP.md", "ARCHITECTURE.md"))
    checks.append(("PASS" if has_map else "INFO", "代码库地图", "已有" if has_map else "无（目录不直观时建议补一张）"))

    # 7. MCP 过早
    has_mcp = os.path.isfile(os.path.join(root, ".mcp.json"))
    skills_dir = os.path.join(root, ".claude", "skills")
    has_skills = os.path.isdir(skills_dir) and any(os.path.isdir(os.path.join(skills_dir, d)) for d in os.listdir(skills_dir)) if os.path.isdir(skills_dir) else False
    if has_mcp and not (has_root_md and has_skills):
        checks.append(("WARN", "MCP 可能上早了", "接了 MCP，但 CLAUDE.md/skill 还没打磨好——MCP 是最后一层，基础没搭好接进来的是噪音"))

    # 8. 清单
    has_manifest = os.path.isfile(os.path.join(root, ".claude", "HARNESS.md"))
    checks.append(("PASS" if has_manifest else "INFO", "harness 清单", "已有 .claude/HARNESS.md" if has_manifest else "无（搭建收尾应生成，作为纠偏入口）"))

    # 渲染
    order = {"FAIL": 0, "WARN": 1, "INFO": 2, "PASS": 3}
    checks.sort(key=lambda c: order[c[0]])
    n_fail = sum(1 for c in checks if c[0] == "FAIL")
    n_warn = sum(1 for c in checks if c[0] == "WARN")

    if args.json:
        print(json.dumps([{"level": l, "title": t, "detail": d} for l, t, d in checks], ensure_ascii=False, indent=2))
    else:
        icon = {"FAIL": "🔴", "WARN": "🟡", "INFO": "ℹ️ ", "PASS": "✅"}
        print("# harness 机械体检报告\n")
        print("仓库: `%s`\n" % os.path.abspath(root))
        print("**%d 项 FAIL · %d 项 WARN**（机械可查项；判断类问题请对照 audit-checklist.md 与 judgment-and-taste.md）\n" % (n_fail, n_warn))
        for level, title, detail in checks:
            print("- %s **%s** — %s" % (icon[level], title, detail))
        print("\n> 下一步：把 FAIL / WARN 项整理成分优先级的纠偏报告，逐项「现状→问题→建议→为什么」，审批后落地。")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
