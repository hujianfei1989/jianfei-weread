#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from collections import OrderedDict
from html import escape
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
RAW = BASE / "weread-export" / "weread-raw-data.json"
OUT = BASE / "weread-export" / "slides"


def load_data() -> dict[str, Any]:
    text = RAW.read_text(encoding="utf-8").strip()
    if text.startswith("var RAW_DATA = "):
        text = text[len("var RAW_DATA = ") :]
    if text.endswith(";"):
        text = text[:-1]
    return json.loads(text)


def slug(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "-", text).strip()
    return text[:80] or "book"


def is_jianfei(book: dict[str, Any]) -> bool:
    return "剑飞" in f"{book.get('t', '')} {book.get('a', '')}"


def date_only(value: Any) -> str:
    if not value:
        return ""
    text = str(value)
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    try:
        return __import__("datetime").datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d")
    except Exception:
        return ""


def metric(value: int) -> str:
    return f"{value:,}"


def collect_items(notes: dict[str, Any]) -> OrderedDict[str, list[dict[str, Any]]]:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    chapter_order = [c.get("title") for c in notes.get("chapters", []) if c.get("title")]
    for chapter in chapter_order:
        groups.setdefault(chapter, [])
    for item in notes.get("bms", []):
        chapter = item.get("c") or "其他"
        groups.setdefault(chapter, []).append({"kind": "划线", **item})
    for item in notes.get("rvs", []):
        chapter = item.get("c") or "其他"
        groups.setdefault(chapter, []).append({"kind": "想法", **item})
    return OrderedDict((k, v) for k, v in groups.items() if v)


def chunk_size(total: int, avg_len: float) -> int:
    if avg_len > 180:
        return 1
    if total >= 420:
        return 3
    if total >= 120:
        return 2
    return 1


def chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def split_text(text: str, limit: int = 155) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return [text] if text else []
    sentences = [part for part in re.split(r"(?<=[。！？!?；;])", text) if part]
    parts: list[str] = []
    current = ""
    for sentence in sentences or [text]:
        if len(sentence) > limit:
            if current:
                parts.append(current.strip())
                current = ""
            for index in range(0, len(sentence), limit):
                parts.append(sentence[index : index + limit].strip())
            continue
        if current and len(current) + len(sentence) > limit:
            parts.append(current.strip())
            current = sentence
        else:
            current += sentence
    if current:
        parts.append(current.strip())
    return [part for part in parts if part]


def expand_long_items(groups: OrderedDict[str, list[dict[str, Any]]]) -> OrderedDict[str, list[dict[str, Any]]]:
    expanded: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for chapter, items in groups.items():
        expanded[chapter] = []
        for item in items:
            parts = split_text(item.get("t", ""))
            if len(parts) <= 1:
                expanded[chapter].append(item)
                continue
            for index, part in enumerate(parts, 1):
                cloned = {**item, "t": part, "part": index, "parts": len(parts)}
                expanded[chapter].append(cloned)
    return expanded


def chapter_top(groups: OrderedDict[str, list[dict[str, Any]]]) -> list[tuple[str, int]]:
    rows = [(chapter, len(items)) for chapter, items in groups.items()]
    return sorted(rows, key=lambda row: row[1], reverse=True)[:10]


def render_items(items: list[dict[str, Any]]) -> str:
    html = []
    for item in items:
        kind = item.get("kind") or "划线"
        text = escape(item.get("t", ""))
        date = date_only(item.get("s"))
        part = ""
        if item.get("parts"):
            part = f"<span class=\"quote-part\">{int(item.get('part', 1))}/{int(item.get('parts', 1))}</span>"
        html.append(
            f"""
<article class="quote-card {'thought' if kind == '想法' else ''}">
  <div class="quote-top"><div class="quote-tag">{escape(kind)}</div>{part}</div>
  <p>{text}</p>
  <div class="quote-meta">{escape(date or '未记录日期')}</div>
</article>"""
        )
    return "\n".join(html)


