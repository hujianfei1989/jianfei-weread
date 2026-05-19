# Privacy Checklist

Before sharing this skill or a generated project, confirm:

- No real `wrk-` API key appears in files.
- No `.weread-accounts.json` is included.
- No `weread-export/` folder is included.
- `weread-obsidian.html` contains an empty `RAW_DATA` object in templates.
- Generated reports and slides from a real account are excluded.

Recommended public repository ignore rules:

```gitignore
.weread-accounts.json
weread-export/
__pycache__/
*.pyc
*.key
*.token
```
