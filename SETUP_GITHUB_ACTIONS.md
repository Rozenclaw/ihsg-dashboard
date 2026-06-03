# Cloud automation with GitHub Actions — setup walkthrough

Run the daily IHSG job **in the cloud, for free, even when your laptop is off.**
GitHub runs `scripts/daily_job.py` on a schedule, keeps the database between
runs, and (optionally) sends you a Telegram/email digest.

Time needed: ~15 minutes. No coding.

---

## What you need
- A free [GitHub](https://github.com) account.
- The `ihsg_dashboard` folder (this project).
- Your iTick token + host (already have: `api0.itick.org`).
- *(Optional)* a Telegram bot, for the daily message.

---

## Step 1 — Put the project on GitHub (private)

1. Go to https://github.com/new
2. Repository name: `ihsg-dashboard` · set it to **Private** · click **Create repository**.
3. On the next page, follow **"…or push an existing repository from the command line."**
   In Terminal, from inside the project folder:
   ```bash
   cd /path/to/ihsg_dashboard
   git init
   git add .
   git commit -m "IHSG dashboard"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ihsg-dashboard.git
   git push -u origin main
   ```
   *(If `git` asks you to sign in, follow the browser prompt.)*

> ✅ Your `.gitignore` already excludes `data/*.db` and `.streamlit/secrets.toml`,
> so your local database and keys are **not** uploaded. Good — secrets go in
> GitHub's encrypted store instead (Step 3).

The workflow file `.github/workflows/daily.yml` is included, so GitHub will
detect the scheduled job automatically once pushed.

---

## Step 2 — (Optional) Create a Telegram bot for alerts

Skip if you don't want messages.

1. In Telegram, search **@BotFather** → send `/newbot` → follow prompts.
   It gives you a **bot token** (looks like `123456:ABC-...`).
2. Send any message to your new bot (e.g. "hi") so it can reply to you.
3. Get your **chat ID**: open this URL in a browser (paste your token):
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   Look for `"chat":{"id":123456789,...}` — that number is your chat ID.

---

## Step 3 — Add your secrets to GitHub

In your repo: **Settings → Secrets and variables → Actions → New repository secret.**
Add each of these (name on the left, your value on the right):

**Required for live quotes:**
| Secret name | Value |
|---|---|
| `ITICK_TOKEN` | your iTick API key |
| `ITICK_HOST` | `api0.itick.org` |

**Optional — Telegram digest:**
| Secret name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the bot token from BotFather |
| `TELEGRAM_CHAT_ID` | your chat ID |

**Optional — email digest (instead of/with Telegram):**
| Secret name | Value (example for Gmail) |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | your email address |
| `SMTP_PASS` | a Gmail **App Password** (not your normal password) |
| `EMAIL_TO` | where to send the digest |

> Gmail note: create an **App Password** at
> https://myaccount.google.com/apppasswords (requires 2-step verification on).

Click **Add secret** for each one.

---

## Step 4 — Turn the schedule on & test it

1. In your repo, open the **Actions** tab. If prompted, click
   **"I understand my workflows, enable them."**
2. Click **"IHSG daily job"** in the left list.
3. Click **Run workflow → Run workflow** (the manual trigger) to test it now.
4. Wait ~1–2 minutes, then click the run to watch the logs. You should see the
   four steps: refresh → evaluate → paper → digest. If Telegram is set up, you'll
   get a message.

After this test, it runs **automatically Monday–Friday at 09:30 UTC**
(= 16:30 WIB, right after IDX closes). No laptop needed.

---

## Changing the schedule

Edit `.github/workflows/daily.yml`, the `cron` line (times are **UTC**):
```yaml
schedule:
  - cron: "30 9 * * 1-5"   # 09:30 UTC, Mon–Fri
```
WIB is UTC+7, so `30 9` = 16:30 WIB. Want 17:00 WIB? Use `0 10`. Commit and push
the change.

---

## How your data persists

The workflow **caches `data/ihsg.db` between runs**, so your signal history and
paper-portfolio equity curve build up over time. The DB is also uploaded as a
downloadable **artifact** on each run (Actions → a run → Artifacts) if you ever
want to pull it back to your laptop.

To view it locally afterward: download the artifact, drop `ihsg.db` into your
local `data/` folder, then `streamlit run app/dashboard.py`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Workflow didn't run on schedule | GitHub disables schedules on repos with no activity for 60 days — just push any commit, or trigger manually. Scheduled runs can also lag a few minutes at peak times. |
| "Invalid API key" in logs | Re-check `ITICK_TOKEN` / `ITICK_HOST` secrets; your iTick key also **expires** (renew in the iTick dashboard, then update the secret). |
| No Telegram message | Confirm you messaged the bot first (Step 2.2) and that `TELEGRAM_CHAT_ID` is the number, not your username. |
| Yahoo returns no data | Occasionally rate-limited; the next scheduled run usually recovers. |

---

## Cost & limits
GitHub Actions is **free** for private repos up to 2,000 minutes/month. This job
takes ~1–3 minutes per day (~60 min/month) — comfortably free.

---

*Reminder: this is a personal decision-support tool, not financial advice, and it
does **not** place real trades. See the PRD (§3, §9) on why real auto-execution
isn't available on the free IDX path.*
