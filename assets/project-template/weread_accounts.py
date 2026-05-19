#!/usr/bin/env python3
import argparse
import getpass
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE / ".weread-accounts.json"


def load_config():
    if not CONFIG.exists():
        return {"active": "", "accounts": {}}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def save_config(config):
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(CONFIG, 0o600)


def set_account(name, key):
    config = load_config()
    config.setdefault("accounts", {})[name] = {"api_key": key}
    config["active"] = name
    save_config(config)


def switch_account(name):
    config = load_config()
    if name not in config.get("accounts", {}):
        raise SystemExit(f"账号不存在: {name}")
    config["active"] = name
    save_config(config)


def delete_account(name):
    config = load_config()
    accounts = config.setdefault("accounts", {})
    if name not in accounts:
        raise SystemExit(f"账号不存在: {name}")
    del accounts[name]
    if config.get("active") == name:
        config["active"] = sorted(accounts.keys())[0] if accounts else ""
    save_config(config)


def active_key():
    config = load_config()
    active = config.get("active")
    if not active:
        return ""
    return config.get("accounts", {}).get(active, {}).get("api_key", "")


def public_accounts():
    config = load_config()
    return {
        "active": config.get("active", ""),
        "accounts": sorted(config.get("accounts", {}).keys()),
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("set")
    add.add_argument("name")
    add.add_argument("--key")
    sw = sub.add_parser("switch")
    sw.add_argument("name")
    delete = sub.add_parser("delete")
    delete.add_argument("name")
    sub.add_parser("list")
    sub.add_parser("active-key")
    args = parser.parse_args()

    if args.cmd == "set":
        key = args.key or getpass.getpass("WeRead API key: ")
        set_account(args.name, key.strip())
        print(f"已保存账号: {args.name}")
    elif args.cmd == "switch":
      switch_account(args.name)
      print(f"已切换账号: {args.name}")
    elif args.cmd == "delete":
      delete_account(args.name)
      print(f"已删除账号: {args.name}")
    elif args.cmd == "list":
      print(json.dumps(public_accounts(), ensure_ascii=False))
    elif args.cmd == "active-key":
      print(active_key())


if __name__ == "__main__":
    main()
