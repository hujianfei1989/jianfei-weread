---
name: jianfei-weread
description: Use when users want to install, export, sync, analyze, browse, present, or package a local WeRead dashboard with books, highlights, thoughts, reading reports, recommendations, quote cards, slides, and multi-account API keys.
---

# jianfei-weread

This skill builds a reusable local WeRead dashboard from the user's own API key and data. Keep secrets and personal exports local; never put API keys or `weread-export/` data into shared artifacts.

## Quick Start

Install a clean project:

```bash
python3 scripts/install.py --target "$HOME/Documents/jianfei-weread" --title "我的微信读书" --keyword "专题"
```

Add an account:

```bash
python3 scripts/accounts.py --target "$HOME/Documents/jianfei-weread" set default
```

Sync data:

```bash
python3 scripts/sync.py --target "$HOME/Documents/jianfei-weread"
```

Open the dashboard:

```bash
python3 scripts/serve.py --target "$HOME/Documents/jianfei-weread"
```

## Workflow

1. Run `scripts/install.py` to copy the sanitized project template into a user-owned directory.
2. Use `scripts/accounts.py` or the dashboard Settings page to save a WeRead `wrk-...` API key locally.
3. Run `scripts/sync.py` or click the dashboard sync button to export shelf, metadata, highlights, thoughts, recommendations, and slides.
4. Use `scripts/serve.py` while the dashboard is open so Settings and one-click sync can call `http://127.0.0.1:18766`.
5. For sharing, publish this skill folder, not a populated project folder.

## Privacy Rules

Do not include these in Git, zip files, or shared examples:

- `.weread-accounts.json`
- `weread-export/`
- generated slide HTML from a real account
- personal annual reports
- any real `wrk-...` key

Use `references/privacy.md` when preparing a public release.

## Customization

- `--title` controls the dashboard title.
- `--keyword` controls the special-topic tab and generated slides filter.
- Users can still search, filter by year, blacklist books, tune minimum note count, switch themes, and manage accounts inside the page.

## Validation

After editing the template or scripts:

```bash
python3 -m py_compile scripts/*.py assets/project-template/*.py
python3 scripts/install.py --target /tmp/jianfei-weread-test --force
python3 scripts/accounts.py --target /tmp/jianfei-weread-test list
```

Then inspect the generated HTML and confirm `var RAW_DATA` is empty before sharing.
