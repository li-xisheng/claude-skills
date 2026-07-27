#!/usr/bin/env python3
"""Lint goal-engineer outputs before delivery.

Usage: lint_goal.py [--mode goal|brief] <file> [<file> ...]

Deliverable types:
- "goal"  — a 7-field /goal command (light tier)
- "brief" — a full task brief (heavy tier; pasted after typing `/goal `)

Detection is structural (not size-based): a brief must contain PROGRESS.md /
BLOCKED.md / 任务 0 markers; a goal starts with a /goal line and carries the
field labels. Pass --mode to override when a file is ambiguous.

Adapted from qiaomu-goal-meta-skill's lint_goal_command.py (向阳乔木),
extended with brief-mode checks from leader.skill (卡兹克).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BRIEF_CHAR_LIMIT = 4000

GOAL_MARKER_GROUPS = [
    ("verification", [r"Verification[:：]", r"验证[:：]"]),
    ("constraints", [r"Constraints[:：]", r"约束[:：]"]),
    ("boundaries", [r"Boundaries[:：]", r"边界[:：]"]),
    ("iteration policy", [r"Iteration policy[:：]", r"迭代策略[:：]"]),
    ("stop when", [r"Stop when[:：]", r"完成条件[:：]", r"停止条件[:：]"]),
    ("pause if", [r"Pause if[:：]", r"暂停条件[:：]", r"阻塞条件[:：]"]),
]

BRIEF_STRUCTURE_MARKERS = [r"PROGRESS\.md", r"BLOCKED\.md", r"任务\s*0", r"Task\s*0"]

BRIEF_REQUIRED_MARKERS = [
    ("progress log", [r"PROGRESS\.md"]),
    ("blocked list", [r"BLOCKED\.md"]),
    ("task zero", [r"任务\s*0", r"Task\s*0"]),
    ("completion section", [r"完成条件", r"Stop when"]),
]

# Applies to BOTH tiers: the executor has nobody to ask mid-run.
FORBIDDEN_ASK_PATTERNS = [
    (r"来找我", "must not tell the executor to come ask — nobody is there"),
    (r"随时问我", "must not tell the executor to come ask — nobody is there"),
    (r"联系我", "must not tell the executor to contact anyone mid-run"),
]

# Hard placeholders: case-sensitive TODO/TBD so the anti-cheat callout
# "(skip/todo)" required in every brief is not a false positive.
PLACEHOLDER_HARD_PATTERNS = [
    r"\bTBD\b",
    r"\bTODO\b",
    r"待补充",
    r"待定",
]

# Soft placeholders (warnings only): brackets legitimately appear in markdown
# links, regexes, generics — flag but do not fail.
PLACEHOLDER_SOFT_PATTERNS = [
    r"\[[^\]]+\](?!\()",  # [X] not followed by ( — markdown links exempt
    r"<[A-Za-z][^>]*>",
]

VERIFICATION_EVIDENCE_PATTERNS = [
    r"\b(run|start|open|test|build|lint|typecheck|verify|inspect|capture|screenshot|log|artifact|file|url|api|simulator|browser|local)\b",
    r"(运行|启动|打开|测试|构建|检查|验证|读取|截图|日志|产物|文件|链接|接口|API|模拟器|浏览器|本地|证据)",
]

DANGEROUS_VAGUE_PATTERNS = [
    r"make sure it works",
    r"edit anything",
    r"change whatever",
    r"keep trying",
    r"until it (looks|seems|feels) good",
    r"随便改",
    r"随意修改",
    r"一直尝试",
    r"直到满意",
    r"看起来不错就行",
    r"感觉可以",
]

# Exploratory / discovery-only briefs may legitimately lack a red→green step.
REVERSE_VERIFICATION_EXEMPT = [r"免反向验证", r"无静默检查", r"可承受损失", r"学习目标", r"结论条数"]


def detect_mode(text: str) -> str | None:
    if any(re.search(p, text) for p in BRIEF_STRUCTURE_MARKERS):
        return "brief"
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    field_hits = sum(
        1 for _, patterns in GOAL_MARKER_GROUPS if any(re.search(p, text) for p in patterns)
    )
    if first_line.startswith("/goal") and field_hits >= 2:
        return "goal"
    return None


def find_marker_content(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(rf"^{pattern}\s*(.+)$", text, flags=re.MULTILINE | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def lint_common(text: str, source: str, warnings: list[str]) -> list[str]:
    errors: list[str] = []
    if re.search(r"^\s*/目标\b", text, flags=re.MULTILINE):
        errors.append(f"{source}: use `/goal`, not `/目标`, as the executable command")
    for pattern, reason in FORBIDDEN_ASK_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"{source}: {reason} (matched `{pattern}`)")
    for pattern in PLACEHOLDER_HARD_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"{source}: unresolved placeholder matched `{pattern}`")
    for pattern in PLACEHOLDER_SOFT_PATTERNS:
        if re.search(pattern, text):
            warnings.append(
                f"{source}: possible placeholder matched `{pattern}` — fine if it is a "
                "path, regex, or generic type; fix if it is an unfilled blank"
            )
    for pattern in DANGEROUS_VAGUE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"{source}: dangerous vague instruction matched `{pattern}`")
    return errors


def lint_goal(text: str, source: str, warnings: list[str]) -> list[str]:
    errors = lint_common(text, source, warnings)

    if "/goal" not in text:
        errors.append(f"{source}: missing `/goal` command line")
    else:
        goal_line = next(
            (line.strip() for line in text.splitlines() if line.strip().startswith("/goal")), ""
        )
        if len(goal_line.removeprefix("/goal").strip()) < 20:
            errors.append(f"{source}: /goal outcome is too short to be actionable")

    for name, patterns in GOAL_MARKER_GROUPS:
        if not any(re.search(pattern, text) for pattern in patterns):
            readable = " or ".join(p.replace(r"[:：]", ":") for p in patterns)
            errors.append(f"{source}: missing required marker `{readable}`")

    verification = find_marker_content(text, GOAL_MARKER_GROUPS[0][1])
    if verification and not any(
        re.search(p, verification, flags=re.IGNORECASE) for p in VERIFICATION_EVIDENCE_PATTERNS
    ):
        errors.append(
            f"{source}: verification should name concrete evidence such as commands, "
            "logs, screenshots, files, APIs, browser/simulator checks, or artifacts"
        )

    for name, patterns in GOAL_MARKER_GROUPS:
        content = find_marker_content(text, patterns)
        if content and len(content) < 12:
            errors.append(f"{source}: `{name}` content is too thin")

    return errors


def lint_brief(text: str, source: str, warnings: list[str]) -> list[str]:
    errors = lint_common(text, source, warnings)

    if len(text) > BRIEF_CHAR_LIMIT:
        errors.append(
            f"{source}: brief is {len(text)} chars, over the {BRIEF_CHAR_LIMIT}-char /goal "
            "limit — it will not paste; split the work instead"
        )

    for name, patterns in BRIEF_REQUIRED_MARKERS:
        if not any(re.search(pattern, text) for pattern in patterns):
            readable = " or ".join(patterns)
            errors.append(f"{source}: missing {name} (`{readable}`)")

    has_reverse = re.search(
        r"(反向验证|故意.{0,8}(失败|弄坏)|red.{0,20}green)", text, flags=re.IGNORECASE
    )
    exempt = any(re.search(p, text) for p in REVERSE_VERIFICATION_EXEMPT)
    if not has_reverse and not exempt:
        warnings.append(
            f"{source}: no negative-verification step found — required for any check that "
            "could silently pass; exploratory/discovery-only briefs may skip it but should "
            "say why (e.g. 「无静默检查,免反向验证」)"
        )

    return errors


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = argv[1:]
    forced_mode: str | None = None
    if args[:1] == ["--mode"]:
        if len(args) < 3 or args[1] not in ("goal", "brief"):
            print("Usage: lint_goal.py [--mode goal|brief] <file> [<file> ...]", file=sys.stderr)
            return 2
        forced_mode, args = args[1], args[2:]

    if not args:
        print("Usage: lint_goal.py [--mode goal|brief] <file> [<file> ...]", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    warnings: list[str] = []
    for raw_path in args:
        path = Path(raw_path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            all_errors.append(f"{path}: cannot read file: {exc}")
            continue
        mode = forced_mode or detect_mode(text)
        if mode is None:
            all_errors.append(
                f"{path}: cannot tell goal from brief (no /goal-with-fields shape, no "
                "PROGRESS.md/BLOCKED.md/任务 0 markers) — rerun with --mode goal|brief"
            )
            continue
        linter = lint_goal if mode == "goal" else lint_brief
        all_errors.extend(linter(text, f"{path} [{mode}]", warnings))

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        return 1

    print("Goal lint passed." + (f" ({len(warnings)} warning(s))" if warnings else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
