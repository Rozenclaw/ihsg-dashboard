"""Bilingual UI strings (English / Bahasa Indonesia).

Design rule — "smart" translation: financial & technical terms that are normally
used in English by Indonesian investors are kept in English even inside Bahasa
text (e.g. RSI, Bollinger Band, SMA, BUY/SELL/HOLD, yield, dividend, support,
uptrend, stop-loss, target, lot, ticker codes). We do NOT force literal
Indonesian for those — it would read unnaturally. Only the surrounding,
explanatory prose is translated.

Usage:
    from src import i18n
    i18n.t("section.recommendations", lang)   # lang in {"EN","ID"}
"""
from __future__ import annotations

DEFAULT_LANG = "EN"

# key -> {EN, ID}
STRINGS: dict[str, dict[str, str]] = {
    # Title / header
    "app.title": {"EN": "📈 IHSG Personal Dashboard",
                  "ID": "📈 Dashboard Saham IHSG Pribadi"},
    "app.subtitle": {
        "EN": "Phase 2 · recommendations + live explanations · not financial advice",
        "ID": "Fase 2 · rekomendasi + penjelasan live · bukan saran finansial"},

    # Sidebar / data controls
    "side.data": {"EN": "⚙️ Data", "ID": "⚙️ Data"},
    "side.language": {"EN": "🌐 Language", "ID": "🌐 Bahasa"},
    "side.refresh_now": {"EN": "🔄 Refresh from Yahoo now",
                         "ID": "🔄 Ambil data terbaru dari Yahoo"},
    "side.auto_refresh": {"EN": "Auto-refresh", "ID": "Auto-refresh"},
    "side.every": {"EN": "Every", "ID": "Setiap"},
    "side.last_pull": {"EN": "Last pull", "ID": "Update terakhir"},
    "side.no_data": {"EN": "No data pulled yet.", "ID": "Belum ada data diambil."},
    "side.refreshing": {"EN": "Pulling latest prices from Yahoo Finance…",
                        "ID": "Mengambil harga terbaru dari Yahoo Finance…"},
    "side.best_practice": {
        "EN": "**Best practice:** IDX closes ~16:00 WIB and Yahoo posts the daily "
              "close shortly after. For hands-off daily updates even when this "
              "page is closed, use the scheduled job (Phase 3) — see README.",
        "ID": "**Tips:** IDX tutup ~16:00 WIB dan Yahoo merilis harga penutupan "
              "tak lama setelahnya. Untuk update harian otomatis walau halaman ini "
              "ditutup, pakai scheduled job (Fase 3) — lihat README."},

    # Index header
    "index.title": {"EN": "IDX Composite (IHSG)", "ID": "Indeks IHSG (IDX Composite)"},
    "index.level": {"EN": "Level", "ID": "Level"},
    "index.trend": {"EN": "Trend", "ID": "Tren"},
    "index.range_pos": {"EN": "52w range pos", "ID": "Posisi rentang 52mg"},
    "index.explain_q": {"EN": "ℹ️ What is the IHSG doing? (plain English)",
                        "ID": "ℹ️ Apa yang terjadi dengan IHSG? (bahasa sederhana)"},
    "index.no_data": {"EN": "No IHSG data yet. Run a data refresh.",
                      "ID": "Belum ada data IHSG. Jalankan refresh data."},

    # Recommendations
    "rec.title": {"EN": "📋 Daily recommendations — Dividend + Value",
                  "ID": "📋 Rekomendasi harian — Dividend + Value"},
    "rec.caption": {
        "EN": "Composite = 0.6×fundamental + 0.4×technical · entry/target/stop "
              "are model levels, not advice · tune in config.yaml",
        "ID": "Composite = 0.6×fundamental + 0.4×technical · entry/target/stop "
              "adalah level model, bukan saran · atur di config.yaml"},
    "rec.universe": {"EN": "Universe", "ID": "Total saham"},
    "rec.show_actions": {"EN": "Show actions", "ID": "Tampilkan aksi"},
    "rec.add_buy_uptrend": {"EN": "⭐ Add {n} BUY + uptrend to watchlist",
                            "ID": "⭐ Tambah {n} BUY + uptrend ke watchlist"},
    "rec.none_buy_uptrend": {"EN": "No stocks currently flagged BUY **and** uptrend.",
                             "ID": "Belum ada saham berstatus BUY **dan** uptrend."},
    "rec.added_toast": {"EN": "Added {n} stock(s) to watchlist",
                        "ID": "Menambahkan {n} saham ke watchlist"},
    "rec.already_toast": {"EN": "All BUY + uptrend picks already in watchlist",
                          "ID": "Semua pilihan BUY + uptrend sudah ada di watchlist"},
    "rec.explain_q": {"EN": "ℹ️ Explain these recommendations in plain English",
                      "ID": "ℹ️ Jelaskan rekomendasi ini dengan bahasa sederhana"},
    "rec.no_data": {"EN": "No recommendations yet. Refresh data then reload.",
                    "ID": "Belum ada rekomendasi. Refresh data lalu muat ulang."},
    "rec.disclaimer": {
        "EN": "⚠️ Decision-support only — not financial advice. Verify before trading.",
        "ID": "⚠️ Hanya alat bantu keputusan — bukan saran finansial. Verifikasi "
              "sebelum bertransaksi."},

    # Top-3 daily picks to stack
    "top3.title": {"EN": "🏆 Top 3 BUY to stack today",
                   "ID": "🏆 Top 3 BUY untuk di-stack hari ini"},
    "top3.caption": {
        "EN": "Best 3 BUY picks today for accumulating (stacking) — ranked by "
              "composite score, uptrend preferred. Levels are model guidance.",
        "ID": "3 pilihan BUY terbaik hari ini untuk akumulasi (stacking) — "
              "diurutkan dari composite score, prioritas uptrend. Level di bawah "
              "adalah panduan model."},
    "top3.none": {"EN": "No BUY picks today — nothing to stack. Come back after the "
                        "next data refresh.",
                  "ID": "Belum ada pilihan BUY hari ini — tidak ada yang di-stack. "
                        "Cek lagi setelah refresh data berikutnya."},
    "top3.entry": {"EN": "Entry", "ID": "Entry"},
    "top3.target": {"EN": "Target", "ID": "Target"},
    "top3.stop": {"EN": "Stop", "ID": "Stop"},
    "top3.size": {"EN": "Size", "ID": "Ukuran"},
    "top3.why": {"EN": "Why today", "ID": "Alasan hari ini"},
    "top3.as_of": {"EN": "as of", "ID": "per"},

    # Alerts
    "alert.title": {"EN": "🔔 Price / RSI alerts", "ID": "🔔 Alert harga / RSI"},
    "alert.caption": {
        "EN": "Get notified when a stock hits your level. The daily job checks "
              "these and sends them via your digest (Telegram/email).",
        "ID": "Dapat notifikasi saat saham menyentuh level Anda. Daily job "
              "memeriksa ini dan mengirimnya lewat digest (Telegram/email)."},
    "alert.add": {"EN": "Add alert", "ID": "Tambah alert"},
    "alert.symbol": {"EN": "Symbol", "ID": "Saham"},
    "alert.metric": {"EN": "Metric", "ID": "Metrik"},
    "alert.op": {"EN": "Condition", "ID": "Kondisi"},
    "alert.threshold": {"EN": "Threshold", "ID": "Nilai"},
    "alert.note": {"EN": "Note (optional)", "ID": "Catatan (opsional)"},
    "alert.none": {"EN": "No alerts yet.", "ID": "Belum ada alert."},
    "alert.added": {"EN": "Alert added", "ID": "Alert ditambahkan"},
    "alert.check_now": {"EN": "Check alerts now", "ID": "Cek alert sekarang"},
    "alert.triggered": {"EN": "triggered now", "ID": "aktif sekarang"},
    "alert.none_triggered": {"EN": "Nothing triggered right now.",
                             "ID": "Tidak ada yang aktif saat ini."},

    # Yield-trap
    "trap.badge": {"EN": "⚠️ Yield-trap risk", "ID": "⚠️ Risiko yield-trap"},

    # Monthly stacking allocator
    "stack.title": {"EN": "🏦 My monthly stacking guide — Top 3",
                    "ID": "🏦 Panduan stacking bulanan saya — Top 3"},
    "stack.caption": {
        "EN": "Your personal fund-allocation plan: split this month's budget "
              "into a lot-by-lot buy list across the 3 best BUY picks today.",
        "ID": "Rencana alokasi dana pribadi Anda: bagi budget bulan ini menjadi "
              "daftar beli per-lot dari 3 pilihan BUY terbaik hari ini."},
    "stack.this_month": {"EN": "This month", "ID": "Bulan ini"},
    "stack.advanced": {"EN": "Adjust budget / settings",
                       "ID": "Atur budget / pengaturan"},
    "stack.howto": {
        "EN": "Buy these whole lots in your broker app this month. Re-check near "
              "month-start as prices and picks update.",
        "ID": "Beli lot-lot ini di aplikasi broker Anda bulan ini. Cek lagi di "
              "awal bulan karena harga & pilihan bisa berubah."},
    "stack.budget": {"EN": "Monthly budget (IDR)", "ID": "Budget bulanan (IDR)"},
    "stack.names": {"EN": "Number of stocks", "ID": "Jumlah saham"},
    "stack.use_entry": {"EN": "Price at model entry (vs last close)",
                        "ID": "Harga di entry model (vs close terakhir)"},
    "stack.build": {"EN": "Build plan", "ID": "Buat rencana"},
    "stack.spent": {"EN": "Allocated", "ID": "Teralokasi"},
    "stack.leftover": {"EN": "Leftover cash", "ID": "Sisa kas"},
    "stack.picks": {"EN": "Stocks", "ID": "Saham"},
    "stack.colsym": {"EN": "Stock", "ID": "Saham"},
    "stack.collots": {"EN": "Lots", "ID": "Lot"},
    "stack.colshares": {"EN": "Shares", "ID": "Lembar"},
    "stack.colprice": {"EN": "Price", "ID": "Harga"},
    "stack.colcost": {"EN": "Cost (IDR)", "ID": "Biaya (IDR)"},
    "stack.colpct": {"EN": "% of budget", "ID": "% budget"},
    "stack.colyield": {"EN": "Yield%", "ID": "Yield%"},

    # Time-range toggle
    "range.label": {"EN": "Time range", "ID": "Rentang waktu"},
    "range.return": {"EN": "return", "ID": "return"},
    "range.high": {"EN": "high", "ID": "tertinggi"},
    "range.low": {"EN": "low", "ID": "terendah"},
    "range.avg_vol": {"EN": "Avg volume", "ID": "Rata-rata volume"},
    "range.no_data": {"EN": "No data in this range — showing latest available.",
                      "ID": "Tidak ada data di rentang ini — menampilkan data terbaru."},

    # Tier 2/3
    "port.title": {"EN": "💰 My real holdings", "ID": "💰 Portfolio saya (real)"},
    "port.caption": {
        "EN": "Track YOUR actual positions. Paste CSV: symbol, lots, avg_price[, note]. "
              "Stays on your machine.",
        "ID": "Lacak posisi ASLI Anda. Tempel CSV: symbol, lots, avg_price[, note]. "
              "Tersimpan lokal di perangkat Anda."},
    "port.import": {"EN": "Import holdings", "ID": "Import holdings"},
    "port.clear": {"EN": "Clear holdings", "ID": "Hapus holdings"},
    "port.none": {"EN": "No holdings yet. Paste your positions above.",
                  "ID": "Belum ada holdings. Tempel posisi Anda di atas."},
    "port.value": {"EN": "Market value", "ID": "Nilai pasar"},
    "port.cost": {"EN": "Cost", "ID": "Modal"},
    "port.pl": {"EN": "Unrealized P/L", "ID": "P/L belum terealisasi"},
    "port.sell_warn": {"EN": "⚠️ Strategy flags SELL on: ",
                       "ID": "⚠️ Strategi memberi sinyal SELL untuk: "},
    "news.title": {"EN": "📰 News & sentiment", "ID": "📰 Berita & sentimen"},
    "news.none": {"EN": "No recent headlines available (free source).",
                  "ID": "Belum ada berita terbaru (sumber gratis)."},
    "news.overall": {"EN": "Overall", "ID": "Keseluruhan"},
    "radar.title": {"EN": "Strength profile", "ID": "Profil kekuatan"},
    "conv.high": {"EN": "high conviction", "ID": "keyakinan tinggi"},
    "conv.medium": {"EN": "medium conviction", "ID": "keyakinan sedang"},
    "conv.speculative": {"EN": "speculative", "ID": "spekulatif"},
    "cum.label": {"EN": "Dividend", "ID": "Dividen"},

    # Watchlist / detail
    "wl.title": {"EN": "Watchlist", "ID": "Watchlist"},
    "wl.tickers": {"EN": "Tickers", "ID": "Kode saham"},
    "wl.no_data": {"EN": "No watchlist data. Run a data refresh first.",
                   "ID": "Belum ada data watchlist. Jalankan refresh data dulu."},
    "detail.title": {"EN": "Stock detail", "ID": "Detail saham"},
    "detail.symbol": {"EN": "Symbol", "ID": "Saham"},
    "chart.howto_q": {"EN": "ℹ️ How do I read this chart?",
                      "ID": "ℹ️ Bagaimana cara membaca grafik ini?"},

    # Live panel
    "live.title": {"EN": "🔴 Live quotes", "ID": "🔴 Harga live"},
    "live.updated": {"EN": "updated", "ID": "diperbarui"},
    "live.no_token": {
        "EN": "Live quotes are off — no iTick API key found. Get a free key at "
              "https://itick.org and set ITICK_TOKEN (env or .streamlit/secrets.toml).",
        "ID": "Harga live nonaktif — API key iTick tidak ditemukan. Dapatkan key "
              "gratis di https://itick.org lalu set ITICK_TOKEN (env atau "
              ".streamlit/secrets.toml)."},
    "live.unavailable": {"EN": "Live quotes unavailable",
                         "ID": "Harga live tidak tersedia"},

    # Paper portfolio
    "paper.title": {"EN": "💼 Paper portfolio (simulated)",
                    "ID": "💼 Portfolio simulasi (paper trading)"},
    "paper.caption": {
        "EN": "Virtual money — validates the strategy with zero risk.",
        "ID": "Uang virtual — menguji strategi tanpa risiko."},
    "paper.equity": {"EN": "Equity (IDR)", "ID": "Total ekuitas (IDR)"},
    "paper.cash": {"EN": "Cash", "ID": "Kas"},
    "paper.holdings": {"EN": "Holdings", "ID": "Nilai saham"},
    "paper.positions": {"EN": "Positions", "ID": "Posisi"},
    "paper.advance": {"EN": "▶️ Advance paper trade 1 day (today's signals)",
                      "ID": "▶️ Jalankan paper trade 1 hari (sinyal hari ini)"},
    "paper.reset": {"EN": "♻️ Reset paper portfolio",
                    "ID": "♻️ Reset portfolio simulasi"},
    "paper.no_pos": {
        "EN": "No open paper positions yet. Click 'Advance paper trade' to act on "
              "today's BUY signals.",
        "ID": "Belum ada posisi paper. Klik 'Jalankan paper trade' untuk "
              "mengeksekusi sinyal BUY hari ini."},

    # Backtest
    "bt.title": {"EN": "🧪 Backtest", "ID": "🧪 Backtest"},
    "bt.caption": {
        "EN": "Walk-forward simulation vs buy-and-hold IHSG. Indicative only.",
        "ID": "Simulasi walk-forward vs buy-and-hold IHSG. Hanya indikatif."},
    "bt.lookback": {"EN": "Lookback (days)", "ID": "Periode (hari)"},
    "bt.rebalance": {"EN": "Rebalance every (days)", "ID": "Rebalance tiap (hari)"},
    "bt.maxpos": {"EN": "Max positions", "ID": "Maks posisi"},
    "bt.run": {"EN": "Run backtest", "ID": "Jalankan backtest"},
    "bt.total_return": {"EN": "Total return", "ID": "Total return"},
    "bt.maxdd": {"EN": "Max drawdown", "ID": "Max drawdown"},
    "bt.set_params": {"EN": "Set parameters and click **Run backtest**.",
                      "ID": "Atur parameter lalu klik **Jalankan backtest**."},

    # Navigation
    "nav.dashboard": {"EN": "Dashboard", "ID": "Dashboard"},
    "nav.decision": {"EN": "Decision Helper", "ID": "Bantuan Keputusan"},
    "nav.daytrade": {"EN": "Daily Trading", "ID": "Trading Harian"},

    # Decision Helper page
    "dh.title": {"EN": "🧭 Decision Helper — BUY stacking",
                 "ID": "🧭 Bantuan Keputusan — BUY stacking"},
    "dh.caption": {
        "EN": "A per-day / per-month decision aid: ranked BUY picks with reasons, "
              "a risk-reward table, sector-concentration warnings, and a verdict. "
              "Decision-support only — not financial advice.",
        "ID": "Bantuan keputusan harian / bulanan: pilihan BUY berperingkat dengan "
              "alasan, tabel risk-reward, peringatan konsentrasi sektor, dan verdict. "
              "Hanya alat bantu — bukan saran finansial."},
    "dh.mode": {"EN": "Horizon", "ID": "Horizon"},
    "dh.daily": {"EN": "Today (daily)", "ID": "Hari ini (harian)"},
    "dh.monthly": {"EN": "This month (stacking)", "ID": "Bulan ini (stacking)"},
    "dh.num": {"EN": "How many picks", "ID": "Jumlah pilihan"},
    "dh.picks": {"EN": "Picks", "ID": "Pilihan"},
    "dh.total_capital": {"EN": "Total capital", "ID": "Total modal"},
    "dh.total_gain": {"EN": "Potential gain", "ID": "Potensi gain"},
    "dh.total_loss": {"EN": "Potential loss", "ID": "Potensi loss"},
    "dh.ranking": {"EN": "Priority ranking", "ID": "Ranking prioritas"},
    "dh.rr_table": {"EN": "Risk / reward", "ID": "Risk / reward"},
    "dh.sector_warn": {"EN": "⚠️ Sector concentration — pick one of: ",
                       "ID": "⚠️ Konsentrasi sektor — pilih salah satu: "},
    "dh.full_report": {"EN": "📄 Full written analysis",
                       "ID": "📄 Analisa lengkap (teks)"},
    "dh.gen_ai": {"EN": "✨ Write AI research narrative",
                  "ID": "✨ Tulis narasi riset AI"},
    "dh.ai_on": {"EN": "✨ AI-written narrative", "ID": "✨ Narasi ditulis AI"},
    "dh.det_on": {"EN": "Built-in analysis", "ID": "Analisa bawaan"},
    "dh.ai_spinner": {"EN": "Claude is writing the analysis…",
                      "ID": "Claude sedang menulis analisa…"},
    "dh.ai_unavail": {"EN": "AI narrative unavailable ({why}). Showing the built-in "
                            "analysis instead.",
                      "ID": "Narasi AI tidak tersedia ({why}). Menampilkan analisa "
                            "bawaan."},
    "dh.ai_failed": {"EN": "AI couldn't generate a narrative this time (rate limit or "
                           "network). Try again in a moment.",
                     "ID": "AI gagal membuat narasi kali ini (rate limit atau jaringan). "
                           "Coba lagi sebentar."},
    "dh.press_hint": {"EN": "Press **✨ Write AI research narrative** above to generate "
                            "the written analysis.",
                      "ID": "Tekan **✨ Tulis narasi riset AI** di atas untuk membuat "
                            "analisa tertulis."},
    "dh.download": {"EN": "⬇️ Download as Markdown", "ID": "⬇️ Unduh sebagai Markdown"},

    # Daily Trading page (liquid-universe swing shortlist + budget simulation)
    "dt.title": {"EN": "📊 Daily Trading — Liquid Swing Shortlist",
                 "ID": "📊 Trading Harian — Shortlist Swing Saham Likuid"},
    "dt.explainer": {
        "EN": "This page builds a daily-refreshed shortlist of liquid blue-chip "
              "names that look good for short-hold **swing** trading — **not** "
              "intraday scalping. Each candidate gets a 0–100 day-score from trend "
              "alignment, momentum, RSI entry timing, pullback quality, and volume "
              "confirmation, then a clear **BUY / WATCH / AVOID** signal with model "
              "entry, stop-loss, and target levels. You set a daily budget and the "
              "engine splits it across the top BUY picks in whole lots, so you see "
              "lots, cost, and risk/reward before you open your broker app. "
              "\"Daily\" means the *list* is updated every day — you still hold each "
              "trade for several days to weeks, not seconds.",
        "ID": "Halaman ini menyusun shortlist harian saham blue-chip likuid yang "
              "potensial untuk **swing** trading jangka pendek — **bukan** scalping "
              "intraday. Tiap kandidat diberi day-score 0–100 dari keselarasan "
              "trend, momentum, timing entry lewat RSI, kualitas pullback, dan "
              "konfirmasi volume, lalu sinyal jelas **BUY / WATCH / AVOID** lengkap "
              "dengan level entry, stop-loss, dan target dari model. Anda menentukan "
              "budget harian, lalu engine membaginya ke pilihan BUY teratas dalam "
              "lot penuh, jadi Anda lihat lot, biaya, dan risk/reward sebelum buka "
              "aplikasi broker. \"Harian\" berarti *daftarnya* di-refresh tiap hari "
              "— tiap posisi tetap di-hold beberapa hari hingga minggu, bukan detik."},
    "dt.universe": {"EN": "Universe scored", "ID": "Saham dinilai"},
    "dt.buys": {"EN": "BUY signals", "ID": "Sinyal BUY"},
    "dt.watch_n": {"EN": "WATCH", "ID": "WATCH"},
    "dt.avoid_n": {"EN": "AVOID", "ID": "AVOID"},
    "dt.board_title": {"EN": "📋 Today's shortlist (Top {n})",
                       "ID": "📋 Shortlist hari ini (Top {n})"},
    "dt.candidate_note": {
        "EN": "Signals are **candidates for your own review — not buy instructions**.",
        "ID": "Sinyal adalah **kandidat untuk Anda tinjau sendiri — bukan instruksi "
              "beli**."},
    "dt.col_signal": {"EN": "Signal", "ID": "Sinyal"},
    "dt.col_score": {"EN": "Score", "ID": "Score"},
    "dt.col_rr": {"EN": "R:R", "ID": "R:R"},
    "dt.col_risk": {"EN": "Stop %", "ID": "Stop %"},
    "dt.col_why": {"EN": "Why", "ID": "Alasan"},
    "dt.col_lots": {"EN": "Lots", "ID": "Lot"},
    "dt.col_shares": {"EN": "Shares", "ID": "Shares"},
    "dt.col_weight": {"EN": "%", "ID": "%"},
    "dt.cost_warn": {
        "EN": "⚠️ Round-trip cost ≈ **{pct}%** (fees + 0.1% sell tax) — price must "
              "rise that much just to break even. Frequent trading erodes a small budget.",
        "ID": "⚠️ Biaya per putaran ≈ **{pct}%** (fee + pajak jual 0,1%) — harga harus "
              "naik segitu hanya untuk balik modal. Sering trading menggerus modal kecil."},
    "dt.sim_title": {"EN": "🧮 Daily budget allocation", "ID": "🧮 Alokasi budget harian"},
    "dt.capital": {"EN": "Total trading capital (Rp)", "ID": "Total modal trading (Rp)"},
    "dt.budget": {"EN": "Today's budget (Rp)", "ID": "Budget hari ini (Rp)"},
    "dt.num": {"EN": "Max stocks", "ID": "Maks saham"},
    "dt.include_watch": {"EN": "Also allocate to WATCH (lower-confidence)",
                         "ID": "Ikut alokasikan ke WATCH (keyakinan lebih rendah)"},
    "dt.watch_used": {"EN": "Including WATCH names — lower confidence; size down.",
                      "ID": "Termasuk nama WATCH — keyakinan lebih rendah; perkecil ukuran."},
    "dt.sim_run": {"EN": "🧮 Simulate allocation", "ID": "🧮 Simulasikan alokasi"},
    "dt.sim_hint": {"EN": "Set your budget and press **🧮 Simulate allocation**.",
                    "ID": "Atur budget lalu tekan **🧮 Simulasikan alokasi**."},
    "dt.spent": {"EN": "Spent", "ID": "Terpakai"},
    "dt.leftover": {"EN": "Leftover cash", "ID": "Sisa cash"},
    "dt.net_gain": {"EN": "Net gain at target", "ID": "Net gain di target"},
    "dt.net_loss": {"EN": "Net loss if stopped", "ID": "Net loss bila kena stop"},
    "dt.net_rr": {"EN": "Net R:R", "ID": "Net R:R"},
    "dt.risk_vs_capital": {"EN": "Risk vs capital", "ID": "Risiko vs modal"},
    "dt.col_capital": {"EN": "Capital", "ID": "Modal"},
    "dt.budget_gt_capital": {
        "EN": "⚠️ Your daily budget is larger than your total capital — usually the "
              "daily budget is just a slice of it.",
        "ID": "⚠️ Budget harian Anda lebih besar dari total modal — biasanya budget "
              "harian hanyalah sebagian kecil dari modal."},
    "dt.risk_warn": {
        "EN": "⚠️ Total risk if every stop is hit is **{pct}%** of your capital — above "
              "the {cap}% comfort line. Consider fewer names or a smaller budget.",
        "ID": "⚠️ Total risiko bila semua kena stop = **{pct}%** dari modal — di atas "
              "batas nyaman {cap}%. Pertimbangkan kurangi saham atau perkecil budget."},
    "dt.tips_title": {"EN": "✅ Beginner rules", "ID": "✅ Aturan untuk pemula"},
    "dt.tips": {
        "EN": "- Trade only liquid names (LQ45/IDX30-grade) — they're easy to exit "
              "when you need out.\n"
              "- Risk at most **1% of your capital per trade** (beginners: start at 0.5%).\n"
              "- **ALWAYS set your stop-loss before you buy**, never after.\n"
              "- Only take trades with **R:R of 2 or higher** — skip anything below.\n"
              "- Never chase: avoid RSI above 70 and ARA spikes; enter on volume confirmation.\n"
              "- **Never average down past your stop** — a stop hit means the idea was wrong, exit.\n"
              "- Paper-trade the shortlist for a few weeks before risking real money.",
        "ID": "- Trade hanya saham likuid (kelas LQ45/IDX30) — mudah di-exit saat perlu keluar.\n"
              "- Risiko maksimal **1% dari modal per trade** (pemula: mulai dari 0,5%).\n"
              "- **SELALU pasang stop-loss sebelum beli**, jangan setelahnya.\n"
              "- Ambil hanya trade dengan **R:R 2 atau lebih** — lewati yang di bawah itu.\n"
              "- Jangan FOMO: hindari RSI di atas 70 dan saham yang sudah ARA; masuk saat ada konfirmasi volume.\n"
              "- **Jangan average down menembus stop** — stop kena artinya ide-nya salah, langsung exit.\n"
              "- Paper-trading dulu shortlist ini beberapa minggu sebelum pakai uang sungguhan."},
    "dt.caveats_title": {"EN": "⚠️ Honest caveats", "ID": "⚠️ Catatan jujur"},
    "dt.caveats": {
        "EN": "- This is a daily-refreshed **swing** shortlist, not intraday scalping — "
              "you still hold each trade for days to weeks.\n"
              "- Backtested swing win rates run roughly 50–65%, but **past performance "
              "is no guarantee of future results**.\n"
              "- Transaction costs (~0.15–0.25% per side + 0.1% sell tax) quietly eat a "
              "small budget if you overtrade.\n"
              "- Scores and entry/stop/target are **model levels** from daily OHLCV data — "
              "not predictions, and they can be wrong.\n"
              "- The universe is a small set of stored blue-chips, so on quiet days there "
              "may be **few or no clean BUY picks** — that's normal.",
        "ID": "- Ini shortlist **swing** yang di-refresh harian, bukan scalping intraday — "
              "tiap posisi tetap di-hold beberapa hari hingga minggu.\n"
              "- Win rate swing dari backtest berkisar 50–65%, tapi **performa masa lalu "
              "bukan jaminan hasil ke depan**.\n"
              "- Biaya transaksi (~0,15–0,25% per sisi + pajak jual 0,1%) diam-diam "
              "menggerus modal kecil kalau Anda overtrade.\n"
              "- Score dan level entry/stop/target adalah **level model** dari data OHLCV "
              "harian — bukan prediksi, dan bisa meleset.\n"
              "- Universe-nya kumpulan kecil blue-chip tersimpan, jadi di hari sepi bisa "
              "**sedikit atau tanpa pilihan BUY yang bersih** — itu normal."},
    "dt.disclaimer": {
        "EN": "⚠️ Decision-support only — **not financial advice**. Set your stop and "
              "verify before trading.",
        "ID": "⚠️ Hanya alat bantu keputusan — **bukan saran finansial**. Pasang stop dan "
              "verifikasi sebelum bertransaksi."},
    "dt.ai_title": {"EN": "🤖 AI coach note (optional)", "ID": "🤖 Catatan AI coach (opsional)"},
    "dt.gen_ai": {"EN": "✨ Write AI coach note", "ID": "✨ Tulis catatan AI coach"},
    "dt.ai_on": {"EN": "✨ AI-written coach note", "ID": "✨ Catatan ditulis AI"},
    "dt.ai_spinner": {"EN": "Writing the analysis…", "ID": "Sedang menulis analisa…"},
    "dt.press_hint": {"EN": "Press **✨ Write AI coach note** to get a written, risk-first "
                            "read-through of today's shortlist.",
                      "ID": "Tekan **✨ Tulis catatan AI coach** untuk ulasan tertulis "
                            "(fokus risiko) atas shortlist hari ini."},
}


def t(key: str, lang: str = DEFAULT_LANG, **fmt) -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    s = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    return s.format(**fmt) if fmt else s
