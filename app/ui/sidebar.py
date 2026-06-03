"""Sidebar: language switch, data-refresh controls, and the auto-refresh loop."""
from __future__ import annotations

from ui.common import CFG, LANG, T, db, i18n, st


def sidebar_data_controls():
    import datetime as _dt
    from src import fetch

    st.sidebar.radio(
        i18n.t("side.language", LANG()), options=["EN", "ID"],
        format_func=lambda c: "🇬🇧 English" if c == "EN" else "🇮🇩 Bahasa Indonesia",
        key="lang", horizontal=True)
    st.sidebar.divider()

    st.sidebar.header(T("side.data"))
    last = db.last_refresh()
    if last:
        st.sidebar.caption(f"{T('side.last_pull')}: {last['run_at']} UTC\n\n"
                           f"{last['source']} · {last['symbols']} · {last['status']}")
    else:
        st.sidebar.caption(T("side.no_data"))

    if st.sidebar.button(T("side.refresh_now"), use_container_width=True, type="primary"):
        with st.spinner(T("side.refreshing")):
            try:
                summary = fetch.refresh(full_universe=False, with_fundamentals=True,
                                        verbose=False)
                st.cache_data.clear()
                st.sidebar.success(f"Updated {summary['ok']} ({summary['rows']} rows).")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Refresh failed: {e}")

    st.sidebar.divider()
    auto = st.sidebar.toggle(T("side.auto_refresh"), value=False)
    interval_min = st.sidebar.select_slider(
        T("side.every"), options=[15, 30, 60, 120, 240], value=60,
        disabled=not auto, format_func=lambda m: f"{m} min")
    if auto:
        now = _dt.datetime.utcnow()
        key = "last_auto_refresh"
        prev = st.session_state.get(key)
        if prev is None or (now - prev).total_seconds() >= interval_min * 60:
            st.session_state[key] = now
            try:
                fetch.refresh(full_universe=False, with_fundamentals=True, verbose=False)
                st.cache_data.clear()
            except Exception:
                pass
        nxt = st.session_state[key] + _dt.timedelta(minutes=interval_min)
        st.sidebar.caption(f"Next ~{nxt.strftime('%H:%M')} UTC")
        frag = getattr(st, "fragment", None)
        if frag is not None:
            @st.fragment(run_every=min(interval_min * 60, 300))
            def _tick():
                st.empty()
            _tick()

    st.sidebar.divider()
    st.sidebar.caption(T("side.best_practice"))
