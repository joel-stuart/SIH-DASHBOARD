"""
MineWatch — Automated Underground Mine Subsidence Monitoring
Theme: "Ore & Ember" — dark underground industrial control room.
 
Architecture (see data_layer.py / esp32_connection.py):
    Sensors -> XIAO ESP32-S3 -> ML inference -> LoRa -> Laptop -> this UI
 
This file only ever talks to data_layer.get_dashboard_data(). It has no
knowledge of serial ports, LoRa packets, or ESP32 hardware — see
esp32_connection.py for that integration point.
 
Run with: python -m streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import datetime

from streamlit_autorefresh import st_autorefresh

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_layer import (
    ACTIVE_NODES,
    LIVE_MODE,
    NODE_IDS,
    NODE_POSITIONS,
    NODE_LOCATION_LABEL,
    get_dashboard_data,
    get_demo_alerts,
    get_demo_history,
    summarize,
)

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="MineWatch — Subsidence Monitoring",
    page_icon="\u26cf\ufe0f",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# Auto-refresh dashboard UI every 2 seconds to poll live USB data
st_autorefresh(interval=2000, key="datarefresh")

# ----------------------------------------------------------------------------
# PALETTE — Ore & Ember (dark underground industrial, no blue)
# ----------------------------------------------------------------------------
PALETTE = {
    "bg_base": "#171310",
    "bg_panel": "#211B16",
    "bg_panel_alt": "#29221B",
    "line": "#3A3229",
    "copper": "#C97A4A",
    "amber": "#D4A23C",
    "moss": "#7FA65C",
    "rust": "#B84A3E",
    "text": "#F2E9DD",
    "text_muted": "#A79880",
    "grey": "#6B6459",
}
STATUS_COLOR = {
    "Normal": PALETTE["moss"],
    "Warning": PALETTE["amber"],
    "Critical": PALETTE["rust"],
    "Offline": PALETTE["grey"],
}
STATUS_EMOJI = {
    "Normal": "\U0001f7e2",
    "Warning": "\U0001f7e1",
    "Critical": "\U0001f534",
    "Offline": "\u26ab",
}
PULSE_SPEED = {
    "Normal": "3.2s",
    "Warning": "1.7s",
    "Critical": "0.9s",
    "Offline": "0s",
}

# ----------------------------------------------------------------------------
# LOAD SVG DIGITAL TWIN (local file — offline, no external image/API)
# ----------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
SVG_PATH = os.path.join(HERE, "assets", "mine_background.svg")


@st.cache_data
def load_svg(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


MINE_SVG = load_svg(SVG_PATH)

# ----------------------------------------------------------------------------
# SESSION STATE
# ----------------------------------------------------------------------------
st.session_state.setdefault(
    "selected_node", ACTIVE_NODES[0] if ACTIVE_NODES else NODE_IDS[0]
)
st.session_state.setdefault("show_all_nodes", False)
st.session_state.setdefault("show_gis", False)
st.session_state.setdefault("show_settings", False)
st.session_state.setdefault("trend_window", "24H")
st.session_state.setdefault("tick", 0)
st.session_state["tick"] += 1

# ----------------------------------------------------------------------------
# DATA  (single call — everything below reads from this)
# ----------------------------------------------------------------------------
readings = get_dashboard_data(tick=st.session_state["tick"])
summary = summarize(readings)
alerts = get_demo_alerts(readings)
last_sync = max(
    (r.timestamp for r in readings.values()), default=datetime.now()
)

# Active node selection reference
sel = readings[st.session_state.selected_node]

# ----------------------------------------------------------------------------
# CSS — offline-first: system font stack only, no Google Fonts / CDN
# ----------------------------------------------------------------------------
BG_BASE = PALETTE["bg_base"]
TINT_GREEN_RGB = "40, 148, 78"

st.markdown(
    f"""
<style>
html {{ scroll-behavior: smooth; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; padding-left: 5.2rem; max-width: 1260px; position: relative; z-index: 1; }}

.mw-bg-anim {{
  position: fixed; inset: 0; z-index: -1;
  background-image:
    radial-gradient(ellipse 900px 500px at 12% -8%, rgba(201,122,74,0.09), transparent 60%),
    radial-gradient(ellipse 700px 500px at 100% 8%, rgba(212,162,60,0.05), transparent 55%);
  background-color: {BG_BASE};
}}

