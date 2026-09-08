"""skill-eval workflow の実行結果を skill-creator 形式のディレクトリへ展開する後処理。

入力: Workflow の状態ファイル
      ~/.claude/projects/<project>/<session>/workflows/wf_<runId>.json
      ("result" キーに workflow の戻り値、"runId" に実行 ID が入っている)

出力: <iteration_dir>/eval-<id>-<name>/eval_metadata.json
      <iteration_dir>/eval-<id>-<name>/<arm>/run-<k>/outputs/answer.md
      <iteration_dir>/eval-<id>-<name>/<arm>/run-<k>/grading.json   (評分が取れた run のみ)
      <iteration_dir>/eval-<id>-<name>/<arm>/run-<k>/timing.json    (トランスクリプトが見つかった run のみ)

使い方:
  python skill-eval-postprocess.py <wf_state.json> [--transcripts <dir>]
  --transcripts 省略時は <session>/subagents/workflows/<runId>/ を自動で探す。

終了コード: 0 = 全 run に grading.json を書けた / 1 = 一部欠落 / 2 = 予検で中止された実行
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

MARKER_RE = re.compile(r"^\[eval-job (?P<tag>[A-Za-z0-9_.-]+)#(?P<job>\d+)\] \[role: (?P<role>executor|grader)\]")
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def load_result(state_path: Path) -> tuple[dict, str | None]:
    """状態ファイルから workflow の戻り値と runId を取り出す。"""
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    result = payload.get("result", payload) if isinstance(payload, dict) else payload
    if isinstance(result, str):
        result = json.loads(result)
    if not isinstance(result, dict):
        raise SystemExit(f"想定外の result 形式: {type(result).__name__}（skill-eval workflow の状態ファイルか確認）")
    run_id = payload.get("runId") if isinstance(payload, dict) else None
    return result, run_id


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_eval_metadata(iteration_dir: Path, evals: list[dict]) -> None:
    for e in evals:
        eval_dir = iteration_dir / f"eval-{e['eval_id']}-{e['eval_name']}"
        write_json(eval_dir / "eval_metadata.json", {
            "eval_id": e["eval_id"],
            "eval_name": e["eval_name"],
            "prompt": e["prompt"],
            "assertions": e["assertions"],
        })


def write_run(run: dict, iteration_dir: Path) -> bool:
    """answer.md と grading.json を書く。grading.json を書けたら True。"""
    run_dir = Path(run["run_dir"])
    outputs = run_dir / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    rel = run_dir.relative_to(iteration_dir)

    if run.get("answer"):
        (outputs / "answer.md").write_text(run["answer"].rstrip() + "\n", encoding="utf-8")
    if run.get("exec_error"):
        (outputs / "EXEC_FAILED.txt").write_text(run["exec_error"] + "\n", encoding="utf-8")

    grading = run.get("grading")
    if not grading or not run.get("summary"):
        print(f"WARN  grading 缺失 -> {rel}  ({run.get('exec_error') or run.get('grade_error') or '原因不明'})")
        return False

    write_json(run_dir / "grading.json", {
        "expectations": grading.get("expectations", []),
        "summary": run["summary"],
        "claims": grading.get("claims", []),
        "eval_feedback": grading.get("eval_feedback", {}),
        "quality_note": grading.get("quality_note", ""),
    })
    note = f"  （{run['grade_error']}）" if run.get("grade_error") else ""
    print(f"grading.json -> {rel}  {run['summary']['passed']}/{run['summary']['total']}{note}")
    return True


def user_prompt(entry: dict) -> str | None:
    """user 発話の本文を文字列で返す（content が block 配列の場合は text を連結）。"""
    if entry.get("type") != "user":
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return None


def scan_transcript(jsonl: Path) -> tuple[re.Match | None, float, int]:
    """(marker マッチ, 所要秒, 消費トークン) を返す。marker が見つからなければ None。"""
    match = None
    first_ts = last_ts = None
    tokens = 0
    with jsonl.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("timestamp")
            if ts:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                first_ts = first_ts or t
                last_ts = t
            if match is None:
                prompt = user_prompt(entry)
                if prompt:
                    match = MARKER_RE.match(prompt)
            usage = (entry.get("message") or {}).get("usage") or {}
            tokens += sum(usage.get(k, 0) for k in USAGE_KEYS)
    duration = (last_ts - first_ts).total_seconds() if first_ts and last_ts else 0.0
    return match, duration, tokens


def collect_timing(transcripts: Path, tag: str) -> dict[int, dict[str, tuple[float, int]]]:
    """job_id -> {role: (秒, トークン)}"""
    timing: dict[int, dict[str, tuple[float, int]]] = {}
    for jsonl in sorted(transcripts.glob("agent-*.jsonl")):
        match, duration, tokens = scan_transcript(jsonl)
        if not match or match.group("tag") != tag:
            continue
        job = int(match.group("job"))
        timing.setdefault(job, {})[match.group("role")] = (duration, tokens)
    return timing


def write_timing(runs: list[dict], timing: dict, iteration_dir: Path) -> None:
    for run in runs:
        parts = timing.get(run["job_id"])
        if not parts:
            continue
        ex = parts.get("executor", (0.0, 0))
        gr = parts.get("grader", (0.0, 0))
        run_dir = Path(run["run_dir"])
        write_json(run_dir / "timing.json", {
            "total_tokens": ex[1],
            "duration_ms": int(ex[0] * 1000),
            "total_duration_seconds": round(ex[0], 1),
            "executor_duration_seconds": round(ex[0], 1),
            "grader_duration_seconds": round(gr[0], 1),
            "grader_tokens": gr[1],
        })
        print(f"timing.json  -> {run_dir.relative_to(iteration_dir)}  {round(ex[0], 1)}s  {ex[1]} tok")


def print_totals(runs: list[dict]) -> None:
    print("\n各臂合计（仅计有效评分的 run）:")
    for arm in dict.fromkeys(r["configuration"] for r in runs):
        rs = [r for r in runs if r["configuration"] == arm]
        ok = [r for r in rs if r.get("summary")]
        passed = sum(r["summary"]["passed"] for r in ok)
        total = sum(r["summary"]["total"] for r in ok)
        print(f"  {arm:<14} {passed}/{total}  ({len(ok)}/{len(rs)} run 有效)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("state", type=Path, help="Workflow 状態ファイル wf_<runId>.json")
    parser.add_argument("--transcripts", type=Path, default=None, help="agent-*.jsonl のあるディレクトリ")
    ns = parser.parse_args()

    result, run_id = load_result(ns.state)
    if result.get("aborted"):
        print(f"ABORT {result.get('reason')}")
        for c in (result.get("preflight") or {}).get("checks", []):
            print(f"  [{'ok' if c.get('ok') else 'NG'}] {c.get('condition')}  -- {c.get('evidence')}")
        return 2

    iteration_dir = Path(result["iteration_dir"])
    iteration_dir.mkdir(parents=True, exist_ok=True)
    write_eval_metadata(iteration_dir, result.get("evals", []))
    runs = result.get("runs", [])
    written = [write_run(r, iteration_dir) for r in runs]

    transcripts = ns.transcripts or (ns.state.parent.parent / "subagents" / "workflows" / (run_id or ""))
    if run_id and transcripts.is_dir():
        write_timing(runs, collect_timing(transcripts, result["tag"]), iteration_dir)
    else:
        print(f"WARN  トランスクリプト未検出、timing.json は書かない: {transcripts}")

    print_totals(runs)
    missing = len(written) - sum(written)
    if missing:
        print(f"\nWARN  {missing} 个 run 没有 grading.json，aggregate 时会被排除")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