def build_slides(book_id: str, book: dict[str, Any], notes: dict[str, Any]) -> list[dict[str, Any]]:
    bms = notes.get("bms", [])
    rvs = notes.get("rvs", [])
    total = len(bms) + len(rvs)
    m = book.get("m") or {}
    groups = collect_items(notes)
    display_groups = expand_long_items(groups)
    all_items = [item for items in display_groups.values() for item in items]
    avg_len = sum(len(item.get("t", "")) for item in all_items) / max(1, len(all_items))
    per_slide = chunk_size(total, avg_len)
    slides: list[dict[str, Any]] = [
        {
            "type": "cover",
            "kicker": "Jianfei Weread Archive" if is_jianfei(book) else "Weread Archive",
            "title": book.get("t", ""),
            "subtitle": book.get("a", ""),
            "body": "",
            "meta": f"{metric(len(bms))} 条划线 · {metric(len(rvs))} 条想法 · {metric(total)} 条笔记",
        },
        {
            "type": "overview",
            "kicker": "Book Signals",
            "title": "这本书的笔记密度",
            "subtitle": "",
            "body": "",
            "meta": json.dumps(
                {
                    "notes": total,
                    "highlights": len(bms),
                    "thoughts": len(rvs),
                    "chapters": len(groups),
                    "publish": date_only(m.get("publishTime")),
                    "isbn": m.get("isbn") or "",
                    "publisher": m.get("publisher") or "",
                    "progress": m.get("progress"),
                },
                ensure_ascii=False,
            ),
        },
    ]
    if display_groups:
        top_rows = chapter_top(display_groups)
        max_count = max(count for _, count in top_rows)
        body = "".join(
            f"<div class='toc-row'><span>{escape(chapter)}</span><i style='width:{max(8, round(count / max_count * 100))}%'></i><strong>{count}</strong></div>"
            for chapter, count in top_rows
        )
        slides.append(
            {
                "type": "toc",
                "kicker": "Chapter Map",
                "title": "高密度章节",
                "subtitle": "按划线和想法数量排序",
                "body": body,
                "meta": f"{len(groups)} 个章节有笔记",
            }
        )

    for chapter, items in display_groups.items():
        original_items = groups.get(chapter, [])
        slides.append(
            {
                "type": "chapter",
                "kicker": f"{len(original_items)} 条笔记",
                "title": chapter,
                "subtitle": "章节幕",
                "body": "",
                "meta": f"{sum(1 for i in original_items if i.get('kind') == '划线')} 划线 · {sum(1 for i in original_items if i.get('kind') == '想法')} 想法",
            }
        )
        for page, chunk in enumerate(chunks(items, per_slide), 1):
            slides.append(
                {
                    "type": "quotes",
                    "kicker": f"{chapter} · {page}/{math.ceil(len(items) / per_slide)}",
                    "title": "金句与想法",
                    "subtitle": "",
                    "body": render_items(chunk),
                    "meta": f"本页 {len(chunk)} 条 · 全书 {total} 条",
                }
            )

    slides.append(
        {
            "type": "ending",
            "kicker": "Review Ready",
            "title": "笔记已经整理成演示稿",
            "subtitle": "",
            "body": "<p>适合复盘、分享、写作和二次整理。</p>",
            "meta": f"{len(slides) + 1} 页 · {metric(total)} 条笔记",
        }
    )
    return slides


def render(book_id: str, book: dict[str, Any], slides: list[dict[str, Any]]) -> str:
    sections = []
    total = len(slides)
    for index, slide in enumerate(slides, 1):
        classes = f"slide {slide['type']}"
        meta = ""
        if slide["type"] == "overview":
            data = json.loads(slide["meta"])
            meta = f"""
<div class="metric-grid">
  <div><strong>{metric(data['notes'])}</strong><span>全部笔记</span></div>
  <div><strong>{metric(data['highlights'])}</strong><span>划线</span></div>
  <div><strong>{metric(data['thoughts'])}</strong><span>想法</span></div>
  <div><strong>{metric(data['chapters'])}</strong><span>笔记章节</span></div>
</div>
<div class="book-fields">
  {field('出版', data.get('publish'))}
  {field('出版社', data.get('publisher'))}
  {field('ISBN', data.get('isbn'))}
  {field('进度', str(data.get('progress')) + '%' if data.get('progress') is not None else '')}
</div>"""
        else:
            meta = f"<div class='meta'>{escape(slide.get('meta', ''))}</div>"
        sections.append(
            f"""
<section class="{classes}">
  <div class="count">{index:03d} / {total:03d}</div>
  <div class="kicker">{escape(slide.get('kicker', ''))}</div>
  <h1>{escape(slide.get('title', ''))}</h1>
  {f"<h2>{escape(slide.get('subtitle', ''))}</h2>" if slide.get('subtitle') else ""}
  <div class="body">{slide.get('body', '')}</div>
  {meta}
</section>"""
        )
    app_hash = f"jianfei:{book_id}" if is_jianfei(book) else f"books:{book_id}"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(book['t'])} · 完整笔记幻灯片</title>
