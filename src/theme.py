"""Premium dark 'liquid glass' theme for the Streamlit dashboard.

Injects a single block of high-end CSS: glassmorphism cards, soft depth,
animated gradient backdrop, refined typography (Inter), smooth transitions,
and fixes for text truncation (no clipped labels/metrics). Pure CSS — no extra
dependencies, works on the standard Streamlit runtime.

Call theme.inject(st) once, right after st.set_page_config().
"""
from __future__ import annotations

CSS = r"""
<style>
/* ---------- Fonts ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  --glass-bg: rgba(22, 30, 46, 0.55);
  --glass-bg-strong: rgba(28, 38, 58, 0.72);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-border-hi: rgba(94, 234, 212, 0.35);
  --accent: #5eead4;          /* teal */
  --accent-2: #818cf8;        /* indigo */
  --accent-3: #f472b6;        /* pink */
  --text: #e8edf4;
  --text-dim: #9aa7bd;
  --radius: 18px;
  --shadow: 0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06);
}

/* ---------- App backdrop: deep dark with slow aurora glow ---------- */
.stApp{
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(94,234,212,0.10), transparent 60%),
    radial-gradient(1000px 700px at 110% 10%, rgba(129,140,248,0.12), transparent 55%),
    radial-gradient(900px 600px at 50% 120%, rgba(244,114,182,0.07), transparent 60%),
    #070b12;
  background-attachment: fixed;
  color: var(--text);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.stApp::before{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background: radial-gradient(800px 400px at var(--mx,30%) var(--my,20%),
              rgba(94,234,212,0.06), transparent 70%);
  animation: drift 18s ease-in-out infinite alternate;
}
@keyframes drift{
  0%{transform:translate3d(-2%, -1%, 0)} 100%{transform:translate3d(3%, 2%, 0)}
}

/* keep content above backdrop */
.block-container{position:relative; z-index:1; padding-top:2.2rem; max-width:1400px;}

/* ---------- Typography ---------- */
h1, h2, h3, h4{ letter-spacing:-0.02em; font-weight:700; }
h1{ font-weight:800;
  background: linear-gradient(120deg, #ffffff 0%, var(--accent) 55%, var(--accent-2) 100%);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
}
/* anti-truncation: let text wrap & breathe everywhere */
.stMarkdown, .stMarkdown p, label, .stMetric, .stCaption, span, div[data-testid="stMetricValue"]{
  overflow: visible !important; text-overflow: clip !important; white-space: normal !important;
}
[data-testid="stMetricLabel"]{ white-space: normal !important; overflow: visible !important; }
[data-testid="stMetricValue"]{ font-weight:700; line-height:1.15; }

/* ---------- Glass cards: metrics, expanders, dataframes ---------- */
div[data-testid="stMetric"]{
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius);
  padding: 16px 18px;
  backdrop-filter: blur(18px) saturate(160%);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  box-shadow: var(--shadow);
  transition: transform .35s cubic-bezier(.2,.8,.2,1), border-color .35s, box-shadow .35s;
}
div[data-testid="stMetric"]:hover{
  transform: translateY(-3px);
  border-color: var(--glass-border-hi);
  box-shadow: 0 14px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(94,234,212,0.15) inset;
}
[data-testid="stMetricValue"]{ color: var(--text); }
[data-testid="stMetricDelta"] svg{ vertical-align: middle; }

/* expanders as glass panels */
details, div[data-testid="stExpander"]{
  background: var(--glass-bg);
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--radius) !important;
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  box-shadow: var(--shadow);
  overflow: hidden;
}
div[data-testid="stExpander"] summary:hover{ color: var(--accent); }

/* dataframes / tables */
div[data-testid="stDataFrame"], div[data-testid="stTable"]{
  border-radius: var(--radius); overflow:hidden;
  border:1px solid var(--glass-border);
  box-shadow: var(--shadow);
}

/* ---------- Buttons: glass with sheen ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button{
  position:relative; overflow:hidden;
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border:1px solid var(--glass-border);
  border-radius: 14px; color: var(--text); font-weight:600;
  padding:.55rem 1rem;
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  transition: transform .25s cubic-bezier(.2,.8,.2,1), border-color .25s, box-shadow .25s;
}
.stButton > button:hover, .stFormSubmitButton > button:hover{
  transform: translateY(-2px); border-color: var(--glass-border-hi);
  box-shadow: 0 10px 28px rgba(0,0,0,0.45), 0 0 22px rgba(94,234,212,0.18);
}
.stButton > button::after{
  content:""; position:absolute; top:0; left:-120%; width:60%; height:100%;
  background: linear-gradient(120deg, transparent, rgba(255,255,255,0.18), transparent);
  transition: left .6s ease;
}
.stButton > button:hover::after{ left:140%; }
/* primary button accent */
.stButton > button[kind="primary"], .stFormSubmitButton > button{
  background: linear-gradient(135deg, rgba(94,234,212,0.22), rgba(129,140,248,0.22));
  border-color: rgba(94,234,212,0.4);
}

/* ---------- Inputs / selects ---------- */
div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input,
.stTextArea textarea{
  background: var(--glass-bg) !important;
  border:1px solid var(--glass-border) !important;
  border-radius: 12px !important;
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
}
div[data-baseweb="select"] > div:focus-within{ border-color: var(--accent) !important; }
/* multiselect chips */
span[data-baseweb="tag"]{
  background: linear-gradient(135deg, rgba(94,234,212,0.22), rgba(129,140,248,0.22)) !important;
  border:1px solid rgba(94,234,212,0.35) !important;
  border-radius: 10px !important; color: var(--text) !important;
}

/* ---------- Sidebar as frosted glass ---------- */
section[data-testid="stSidebar"] > div{
  background: linear-gradient(180deg, rgba(16,22,36,0.85), rgba(10,14,23,0.85));
  border-right:1px solid var(--glass-border);
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
}

/* ---------- Tabs / radios ---------- */
.stRadio > div{ gap:.4rem; }
.stRadio [role="radiogroup"] label{
  background: var(--glass-bg); border:1px solid var(--glass-border);
  border-radius: 12px; padding:.35rem .7rem; transition: all .25s;
}
.stRadio [role="radiogroup"] label:hover{ border-color: var(--glass-border-hi); }

/* dividers softer */
hr{ border-color: var(--glass-border) !important; opacity:.6; }

/* alerts (info/warning/success) as glass */
div[data-testid="stAlert"]{
  border-radius: var(--radius); border:1px solid var(--glass-border);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
}

/* plotly charts: round corners + subtle frame */
div[data-testid="stPlotlyChart"]{
  border-radius: var(--radius); overflow:hidden;
  border:1px solid var(--glass-border); box-shadow: var(--shadow);
  background: rgba(12,17,28,0.35);
}

/* gentle entrance animation for blocks */
div[data-testid="stVerticalBlock"] > div{ animation: rise .5s ease both; }
@keyframes rise{ from{opacity:0; transform: translateY(8px)} to{opacity:1; transform:none} }

/* scrollbars */
::-webkit-scrollbar{ width:10px; height:10px; }
::-webkit-scrollbar-thumb{ background: rgba(255,255,255,0.12); border-radius:10px; }
::-webkit-scrollbar-thumb:hover{ background: rgba(94,234,212,0.35); }

/* toast glass */
div[data-baseweb="toast"]{
  background: var(--glass-bg-strong) !important;
  border:1px solid var(--glass-border-hi) !important;
  backdrop-filter: blur(18px); border-radius:14px !important;
}
</style>

<script>
/* pointer-reactive glow: moves the aurora highlight toward the cursor */
(function(){
  const root = document.documentElement;
  let raf=null;
  window.addEventListener('pointermove', (e)=>{
    if(raf) return;
    raf = requestAnimationFrame(()=>{
      root.style.setProperty('--mx', (e.clientX / window.innerWidth * 100) + '%');
      root.style.setProperty('--my', (e.clientY / window.innerHeight * 100) + '%');
      raf=null;
    });
  }, {passive:true});
})();
</script>
"""


def inject(st) -> None:
    """Inject the premium theme. Call once after set_page_config()."""
    st.markdown(CSS, unsafe_allow_html=True)


def glass_card(st, title: str, body_md: str, accent: str = "#5eead4") -> None:
    """Render a standalone liquid-glass card (for hero/section highlights)."""
    html = f"""
    <div style="
       background: rgba(22,30,46,0.55);
       border:1px solid rgba(255,255,255,0.08);
       border-left:3px solid {accent};
       border-radius:18px; padding:18px 20px; margin:6px 0;
       backdrop-filter: blur(18px) saturate(160%);
       -webkit-backdrop-filter: blur(18px) saturate(160%);
       box-shadow: 0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06);">
       <div style="font-weight:700; font-size:1.05rem; margin-bottom:6px;">{title}</div>
       <div style="color:#9aa7bd; font-size:.92rem; line-height:1.5;">{body_md}</div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)