.mw-scroll-tint {{
  position: fixed; inset: 0; z-index: 999; pointer-events: none;
  background-color: rgba({TINT_GREEN_RGB}, 0);
  mix-blend-mode: color;
  animation: mwTintShift 1s linear forwards;
  animation-timeline: --node-explorer-timeline;
  animation-range: cover 0% cover 100%;
}}
@keyframes mwTintShift {{
  from {{ background-color: rgba({TINT_GREEN_RGB}, 0); }}
  to   {{ background-color: rgba({TINT_GREEN_RGB}, 0.68); }}
}}

#node-explorer-anchor {{
  view-timeline-name: --node-explorer-timeline;
  view-timeline-axis: block;
}}

.stApp {{
  background: transparent;
  color: {PALETTE['text']};
  font-family: 'IBM Plex Sans', 'Segoe UI', 'Helvetica Neue', system-ui, -apple-system, sans-serif;
}}
h1, h2, h3 {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; letter-spacing: -0.01em; }}
.mw-hero-wrap {{ animation: mwFadeUp 0.6s ease-out; }}
@keyframes mwFadeUp {{ from {{ opacity:0; transform:translateY(8px);}} to {{ opacity:1; transform:translateY(0);}} }}

.mw-topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:0.9rem; }}
.mw-brand {{ display:flex; align-items:center; gap:0.6rem; }}
.mw-brand-mark {{ width:36px; height:36px; border-radius:9px; background:{PALETTE['copper']}; color:{PALETTE['bg_base']}; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:1.05rem; }}
.mw-brand-name {{ font-weight:700; font-size:1.05rem; line-height:1.1; }}
.mw-brand-sub {{ font-size:0.72rem; color:{PALETTE['text_muted']}; }}
.mw-system-pill {{ display:flex; align-items:center; gap:0.7rem; background:{PALETTE['bg_panel']}; border:1px solid {PALETTE['line']}; border-radius:999px; padding:0.4rem 1rem; font-size:0.8rem; color:{PALETTE['text_muted']}; }}
.mw-status-dot {{ width:8px; height:8px; border-radius:50%; background:{PALETTE['moss']}; box-shadow:0 0 7px {PALETTE['moss']}; }}
.mw-status-dot.demo {{ background:{PALETTE['amber']}; box-shadow:0 0 7px {PALETTE['amber']}; }}

.mw-eyebrow {{ color:{PALETTE['copper']}; font-size:0.8rem; font-weight:600; margin-bottom:0.15rem; letter-spacing:0.01em; }}
.mw-title {{ font-size:1.85rem; font-weight:700; margin:0; line-height:1.18; }}
.mw-subtitle {{ color:{PALETTE['text_muted']}; font-size:0.9rem; margin-top:0.3rem; }}

.mw-panel {{ background:{PALETTE['bg_panel']}; border:1px solid {PALETTE['line']}; border-radius:12px; padding:1.05rem 1.2rem; height:100%; }}
.mw-panel-title {{ font-size:0.86rem; color:{PALETTE['text_muted']}; margin-bottom:0.6rem; }}
.mw-panel-accent {{ border-left:3px solid var(--accent, {PALETTE['copper']}); }}

.mw-ai-status {{ font-size:1.45rem; font-weight:700; color:{PALETTE['moss']}; margin:0.1rem 0 0.15rem 0; }}
.mw-ai-status.warn {{ color:{PALETTE['amber']}; }}
.mw-ai-status.crit {{ color:{PALETTE['rust']}; }}
.mw-ai-conf {{ color:{PALETTE['text_muted']}; font-size:0.85rem; }}
.mw-demo-tag {{ display:inline-block; font-size:0.68rem; letter-spacing:0.03em; color:{PALETTE['amber']}; background:rgba(212,162,60,0.12); border:1px solid rgba(212,162,60,0.35); border-radius:5px; padding:0.1rem 0.4rem; margin-left:0.4rem; vertical-align:middle; }}

.mw-tally-row {{ display:flex; justify-content:space-between; margin-top:0.5rem; flex-wrap:wrap; }}
.mw-tally-item {{ text-align:center; flex:1; min-width:56px; }}
.mw-tally-num {{ font-size:1.5rem; font-weight:700; }}
.mw-tally-label {{ color:{PALETTE['text_muted']}; font-size:0.74rem; }}

