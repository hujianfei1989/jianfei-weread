# User Guide

Install:

```bash
python3 scripts/install.py --target "$HOME/Documents/jianfei-weread" --title "我的微信读书" --keyword "专题"
```

Add API key:

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" set default
```

Sync:

```bash
python3 scripts/sync.py --target "$HOME/Documents/jianfei-weread"
```

Open:

```bash
python3 scripts/serve.py --target "$HOME/Documents/jianfei-weread"
```

Then visit the printed dashboard URL.

The Settings page can add more accounts, switch accounts, choose theme, adjust font size, blacklist books, and trigger one-click sync.
