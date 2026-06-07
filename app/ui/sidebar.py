"""Sidebar: language switch, data-refresh controls, and the auto-refresh loop."""
from __future__ import annotations

from ui.common import LANG, T, db, i18n, st


def _set_lang(code: str):
    """on_click callback: set the UI language. Runs before the rerun, so the
    whole app (nav + every page) re-renders in the new language in ONE click."""
    st.session_state["lang"] = code


def sidebar_data_controls():
    import datetime as _dt
    from src import fetch

    # Language switch via two buttons (not st.radio): a button fires reliably on
    # the FIRST click and its on_click callback commits before the rerun, so a
    # single click switches the entire app. (st.radio dropped the first click;
    # st.segmented_control could deselect to None.)
    cur = LANG()
    st.sidebar.caption(i18n.t("side.language", cur))
    lc1, lc2 = st.sidebar.columns(2)
    lc1.button("🇬🇧 English", key="lang_en", width="stretch",
               type="primary" if cur == "EN" else "secondary",
               on_click=_set_lang, args=("EN",))
    lc2.button("🇮🇩 Indonesia", key="lang_id", width="stretch",
               type="primary" if cur == "ID" else "secondary",
               on_click=_set_lang, args=("ID",))
    st.sidebar.divider()

    st.sidebar.header(T("side.data"))
    last = db.last_refresh()
    if last:
        st.sidebar.caption(f"{T('side.last_pull')}: {last['run_at']} UTC\n\n"
                           f"{last['source']} · {last['symbols']} · {last['status']}")
    else:
        st.sidebar.caption(T("side.no_data"))

    if st.sidebar.button(T("side.refresh_now"), width="stretch", type="primary"):
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