.mw-alert {{ display:flex; gap:0.7rem; padding:0.5rem 0; border-bottom:1px solid {PALETTE['line']}; }}
.mw-alert:last-child {{ border-bottom:none; }}
.mw-alert-dot {{ width:8px; height:8px; border-radius:50%; margin-top:0.35rem; flex-shrink:0; }}
.mw-alert-time {{ color:{PALETTE['text_muted']}; font-size:0.76rem; min-width:42px; display:inline-block; }}
.mw-alert-node {{ color:{PALETTE['copper']}; font-weight:600; font-size:0.85rem; }}
.mw-alert-msg {{ color:{PALETTE['text']}; font-size:0.84rem; }}
.mw-alert-empty {{ color:{PALETTE['text_muted']}; font-size:0.85rem; padding:0.4rem 0; }}

div[data-testid="stButton"] > button {{ background:{PALETTE['bg_panel_alt']}; border:1px solid {PALETTE['line']}; color:{PALETTE['text']}; border-radius:999px; padding:0.4rem 1rem; font-size:0.84rem; font-weight:500; transition:all 0.15s ease; }}
div[data-testid="stButton"] > button:hover {{ border-color:{PALETTE['copper']}; color:{PALETTE['copper']}; }}
.mw-selnode + div[data-testid="stButton"] > button {{ border-color:{PALETTE['copper']}; background:rgba(201,122,74,0.16); width:100%; }}
.mw-unselnode + div[data-testid="stButton"] > button {{ width:100%; }}

.mw-metric {{ background:{PALETTE['bg_panel_alt']}; border-radius:10px; padding:0.65rem 0.85rem; text-align:center; }}
.mw-metric-val {{ font-size:1.3rem; font-weight:700; color:{PALETTE['copper']}; }}
.mw-metric-label {{ color:{PALETTE['text_muted']}; font-size:0.74rem; margin-top:0.1rem; }}
.mw-riskbar-track {{ height:8px; border-radius:6px; background:{PALETTE['bg_panel_alt']}; overflow:hidden; margin-top:0.3rem; }}
.mw-riskbar-fill {{ height:100%; border-radius:6px; }}

.mw-badge {{ background:{PALETTE['bg_panel_alt']}; border-radius:10px; padding:0.55rem 0.8rem; margin-bottom:0.55rem; display:flex; justify-content:space-between; align-items:center; }}
.mw-badge.offline {{ opacity:0.62; }}
.mw-badge-name {{ font-weight:600; font-size:0.87rem; }}
.mw-badge-status {{ font-size:0.76rem; color:{PALETTE['text_muted']}; }}

.mw-footer {{ text-align:center; color:{PALETTE['text_muted']}; font-size:0.76rem; margin-top:2rem; padding-top:1rem; border-top:1px solid {PALETTE['line']}; }}

.mw-hero {{ position:relative; border-radius:16px; overflow:hidden; height:500px; border:1px solid {PALETTE['line']}; background:{PALETTE['bg_panel']}; }}
.mw-hero svg {{ position:absolute; inset:0; width:100%; height:100%; }}
.mw-hero-scrim {{ position:absolute; inset:0; background:linear-gradient(100deg, rgba(15,12,9,0.72) 0%, rgba(15,12,9,0.28) 40%, rgba(15,12,9,0.05) 62%, rgba(15,12,9,0.4) 100%); z-index:1; pointer-events:none; }}
.mw-hero-overlay {{ position:absolute; top:1.5rem; left:1.7rem; z-index:2; max-width:380px; }}
.mw-hero-legend {{ margin-top:0.85rem; display:flex; flex-direction:column; gap:0.32rem; }}
.mw-legend-row {{ display:flex; align-items:center; gap:0.5rem; font-size:0.78rem; color:{PALETTE['text_muted']}; }}
.mw-legend-dot {{ width:9px; height:9px; border-radius:50%; }}
.mw-stat-pills {{ position:absolute; bottom:1.4rem; right:1.7rem; z-index:2; display:flex; gap:0.55rem; }}
.mw-stat-pill {{ background:rgba(33,27,22,0.85); border:1px solid {PALETTE['line']}; border-radius:10px; padding:0.45rem 0.8rem; text-align:center; min-width:58px; }}
.mw-stat-num {{ font-size:1rem; font-weight:700; }}
.mw-stat-label {{ font-size:0.65rem; color:{PALETTE['text_muted']}; margin-top:0.05rem; }}
.mw-scroll-hint {{ position:absolute; bottom:1.3rem; left:50%; transform:translateX(-50%); z-index:2; display:flex; flex-direction:column; align-items:center; gap:0.3rem; color:{PALETTE['text_muted']}; font-size:0.72rem; }}
.mw-scroll-mouse {{ width:18px; height:28px; border:2px solid {PALETTE['text_muted']}; border-radius:11px; position:relative; }}
.mw-scroll-mouse::after {{ content:''; position:absolute; top:5px; left:50%; width:3px; height:5px; background:{PALETTE['copper']}; border-radius:2px; transform:translateX(-50%); animation:mwScrollDot 1.6s ease-in-out infinite; }}
@keyframes mwScrollDot {{ 0%{{opacity:1; transform:translate(-50%,0);}} 60%{{opacity:0; transform:translate(-50%,8px);}} 100%{{opacity:0;}} }}

