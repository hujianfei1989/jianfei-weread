# Data Schema

The dashboard embeds:

```js
var RAW_DATA = {
  books: {},
  notes: {},
  bookIds: [],
  recs: {}
};
```

Common book fields include title, author, cover, category, publisher, publish time, ISBN, rating, chapter count, progress, note count, reader URL, and metadata returned by WeRead.

Common note fields:

- `bms`: highlights/bookmarks
- `rvs`: personal thoughts/reviews
- grouped chapter data generated from WeRead note exports

The exporter also writes JSON files under `weread-export/` for debugging and reuse. That folder is private user data.
