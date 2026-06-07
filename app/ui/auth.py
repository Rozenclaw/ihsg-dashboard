"""Single shared-password gate for public deployments (Streamlit Community Cloud).

On a public host the dashboard URL is reachable by anyone, so we lock the whole
app behind one password. The password is read from ``APP_PASSWORD`` (environment
variable first, then ``st.secrets``). When it is **not** set — e.g. running
locally via ``start.command`` — the gate is a no-op and the app stays open, so
local use keeps zero friction.

Call :func:`require_login` once, at the very top of the app shell, before any
page renders or any data is loaded.
"""
from __future__ import annotations

import hashlib
import hmac
import os

import streamlit as st

from src import theme


def _configured_password() -> str | None:
    """The configured app password, or None when unset (-> open app)."""
    pw = os.environ.get("APP_PASSWORD")
    if pw:
        return pw
    try:
        if "APP_PASSWORD" in st.secrets:           # type: ignore[operator]
            return str(st.secrets["APP_PASSWORD"])
    except Exception:
        pass
    return None


def _token(password: str) -> str:
    """A non-secret, password-derived token kept in the URL query string so a
    logged-in WebView stays authenticated across page reloads / app restore
    (Streamlit's session — and thus the in-memory login flag — resets on reload)."""
    return hashlib.sha256(("ihsg-auth::" + password).encode()).hexdigest()[:24]


def require_login() -> None:
    """Block the app with a password screen unless (a) no password is configured,
    (b) the visitor already authenticated this session, or (c) the URL carries a
    valid auth token (so a refresh / app-restore doesn't force a re-login)."""
    password = _configured_password()
    if not password:                # no password set -> open (local dev)
        return
    token = _token(password)
    qp = st.query_params.get("k")
    if st.session_state.get("_auth_ok") or (qp and hmac.compare_digest(str(qp), token)):
        st.session_state["_auth_ok"] = True
        return

    # --- styled login screen ---
    theme.inject(st)                # so the login page matches the cosmic theme
    theme.hero(st, "IHSG Dashboard", "Private access", badge="LOCKED")

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login", clear_on_submit=False):
            entered = st.text_input("Password", type="password",
                                    placeholder="Enter password",
                                    label_visibility="collapsed")
            ok = st.form_submit_button("Enter", width="stretch", type="primary")
        if ok:
            if hmac.compare_digest(entered or "", password):
                st.session_state["_auth_ok"] = True
                try:
                    st.query_params["k"] = token   # persist across reloads / restore
                except Exception:
                    pass
                st.rerun()
            else:
                st.error("Wrong password — try again.")
        st.caption("🔒 This personal dashboard is password-protected.")
    st.stop()