.mw-node {{ position:absolute; transform:translate(-50%,-50%); z-index:3; }}
.mw-node-dot {{ width:13px; height:13px; border-radius:50%; position:relative; animation:mwBlink var(--pulse,2s) ease-in-out infinite; }}
.mw-node-dot::after {{ content:''; position:absolute; inset:-7px; border-radius:50%; background:inherit; opacity:0.5; animation:mwPulse var(--pulse,2s) ease-out infinite; }}
.mw-node-dot.offline {{ animation:none; opacity:0.55; }}
.mw-node-dot.offline::after {{ animation:none; opacity:0; }}
@keyframes mwPulse {{ 0%{{transform:scale(0.4); opacity:0.5;}} 70%{{transform:scale(1.7); opacity:0;}} 100%{{opacity:0;}} }}
@keyframes mwBlink {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.3;}} }}
.mw-node-tag {{ position:absolute; top:16px; left:50%; transform:translateX(-50%); font-size:0.68rem; color:{PALETTE['text_muted']}; background:rgba(23,19,16,0.75); padding:0.03rem 0.32rem; border-radius:4px; white-space:nowrap; }}
.mw-node-tooltip {{ position:absolute; bottom:130%; left:50%; transform:translateX(-50%) translateY(4px); background:{PALETTE['bg_panel']}; border:1px solid {PALETTE['copper']}; border-radius:99px; padding:0.5rem 0.65rem; white-space:nowrap; opacity:0; visibility:hidden; pointer-events:none; transition:all 0.15s ease; z-index:6; box-shadow:0 6px 16px rgba(0,0,0,0.4); }}
.mw-node:hover .mw-node-tooltip {{ opacity:1; visibility:visible; transform:translateX(-50%) translateY(-2px); }}
.mw-tooltip-title {{ font-weight:700; font-size:0.82rem; margin-bottom:0.25rem; }}
.mw-tooltip-sub {{ font-size:0.68rem; color:{PALETTE['text_muted']}; margin-bottom:0.3rem; }}
.mw-tooltip-row {{ font-size:0.76rem; color:{PALETTE['text_muted']}; display:flex; gap:0.5rem; justify-content:space-between; }}
.mw-tooltip-row b {{ color:{PALETTE['text']}; font-weight:600; }}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="mw-bg-anim"></div><div class="mw-scroll-tint"></div>',
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# TOP BAR — brand + system status
# ----------------------------------------------------------------------------
mode_label = "LIVE" if LIVE_MODE else "DEMO MODE"
dot_class = "" if LIVE_MODE else "demo"
top_html = (
    '<div class="mw-topbar">'
    '<div class="mw-brand">'
    '<div class="mw-brand-mark">\u26cf\ufe0f</div>'
    '<div><div class="mw-brand-name">MineWatch</div>'
    '<div class="mw-brand-sub">Automated subsidence monitoring</div></div>'
    "</div>"
    f'<div class="mw-system-pill"><span class="mw-status-dot {dot_class}"></span>'
    f"SYSTEM ONLINE &middot; {mode_label} &middot; "
    f'Active nodes: {summary["active_nodes"]}/{summary["total_nodes"]} &middot; '
    f'Last sync {last_sync.strftime("%H:%M:%S")}</div>'
    "</div>"
)
st.markdown(top_html, unsafe_allow_html=True)

nav_gis, nav_settings, _ = st.columns([1, 1, 4])
with nav_gis:
    if st.button("\U0001f5fa\ufe0f GIS Map", key="nav_gis", width="stretch"):
        st.session_state.show_gis = not st.session_state.show_gis
with nav_settings:
    if st.button("\u2699\ufe0f Settings", key="nav_settings", width="stretch"):
        st.session_state.show_settings = not st.session_state.get(
            "show_settings", False
        )

