# Instantaneous Loading — Benchmark Notes

## Targets (split)

| Metric | Target | Notes |
| :--- | :--- | :--- |
| Card TTI (warm isolate) | < 0.5s | Time from navigation to first interactive scoring card after `/api/bootstrap` returns |
| Card TTI (cold) | measure separately | First Vercel isolate + pool TLS; not held to 0.45s |
| PDF first paint | async / non-blocking | Must not gate card interactivity |
| Category switch | < 0.05s DOM | Stable iframe; only right pane rebuild |

## How to measure

1. Deploy current `main` to Vercel.
2. Open scorer with an authenticated session (warm: reload once first).
3. DevTools Network: confirm **one** `/api/bootstrap` on initial hydrate (company switch may call `/api/get-startup`).
4. Performance: mark `navigationStart` → first `.h-card` present and clickable.
5. Optional Playwright sketch:

```js
// Warm path: already logged in
await page.goto('/site/index.html');
await page.waitForSelector('.h-card .h-btn');
// assert only one bootstrap request in page requests
```

## Implemented stack

- `api/_db.js` shared `pg.Pool` (max 5)
- `api/bootstrap.js` atomic session + list + active startup
- `api/_project_startup.js` human-only projection shared with `get-startup`
- Client `init` + `handleLogin` hydrate via bootstrap
- PDF skeleton + stable `#primary-pdf-viewer`
- Storage preconnect for project CDN host
