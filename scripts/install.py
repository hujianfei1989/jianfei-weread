#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "project-template"
DEFAULT_TARGET = Path.home() / "Documents" / "jianfei-weread"


def copy_tree(src: Path, dst: Path, force: bool) -> None:
    if dst.exists() and any(dst.iterdir()) and not force:
        raise SystemExit(f"Target already exists and is not empty: {dst}\nUse --force to overwrite template files.")
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name == "__pycache__":
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists() and force:
                shutil.rmtree(target)
            shutil.copytree(item, target, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(item, target)


def replace_placeholders(root: Path, title: str, keyword: str) -> None:
    replacements = {
        "__APP_TITLE__": title,
        "__SPECIAL_KEYWORD__": keyword,
    }
    for path in root.rglob("*"):
        if path.is_dir() or path.suffix not in {".html", ".py", ".sh", ".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


def write_project_gitignore(root: Path) -> None:
    gitignore = root / ".gitignore"
    if gitignore.exists():
        return
    gitignore.write_text(
        "\n".join(
            [
                ".weread-accounts.json",
                "weread-export/",
                "__pycache__/",
                "*.pyc",
                "*.key",
                "*.token",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Install a clean local WeRead dashboard project.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--title", default="我的微信读书")
    parser.add_argument("--keyword", default="专题")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    target = args.target.expanduser().resolve()
    copy_tree(TEMPLATE, target, args.force)
    replace_placeholders(target, args.title, args.keyword)
    write_project_gitignore(target)
    for script in ["start_weread_sync_server.sh", "weread_accounts.py", "weread_sync_server.py"]:
        path = target / script
        if path.exists():
            os.chmod(path, 0o700)
    print(f"Installed jianfei-weread project: {target}")
    print(f"Dashboard file: {target / 'weread-obsidian.html'}")
    print("Next: python3 scripts/accounts.py --target <project> set default")


if __name__ == "__main__":
    main()
