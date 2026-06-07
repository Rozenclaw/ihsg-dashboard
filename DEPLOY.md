# Deploying the IHSG Dashboard as an Android app

This turns the dashboard into a phone app in two layers:

1. **Cloud** — the dashboard runs 24/7 on **Streamlit Community Cloud** (free,
   HTTPS, deploy-from-GitHub).
2. **Android** — a thin **WebView APK** opens that URL full-screen like a native
   app.

> **The big win:** to update the app you just **`git push`**. Community Cloud
> redeploys automatically and your phone shows the new version on next open.
> You only rebuild the APK if the *URL* ever changes (basically never).

```
  edit Python  →  git push  →  Community Cloud redeploys  →  phone shows update
                                   (no APK rebuild)
```

---

## What changed to make this cloud-ready

A few additions (already done, all backward-compatible — local use is unchanged):

| Piece | Why |
|---|---|
| `app/ui/auth.py` (password gate) | The cloud URL is public, so the app locks behind `APP_PASSWORD`. **Unset locally → no login.** |
| `app/ui/bootstrap.py` (DB self-seed) | Community Cloud's disk is wiped on restart. On a cloud host the app lays down `data/seed.db`, then best-effort refreshes today's prices. **No-op locally.** |
| `data/seed.db` (committed) | A market-data snapshot (prices/fundamentals only, no personal data) so the app always has data even if Yahoo rate-limits the cloud IP. |
| `scripts/make_seed.py` | Rebuilds `data/seed.db` from your live DB (run before a push if you want a fresher seed). |
| `requirements.txt` → `streamlit>=1.50` | Pins the version the app was built against. |

---

## Step 1 — Put the repo on GitHub (private)

The dashboard is personal, so use a **private** repo.

1. Create an empty repo at <https://github.com/new> — name it e.g. `ihsg-dashboard`,
   visibility **Private**, and **don't** add a README/.gitignore (you already have them).
2. In a terminal, from the project folder:

   ```bash
   cd /Users/ekp1/Desktop/ihsg_dashboard
   git remote add origin https://github.com/<your-username>/ihsg-dashboard.git
   git push -u origin master
   ```

   (If GitHub asks for a password, use a **Personal Access Token**:
   <https://github.com/settings/tokens> → "Generate new token (classic)" → scope `repo`.)

> ✅ Secrets are safe: `.streamlit/secrets.toml`, `data/*.db` (except the
> sanitized `data/seed.db`), and `.claude/` are gitignored. Your Gemini/iTick
> keys never touch GitHub.

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and **sign in with GitHub** (authorize it to
   read your **private** repos).
2. **Create app → Deploy a public app from GitHub** (the app is still gated by
   your password):
   - **Repository:** `<your-username>/ihsg-dashboard`
   - **Branch:** `master`
   - **Main file path:** `app/dashboard.py`
   - **Advanced settings → Python version:** `3.12`
3. **Advanced settings → Secrets** — paste this (fill in real values):

   ```toml
   APP_PASSWORD = "pick-a-strong-password"
   GEMINI_API_KEY = "your-gemini-key"      # optional (AI narrative)
   # ITICK_TOKEN = "..."                    # optional (only if you switch to iTick)
   ```

   See `.streamlit/secrets.toml.example` for the full template.
4. Click **Deploy**. First boot takes a few minutes (installing packages + seeding
   data). When it's live you'll get a URL like
   **`https://ihsg-dashboard.streamlit.app`** — copy it.

> The app opens to the **password screen**. Enter your `APP_PASSWORD` to get in.

## Step 3 — Instant test on your phone (no build needed)

1. On the phone, open the `https://….streamlit.app` URL in **Chrome**.
2. Enter your password — the full dashboard loads, mobile-friendly.
3. **Chrome menu (⋮) → Add to Home screen.** You now have an app icon that opens
   it full-screen. Great for a first end-to-end test.

## Step 4 — Build the real Android APK

For a proper installable app (your own icon, offline shell, pull-to-refresh):

1. Put your URL into the project: edit
   [`android/app/src/main/res/values/strings.xml`](android/app/src/main/res/values/strings.xml)
   → replace `https://YOUR-APP-NAME.streamlit.app`.
2. Follow [`android/README.md`](android/README.md): **Android Studio → Open
   `android/` → Build → Build APK(s)**, then install `app-debug.apk` on the phone.

---

## Updating later (the easy part)

```bash
# make your edits to the Python, then:
git add -A && git commit -m "…"   && git push
```

Community Cloud redeploys in ~1–2 minutes; reopen the app on the phone to see it.
**No APK rebuild.** (Optional: run `python scripts/make_seed.py` before pushing to
freshen the offline seed snapshot.)

## Notes & limits (Community Cloud free tier)

- **Full IDX universe (~950 stocks):** the complete ticker list is in
  `data/universe.csv` (built by `scripts/fetch_idx_universe.py` from a free
  source; re-run it to pick up new IPOs). The committed `data/seed.db.gz` (28 MB)
  is the bundled market snapshot the cloud/local unpacks on first boot.
- **Resources:** ~1 GB RAM. Charting/watchlist/alerts cover every stock, but the
  universe-wide **screening** (recommendations, Daily Trading board) is capped to
  the most-liquid `strategy.screen_max_names` (300) for speed — raise/lower it in
  `config.yaml`, or set 0 to screen all.
- **Data freshness (the rule):** prices refresh **once per trading day, after the
  IDX close (~17:00 WIB), and never on weekends/holidays** (see
  `src/market_calendar.py`). Fundamentals come from the snapshot (refresh anytime
  with `python scripts/refresh_data.py`). If Yahoo rate-limits the cloud IP you
  still see the seed snapshot. Add lunar-holiday dates to `MOVABLE_HOLIDAYS`.
- **Sleep:** the app may sleep after long inactivity and cold-start on next open
  (a few seconds; if it had to rebuild data, a bit longer).
- **Privacy:** keep the GitHub repo **private** and always set `APP_PASSWORD`.
```