if st.session_state.get("show_settings", False):
    st.markdown(
        f'<div class="mw-panel" style="margin-bottom:0.8rem;">'
        f'<div class="mw-panel-title">System configuration</div>'
        f'<p class="mw-ai-conf">Mode: <b style="color:{PALETTE["text"]};">{mode_label}</b> &middot; '
        f'Active nodes: <b style="color:{PALETTE["text"]};">{", ".join(ACTIVE_NODES) if ACTIVE_NODES else "none"}</b> '
        f"&middot; Risk thresholds \u2014 Warning &ge; 35%, Critical &ge; 65% &middot; "
        f"Stale timeout: 30s</p></div>",
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------------
# HERO — SVG digital twin + live node overlay
# ----------------------------------------------------------------------------
node_html_parts = []
for nid in NODE_IDS:
    r = readings[nid]
    top, left = NODE_POSITIONS[nid]
    color = STATUS_COLOR[r.status]
    speed = PULSE_SPEED[r.status]
    offline_cls = "offline" if r.status == "Offline" else ""
    if r.status == "Offline":
        tooltip_body = (
            f'<div class="mw-tooltip-row">Pitch <b>0\u00b0</b></div>'
            f'<div class="mw-tooltip-row">Roll <b>0\u00b0</b></div>'
            f'<div class="mw-tooltip-row">Vibration <b>0</b></div>'
            f'<div class="mw-tooltip-row">Temperature <b>0\u00b0C</b></div>'
            f'<div class="mw-tooltip-row">Risk <b>0%</b></div>'
            f'<div class="mw-tooltip-row">Status <b>OFFLINE</b></div>'
        )
    else:
        tooltip_body = (
            f'<div class="mw-tooltip-row">Pitch <b>{r.pitch}\u00b0</b></div>'
            f'<div class="mw-tooltip-row">Roll <b>{r.roll}\u00b0</b></div>'
            f'<div class="mw-tooltip-row">Vibration <b>{r.vibration}</b></div>'
            f'<div class="mw-tooltip-row">Temperature <b>{r.temperature}\u00b0C</b></div>'
            f'<div class="mw-tooltip-row">Risk <b>{r.risk}%</b></div>'
            f'<div class="mw-tooltip-row">Status <b>ONLINE</b></div>'
        )
    node_html_parts.append(
        f'<div class="mw-node" style="top:{top}%; left:{left}%;">'
        f'<div class="mw-node-dot {offline_cls}" style="background:{color}; '
        f'box-shadow:0 0 9px {color}; --pulse:{speed};"></div>'
        f'<span class="mw-node-tag">{nid}</span>'
        f'<div class="mw-node-tooltip">'
        f'<div class="mw-tooltip-title" style="color:{color};">{nid} \u00b7 {r.status.upper()}</div>'
        f'<div class="mw-tooltip-sub">{NODE_LOCATION_LABEL.get(nid, "")}</div>'
        f"{tooltip_body}</div></div>"
    )
nodes_layer = "".join(node_html_parts)

legend_rows = "".join(
    f'<div class="mw-legend-row"><span class="mw-legend-dot" style="background:{STATUS_COLOR[s]}; '
    f'box-shadow:0 0 6px {STATUS_COLOR[s]};"></span>{s}</div>'
    for s in ["Normal", "Warning", "Critical", "Offline"]
)

stat_pills = (
    f'<div class="mw-stat-pill"><div class="mw-stat-num">{summary["total_nodes"]}</div><div class="mw-stat-label">Total nodes</div></div>'
    f'<div class="mw-stat-pill"><div class="mw-stat-num" style="color:{PALETTE["moss"]}">{summary["counts"]["Normal"]}</div><div class="mw-stat-label">Normal</div></div>'
    f'<div class="mw-stat-pill"><div class="mw-stat-num" style="color:{PALETTE["amber"]}">{summary["counts"]["Warning"]}</div><div class="mw-stat-label">Warning</div></div>'
    f'<div class="mw-stat-pill"><div class="mw-stat-num" style="color:{PALETTE["rust"]}">{summary["counts"]["Critical"]}</div><div class="mw-stat-label">Critical</div></div>'
    f'<div class="mw-stat-pill"><div class="mw-stat-num" style="color:{PALETTE["grey"]}">{summary["counts"]["Offline"]}</div><div class="mw-stat-label">Offline</div></div>'
)

hero_html = (
    '<div class="mw-hero-wrap"><div class="mw-hero">'
    f"{MINE_SVG}"
    '<div class="mw-hero-scrim"></div>'
    '<div class="mw-hero-overlay">'
    '<div class="mw-eyebrow">Underground mine digital twin</div>'
    '<p class="mw-title">Automated Precision Subsidence Monitoring</p>'
    '<p class="mw-subtitle">IMU &middot; ML inference &middot; LoRa mesh &middot; 6 monitoring nodes</p>'
    f'<div class="mw-hero-legend">{legend_rows}</div>'
    "</div>"
    f"{nodes_layer}"
    f'<div class="mw-stat-pills">{stat_pills}</div>'
    '<div class="mw-scroll-hint"><div class="mw-scroll-mouse"></div>Scroll for risk analysis</div>'
    "</div></div>"
)
st.markdown(hero_html, unsafe_allow_html=True)
st.write("")

# ----------------------------------------------------------------------------
# GIS MAP
# ----------------------------------------------------------------------------
st.markdown('<div id="gis-section"></div>', unsafe_allow_html=True)

if st.session_state.show_gis:
    st.markdown(
        '<div class="mw-panel-title" style="font-size:1rem; color:#F2E9DD; margin-top:0.6rem;">'
        "GIS view \u2014 node footprint (offline placeholder, no external map tiles)</div>",
        unsafe_allow_html=True,
    )
    gis_fig = go.Figure()
    for nid in NODE_IDS:
        r = readings[nid]
        top, left = NODE_POSITIONS[nid]
        gis_fig.add_trace(
            go.Scatter(
                x=[left],
                y=[100 - top],
                mode="markers+text",
                text=[nid],
                textposition="top center",
                textfont=dict(color=PALETTE["text_muted"], size=11),
                marker=dict(
                    size=22 if r.status != "Offline" else 14,
                    color=STATUS_COLOR[r.status],
                    line=dict(width=1, color=PALETTE["bg_base"]),
                ),
                hovertemplate=f"{nid}<br>Status: {r.status}<br>Risk: {r.risk}%<extra></extra>",
                showlegend=False,
            )
        )
    gis_fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PALETTE["bg_panel_alt"],
        xaxis=dict(visible=False, range=[0, 100]),
        yaxis=dict(visible=False, range=[0, 100]),
    )
    st.plotly_chart(gis_fig, width="stretch", config={"displayModeBar": False})
    st.caption(
        "Placeholder GIS projection of node positions. Replace with the real GIS/GPS "
        "layer here once site survey coordinates are available."
    )

