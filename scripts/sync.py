#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


DEFAULT_TARGET = Path.home() / "Documents" / "jianfei-weread"


def refresh_html_data(target: Path) -> dict:
    raw = target / "weread-export" / "weread-raw-data.json"
    html_path = target / "weread-obsidian.html"
    raw_text = raw.read_text(encoding="utf-8").strip()
    if raw_text.startswith("var RAW_DATA = "):
        raw_text = raw_text[len("var RAW_DATA = ") :]
    if raw_text.endswith(";"):
        raw_text = raw_text[:-1]
    html = html_path.read_text(encoding="utf-8")
    start = html.index("var RAW_DATA = ")
    end = html.index("\ninit(RAW_DATA);", start)
    html_path.write_text(html[:start] + "var RAW_DATA = " + raw_text + ";" + html[end:], encoding="utf-8")
    return json.loads(raw_text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync WeRead data into a local dashboard project.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--key", help="Optional one-time WEREAD_API_KEY. Prefer accounts.py for persistence.")
    args = parser.parse_args()

    target = args.target.expanduser().resolve()
    exporter = target / "weread_export_notes.py"
    slides = target / "weread_generate_slides.py"
    if not exporter.exists():
        raise SystemExit(f"Project not installed or missing weread_export_notes.py: {target}")

    env = os.environ.copy()
    if args.key:
        env["WEREAD_API_KEY"] = args.key
    subprocess.run(["python3", str(exporter)], cwd=str(target), check=True, env=env)
    data = refresh_html_data(target)
    if slides.exists():
        subprocess.run(["python3", str(slides)], cwd=str(target), check=True, env=env)

    note_ids = data.get("bookIds", [])
    highlights = sum(len((data.get("notes", {}).get(i, {}) or {}).get("bms", [])) for i in note_ids)
    thoughts = sum(len((data.get("notes", {}).get(i, {}) or {}).get("rvs", [])) for i in note_ids)
    print(json.dumps({"books": len(note_ids), "highlights": highlights, "thoughts": thoughts}, ensure_ascii=False))
    print(f"Dashboard file: {target / 'weread-obsidian.html'}")


if __name__ == "__main__":
    main()
