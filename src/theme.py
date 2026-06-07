"""Cosmic-aurora PREMIUM theme for the Streamlit dashboard.

Award-winning dark "deep-space nebula" look: tinted near-black surfaces, an
animated aurora mesh backdrop with drifting glow orbs, film-grain + dot-grid
ornament layers, floating particles, frosted-glass cards with cursor-reactive
spotlight / hover lift / shimmer sweep, gradient headings & buttons, and
premium animated dropdown (expander) sections. Motion is compositor-only
(transform/opacity) and honours prefers-reduced-motion.

WHY THE IFRAME TRICK (inject): Streamlit 1.50's HTML sanitizer (DOMPurify)
drops large/complex <style> blocks injected via st.markdown / st.html, so the
full premium CSS never lands that way. A <style> created with the DOM API
INSIDE a components.html iframe and appended to the PARENT document head is NOT
sanitized, so it lands reliably on every rerun. The same iframe script also
builds the fixed ornament layers as direct children of <body> (outside
Streamlit's managed tree, so they survive reruns) and wires the cursor /
parallax handlers exactly once. Verified to apply @keyframes, CSS custom
properties and .stApp overrides in this runtime.

inject(st) is called once per rerun from app/dashboard.py (before nav.run()),
so it covers every page. It is idempotent (dedupe by element id / window flag).
"""
from __future__ import annotations

import re

import streamlit.components.v1 as components

# --------------------------------------------------------------------------- #
# Locked cosmic-aurora palette (see src/theme.py header / config.toml).        #
# --------------------------------------------------------------------------- #
BG = "#07070B"            # deepest app background (tinted near-black)
PANEL = "#0C0C13"         # panel
CARD = "#121220"          # card surface
CARD_HI = "#1A1A2B"       # raised / hover surface
TEXT = "#F5F6FA"          # primary text
TEXT_DIM = "rgba(255,255,255,0.62)"
TEXT_MUTE = "rgba(255,255,255,0.42)"
ACCENT = "#6366F1"        # electric indigo (primary)
ACCENT2 = "#22D3EE"       # cyan
ACCENT3 = "#8B5CF6"       # violet
ACCENT4 = "#2EE6C5"       # neon mint
UP = "#34D399"            # positive / up
DOWN = "#FB7185"          # negative / down
WARN = "#FBBF24"

# Gradient used for headings, the hero, primary buttons and accent rules.
GRAD = f"linear-gradient(120deg,{ACCENT} 0%,{ACCENT3} 42%,{ACCENT2} 100%)"


# --------------------------------------------------------------------------- #
# The full premium stylesheet (lands in the PARENT <head> via the iframe).     #
# --------------------------------------------------------------------------- #
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;600&display=swap');

