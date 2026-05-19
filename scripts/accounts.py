#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


DEFAULT_TARGET = Path.home() / "Documents" / "jianfei-weread"


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage local WeRead API-key accounts for a dashboard project.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to weread_accounts.py")
    ns = parser.parse_args()

    target = ns.target.expanduser().resolve()
    helper = target / "weread_accounts.py"
    if not helper.exists():
        raise SystemExit(f"Project not installed or missing weread_accounts.py: {target}")
    if not ns.args:
        raise SystemExit("Pass an account command, for example: set default, list, switch default")
    subprocess.run(["python3", str(helper), *ns.args], cwd=str(target), check=True)


if __name__ == "__main__":
    main()
