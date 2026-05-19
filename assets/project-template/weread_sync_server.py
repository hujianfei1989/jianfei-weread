#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
HTML = BASE / "weread-obsidian.html"
EXPORT = BASE / "weread_export_notes.py"
RAW = BASE / "weread-export" / "weread-raw-data.json"
SLIDE_GEN = BASE / "weread_generate_slides.py"
sys.path.insert(0, str(BASE))
from weread_accounts import active_key, delete_account, public_accounts, set_account, switch_account  # noqa: E402


def refresh_html_data():
    raw_text = RAW.read_text(encoding="utf-8").strip()
    if raw_text.startswith("var RAW_DATA = "):
        raw_text = raw_text[len("var RAW_DATA = "):]
    if raw_text.endswith(";"):
        raw_text = raw_text[:-1]
    html = HTML.read_text(encoding="utf-8")
    start = html.index("var RAW_DATA = ")
    end = html.index("\ninit(RAW_DATA);", start)
    updated = html[:start] + "var RAW_DATA = " + raw_text + ";" + html[end:]
    HTML.write_text(updated, encoding="utf-8")
    return json.loads(raw_text)


def run_sync():
    key = os.environ.get("WEREAD_API_KEY") or active_key()
    if not key:
        raise RuntimeError("WEREAD_API_KEY is not set")
    env = os.environ.copy()
    env["WEREAD_API_KEY"] = key
    subprocess.run(["python3", str(EXPORT)], cwd=str(BASE), check=True, env=env)
    data = refresh_html_data()
    if SLIDE_GEN.exists():
        subprocess.run(["python3", str(SLIDE_GEN)], cwd=str(BASE), check=True)
    highlights = sum(len((data.get("notes", {}).get(i, {}) or {}).get("bms", [])) for i in data.get("bookIds", []))
    thoughts = sum(len((data.get("notes", {}).get(i, {}) or {}).get("rvs", [])) for i in data.get("bookIds", []))
    return {"ok": True, "books": len(data.get("bookIds", [])), "highlights": highlights, "thoughts": thoughts}


class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path != "/sync":
            if self.path == "/accounts":
                try:
                    payload = self.read_json_body()
                    name = str(payload.get("name", "")).strip()
                    key = str(payload.get("api_key", "")).strip()
                    if not name:
                        raise ValueError("账号名不能为空")
                    if not key:
                        raise ValueError("API key 不能为空")
                    if not key.startswith("wrk-"):
                        raise ValueError("API key 格式看起来不正确，应以 wrk- 开头")
                    set_account(name, key)
                    self.send_json(200, {"ok": True, **public_accounts()})
                except Exception as exc:
                    self.send_json(400, {"ok": False, "error": str(exc)})
                return
            if self.path.startswith("/switch-account/"):
                try:
                    name = urllib.parse.unquote(self.path.split("/switch-account/", 1)[1])
                    switch_account(name)
                    self.send_json(200, {"ok": True, **public_accounts()})
                except Exception as exc:
                    self.send_json(400, {"ok": False, "error": str(exc)})
                return
            if self.path.startswith("/delete-account/"):
                try:
                    name = urllib.parse.unquote(self.path.split("/delete-account/", 1)[1])
                    delete_account(name)
                    self.send_json(200, {"ok": True, **public_accounts()})
                except Exception as exc:
                    self.send_json(400, {"ok": False, "error": str(exc)})
                return
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        try:
            self.send_json(200, run_sync())
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})

    def do_GET(self):
        if self.path == "/accounts":
            self.send_json(200, {"ok": True, **public_accounts()})
        else:
            self.send_json(404, {"ok": False, "error": "not found"})

    def read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 18766), Handler)
    print("WeRead sync server: http://127.0.0.1:18766")
    server.serve_forever()