:root{
  --bg:#07070B; --panel:#0C0C13; --card:#121220; --card-hi:#1A1A2B;
  --text:#F5F6FA; --dim:rgba(255,255,255,0.62); --mute:rgba(255,255,255,0.42);
  --accent:#6366F1; --accent2:#22D3EE; --accent3:#8B5CF6; --accent4:#2EE6C5;
  --up:#34D399; --down:#FB7185; --warn:#FBBF24;
  --hair:rgba(255,255,255,0.08); --hair-hi:rgba(255,255,255,0.16);
  --bevel: inset 0 1px 0 rgba(255,255,255,0.06);
  --shadow: 0 1px 2px rgba(0,0,0,0.45), 0 14px 44px rgba(0,0,0,0.40);
  --glow: 0 0 0 1px rgba(99,102,241,0.18), 0 18px 50px rgba(99,102,241,0.10);
  --radius:18px;
  --mx:50%; --my:18%;        /* cursor-reactive aurora highlight position */
  --grad:linear-gradient(120deg,#6366F1 0%,#8B5CF6 42%,#22D3EE 100%);
}
@property --angle{ syntax:'<angle>'; initial-value:0deg; inherits:false; }

/* ---------------- Base + transparent shells so ornaments show through ----- */
html, body{ font-size:15px; background:#07070B; }
.stApp{ background:transparent !important; color:var(--text);
  font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif; }
[data-testid="stHeader"]{ background:transparent !important; }
[data-testid="stHeader"]::before{ display:none; }
[data-testid="stAppViewContainer"]{ position:relative; z-index:1; background:transparent !important; }
[data-testid="stMain"]{ background:transparent !important; }
.block-container, [data-testid="stMainBlockContainer"]{
  position:relative; z-index:1; padding-top:2.2rem; padding-bottom:3rem; max-width:1500px; }
div[data-testid="stToolbar"]{ right:1rem; }

/* ---------------- Typography ---------------------------------------------- */
h1,h2,h3,h4,h5{ letter-spacing:-0.02em; font-weight:800; color:var(--text); }
h1{ font-weight:900; font-size:2.1rem;
  background:var(--grad); -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; }
h2{ font-size:1.6rem; } h3{ font-size:1.28rem; margin:.2rem 0 .5rem; }
h4{ font-size:1.05rem; margin:.15rem 0 .4rem; } h5{ font-size:.95rem; }
.stMarkdown a{ color:var(--accent2); text-decoration:none; }
.stMarkdown a:hover{ text-decoration:underline; }

/* tabular numerals everywhere numbers matter (no jitter on live updates) */
[data-testid="stMetricValue"], [data-testid="stMetricDelta"],
[data-testid="stDataFrame"], [data-baseweb="input"] input{
  font-variant-numeric:tabular-nums; font-feature-settings:'tnum'; }

/* ---------------- Metric cards: glass, lit edge, hover lift + spotlight ---- */
[data-testid="stMetric"]{
  position:relative; overflow:hidden;
  background:linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
  border:1px solid var(--hair); border-radius:var(--radius);
  padding:14px 16px;
  backdrop-filter:blur(16px) saturate(150%); -webkit-backdrop-filter:blur(16px) saturate(150%);
  box-shadow:var(--bevel), var(--shadow);
  transition:transform .4s cubic-bezier(.2,.8,.2,1), border-color .4s, box-shadow .4s;
}
/* cursor-reactive sheen on every card */
[data-testid="stMetric"]::before{
  content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none;
  background:radial-gradient(220px circle at var(--mx) var(--my),
            rgba(99,102,241,0.16), transparent 42%);
  opacity:0; transition:opacity .35s; }
[data-testid="stMetric"]:hover{
  transform:translateY(-4px); border-color:var(--hair-hi);
  box-shadow:var(--bevel), 0 22px 60px rgba(0,0,0,0.55), var(--glow); }
[data-testid="stMetric"]:hover::before{ opacity:1; }
[data-testid="stMetricValue"]{ font-weight:800; font-size:1.5rem; line-height:1.12; color:var(--text);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
[data-testid="stMetricLabel"]{ font-size:.72rem !important; text-transform:uppercase;
  letter-spacing:.06em; color:var(--mute); white-space:normal; overflow:visible; }
[data-testid="stMetricLabel"] p{ font-size:.72rem !important; }
[data-testid="stMetricDelta"]{ font-size:.82rem !important; font-weight:600; }

/* ---------------- Premium animated DROPDOWN (expander) -------------------- */
[data-testid="stExpander"]{
  border:none !important; background:transparent !important; margin:.2rem 0 .1rem; }
[data-testid="stExpander"] details{
  position:relative; overflow:hidden;
  background:linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015));
  border:1px solid var(--hair); border-radius:var(--radius);
  backdrop-filter:blur(16px) saturate(140%); -webkit-backdrop-filter:blur(16px) saturate(140%);
  box-shadow:var(--bevel), var(--shadow);
  transition:border-color .35s, box-shadow .35s, transform .35s; }
[data-testid="stExpander"] details:hover{
  border-color:var(--hair-hi); box-shadow:var(--bevel), var(--shadow), var(--glow); }
/* glowing gradient accent rail on the left of the header */
[data-testid="stExpander"] details > summary{
  position:relative; padding:.72rem 1rem .72rem 1.1rem; font-weight:700; font-size:1.02rem;
  color:var(--text); list-style:none; cursor:pointer; transition:color .25s; }
[data-testid="stExpander"] details > summary::before{
  content:""; position:absolute; left:0; top:14%; bottom:14%; width:3px; border-radius:3px;
  background:var(--grad); box-shadow:0 0 14px rgba(99,102,241,0.7);
  transform:scaleY(.5); opacity:.55; transition:transform .35s, opacity .35s; }
[data-testid="stExpander"] details[open] > summary::before{ transform:scaleY(1); opacity:1; }
[data-testid="stExpander"] details > summary:hover{ color:var(--accent2); }
[data-testid="stExpander"] details[open]{ box-shadow:var(--bevel), var(--shadow), var(--glow); }
/* chevron rotate */
[data-testid="stExpander"] summary svg{ transition:transform .35s cubic-bezier(.2,.8,.2,1); }
/* direct-child combinator so an OPEN outer expander does not rotate a COLLAPSED
   inner expander's chevron (nested expanders are allowed in Streamlit 1.50). */
[data-testid="stExpander"] details[open] > summary svg{ transform:rotate(90deg); }
/* the panel body reveals with a soft slide */
[data-testid="stExpander"] details[open] > div{ animation:revealY .45s cubic-bezier(.2,.8,.2,1) both; }

/* ---------------- Buttons: gradient glass + shimmer sweep ----------------- */
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button{
  position:relative; overflow:hidden; font-weight:650; color:var(--text);
  background:linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
  border:1px solid var(--hair); border-radius:13px; padding:.46rem .95rem;
  transition:transform .25s cubic-bezier(.2,.8,.2,1), border-color .25s, box-shadow .25s; }
.stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover{
  transform:translateY(-2px); border-color:var(--hair-hi);
  box-shadow:0 12px 30px rgba(0,0,0,0.5), 0 0 26px rgba(99,102,241,0.28); }
.stButton>button::after, .stDownloadButton>button::after, .stFormSubmitButton>button::after{
  content:""; position:absolute; top:0; left:-130%; width:55%; height:100%;
  background:linear-gradient(120deg, transparent, rgba(255,255,255,0.28), transparent);
  transform:skewX(-18deg); transition:left .6s ease; }
.stButton>button:hover::after, .stDownloadButton>button:hover::after,
.stFormSubmitButton>button:hover::after{ left:150%; }
/* primary = solid aurora gradient */
.stButton>button[kind="primary"], .stFormSubmitButton>button,
[data-testid="stBaseButton-primary"]{
  background:var(--grad) !important; border:1px solid rgba(99,102,241,0.5) !important;
  color:#0a0a12 !important; font-weight:750; box-shadow:0 10px 26px rgba(99,102,241,0.30); }
.stButton>button[kind="primary"]:hover{ box-shadow:0 16px 40px rgba(99,102,241,0.45); }
.stButton>button:active{ transform:translateY(0) scale(.98); }

/* ---------------- Inputs / selects / multiselect chips -------------------- */
[data-baseweb="select"]>div, .stTextInput input, .stNumberInput input,
.stTextArea textarea, [data-baseweb="input"]{
  background:rgba(255,255,255,0.04) !important; border:1px solid var(--hair) !important;
  border-radius:12px !important; color:var(--text) !important; }
[data-baseweb="select"]>div:focus-within, .stTextInput input:focus,
.stNumberInput input:focus{ border-color:var(--accent) !important;
  box-shadow:0 0 0 3px rgba(99,102,241,0.18) !important; }
span[data-baseweb="tag"]{
  background:var(--grad) !important; border:none !important; color:#0a0a12 !important;
  border-radius:9px !important; font-weight:600; }

/* ---------------- Radio / segmented as glass pills ------------------------ */
.stRadio [role="radiogroup"]{ gap:.4rem; }
.stRadio [role="radiogroup"] label{
  background:rgba(255,255,255,0.04); border:1px solid var(--hair);
  border-radius:11px; padding:.3rem .7rem; transition:all .25s; }
.stRadio [role="radiogroup"] label:hover{ border-color:var(--hair-hi);
  background:rgba(99,102,241,0.10); }

/* ---------------- Sidebar: deep frosted glass ----------------------------- */
[data-testid="stSidebar"]{ background:transparent !important; }
[data-testid="stSidebar"]>div:first-child{
  background:linear-gradient(180deg, rgba(14,14,26,0.82), rgba(8,8,16,0.88)) !important;
  border-right:1px solid var(--hair);
  backdrop-filter:blur(26px) saturate(150%); -webkit-backdrop-filter:blur(26px) saturate(150%); }
/* st.navigation links: active = accent tint + left rail */
[data-testid="stSidebarNav"] a{ border-radius:11px; transition:background .2s, box-shadow .2s; }
[data-testid="stSidebarNav"] a:hover{ background:rgba(99,102,241,0.10); }
[data-testid="stSidebarNav"] a[aria-current="page"]{
  background:rgba(99,102,241,0.14); box-shadow:inset 3px 0 0 var(--accent); }

/* ---------------- DataFrames / tables / plotly: glass frames -------------- */
[data-testid="stDataFrame"], [data-testid="stTable"]{
  border-radius:14px; overflow:hidden; border:1px solid var(--hair);
  box-shadow:var(--bevel), var(--shadow); }
[data-testid="stPlotlyChart"]{
  border-radius:var(--radius); overflow:hidden; border:1px solid var(--hair);
  box-shadow:var(--bevel), var(--shadow);
  background:linear-gradient(180deg, rgba(255,255,255,0.025), rgba(0,0,0,0.10)); }

/* ---------------- Alerts / popover / toast as glass ----------------------- */
[data-testid="stAlert"], [data-testid="stNotification"]{
  border-radius:14px; border:1px solid var(--hair); }
[data-testid="stPopoverBody"], [data-baseweb="popover"] [role="dialog"]{
  background:rgba(16,16,28,0.92) !important; border:1px solid var(--hair-hi) !important;
  border-radius:16px !important; backdrop-filter:blur(22px) saturate(150%);
  box-shadow:0 24px 70px rgba(0,0,0,0.6); }
div[data-baseweb="toast"]{ background:rgba(16,16,28,0.94) !important;
  border:1px solid var(--hair-hi) !important; border-radius:13px !important; }

/* tabs */
.stTabs [data-baseweb="tab-list"]{ gap:.3rem; border-bottom:1px solid var(--hair); }
.stTabs [data-baseweb="tab"]{ border-radius:11px 11px 0 0; }
.stTabs [aria-selected="true"]{ color:var(--accent2) !important; }

hr{ border:none; height:1px;
  background:linear-gradient(90deg, transparent, var(--hair-hi), transparent);
  margin:.7rem 0 !important; }

/* ---------------- Entrance: staggered rise on the main column ------------- */
section[data-testid="stMain"] .block-container > div > [data-testid="stVerticalBlock"] > div{
  animation:revealY .55s cubic-bezier(.2,.8,.2,1) both; }
section[data-testid="stMain"] .block-container > div > [data-testid="stVerticalBlock"] > div:nth-child(1){animation-delay:.02s}
section[data-testid="stMain"] .block-container > div > [data-testid="stVerticalBlock"] > div:nth-child(2){animation-delay:.07s}
section[data-testid="stMain"] .block-container > div > [data-testid="stVerticalBlock"] > div:nth-child(3){animation-delay:.12s}
section[data-testid="stMain"] .block-container > div > [data-testid="stVerticalBlock"] > div:nth-child(4){animation-delay:.17s}
section[data-testid="stMain"] .block-container > div > [data-testid="stVerticalBlock"] > div:nth-child(5){animation-delay:.22s}
section[data-testid="stMain"] .block-container > div > [data-testid="stVerticalBlock"] > div:nth-child(n+6){animation-delay:.27s}

/* ---------------- Keyframes ----------------------------------------------- */
@keyframes revealY{ from{opacity:0; transform:translate3d(0,14px,0)} to{opacity:1; transform:none} }
@keyframes pulse{ 0%,100%{opacity:1; box-shadow:0 0 10px currentColor} 50%{opacity:.45; box-shadow:0 0 2px currentColor} }
@keyframes floatUp{ 0%{transform:translate(0,0); opacity:0} 12%{opacity:.7} 88%{opacity:.7} 100%{transform:translate(var(--drift,0px),-120vh); opacity:0} }
@keyframes spin{ to{ --angle:360deg } }
@keyframes shimmer{ 0%{background-position:100% 0} 100%{background-position:-100% 0} }
@keyframes hueShift{ 0%{filter:hue-rotate(0deg)} 100%{filter:hue-rotate(26deg)} }

/* ---------------- Reusable premium component classes ---------------------- */
.aurora-hero{ position:relative; overflow:hidden; border-radius:24px; padding:26px 28px 22px;
  background:linear-gradient(135deg, rgba(99,102,241,0.14), rgba(34,211,238,0.06) 60%, rgba(139,92,246,0.12));
  border:1px solid var(--hair-hi); box-shadow:var(--bevel), var(--shadow);
  backdrop-filter:blur(18px) saturate(150%); -webkit-backdrop-filter:blur(18px) saturate(150%); margin-bottom:.4rem; }
.aurora-hero::after{ content:""; position:absolute; inset:-1px; border-radius:inherit; padding:1px;
  background:conic-gradient(from var(--angle), rgba(99,102,241,0.0), rgba(99,102,241,0.55), rgba(34,211,238,0.55), rgba(139,92,246,0.0));
  -webkit-mask:linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite:xor; mask-composite:exclude;
  animation:spin 8s linear infinite; pointer-events:none; opacity:.7; }
.aurora-title{ font-size:2.5rem; font-weight:900; letter-spacing:-0.03em; line-height:1.05;
  background:linear-gradient(120deg,#FFFFFF 0%,#A5B0FF 46%,#38E1F0 100%);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
/* leading title emoji rendered as its own COLOR icon tile — kept OUT of the
   gradient-clipped .aurora-title (color emoji can't be background-clipped, they
   render as a blank box). text-fill-color:initial guarantees full colour. */
.aurora-hero-ico{ display:inline-grid; place-items:center; width:46px; height:46px;
  border-radius:14px; font-size:1.55rem; line-height:1; flex:0 0 auto;
  background:linear-gradient(135deg, rgba(99,102,241,0.26), rgba(34,211,238,0.16));
  border:1px solid var(--hair-hi); box-shadow:var(--bevel), 0 8px 24px rgba(99,102,241,0.18);
  -webkit-text-fill-color:initial; }
.aurora-sub{ color:var(--dim); font-size:.95rem; margin-top:4px; }
.live-badge{ display:inline-flex; align-items:center; gap:7px; padding:4px 13px; border-radius:999px;
  font-size:.72rem; font-weight:700; letter-spacing:.05em; color:var(--accent2);
  background:rgba(34,211,238,0.10); border:1px solid rgba(34,211,238,0.32); }
.live-dot{ width:7px; height:7px; border-radius:50%; background:var(--accent2); color:var(--accent2);
  display:inline-block; animation:pulse 1.8s infinite; }
.sec-head{ display:flex; align-items:center; gap:11px; margin:.2rem 0 .55rem; }
.sec-ico{ width:34px; height:34px; border-radius:11px; display:grid; place-items:center; font-size:1.05rem;
  background:linear-gradient(135deg, rgba(99,102,241,0.22), rgba(34,211,238,0.14));
  border:1px solid var(--hair-hi); box-shadow:var(--bevel); }
.sec-title{ font-size:1.3rem; font-weight:800; letter-spacing:-0.02em; color:var(--text); }
.sec-sub{ font-size:.82rem; color:var(--mute); margin-top:1px; }
.chip{ display:inline-flex; align-items:center; gap:6px; padding:3px 11px; border-radius:999px;
  font-size:.74rem; font-weight:600; border:1px solid var(--hair); background:rgba(255,255,255,0.04);
  color:var(--dim); }

/* ---------------- Scrollbars ---------------------------------------------- */
::-webkit-scrollbar{ width:10px; height:10px; }
::-webkit-scrollbar-track{ background:transparent; }
::-webkit-scrollbar-thumb{ background:rgba(255,255,255,0.12); border-radius:10px; }
::-webkit-scrollbar-thumb:hover{ background:rgba(99,102,241,0.45); }

/* ---------------- Ornament layers (built in JS, styled here) -------------- */
#aurora-orn{ position:fixed; inset:0; z-index:0; pointer-events:none; overflow:hidden; }
/* NOTE: mesh positions are STATIC (no var(--mx/my)) so pointer movement never
   repaints this full-screen gradient or re-blurs the glass cards above it. The
   drifting orbs (cheap compositor transforms) carry the cursor reactivity. */
#aurora-orn .mesh{ position:absolute; inset:0;
  background:
    radial-gradient(58vw 58vw at 16% 6%, rgba(99,102,241,0.30), transparent 58%),
    radial-gradient(54vw 54vw at 86% 4%, rgba(139,92,246,0.26), transparent 55%),
    radial-gradient(60vw 56vw at 52% 104%, rgba(46,230,197,0.16), transparent 60%),
    var(--bg); }
/* Orbs are STATIC at idle (no perpetual animation): a continuously-moving
   backdrop would force every backdrop-filter glass card above to re-blur every
   frame (jank, esp. on the fanless M1 Air). Their life comes from cursor
   parallax — the JS sets a transform on pointermove and this transition glides
   it, so motion happens only on interaction, not endlessly at idle. */
#aurora-orn .orb{ position:absolute; border-radius:50%; filter:blur(80px); opacity:.5;
  will-change:transform; transition:transform .8s cubic-bezier(.2,.8,.2,1); }
#aurora-orn .orb.o1{ width:46vw; height:46vw; left:-8vw; top:-12vw;
  background:radial-gradient(circle, rgba(99,102,241,0.55), transparent 70%); }
#aurora-orn .orb.o2{ width:40vw; height:40vw; right:-10vw; top:-6vw;
  background:radial-gradient(circle, rgba(139,92,246,0.50), transparent 70%); }
