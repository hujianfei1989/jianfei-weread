#!/usr/bin/env python3
"""Export WeRead shelf, highlights, and personal thoughts to local JSON.

Usage:
  export WEREAD_API_KEY='wrk-...'
  python3 weread_export_notes.py

The script uses the local weread skill contract:
  POST https://i.weread.qq.com/api/agent/gateway
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from weread_accounts import active_key
except Exception:  # pragma: no cover - optional local helper
    active_key = None


SKILL_VERSION = "1.2.0"
GATEWAY = "https://i.weread.qq.com/api/agent/gateway"
OUT_DIR = Path(__file__).resolve().parent / "weread-export"
MAX_WORKERS = 8
RECOMMENDATIONS_PATH = OUT_DIR / "recommendations.json"


def weread_reader_hash(book_id: Any) -> str:
    """Return the WeRead web reader id derived from the numeric book id."""
    raw_id = str(book_id or "")
    if not raw_id:
        return ""
    digest = hashlib.md5(raw_id.encode("utf-8")).hexdigest()
    result = digest[:3]
    if raw_id.isdigit():
        chunks = [
            format(int(raw_id[idx : idx + 9]), "x")
            for idx in range(0, len(raw_id), 9)
        ]
        result += "3"
    else:
        chunks = ["".join(format(ord(char), "x") for char in raw_id)]
        result += "4"
    result += "2" + digest[-2:]
    for index, chunk in enumerate(chunks):
        result += f"{len(chunk):02x}{chunk}"
        if index < len(chunks) - 1:
            result += "g"
    if len(result) < 20:
        result += digest[: 20 - len(result)]
    return result + hashlib.md5(result.encode("utf-8")).hexdigest()[:3]


def clean_control_chars(raw: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", raw)


def call_api(api_name: str, **params: Any) -> dict[str, Any]:
    api_key = os.environ.get("WEREAD_API_KEY", "").strip()
    if not api_key and active_key:
        api_key = active_key().strip()
    if not api_key:
        raise SystemExit(
            "WEREAD_API_KEY is not set. Run:\n"
            "  export WEREAD_API_KEY='wrk-...'\n"
            "then run this script again."
        )

    body = {"api_name": api_name, "skill_version": SKILL_VERSION, **params}
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        GATEWAY,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{api_name} HTTP {exc.code}: {detail[:800]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{api_name} network error: {exc}") from exc

    data = json.loads(clean_control_chars(text), strict=False)
    if isinstance(data, dict) and data.get("upgrade_info"):
        raise RuntimeError(f"weread skill upgrade required: {data['upgrade_info']}")
    if isinstance(data, dict) and data.get("errcode") not in (None, 0):
        raise RuntimeError(f"{api_name} errcode={data.get('errcode')}: {data}")
    return data


def safe_call_api(api_name: str, **params: Any) -> tuple[dict[str, Any], str | None]:
    try:
        return call_api(api_name, **params), None
    except Exception as exc:
        return {}, str(exc)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def fetch_all_notebooks() -> list[dict[str, Any]]:
    books: list[dict[str, Any]] = []
    last_sort = None
    page = 1
    while True:
        params: dict[str, Any] = {"count": 100}
        if last_sort is not None:
            params["lastSort"] = last_sort
        data = call_api("/user/notebooks", **params)
        page_books = data.get("books") or []
        books.extend(page_books)
        print(f"notebooks page {page}: +{len(page_books)} books, total {len(books)}")
        if not data.get("hasMore") or not page_books:
            break
        last_sort = page_books[-1].get("sort")
        page += 1
        time.sleep(0.15)
    return books


def fetch_all_reviews(book_id: str) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    synckey = 0
    while True:
        data = call_api("/review/list/mine", bookid=book_id, count=100, synckey=synckey)
        reviews.extend(data.get("reviews") or [])
        if not data.get("hasMore"):
            break
        next_key = data.get("synckey")
        if not next_key or next_key == synckey:
            break
        synckey = next_key
        time.sleep(0.1)
    return reviews


def normalize_book_meta(item: dict[str, Any]) -> dict[str, Any]:
    book = item.get("book") or {}
    return {
        "bookId": item.get("bookId") or book.get("bookId"),
        "title": book.get("title") or item.get("title") or "",
        "author": book.get("author") or "",
        "cover": book.get("cover") or "",
        "reviewCount": item.get("reviewCount") or 0,
        "noteCount": item.get("noteCount") or 0,
        "bookmarkCount": item.get("bookmarkCount") or 0,
        "readingProgress": item.get("readingProgress"),
        "markedStatus": item.get("markedStatus"),
        "sort": item.get("sort"),
    }


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def build_book_metadata(
    notebook_item: dict[str, Any],
    notebook_meta: dict[str, Any],
    book_info: dict[str, Any],
    chapter_info: dict[str, Any],
    progress_info: dict[str, Any],
) -> dict[str, Any]:
    notebook_book = notebook_item.get("book") or {}
    progress_book = progress_info.get("book") or {}
    chapters = chapter_info.get("chapters") or []
    return {
        "bookId": first_present(book_info.get("bookId"), notebook_meta.get("bookId")),
        "title": first_present(book_info.get("title"), notebook_meta.get("title")),
        "author": first_present(book_info.get("author"), notebook_meta.get("author")),
        "translator": book_info.get("translator"),
        "cover": first_present(book_info.get("cover"), notebook_meta.get("cover")),
        "intro": first_present(book_info.get("intro"), notebook_book.get("intro")),
        "category": first_present(book_info.get("category"), notebook_book.get("category")),
        "publisher": book_info.get("publisher"),
        "publishTime": book_info.get("publishTime"),
        "isbn": book_info.get("isbn"),
        "wordCount": book_info.get("wordCount"),
        "newRating": book_info.get("newRating"),
        "newRatingCount": book_info.get("newRatingCount"),
        "newRatingDetail": book_info.get("newRatingDetail"),
        "readingProgress": first_present(progress_book.get("progress"), notebook_meta.get("readingProgress")),
        "readUpdateTime": first_present(progress_book.get("updateTime"), notebook_book.get("readUpdateTime")),
        "recordReadingTime": progress_book.get("recordReadingTime"),
        "finishTime": progress_book.get("finishTime"),
        "isStartReading": progress_book.get("isStartReading"),
        "currentChapterUid": progress_book.get("chapterUid"),
        "currentChapterOffset": progress_book.get("chapterOffset"),
        "chapterCount": len(chapters),
        "chapterUpdateTime": chapter_info.get("chapterUpdateTime"),
        "chapterSynckey": chapter_info.get("synckey"),
        "markedStatus": notebook_meta.get("markedStatus"),
        "sort": notebook_meta.get("sort"),
        "noteCount": notebook_meta.get("noteCount", 0),
        "reviewCount": notebook_meta.get("reviewCount", 0),
        "bookmarkCount": notebook_meta.get("bookmarkCount", 0),
    }


def export_one_book(item: dict[str, Any]) -> dict[str, Any]:
    meta = normalize_book_meta(item)
    book_id = str(meta["bookId"])
    book_info, book_info_error = safe_call_api("/book/info", bookId=book_id)
    chapter_info, chapter_info_error = safe_call_api("/book/chapterinfo", bookId=book_id)
    progress_info, progress_error = safe_call_api("/book/getprogress", bookId=book_id)
    bookmark_data = call_api("/book/bookmarklist", bookId=book_id)
    reviews = fetch_all_reviews(book_id)
    chapters = chapter_info.get("chapters") or bookmark_data.get("chapters") or []
    chapter_titles = {str(c.get("chapterUid")): c.get("title", "") for c in chapters}
    bookmarks = []
    for bm in bookmark_data.get("updated") or []:
        chapter_uid = bm.get("chapterUid")
        bookmarks.append(
            {
                "bookmarkId": bm.get("bookmarkId"),
                "bookId": bm.get("bookId") or book_id,
                "markText": bm.get("markText") or "",
                "chapterUid": chapter_uid,
                "chapterTitle": chapter_titles.get(str(chapter_uid), ""),
                "createTime": bm.get("createTime"),
                "range": bm.get("range"),
                "colorStyle": bm.get("colorStyle"),
            }
        )

    normalized_reviews = []
    for entry in reviews:
        review = entry.get("review") or {}
        normalized_reviews.append(
            {
                "reviewId": review.get("reviewId"),
                "content": review.get("content") or "",
                "chapterName": review.get("chapterName") or "",
                "createTime": review.get("createTime"),
                "star": review.get("star"),
                "isFinish": review.get("isFinish"),
                "range": review.get("range"),
                "chapterUid": review.get("chapterUid"),
                "abstract": review.get("abstract"),
            }
        )

    metadata = build_book_metadata(item, meta, book_info, chapter_info, progress_info)
    result = {
        **meta,
        "metadata": metadata,
        "bookInfo": book_info,
        "chapterInfo": chapter_info,
        "progressInfo": progress_info,
        "rawNotebook": item,
        "bookmarklistBook": bookmark_data.get("book") or {},
        "syncErrors": {
            "bookInfo": book_info_error,
            "chapterInfo": chapter_info_error,
            "progressInfo": progress_error,
        },
        "bookmarks": bookmarks,
        "bookmarkContentCount": len(bookmarks),
        "reviews": normalized_reviews,
        "reviewContentCount": len(normalized_reviews),
        "chapters": chapters,
    }
    write_json(OUT_DIR / "books" / f"{book_id}.json", result)
    return result


def build_embeddable_data(exported_books: list[dict[str, Any]]) -> dict[str, Any]:
    recommendations = load_recommendations()
    books: dict[str, Any] = {}
    notes: dict[str, Any] = {}
    book_ids: list[str] = []
    for item in exported_books:
        book_id = str(item["bookId"])
        book_ids.append(book_id)
        count = item.get("noteCount", 0) + item.get("reviewCount", 0) + item.get("bookmarkCount", 0)
        metadata = item.get("metadata") or {}
        books[book_id] = {
            "t": item.get("title", ""),
            "a": item.get("author", ""),
            "c": item.get("cover", ""),
            "w": weread_reader_hash(book_id),
            "n": count,
            "f": bool(item.get("markedStatus")),
            "m": {
                "translator": metadata.get("translator"),
                "intro": metadata.get("intro"),
                "category": metadata.get("category"),
                "publisher": metadata.get("publisher"),
                "publishTime": metadata.get("publishTime"),
                "isbn": metadata.get("isbn"),
                "wordCount": metadata.get("wordCount"),
                "rating": metadata.get("newRating"),
                "ratingCount": metadata.get("newRatingCount"),
                "progress": metadata.get("readingProgress"),
                "readUpdateTime": metadata.get("readUpdateTime"),
                "recordReadingTime": metadata.get("recordReadingTime"),
                "finishTime": metadata.get("finishTime"),
                "chapterCount": metadata.get("chapterCount"),
            },
        }
        notes[book_id] = {
            "title": item.get("title", ""),
            "chapters": [
                {
                    "uid": c.get("chapterUid"),
                    "idx": c.get("chapterIdx"),
                    "title": c.get("title", ""),
                    "level": c.get("level"),
                    "wordCount": c.get("wordCount"),
                    "updateTime": c.get("updateTime"),
                    "paid": c.get("paid"),
                    "anchors": c.get("anchors"),
                }
                for c in item.get("chapters", [])
            ],
            "bms": [
                {
                    "t": bm.get("markText", ""),
                    "c": bm.get("chapterTitle", "") or "其他",
                    "s": bm.get("createTime"),
                    "range": bm.get("range"),
                    "chapterUid": bm.get("chapterUid"),
                    "bookmarkId": bm.get("bookmarkId"),
                    "colorStyle": bm.get("colorStyle"),
                }
                for bm in item.get("bookmarks", [])
                if bm.get("markText")
            ],
            "rvs": [
                {
                    "t": rv.get("content", ""),
                    "c": rv.get("chapterName", "") or "其他",
                    "s": rv.get("createTime"),
                    "range": rv.get("range"),
                    "chapterUid": rv.get("chapterUid"),
                    "abstract": rv.get("abstract"),
                    "reviewId": rv.get("reviewId"),
                }
                for rv in item.get("reviews", [])
                if rv.get("content")
            ],
        }
    recs = {book_id: recommendations.get(book_id, []) for book_id in book_ids if recommendations.get(book_id)}
    return {"books": books, "notes": notes, "bookIds": book_ids, "recs": recs}


def normalize_recommended_book(item: dict[str, Any]) -> dict[str, Any]:
    book_id = str(item.get("bookId") or "")
    return {
        "id": book_id,
        "t": item.get("title", ""),
        "a": item.get("author", ""),
        "c": item.get("cover", ""),
        "cat": item.get("category", ""),
        "intro": item.get("intro", ""),
        "w": weread_reader_hash(book_id),
    }


def load_recommendations() -> dict[str, list[dict[str, Any]]]:
    if not RECOMMENDATIONS_PATH.exists():
        return {}
    try:
        data = json.loads(RECOMMENDATIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, list)}


def fetch_recommendations_for_books(book_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    recommendations = load_recommendations()
    missing = [book_id for book_id in book_ids if book_id not in recommendations]
    if not missing:
        return recommendations

    print(f"fetching system recommendations for {len(missing)} books")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(safe_call_api, "/book/recommend", bookId=book_id): book_id for book_id in missing}
        for index, future in enumerate(as_completed(futures), 1):
            book_id = futures[future]
            data, error = future.result()
            if error:
                if "频率超限" not in error:
                    recommendations[book_id] = []
                print(f"[recommend {index}/{len(missing)}] {book_id} FAILED {error}", file=sys.stderr)
                continue
            books = data.get("books") or []
            recommendations[book_id] = [
                normalized
                for normalized in (normalize_recommended_book(book) for book in books)
                if normalized["id"]
            ][:12]
            print(f"[recommend {index}/{len(missing)}] {book_id} +{len(recommendations[book_id])}")

    write_json(RECOMMENDATIONS_PATH, recommendations)
    return recommendations


def is_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def count_fields(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    fields: dict[str, int] = {}
    for item in items:
        payload = item.get(key) or {}
        if not isinstance(payload, dict):
            continue
        for field, value in payload.items():
            if is_present(value):
                fields[field] = fields.get(field, 0) + 1
    return dict(sorted(fields.items()))


def build_metadata_summary(exported_books: list[dict[str, Any]]) -> dict[str, Any]:
    chapter_counts = [len(item.get("chapters") or []) for item in exported_books]
    missing_publish = [
        {"bookId": str(item.get("bookId")), "title": item.get("title", "")}
        for item in exported_books
        if not is_present((item.get("metadata") or {}).get("publishTime"))
    ]
    missing_chapters = [
        {"bookId": str(item.get("bookId")), "title": item.get("title", "")}
        for item in exported_books
        if not item.get("chapters")
    ]
    return {
        "generatedAt": int(time.time()),
        "bookCount": len(exported_books),
        "fieldCoverage": {
            "metadata": count_fields(exported_books, "metadata"),
            "bookInfo": count_fields(exported_books, "bookInfo"),
            "chapterInfo": count_fields(exported_books, "chapterInfo"),
            "progressInfo": count_fields(exported_books, "progressInfo"),
        },
        "chapterStats": {
            "booksWithChapters": sum(1 for count in chapter_counts if count > 0),
            "totalChapters": sum(chapter_counts),
            "maxChapters": max(chapter_counts) if chapter_counts else 0,
        },
        "missing": {
            "publishTime": missing_publish,
            "chapters": missing_chapters,
        },
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"exporting to {OUT_DIR}")
    shelf = call_api("/shelf/sync")
    write_json(OUT_DIR / "shelf.json", shelf)
    notebooks = fetch_all_notebooks()
    write_json(OUT_DIR / "notebooks.json", notebooks)

    targets = [item for item in notebooks if normalize_book_meta(item).get("bookId")]
    exported: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(export_one_book, item): item for item in targets}
        for index, future in enumerate(as_completed(futures), 1):
            item = futures[future]
            meta = normalize_book_meta(item)
            try:
                result = future.result()
                exported.append(result)
                print(
                    f"[{index}/{len(targets)}] {result['title']} "
                    f"highlights={result['bookmarkContentCount']} thoughts={result['reviewContentCount']}"
                )
            except Exception as exc:
                failures.append({"bookId": str(meta.get("bookId")), "title": meta.get("title", ""), "error": str(exc)})
                print(f"[{index}/{len(targets)}] FAILED {meta.get('title')}: {exc}", file=sys.stderr)

    exported.sort(key=lambda x: (x.get("noteCount", 0) + x.get("reviewCount", 0) + x.get("bookmarkCount", 0)), reverse=True)
    fetch_recommendations_for_books([str(item.get("bookId")) for item in exported if item.get("bookId")])
    write_json(OUT_DIR / "weread-full-notes.json", exported)
    write_json(OUT_DIR / "weread-raw-data.json", build_embeddable_data(exported))
    write_json(OUT_DIR / "weread-metadata-summary.json", build_metadata_summary(exported))
    write_json(OUT_DIR / "failures.json", failures)
    print("")
    print(f"books exported: {len(exported)}")
    print(f"failures: {len(failures)}")
    print(f"full export: {OUT_DIR / 'weread-full-notes.json'}")
    print(f"embeddable RAW_DATA: {OUT_DIR / 'weread-raw-data.json'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