st.write("")

# ----------------------------------------------------------------------------
# RISK OVERVIEW ROW
# ----------------------------------------------------------------------------
r1, r2, r3 = st.columns([1.3, 1, 1])

with r1:
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=summary["overall_risk"],
            number={
                "suffix": "%",
                "font": {"size": 32, "color": PALETTE["text"]},
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickcolor": PALETTE["text_muted"],
                    "tickfont": {"size": 9},
                },
                "bar": {"color": PALETTE["copper"], "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 35], "color": "rgba(127,166,92,0.25)"},
                    {"range": [35, 65], "color": "rgba(212,162,60,0.25)"},
                    {"range": [65, 100], "color": "rgba(184,74,62,0.25)"},
                ],
            },
        )
    )
    gauge.update_layout(
        height=190,
        margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=PALETTE["text"],
    )
    st.markdown(
        f'<div class="mw-panel"><div class="mw-panel-title">\u26f0\ufe0f Overall mine risk \u2014 '
        f'{summary["overall_label"]}</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(gauge, width="stretch", config={"displayModeBar": False})
    st.markdown(
        f'<p class="mw-ai-conf">Computed from {summary["online_nodes"]} online node(s). '
        f"Offline nodes are excluded from this figure.</p></div>",
        unsafe_allow_html=True,
    )

with r2:
    ai_class = (
        ""
        if sel.status == "Normal"
        else ("warn" if sel.status == "Warning" else "crit")
    )
    stage_raw = getattr(sel, "stage_label", None) or getattr(
        sel, "stage", None
    )
    stage_display = (
        stage_raw.replace("_", " ").title() if stage_raw else sel.status
    )
    st.markdown(
        f'<div class="mw-panel"><div class="mw-panel-title">\U0001f9e0 MineSafe AI \u2014 ML Stage</div>'
        f'<p class="mw-ai-status {ai_class}">{stage_display}</p>'
        f'<p class="mw-ai-conf">Node {sel.node_id} confidence: {sel.risk}%</p></div>',
        unsafe_allow_html=True,
    )

with r3:
    c = summary["counts"]
    st.markdown(
        f'<div class="mw-panel"><div class="mw-panel-title">\U0001f4e1 Node status</div>'
        f'<div class="mw-tally-row">'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="color:{PALETTE["moss"]}">{c["Normal"]}</div><div class="mw-tally-label">Normal</div></div>'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="color:{PALETTE["amber"]}">{c["Warning"]}</div><div class="mw-tally-label">Warning</div></div>'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="color:{PALETTE["rust"]}">{c["Critical"]}</div><div class="mw-tally-label">Critical</div></div>'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="color:{PALETTE["grey"]}">{c["Offline"]}</div><div class="mw-tally-label">Offline</div></div>'
        f"</div>"
        f'<p class="mw-ai-conf" style="margin-top:0.8rem;">{summary["total_nodes"]} nodes deployed \u00b7 '
        f'{summary["active_nodes"]} active \u00b7 {summary["offline_nodes"]} awaiting hardware</p></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------------------------------------------------------------------
# RISK TREND + RECENT ALERTS
# ----------------------------------------------------------------------------
t1, t2 = st.columns([2, 1])

with t1:
    window_hours = {"1H": 1, "6H": 6, "24H": 24, "7D": 168}
    st.markdown(
        '<div class="mw-panel"><div class="mw-panel-title">\U0001f4c8 Risk trend analysis</div>',
        unsafe_allow_html=True,
    )
    chosen = st.radio(
        "Window",
        list(window_hours.keys()),
        horizontal=True,
        key="trend_window",
        label_visibility="collapsed",
    )
    hist = get_demo_history(window_hours[chosen], node_ids=ACTIVE_NODES)

    trend = go.Figure()
    trend.add_trace(
        go.Scatter(
            x=hist["times"],
            y=hist["overall"],
            name="Overall",
            mode="lines",
            line=dict(color=PALETTE["copper"], width=3),
            fill="tozeroy",
            fillcolor="rgba(201,122,74,0.08)",
        )
    )
    node_colors = {"N02": PALETTE["amber"], "N04": PALETTE["rust"]}
    for nid in ACTIVE_NODES:
        trend.add_trace(
            go.Scatter(
                x=hist["times"],
                y=hist["series"][nid],
                name=nid,
                mode="lines",
                line=dict(
                    color=node_colors.get(nid, PALETTE["moss"]), width=1.5
                ),
            )
        )
    trend.update_layout(
        height=290,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=PALETTE["text_muted"],
        font_size=11,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(color=PALETTE["text_muted"]),
        ),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=PALETTE["line"], range=[0, 100], ticksuffix="%"),
        hovermode="x unified",
    )
    st.plotly_chart(trend, width="stretch", config={"displayModeBar": False})
    st.markdown(
        '<p class="mw-ai-conf">Offline nodes are excluded from the trend unless selected \u2014 '
        "their zero values would otherwise distort the picture.</p></div>",
        unsafe_allow_html=True,
    )