#aurora-orn .orb.o3{ width:48vw; height:48vw; left:32vw; bottom:-22vw;
  background:radial-gradient(circle, rgba(46,230,197,0.34), transparent 70%); }
#aurora-orn .grid{ position:absolute; inset:0; opacity:.5;
  background-image:radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size:24px 24px;
  -webkit-mask:radial-gradient(120vw 90vh at 50% 0%, #000 30%, transparent 78%);
          mask:radial-gradient(120vw 90vh at 50% 0%, #000 30%, transparent 78%); }
#aurora-orn .grain{ position:absolute; inset:0; opacity:.05; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
#aurora-orn .pt{ position:absolute; bottom:-12px; width:3px; height:3px; border-radius:50%;
  background:rgba(180,200,255,0.9); box-shadow:0 0 8px rgba(120,150,255,0.9);
  will-change:transform, opacity; }

@media (prefers-reduced-motion:reduce){
  *{ animation-duration:.001ms !important; animation-iteration-count:1 !important;
     transition-duration:.001ms !important; }
  #aurora-orn .pt{ display:none; }
}
"""


# JavaScript run inside the component iframe: lands the CSS in the parent head,
# builds the ornament layers once, and wires cursor-reactive + parallax handlers
# exactly once (guarded by window flags so reruns don't stack listeners).
_JS = """
(function(){
  var doc = window.parent.document, win = window.parent;
  // 1) stylesheet
  var ID='aurora-css', tag=doc.getElementById(ID);
  if(!tag){ tag=doc.createElement('style'); tag.id=ID; doc.head.appendChild(tag); }
  tag.textContent = %(css)r;
  // 2) ornament layers (once)
  var orn=doc.getElementById('aurora-orn');
  if(!orn){
    orn=doc.createElement('div'); orn.id='aurora-orn';
    orn.innerHTML='<div class="mesh"></div><div class="orb o1"></div>'+
      '<div class="orb o2"></div><div class="orb o3"></div>'+
      '<div class="grid"></div><div class="grain"></div>';
    var reduce = win.matchMedia && win.matchMedia('(prefers-reduced-motion:reduce)').matches;
    if(!reduce){
      for(var i=0;i<12;i++){
        var p=doc.createElement('div'); p.className='pt';
        var L=(i*8.1+4)%%100, dur=14+(i%%7)*3, delay=-(i*1.9), drift=((i%%5)-2)*22;
        p.style.left=L+'vw';
        p.style.animation='floatUp '+dur+'s linear '+delay+'s infinite';
        p.style.setProperty('--drift', drift+'px');
        p.style.opacity='0';
        orn.appendChild(p);
      }
    }
    doc.body.insertBefore(orn, doc.body.firstChild);
  }
  // 3) cursor-reactive aurora highlight + subtle orb parallax (listeners once)
  if(!win.__auroraInit){
    win.__auroraInit=true;
    var root=doc.documentElement, raf=null, mx=50, my=18;
    win.addEventListener('pointermove', function(e){
      mx = e.clientX / win.innerWidth * 100;
      my = e.clientY / win.innerHeight * 100;
      if(raf) return;
      raf=win.requestAnimationFrame(function(){
        root.style.setProperty('--mx', mx.toFixed(1)+'%%');
        root.style.setProperty('--my', my.toFixed(1)+'%%');
        var o=doc.getElementById('aurora-orn');
        if(o){
          var dx=(mx-50)/50, dy=(my-50)/50;
          var orbs=o.querySelectorAll('.orb');
          if(orbs[0]) orbs[0].style.transform='translate3d('+(dx*18)+'px,'+(dy*14)+'px,0)';
          if(orbs[1]) orbs[1].style.transform='translate3d('+(-dx*22)+'px,'+(dy*12)+'px,0)';
          if(orbs[2]) orbs[2].style.transform='translate3d('+(dx*12)+'px,'+(-dy*16)+'px,0)';
        }
        raf=null;
      });
    }, {passive:true});
  }
})();
"""


def inject(st) -> None:
    """Inject the premium theme + ornaments into the PARENT document via the
    iframe trick. Call once per rerun (idempotent). height=0 keeps it invisible."""
    payload = "<script>%s</script>" % (_JS % {"css": CSS})
    components.html(payload, height=0, width=0)


# --------------------------------------------------------------------------- #
# Inline-HTML helpers (inline style="" attrs survive the sanitizer).           #
# --------------------------------------------------------------------------- #
# Leading emoji / pictographic icon at the start of a title (so it can be split
# off and rendered in colour outside the gradient-clipped title text).
_ICON_RE = re.compile(
    "^([\U0001F000-\U0001FAFF←-⇿⌀-➿⬀-⯿"
    "️‍⃣™ℹⓂ㊗㊙]+)\\s*(.+)$",
    re.DOTALL)


def _split_icon(title: str):
    """('📈 IHSG …') -> ('📈', 'IHSG …'); ('Plain') -> ('', 'Plain')."""
    m = _ICON_RE.match(title.strip())
    return (m.group(1), m.group(2)) if m else ("", title.strip())


def hero(st, title: str, subtitle: str = "", badge: str = "LIVE") -> None:
    """Animated aurora hero: colour icon tile + gradient title + pulsing badge.

    A leading emoji in `title` is split into its own colour tile so it is NOT
    swallowed by the gradient text-clip (which renders colour emoji as a blank
    box). The live dot is a CSS-drawn circle (no glyph) to avoid a double dot."""
    icon, text = _split_icon(title)
    icon_html = f'<span class="aurora-hero-ico">{icon}</span>' if icon else ""
    badge_html = (
        f'<span class="live-badge"><span class="live-dot"></span>{badge}</span>'
        if badge else "")
    st.markdown(
        f'<div class="aurora-hero">'
        f'  <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">'
        f'    {icon_html}<span class="aurora-title">{text}</span>{badge_html}'
        f'  </div>'
        f'  <div class="aurora-sub">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True)


def section_header(st, title: str, icon: str = "✦", sub: str = "") -> None:
    """A premium section header (gradient icon tile + title + optional subtitle)
    for the KEY always-open sections (not wrapped in a dropdown)."""
    sub_html = f'<div class="sec-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="sec-head"><div class="sec-ico">{icon}</div>'
        f'<div><div class="sec-title">{title}</div>{sub_html}</div></div>',
        unsafe_allow_html=True)


def glass_card(st, title: str, body_md: str, accent: str = ACCENT) -> None:
    """Standalone liquid-glass card (hero/section highlight)."""
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.10);'
        f' border-left:3px solid {accent}; border-radius:18px; padding:16px 18px; margin:6px 0;'
        f' backdrop-filter:blur(16px) saturate(150%); box-shadow:var(--bevel),var(--shadow);">'
        f'<div style="font-weight:700; font-size:1.02rem; margin-bottom:6px;">{title}</div>'
        f'<div style="color:#9aa7bd; font-size:.92rem; line-height:1.5;">{body_md}</div></div>',
        unsafe_allow_html=True)