<style>
:root {{ color-scheme: light dark; --bg:#f7f3ea; --ink:#231f19; --muted:#766a5c; --line:#dccdb8; --paper:#fffdf8; --accent:#08796f; --warm:#b76722; --dark:#202327; }}
* {{ box-sizing:border-box; }}
html, body {{ margin:0; min-height:100%; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Noto Sans SC",sans-serif; scroll-snap-type:y mandatory; }}
body::before {{ content:""; position:fixed; inset:0; pointer-events:none; background:linear-gradient(90deg,rgba(89,72,48,.055) 1px,transparent 1px),linear-gradient(180deg,rgba(89,72,48,.045) 1px,transparent 1px); background-size:42px 42px; }}
.slide {{ min-height:100vh; scroll-snap-align:start; display:grid; align-content:center; justify-items:start; padding:8vh 8vw; position:relative; overflow:hidden; }}
.slide > * {{ width:100%; max-width:1180px; }}
.slide::after {{ content:""; position:absolute; left:8vw; right:8vw; bottom:6vh; height:4px; border-radius:999px; background:linear-gradient(90deg,var(--accent),var(--warm)); }}
.count {{ position:absolute; top:30px; right:42px; color:var(--muted); font-weight:900; letter-spacing:.12em; }}
.kicker {{ color:var(--accent); text-transform:uppercase; letter-spacing:.15em; font-weight:900; font-size:13px; margin-bottom:18px; }}
h1 {{ max-width:1120px; margin:0; color:var(--ink); font-size:clamp(38px,6.8vw,88px); line-height:1.05; letter-spacing:0; }}
h2 {{ margin:18px 0 0; color:var(--muted); font-size:clamp(20px,2.4vw,32px); font-weight:700; }}
.body {{ width:min(1180px,100%); margin-top:28px; }}
.cover {{ background:radial-gradient(circle at top right,rgba(183,103,34,.14),transparent 34%),linear-gradient(135deg,#fffdf8,#edf4ee); }}
.overview .body {{ display:none; }}
.metric-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; width:min(980px,100%); margin-top:30px; }}
.metric-grid div {{ border:1px solid var(--line); border-radius:16px; background:rgba(255,253,248,.82); padding:18px; box-shadow:0 14px 34px rgba(84,64,35,.08); }}
.metric-grid strong {{ display:block; font-size:clamp(32px,4.5vw,58px); line-height:1; color:var(--warm); }}
.metric-grid span {{ display:block; margin-top:8px; color:var(--muted); font-size:13px; }}
.book-fields {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; }}
.book-fields span {{ border:1px solid var(--line); border-radius:999px; background:rgba(255,253,248,.72); padding:8px 12px; color:var(--muted); font-weight:700; }}
.toc-row {{ display:grid; grid-template-columns:minmax(180px,360px) 1fr auto; gap:14px; align-items:center; margin:10px 0; font-size:17px; color:var(--muted); }}
.toc-row i {{ display:block; height:12px; border-radius:999px; background:linear-gradient(90deg,var(--accent),var(--warm)); }}
.toc-row strong {{ color:var(--ink); }}
.chapter {{ background:linear-gradient(135deg,#232323,#31403d); color:#f4eadf; }}
.chapter h1, .chapter h2 {{ color:#f4eadf; }}
.chapter .kicker, .chapter .meta {{ color:#d9a441; }}
.quotes h1 {{ font-size:clamp(26px,3.8vw,48px); color:var(--muted); }}
.quotes .body {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:16px; }}
.quote-card {{ position:relative; border:1px solid var(--line); border-radius:18px; background:rgba(255,253,248,.88); padding:22px 22px 18px; box-shadow:0 14px 34px rgba(84,64,35,.08); overflow:hidden; }}
.quote-card::before {{ content:""; position:absolute; inset:0 0 auto; height:5px; background:linear-gradient(90deg,var(--accent),var(--warm)); }}
.quote-card::after {{ content:"“"; position:absolute; right:16px; top:2px; color:rgba(84,64,35,.08); font-size:76px; font-weight:900; line-height:1; }}
.quote-card.thought {{ background:#fff7ec; border-color:rgba(183,103,34,.26); }}
.quote-top {{ position:relative; z-index:1; display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:12px; }}
.quote-tag {{ display:inline-flex; border:1px solid rgba(8,121,111,.24); border-radius:999px; background:rgba(8,121,111,.08); color:var(--accent); padding:5px 9px; font-size:12px; font-weight:900; margin-bottom:12px; }}
.quote-top .quote-tag {{ margin-bottom:0; }}
.quote-part {{ display:inline-flex; align-items:center; justify-content:center; min-width:42px; height:26px; border-radius:999px; background:rgba(35,31,25,.08); color:var(--muted); font-size:12px; font-weight:900; }}
.thought .quote-tag {{ border-color:rgba(183,103,34,.28); background:rgba(183,103,34,.10); color:var(--warm); }}
.quote-card p {{ position:relative; z-index:1; margin:0; font-size:clamp(18px,1.72vw,25px); line-height:1.58; font-weight:750; }}
.quote-meta {{ position:relative; z-index:1; margin-top:16px; color:var(--muted); font-size:13px; }}
.meta {{ margin-top:24px; color:var(--muted); font-size:14px; font-weight:800; }}
.home {{ position:fixed; top:26px; left:32px; z-index:10; color:var(--ink); text-decoration:none; border:1px solid var(--line); border-radius:999px; padding:9px 14px; background:rgba(255,253,248,.76); backdrop-filter:blur(10px); }}
@media (orientation: landscape) and (min-width: 960px) {{
  .slide {{ justify-items:center; padding-left:6vw; padding-right:6vw; }}
  .slide > * {{ width:min(1180px,86vw); }}
  .quotes .body {{ width:min(1180px,86vw); }}
  h1, h2, .kicker, .meta, .metric-grid, .book-fields {{ margin-left:auto; margin-right:auto; }}
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#101111; --ink:#f2eadf; --muted:#a8a094; --line:#3b3b35; --paper:#202327; }}
  body::before {{ background:linear-gradient(90deg,rgba(255,255,255,.03) 1px,transparent 1px),linear-gradient(180deg,rgba(255,255,255,.02) 1px,transparent 1px); background-size:42px 42px; }}
  .cover {{ background:radial-gradient(circle at top right,rgba(217,164,65,.18),transparent 34%),linear-gradient(135deg,#202327,#132a2b); }}
  .metric-grid div, .book-fields span, .quote-card, .home {{ background:rgba(32,35,39,.88); }}
  .quote-card.thought {{ background:linear-gradient(135deg,#29231d,#242830); }}
  .quote-card::after {{ color:rgba(255,255,255,.06); }}
}}
@media (max-width:760px) {{
  .slide {{ padding:72px 20px 54px; }}
  .metric-grid, .quotes .body {{ grid-template-columns:1fr; }}
  .toc-row {{ grid-template-columns:1fr auto; }}
  .toc-row i {{ grid-column:1 / -1; }}
}}
</style>
</head>
<body>
<a class="home" href="../../weread-obsidian.html#{app_hash}">返回这本书</a>
{''.join(sections)}
<script>
document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowDown' || e.key === ' ' || e.key === 'ArrowRight') window.scrollBy({{top: innerHeight, behavior: 'smooth'}});
  if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') window.scrollBy({{top: -innerHeight, behavior: 'smooth'}});
}});
</script>
</body>
</html>"""


def field(label: str, value: Any) -> str:
    if value in (None, ""):
        return ""
    return f"<span>{escape(label)}：{escape(str(value))}</span>"


def main() -> int:
    data = load_data()
    OUT.mkdir(parents=True, exist_ok=True)
    links = []
    for book_id in data["bookIds"]:
        book = data["books"][book_id]
        notes = data.get("notes", {}).get(book_id, {})
        filename = f"{slug(book['t'])}-{book_id}.html"
        slides = build_slides(book_id, book, notes)
        (OUT / filename).write_text(render(book_id, book, slides), encoding="utf-8")
        links.append(
            {
                "is_jianfei": is_jianfei(book),
                "title": book["t"],
                "author": book.get("a", ""),
                "cover": book.get("c", ""),
                "filename": filename,
                "slide_count": len(slides),
                "note_count": book.get("n", 0),
            }
        )
    links.sort(key=lambda row: (not row["is_jianfei"], -row["note_count"], row["title"]))
    print(f"generated {len(links)} slide decks: {OUT}")
    print(f"jianfei decks: {sum(1 for row in links if row['is_jianfei'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