with t2:
    if alerts:
        alert_rows = "".join(
            f'<div class="mw-alert"><div class="mw-alert-dot" style="background:{STATUS_COLOR.get(a["severity"], PALETTE["grey"])}; '
            f'box-shadow:0 0 6px {STATUS_COLOR.get(a["severity"], PALETTE["grey"])};"></div>'
            f'<div><span class="mw-alert-time">{a["timestamp"].strftime("%H:%M")}</span> '
            f'<span class="mw-alert-node">{a["node"]}</span><br/>'
            f'<span class="mw-alert-msg">{a["event"]}</span></div></div>'
            for a in alerts
        )
    else:
        alert_rows = (
            '<div class="mw-alert-empty">No alerts \u2014 all active nodes nominal.</div>'
        )
    st.markdown(
        f'<div class="mw-panel"><div class="mw-panel-title">\U0001f514 Recent alerts</div>{alert_rows}</div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------------------------------------------------------------------
# NODE EXPLORER
# ----------------------------------------------------------------------------
st.markdown('<div id="node-explorer-anchor"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="mw-panel-title" style="font-size:1rem; color:#F2E9DD;">'
    "\U0001f526 Node explorer \u2014 select a node for detailed readings</div>",
    unsafe_allow_html=True,
)

chip_cols = st.columns(6)
for i, nid in enumerate(NODE_IDS):
    r = readings[nid]
    with chip_cols[i]:
        marker_class = (
            "mw-selnode"
            if st.session_state.selected_node == nid
            else "mw-unselnode"
        )
        st.markdown(
            f'<div class="{marker_class}"></div>', unsafe_allow_html=True
        )
        label = (
            f"{STATUS_EMOJI[r.status]} {nid}  {r.risk}%"
            if r.status != "Offline"
            else f"{STATUS_EMOJI[r.status]} {nid}  OFF"
        )
        if st.button(label, key=f"chip_{nid}", width="stretch"):
            st.session_state.selected_node = nid
            st.rerun()

st.write("")

accent = STATUS_COLOR[sel.status]

detail_head, detail_extra = st.columns([1, 1.3])

with detail_head:
    online_txt = "ONLINE" if sel.online else "OFFLINE / INACTIVE"
    st.markdown(
        f'<div class="mw-panel mw-panel-accent" style="--accent:{accent};">'
        f'<div class="mw-panel-title">{STATUS_EMOJI[sel.status]} Node {sel.node_id} \u00b7 {sel.status} \u00b7 {online_txt}</div>'
        f'<p class="mw-ai-conf" style="margin:-0.3rem 0 0.4rem 0;">{sel.location_label}</p>'
        f'<div class="mw-riskbar-track"><div class="mw-riskbar-fill" style="width:{sel.risk}%; background:{accent};"></div></div>'
        f'<p class="mw-ai-conf" style="margin-top:0.35rem;">Risk level: {sel.risk}%</p></div>',
        unsafe_allow_html=True,
    )
    m1, m2 = st.columns(2)
    m1.markdown(
        f'<div class="mw-metric"><div class="mw-metric-val">{sel.pitch}\u00b0</div><div class="mw-metric-label">Pitch</div></div>',
        unsafe_allow_html=True,
    )
    m2.markdown(
        f'<div class="mw-metric"><div class="mw-metric-val">{sel.roll}\u00b0</div><div class="mw-metric-label">Roll</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    m3, m4 = st.columns(2)
    m3.markdown(
        f'<div class="mw-metric"><div class="mw-metric-val">{sel.vibration}</div><div class="mw-metric-label">Vibration</div></div>',
        unsafe_allow_html=True,
    )
    m4.markdown(
        f'<div class="mw-metric"><div class="mw-metric-val">{sel.temperature}\u00b0C</div><div class="mw-metric-label">Temperature</div></div>',
        unsafe_allow_html=True,
    )

with detail_extra:
    stage_raw = getattr(sel, "stage_label", None) or getattr(
        sel, "stage", None
    )
    stage_text = stage_raw.replace("_", " ").title() if stage_raw else sel.status
    st.markdown(
        f'<div class="mw-panel"><div class="mw-panel-title">Additional telemetry</div>'
        f'<div class="mw-tally-row">'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="font-size:1.15rem;">{sel.pitch}\u00b0</div><div class="mw-tally-label">Pitch</div></div>'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="font-size:1.15rem;">{sel.roll}\u00b0</div><div class="mw-tally-label">Roll</div></div>'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="font-size:1.15rem;">{sel.vibration}</div><div class="mw-tally-label">Vibration</div></div>'
        f'<div class="mw-tally-item"><div class="mw-tally-num" style="font-size:1.15rem;">{sel.temperature}\u00b0C</div><div class="mw-tally-label">Temperature</div></div>'
        f"</div>"
        f'<p class="mw-ai-conf" style="margin-top:0.7rem;">ML anomaly flag: '
        f'<b style="color:{PALETTE["text"]};">{"Yes" if sel.anomaly else "No"}</b> &middot; '
        f'ML stage: <b style="color:{PALETTE["text"]};">{stage_text}</b> &middot; '
        f'Last update: {sel.timestamp.strftime("%H:%M:%S")} &middot; '
        f'Communication: {"OK" if sel.online else "No link"}</p></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------------------------------------------------------------------
# SHOW ALL NODES
# ----------------------------------------------------------------------------
st.toggle("Show all nodes", key="show_all_nodes")

if st.session_state.show_all_nodes:
    table_rows = []
    for nid in NODE_IDS:
        r = readings[nid]
        table_rows.append(
            {
                "Node": nid,
                "Status": r.status,
                "Risk": f"{r.risk}%",
                "Pitch": f"{r.pitch}\u00b0",
                "Roll": f"{r.roll}\u00b0",
                "Vibration": r.vibration,
                "Temperature": f"{r.temperature}\u00b0C",
                "Signal/Health": f"{r.signal}% / {r.health}%",
                "Last Update": r.timestamp.strftime("%H:%M:%S"),
            }
        )
    df = pd.DataFrame(table_rows)
    st.dataframe(df, width="stretch", hide_index=True)

# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
st.markdown(
    f'<div class="mw-footer">MineWatch \u00b7 Automated Precision Subsidence Monitoring \u00b7 '
    f'{"Live mesh" if LIVE_MODE else "Demo mode \u2014 running on simulated data"} \u00b7 '
    f'last sync {last_sync.strftime("%d %b, %H:%M")}</div>',
    unsafe_allow_html=True,
)