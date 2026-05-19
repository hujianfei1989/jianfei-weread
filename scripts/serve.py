#!/usr/bin/env python3
from __future__ import annotations

import argparse
import functools
import http.server
import subprocess
from pathlib import Path


DEFAULT_TARGET = Path.home() / "Documents" / "jianfei-weread"


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a local WeRead dashboard project.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--port", type=int, default=18767)
    args = parser.parse_args()

    target = args.target.expanduser().resolve()
    server_script = target / "weread_sync_server.py"
    html = target / "weread-obsidian.html"
    if not server_script.exists() or not html.exists():
        raise SystemExit(f"Project not installed or incomplete: {target}")

    api = subprocess.Popen(["python3", str(server_script)], cwd=str(target))
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(target))
    url = f"http://127.0.0.1:{args.port}/weread-obsidian.html"
    print("Sync API: http://127.0.0.1:18766")
    print(f"Dashboard: {url}")
    try:
        http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()
    finally:
        api.terminate()


if __name__ == "__main__":
    main()
