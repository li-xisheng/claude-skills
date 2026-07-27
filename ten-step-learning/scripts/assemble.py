#!/usr/bin/env python3
"""Assemble the ten-step learning HTML: template + fragments -> single file.

Each placeholder {{NAME}} in the template is filled from fragments/NAME.html.
{{TOPIC}} comes from --topic. *_VIZ placeholders default to empty when no
fragment file exists (only steps 1/2/6 and the closing loop need a viz).

Fails loudly on missing fragments or residual placeholders, so a truncated
or partial build can never be delivered silently.

Usage:
  python assemble.py --template <skill>/assets/template.html \
      --fragments <build>/fragments --topic "RAG" --out "RAG-十步学习.html"
"""
import argparse
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, help="path to template.html")
    parser.add_argument("--fragments", required=True, help="directory of NAME.html fragments")
    parser.add_argument("--topic", required=True, help="learning topic, fills {{TOPIC}}")
    parser.add_argument("--out", required=True, help="output HTML path")
    args = parser.parse_args()

    template_path = Path(args.template)
    fragments_dir = Path(args.fragments)
    if not template_path.is_file():
        sys.exit(f"ERROR: template not found: {template_path}")
    if not fragments_dir.is_dir():
        sys.exit(f"ERROR: fragments directory not found: {fragments_dir}")

    html = template_path.read_text(encoding="utf-8")
    names = sorted(set(PLACEHOLDER_RE.findall(html)))

    mapping = {}
    missing = []
    for name in names:
        if name == "TOPIC":
            mapping[name] = args.topic
            continue
        fragment = fragments_dir / f"{name}.html"
        if fragment.is_file():
            mapping[name] = fragment.read_text(encoding="utf-8").strip()
        elif name.endswith("_VIZ"):
            mapping[name] = ""  # viz slots are optional by design
        else:
            missing.append(name)

    if missing:
        sys.exit(
            "ERROR: missing fragment files for: "
            + ", ".join(missing)
            + f"\nWrite them into {fragments_dir} and rerun."
        )

    # Single-pass substitution: fragment content is never rescanned, so a
    # literal "{{...}}" inside a fragment surfaces in the residual check below.
    result = PLACEHOLDER_RE.sub(lambda m: mapping[m.group(1)], html)

    residual = sorted(set(PLACEHOLDER_RE.findall(result)))
    if residual:
        sys.exit(
            "ERROR: residual placeholders after assembly (a fragment probably "
            "contains {{...}} literally): " + ", ".join(residual)
        )

    unused = sorted(
        p.stem for p in fragments_dir.glob("*.html") if p.stem not in mapping
    )
    if unused:
        print(f"WARN: unused fragments (not in template): {', '.join(unused)}")

    out_path = Path(args.out)
    out_path.write_text(result, encoding="utf-8")
    print(f"OK: {out_path} ({len(result):,} chars, {len(names)} placeholders filled)")


if __name__ == "__main__":
    main()
