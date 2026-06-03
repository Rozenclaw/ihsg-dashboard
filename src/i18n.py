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
    "live.title": {"EN": "🔴 Live quotes (iTick)", "ID": "🔴 Harga live (iTick)"},
    "live.updated": {"EN": "updated", "ID": "diperbarui"},
    "live.no_token": {
        "EN": "Live quotes are off — no iTick API key found. Get a free key at "
              "https://itick.org and set ITICK_TOKEN (env or .streamlit/secrets.toml).",
        "ID": "Harga live nonaktif — API key iTick tidak ditemukan. Dapatkan key "
              "gratis di https://itick.org lalu set ITICK_TOKEN (env atau "
              ".streamlit/secrets.toml)."},

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
}


def t(key: str, lang: str = DEFAULT_LANG, **fmt) -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    s = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    return s.format(**fmt) if fmt else s
