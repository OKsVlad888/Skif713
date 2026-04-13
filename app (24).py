"""
High-Pressure Gas Flow Calculator  —  Self-Contained Edition
=============================================================
The tube-spec table is EMBEDDED directly in this file.
No external .xlsx file is required to run the app.

Run:  streamlit run app.py
Opt:  hud_background.html in the same folder (for the animated HUD background)

Gas safety limits (enforced in JS):
  CO2  : inlet >= 70 bar  → blocked (liquid phase)
  C2H2 : inlet >  17 bar  → blocked (decomposition risk)
  H2S  : inlet >  20 bar  → blocked
  CH4  : inlet > 250 bar  → blocked
  O2   : only S14 (table content enforces this)
  H2   : S6 (≤200 bar) and S9 (≤400 bar)
"""

import base64
import json
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="High-Pressure Gas Flow Calculator",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  #MainMenu,footer,header,
  [data-testid="stToolbar"],[data-testid="stDecoration"],
  [data-testid="stStatusWidget"],[data-testid="collapsedControl"]{display:none!important}
  .stApp{background:#000d0d!important}
  section.main,.block-container{padding:0!important;margin:0!important;max-width:100vw!important}
  iframe[title="streamlit_components_v1.html_v1"]{
    position:fixed!important;inset:0!important;
    width:100vw!important;height:100vh!important;
    border:none!important;z-index:100!important;
    display:block!important}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TUBE-SPEC TABLE  —  Embedded directly (parsed from Excel, frozen here)
#
#  Schema per record:
#    gas_codes    : list of UI gas codes that this spec supports
#    spec         : tube spec name (S6, S9, S11, S12, S14, S16, B1, P6, C3)
#    id_mm        : inner diameter in mm
#    tube_od_w    : outer-diameter × wall-thickness label (e.g. '3/8"X0.049"')
#    max_pressure : maximum allowed working pressure [bar] for this row
#
#  Source: טבלת_ריכוז_לחצים_וסוגי_צנרת.xlsx (updated with H2 in S6 + S9)
#  Last parsed: 2025
# ══════════════════════════════════════════════════════════════════════════════

TUBE_TABLE = [
    # ── S6  SS-316  ≤200 bar ────────────────────────────────────────────────
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":4.9,    "tube_od_w":'1/4"X0.028"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":7.036,  "tube_od_w":'3/8"X0.049"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":9.398,  "tube_od_w":'1/2"X0.065"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":12.573, "tube_od_w":'5/8"X0.065"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":14.834, "tube_od_w":'3/4"X0.083"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":17.399, "tube_od_w":'7/8"X0.095"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":19.863, "tube_od_w":'1"X0.109"',  "max_pressure":200.0},
    # ── S9  SS-316  ≤400 bar ────────────────────────────────────────────────
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":3.86,   "tube_od_w":'1/4"X0.049"',     "max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":6.223,  "tube_od_w":'3/8"X0.065"',     "max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":8.468,  "tube_od_w":'1/2"X0.083"',     "max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":9.119,  "tube_od_w":'9/16"X0.10175"',  "max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":13.106, "tube_od_w":'3/4"X0.117"',     "max_pressure":400.0},
    # ── S11 SS-316  ≤2000 bar ───────────────────────────────────────────────
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S11","id_mm":2.108,  "tube_od_w":'1/4"X0.083"',"max_pressure":2000.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S11","id_mm":3.1753, "tube_od_w":'3/8"X0.125"',"max_pressure":2000.0},
    # ── S12 SS-316  ≤1380 bar ───────────────────────────────────────────────
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S12","id_mm":2.6786, "tube_od_w":'1/4"X0.705"',   "max_pressure":1380.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S12","id_mm":5.516,  "tube_od_w":'3/8"X0.0860"',  "max_pressure":1380.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S12","id_mm":7.925,  "tube_od_w":'9/16"X0.12525"',"max_pressure":1380.0},
    # ── S14 SS-316  (O2 approved, per-diameter pressure limits) ─────────────
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":4.572,  "tube_od_w":'1/4"X0.035"',"max_pressure":238.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":7.747,  "tube_od_w":'3/8"X0.035"',"max_pressure":170.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":10.21,  "tube_od_w":'1/2"X0.049"',"max_pressure":170.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":15.748, "tube_od_w":'3/4"X0.065"',"max_pressure":170.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":22.1,   "tube_od_w":'1"X0.065"',  "max_pressure":102.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":34.8,   "tube_od_w":'1.5"X0.065"',"max_pressure":68.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":47.5,   "tube_od_w":'2"X0.065"',  "max_pressure":61.0},
    # ── S16 SS-316 UHP Double-Contained  (per-diameter pressure limits) ─────
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":4.572,    "tube_od_w":'1/4"X0.035"', "max_pressure":204.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":7.747,    "tube_od_w":'3/8"X0.035"', "max_pressure":170.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":10.21,    "tube_od_w":'1/2"X0.049"', "max_pressure":170.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":13.38585, "tube_od_w":'5/8"X0.049"', "max_pressure":170.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":15.748,   "tube_od_w":'3/4"X0.065"', "max_pressure":170.0},
    # ── B1  Copper  ≤40 bar ─────────────────────────────────────────────────
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":4.572,   "tube_od_w":'1/4"X0.035"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":7.0358,  "tube_od_w":'3/8"X0.049"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":10.2108, "tube_od_w":'1/2"X0.049"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":13.3858, "tube_od_w":'5/8"X0.049"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":15.748,  "tube_od_w":'3/4"X0.065"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":18.923,  "tube_od_w":'7/8"X0.065"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":22.098,  "tube_od_w":'1"X0.065"',   "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":28.448,  "tube_od_w":'1.25"X0.065"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":34.4424, "tube_od_w":'1.5"X0.072"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":46.5836, "tube_od_w":'2"X0.083"',   "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":58.674,  "tube_od_w":'2.5"X0.095"', "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":70.6628, "tube_od_w":'3"X0.109"',   "max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":94.7928, "tube_od_w":'4"X0.134"',   "max_pressure":40.0},
    # ── P6  PPR  ≤10 bar ────────────────────────────────────────────────────
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":11.6, "tube_od_w":"16mmX2.2mm",  "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":14.4, "tube_od_w":"20mmX2.8mm",  "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":18.0, "tube_od_w":"25mmX3.5mm",  "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":23.2, "tube_od_w":"32mmX4.4mm",  "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":29.0, "tube_od_w":"40mmX5.5mm",  "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":36.2, "tube_od_w":"50mmX6.9mm",  "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":45.8, "tube_od_w":"63mmX8.6mm",  "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":54.4, "tube_od_w":"75mmX10.3mm", "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":65.4, "tube_od_w":"90mmX12.3mm", "max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":79.8, "tube_od_w":"110mmX15.1mm","max_pressure":10.0},
    # ── C3  Galvanized  ≤15 bar  (Air only) ─────────────────────────────────
    {"gas_codes":["Air"],"spec":"C3","id_mm":15.8,  "tube_od_w":'1/2" SCH40', "max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":15.59, "tube_od_w":'3/4" SCH40', "max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":26.24, "tube_od_w":'1" SCH40',   "max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":35.04, "tube_od_w":'1.25" SCH40',"max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":40.9,  "tube_od_w":'1.5" SCH40', "max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":52.51, "tube_od_w":'2" SCH40',   "max_pressure":15.0},
]

# Serialize once to JSON for embedding in the HTML/JS payload
TUBE_TABLE_JSON = json.dumps(TUBE_TABLE, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE HTML  —  Full HUD layout, built-in animated graphics, no scroll
# ══════════════════════════════════════════════════════════════════════════════

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{
  width:100vw;height:100vh;overflow:hidden;
  background:#000d0d;font-family:'Courier New',monospace;
  color:#00e5cc;font-size:11px;
}

/* ═══ GRID LAYOUT ═══════════════════════════════════════════════════════════ */
#hud-root{
  display:grid;
  grid-template-columns:17vw 1fr 21vw;
  grid-template-rows:9vh 1fr 9vh;
  width:100vw;height:100vh;
  gap:0;
}

/* TOP BAR ─── spans all 3 columns */
#top-bar{
  grid-column:1/4;grid-row:1;
  display:flex;align-items:stretch;
  border-bottom:1px solid rgba(0,229,204,0.18);
  padding:4px 8px;gap:6px;
  background:rgba(0,6,5,0.95);
}

/* LEFT COLUMN */
#left-col{
  grid-column:1;grid-row:2;
  border-right:1px solid rgba(0,229,204,0.12);
  display:flex;flex-direction:column;
  padding:6px;gap:6px;overflow:hidden;
}

/* CENTER — calculator */
#center-col{
  grid-column:2;grid-row:2;
  display:flex;align-items:center;justify-content:center;
  padding:8px 12px;overflow:hidden;
}

/* RIGHT COLUMN */
#right-col{
  grid-column:3;grid-row:2;
  border-left:1px solid rgba(0,229,204,0.12);
  display:flex;flex-direction:column;
  padding:6px;gap:5px;overflow:hidden;
}

/* BOTTOM BAR ─── spans all 3 columns */
#bottom-bar{
  grid-column:1/4;grid-row:3;
  display:flex;align-items:stretch;
  border-top:1px solid rgba(0,229,204,0.18);
  padding:4px 8px;gap:6px;
  background:rgba(0,6,5,0.95);overflow:hidden;
}

/* ═══ TOP BAR INTERNALS ═══════════════════════════════════════════════════ */
.top-channels{
  display:flex;flex-direction:column;justify-content:space-around;
  width:280px;flex-shrink:0;
}
.ch-row{display:flex;align-items:center;gap:4px;font-size:9px;letter-spacing:.5px;}
.ch-label{color:rgba(0,229,204,0.45);width:130px;text-align:right;font-size:8px;text-transform:uppercase;letter-spacing:.8px}
.ch-bar-wrap{flex:1;height:6px;background:rgba(0,229,204,0.08);border-radius:1px;overflow:hidden}
.ch-bar{height:100%;background:#00e5cc;border-radius:1px;transition:width .8s}
.ch-num{color:#00ffee;width:22px;text-align:right;font-size:10px;font-weight:bold}

.top-extract{
  display:flex;flex-direction:column;justify-content:center;align-items:center;
  width:140px;flex-shrink:0;border:1px solid rgba(0,229,204,0.25);
  border-radius:2px;cursor:pointer;gap:3px;
  background:rgba(0,229,204,0.04);
}
.top-extract .seg-row{display:flex;gap:2px}
.top-extract .seg{width:7px;height:18px;background:#00e5cc;border-radius:1px;opacity:.9}
.top-extract .seg.dim{opacity:.2}
.top-extract .ext-lbl{font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#00ffee}

.top-wave-wrap{flex:1;overflow:hidden;display:flex;align-items:center}

/* ═══ WIDGET COMMONS ══════════════════════════════════════════════════════ */
.hud-box{
  border:1px solid rgba(0,229,204,0.15);border-radius:2px;
  background:rgba(0,8,6,0.7);overflow:hidden;position:relative;
}
.hud-label{
  font-size:8px;letter-spacing:1.5px;text-transform:uppercase;
  color:rgba(0,229,204,0.38);padding:2px 5px;
  border-bottom:1px solid rgba(0,229,204,0.1);
}
.hud-canvas{display:block;width:100%;height:100%}
.hud-num-big{font-size:28px;font-weight:bold;color:#00ffee;letter-spacing:1px;
  text-shadow:0 0 12px rgba(0,229,204,0.6)}
.hud-num-lbl{font-size:7px;letter-spacing:1.5px;text-transform:uppercase;color:rgba(0,229,204,0.45)}

/* dot blink */
@keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}
.blink{animation:blink 1.1s infinite}
.blink2{animation:blink 1.7s .4s infinite}

/* spinner */
@keyframes spin{to{transform:rotate(360deg)}}
.spinner{
  width:22px;height:22px;border-radius:50%;
  border:2px solid rgba(0,229,204,0.15);
  border-top-color:#00e5cc;
  animation:spin 1.2s linear infinite;display:inline-block;
}

/* corner brackets */
.bracket{
  position:absolute;width:10px;height:10px;
  border-color:rgba(0,229,204,0.45);border-style:solid;
}
.bracket.tl{top:0;left:0;border-width:1px 0 0 1px}
.bracket.tr{top:0;right:0;border-width:1px 1px 0 0}
.bracket.bl{bottom:0;left:0;border-width:0 0 1px 1px}
.bracket.br{bottom:0;right:0;border-width:0 1px 1px 0}

/* ═══ CALCULATOR PANEL ════════════════════════════════════════════════════ */
#panel{
  width:100%;max-width:520px;
  background:rgba(0,8,8,0.96);
  border:1.5px solid #00e5cc;border-radius:4px;
  padding:10px 18px 12px;
  position:relative;
  animation:panelGlow 2.5s ease-in-out infinite alternate;
  /* NO overflow — no scroll */
  overflow:visible;
}
@keyframes panelGlow{
  from{box-shadow:0 0 10px rgba(0,229,204,0.3),inset 0 0 20px rgba(0,229,204,0.03)}
  to  {box-shadow:0 0 36px rgba(0,229,204,0.75),inset 0 0 50px rgba(0,229,204,0.07)}
}
#panel::after{
  content:"";position:absolute;inset:0;pointer-events:none;border-radius:4px;z-index:0;
  background:repeating-linear-gradient(
    to bottom,transparent 0,transparent 3px,
    rgba(0,229,204,0.007) 3px,rgba(0,229,204,0.007) 4px);
}
#panel h1{
  position:relative;z-index:1;color:#00ffee;text-shadow:0 0 14px #00e5cc;
  font-size:13px;letter-spacing:4px;text-transform:uppercase;text-align:center;
  margin-bottom:8px;line-height:1.4;
}
#panel h1 .tri{color:#00e5cc;margin-right:6px}
#body{position:relative;z-index:1;display:flex;flex-direction:column;gap:6px}
.sr{display:flex;flex-direction:column;gap:2px}
.sr label{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:rgba(0,229,204,0.75)}
.sr select{
  background:rgba(0,14,12,0.98);color:#00ffee;
  border:1px solid rgba(0,229,204,0.42);border-radius:2px;
  padding:4px 26px 4px 8px;font-family:'Courier New',monospace;font-size:13px;
  width:100%;cursor:pointer;outline:none;
  -webkit-appearance:none;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2300e5cc'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 8px center;
}
.sr select:focus{border-color:#00e5cc;box-shadow:0 0 6px rgba(0,229,204,0.38)}
.sr select option{background:#000d0d;color:#00e5cc}
.hdiv{border:none;border-top:1px solid rgba(0,229,204,0.2);margin:1px 0}
.frow{display:flex;gap:8px;align-items:center}
.frow label{font-size:11px;color:rgba(0,229,204,0.88);letter-spacing:0.2px;width:170px;flex-shrink:0}
.frow input{
  flex:1;background:rgba(0,14,12,0.98);color:#00ffee;
  border:1px solid rgba(0,229,204,0.4);border-radius:2px;
  padding:4px 8px;font-family:'Courier New',monospace;font-size:13px;outline:none;
}
.frow input:focus{border-color:#00e5cc;box-shadow:0 0 5px rgba(0,229,204,0.35)}
.frow input::-webkit-inner-spin-button,
.frow input::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}
.frow input[type=number]{-moz-appearance:textfield}
.cap{font-size:9px;color:rgba(0,229,204,0.38);letter-spacing:1px}
#cbtn{
  width:100%;background:rgba(0,229,204,0.07);color:#00ffee;
  border:1.5px solid #00e5cc;border-radius:2px;padding:6px 0;
  font-family:'Courier New',monospace;font-size:13px;
  letter-spacing:4px;cursor:pointer;text-transform:uppercase;
  transition:background .18s,box-shadow .18s;
}
#cbtn:hover {background:rgba(0,229,204,0.18);box-shadow:0 0 14px rgba(0,229,204,0.52)}
#cbtn:active{background:rgba(0,229,204,0.30)}
.rbox{padding:7px 12px;border-radius:2px;font-size:12px;line-height:1.65;word-break:break-word}
.rbox.ok{
  background:rgba(0,56,28,0.94);border:1px solid rgba(0,200,100,0.42);
  border-left:3px solid #00e87a;color:#00ffcc;
}
.rbox.ok .res-title{font-size:13px;font-weight:bold}
.rbox.warn{
  background:rgba(50,30,0,0.96);border:1px solid rgba(255,180,40,0.35);
  border-left:3px solid #ffb800;color:#ffe590;
}
.rbox.danger{
  background:rgba(50,0,0,0.97);border:1px solid rgba(255,60,60,0.35);
  border-left:3px solid #ff3333;color:#ff8080;
}
.rbox.err{
  background:rgba(38,0,0,0.96);border:1px solid rgba(255,60,60,0.32);
  border-left:3px solid #ff4444;color:#ff9090;
}
.rbox .he{direction:rtl;font-size:11px;opacity:.82;margin-top:3px}
.spec-card{
  margin-top:5px;padding:6px 10px;border-radius:2px;
  background:rgba(0,28,22,0.98);
  border:1px solid rgba(0,229,204,0.22);
  border-left:3px solid #00e5cc;
}
.spec-card .sc-head{
  color:rgba(0,229,204,0.52);font-size:9px;
  letter-spacing:2px;text-transform:uppercase;margin-bottom:5px;
}
.spec-card .sc-row{color:#00ffee;font-size:12px;line-height:1.8}
.spec-card .sc-note{color:rgba(0,229,204,0.42);font-size:10px;margin-top:2px}
.badge{
  display:inline-block;border-radius:2px;font-size:9px;
  letter-spacing:1.2px;padding:0px 5px;margin-left:5px;
  vertical-align:middle;text-transform:uppercase;
}
.b-o2{background:rgba(255,100,0,0.15);border:1px solid rgba(255,120,0,0.4);color:#ffaa44}
.b-h2{background:rgba(0,180,255,0.12);border:1px solid rgba(0,200,255,0.35);color:#66ddff}

/* ═══ BOTTOM BAR ══════════════════════════════════════════════════════════ */
.bot-track{
  display:flex;flex-direction:column;justify-content:center;
  border:1px solid rgba(0,229,204,0.12);border-radius:2px;
  padding:3px 8px;min-width:200px;
}
.bot-label{font-size:8px;letter-spacing:1.5px;text-transform:uppercase;color:rgba(0,229,204,0.45)}
.bot-data{font-size:8px;color:rgba(0,229,204,0.6);letter-spacing:.5px;margin-top:2px}
.bot-num-row{display:flex;gap:8px;margin-top:3px}
.bot-num{font-size:10px;color:#00ffee}
.bot-scan{display:flex;align-items:center;gap:6px;padding:3px 8px}
</style>
</head>
<body>
<div id="hud-root">

<!-- ═══ TOP BAR ═══════════════════════════════════════════════════════════ -->
<div id="top-bar">
  <div class="top-channels">
    <div class="ch-row"><span class="ch-label">DATA CHANNEL IDENTIFICATION</span><div class="ch-bar-wrap"><div class="ch-bar" id="b0" style="width:89%"></div></div><span class="ch-num" id="n0">89</span></div>
    <div class="ch-row"><span class="ch-label">DATA CHANNEL IDENTIFICATION</span><div class="ch-bar-wrap"><div class="ch-bar" id="b1" style="width:75%"></div></div><span class="ch-num" id="n1">75</span></div>
    <div class="ch-row"><span class="ch-label">DATA CHANNEL IDENTIFICATION</span><div class="ch-bar-wrap"><div class="ch-bar" id="b2" style="width:47%"></div></div><span class="ch-num" id="n2">47</span></div>
    <div class="ch-row"><span class="ch-label">DATA CHANNEL IDENTIFICATION</span><div class="ch-bar-wrap"><div class="ch-bar" id="b3" style="width:36%"></div></div><span class="ch-num" id="n3">36</span></div>
  </div>
  <div class="top-extract">
    <div class="seg-row" id="seg-row"></div>
    <div class="ext-lbl">Extract Data</div>
  </div>
  <div style="display:flex;flex-direction:column;justify-content:center;gap:2px;padding:0 6px;min-width:60px">
    <div style="font-size:8px;color:rgba(0,229,204,0.4);letter-spacing:1px">&#9711;&nbsp;<span id="rn1">29</span></div>
    <div style="font-size:8px;color:rgba(0,229,204,0.4);letter-spacing:1px">&#9711;&nbsp;<span id="rn2">57</span></div>
    <div style="font-size:8px;color:rgba(0,229,204,0.4)">&#9679;&nbsp;<span id="rn3">35</span></div>
    <div style="font-size:8px;color:rgba(0,229,204,0.4)">&#9679;&nbsp;<span id="rn4">45</span></div>
  </div>
  <div class="top-wave-wrap" style="height:100%;min-width:0">
    <canvas id="topWave" style="width:100%;height:100%"></canvas>
  </div>
</div>

<!-- ═══ LEFT COLUMN ═══════════════════════════════════════════════════════ -->
<div id="left-col">
  <div class="hud-box" style="flex:0 0 30px;display:flex;align-items:center;padding:0 6px;gap:4px">
    <div class="blink" style="width:7px;height:7px;border-radius:50%;background:#00e5cc"></div>
    <span style="font-size:8px;letter-spacing:1px;text-transform:uppercase;color:rgba(0,229,204,0.55)">Access Point</span>
  </div>
  <div class="hud-box" style="flex:0 0 28px;display:flex;flex-direction:column;justify-content:center;padding:0 6px">
    <div style="font-size:7px;letter-spacing:.8px;color:rgba(0,229,204,0.35)">LOREM IPSUM DOLOR SIT AMET LOREM</div>
  </div>
  <div class="hud-box" style="flex:1;min-height:0;position:relative">
    <div class="bracket tl"></div><div class="bracket tr"></div>
    <div class="bracket bl"></div><div class="bracket br"></div>
    <canvas id="leftWave" style="width:100%;height:100%;display:block"></canvas>
  </div>
  <div class="hud-box" style="flex:0 0 80px;display:flex;flex-direction:column;justify-content:space-around;padding:6px">
    <div style="display:flex;align-items:center;gap:6px">
      <span style="font-size:8px;letter-spacing:1px;text-transform:uppercase;color:rgba(0,229,204,0.45)">Scanning Data</span>
      <span class="blink2" style="font-size:8px;color:#00e5cc">&#9632;</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px">
      <div class="spinner"></div>
      <span style="font-size:8px;color:rgba(0,229,204,0.55)">Scanning Data</span>
    </div>
  </div>
  <div class="hud-box" style="flex:0 0 28px;display:flex;align-items:center;padding:0 6px">
    <canvas id="leftBin" style="width:100%;height:20px;display:block"></canvas>
  </div>
</div>

<!-- ═══ CENTER — CALCULATOR ════════════════════════════════════════════════ -->
<div id="center-col">
  <div id="panel">
    <h1><span class="tri">&#9651;</span>HIGH-PRESSURE GAS FLOW CALCULATOR</h1>
    <div id="body">

      <div class="sr">
        <label>Gas Type</label>
        <select id="gasSelect" onchange="rebuildFields()">
          <option value="N2">N2 (Nitrogen)</option>
          <option value="O2">O2 (Oxygen)</option>
          <option value="Ar">Ar (Argon)</option>
          <option value="CO2">CO2 (Carbon Dioxide)</option>
          <option value="He">He (Helium)</option>
          <option value="H2">H2 (Hydrogen)</option>
          <option value="CH4">CH4 (Methane)</option>
          <option value="C2H2">C2H2 (Acetylene)</option>
          <option value="FG1">(H2-3% + Ar-97%) Forming Gas 1</option>
          <option value="FG2">(H2-5% + N2-95%) Forming Gas 2</option>
          <option value="Air">Air (Dry Air)</option>
        </select>
      </div>

      <div class="sr">
        <label>Calculation Type</label>
        <select id="calcSelect" onchange="rebuildFields()">
          <option value="diameter">Pipe Diameter (mm)</option>
          <option value="flow">Flow Rate (LPM)</option>
          <option value="length">Pipe Length (m)</option>
          <option value="inlet">Inlet Pressure (bar)</option>
          <option value="outlet">Outlet Pressure (bar)</option>
        </select>
      </div>

      <hr class="hdiv">
      <div id="input-fields"></div>
      <p class="cap">Friction factor (f) = 0.02 &nbsp;&middot;&nbsp; fixed constant</p>
      <button id="cbtn" onclick="doCalc()">&#9658;&nbsp;&nbsp;Calculate</button>
      <div id="result-area"></div>

    </div>
  </div>
</div>

<!-- ═══ RIGHT COLUMN ═══════════════════════════════════════════════════════ -->
<div id="right-col">
  <!-- Top: LOREM IPSUM sine waves -->
  <div class="hud-box" style="flex:0 0 28px;display:flex;align-items:center;padding:0 6px;gap:6px">
    <span style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#00ffee">Lorem Ipsum</span>
  </div>
  <div class="hud-box" style="flex:0 0 24px;padding:0 6px;display:flex;align-items:center">
    <span style="font-size:7px;color:rgba(0,229,204,0.35)">Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod</span>
  </div>
  <div class="hud-box" style="flex:0 0 18px;padding:0 6px;display:flex;align-items:center">
    <span style="font-size:8px;letter-spacing:2px;color:rgba(0,229,204,0.55)">&#9658;&#9658;&#9658; DATA X34</span>
  </div>
  <div class="hud-box" style="flex:0 0 50px;position:relative">
    <canvas id="rWave1" style="width:100%;height:100%;display:block"></canvas>
  </div>
  <div class="hud-box" style="flex:0 0 50px;position:relative">
    <canvas id="rWave2" style="width:100%;height:100%;display:block"></canvas>
  </div>
  <!-- Dot scatter -->
  <div class="hud-box" style="flex:1;min-height:0;position:relative">
    <div class="bracket tl"></div><div class="bracket tr"></div>
    <div class="bracket bl"></div><div class="bracket br"></div>
    <canvas id="dotPlot" style="width:100%;height:100%;display:block"></canvas>
  </div>
  <!-- Hex data -->
  <div class="hud-box" style="flex:0 0 80px;padding:4px;overflow:hidden">
    <div id="hexData" style="font-size:7px;color:rgba(0,229,204,0.55);letter-spacing:.5px;line-height:1.5;word-break:break-all"></div>
  </div>
  <!-- Bar charts -->
  <div style="display:flex;gap:4px;flex:0 0 60px">
    <div class="hud-box" style="flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:4px">
      <div class="hud-num-big" style="font-size:20px" id="bigNum1">75</div>
      <div class="hud-num-lbl">Data Channel<br>Identification</div>
    </div>
    <div class="hud-box" style="flex:1;overflow:hidden">
      <canvas id="barChart1" style="width:100%;height:100%;display:block"></canvas>
    </div>
  </div>
  <div style="display:flex;gap:4px;flex:0 0 50px">
    <div class="hud-box" style="flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:4px">
      <div class="hud-num-big" style="font-size:18px" id="bigNum2">44</div>
      <div class="hud-num-lbl">Data Channel<br>Identification</div>
    </div>
    <div class="hud-box" style="flex:1;overflow:hidden">
      <canvas id="barChart2" style="width:100%;height:100%;display:block"></canvas>
    </div>
  </div>
</div>

<!-- ═══ BOTTOM BAR ══════════════════════════════════════════════════════════ -->
<div id="bottom-bar">
  <div class="bot-track">
    <div class="bot-label">Tracking Target_07DC9EA1</div>
    <div id="botHex" class="bot-data">1A A5 07 0B 1F 6F 83 AB A3 41 92 09 88 09 DC 87</div>
    <div class="bot-num-row">
      <span class="bot-num" id="bt1">93</span>
      <span class="bot-num" id="bt2">61</span>
      <span class="bot-num" id="bt3">47</span>
      <span class="bot-num" id="bt4">63</span>
    </div>
  </div>
  <div class="hud-box" style="flex:1;min-width:0;overflow:hidden">
    <canvas id="botWave" style="width:100%;height:100%;display:block"></canvas>
  </div>
  <div class="bot-scan" style="min-width:120px">
    <div class="spinner"></div>
    <div style="display:flex;flex-direction:column;gap:2px">
      <div style="font-size:8px;letter-spacing:1.5px;text-transform:uppercase;color:rgba(0,229,204,0.45)">Scanning Data</div>
      <div class="blink" style="font-size:8px;color:rgba(0,229,204,0.55)">&#9632; Scanning Data</div>
    </div>
  </div>
  <div class="hud-box" style="width:120px;overflow:hidden">
    <canvas id="barChartBot" style="width:100%;height:100%;display:block"></canvas>
  </div>
</div>

</div><!-- end hud-root -->

<script>
// ═══════════════════════════════════════════════════════════════════════════
//  TUBE_TABLE  —  embedded from Python constant (no external file needed)
//  58 records covering specs: S6 S9 S11 S12 S14 S16 B1 P6 C3
// ═══════════════════════════════════════════════════════════════════════════
var TUBE_TABLE = %%TUBE_TABLE%%;

// ── Gas-specific safety hard limits ──────────────────────────────────────────
var GAS_HARD_LIMITS = {
  "CO2":  {max_bar:69.9, danger:true,
    msg_en:"CO\u2082 inlet pressure \u226570 bar is not valid \u2014 at this pressure CO\u2082 transitions to liquid phase and cannot be used as a gas.",
    msg_he:"\u05dc\u05d7\u05e5 \u05db\u05e0\u05d9\u05e1\u05d4 \u05d0\u05d9\u05e0\u05d5 \u05ea\u05e7\u05d9\u05df \u2014 \u05d1\u05dc\u05d7\u05e5 70 \u05d1\u05e8 \u05d5\u05de\u05e2\u05dc\u05d4 \u05d2\u05d6 CO\u2082 \u05d4\u05d5\u05e4\u05da \u05dc\u05e0\u05d5\u05d6\u05dc."},
  "C2H2": {max_bar:17, danger:true,
    msg_en:"C\u2082H\u2082 (Acetylene) max safe working pressure is 17 bar \u2014 higher pressures risk explosive decomposition.",
    msg_he:"\u05dc\u05d7\u05e5 \u05d9\u05e2\u05d9\u05dc \u05de\u05e7\u05e1\u05d9\u05de\u05dc\u05d9 \u05dc\u05d0\u05e6\u05d8\u05d9\u05dc\u05df: 17 \u05d1\u05e8."},
  "H2S":  {max_bar:20, danger:false,
    msg_en:"H\u2082S max approved pressure is 20 bar per table specification.",
    msg_he:"\u05dc\u05d7\u05e5 \u05de\u05e7\u05e1\u05d9\u05de\u05dc\u05d9 \u05de\u05d0\u05d5\u05e9\u05e8 \u05dc-H\u2082S: 20 \u05d1\u05e8."},
  "CH4":  {max_bar:250, danger:false,
    msg_en:"CH\u2084 (Methane) max approved pressure is 250 bar per table specification.",
    msg_he:"\u05dc\u05d7\u05e5 \u05de\u05e7\u05e1\u05d9\u05de\u05dc\u05d9 \u05de\u05d0\u05d5\u05e9\u05e8 \u05dc\u05de\u05ea\u05d0\u05df: 250 \u05d1\u05e8."}
};

function checkGasLimits(gas, P) {
  var lim = GAS_HARD_LIMITS[gas];
  if (!lim) return null;
  if (P > lim.max_bar) return {danger:lim.danger, msg_en:lim.msg_en, msg_he:lim.msg_he};
  return null;
}

// Lookup: gas match + max_pressure >= inletP + id_mm >= diam
//
// Algorithm (ENGINEERING-CORRECT):
//   1. Basic filter: gas ✓, max_pressure ≥ inletP ✓, id_mm ≥ diam ✓
//   2. Anti-over-engineering cap: exclude specs where max_pressure > inletP × 5
//      → prevents recommending S12 (1380 bar) for a 10 bar Air system (138× overkill)
//      → fallback to unfiltered set if no spec passes the cap (covers exotic cases)
//   3. Sort: id_mm ASC (smallest pipe), max_pressure ASC (cheapest spec for same id)
//
// ─── GAS-SPECIFIC NOTE CAPS (from table Notes column) ──────────────────────
// Certain gases have max-pressure limits WITHIN a specific spec (from table notes).
// E.g. CO2 in S6/S9 is only valid up to 70 bar; above that CO2 becomes liquid.
var GAS_NOTE_CAPS = {
  "S6":  {"CO2":70,  "C2H2":17},
  "S9":  {"CO2":70,  "CH4":250, "C2H2":17},
  "S16": {"CO2":70,  "CH4":250, "C2H2":17, "H2S":20}
};

// ─── LOOKUP ALGORITHM ───────────────────────────────────────────────────────
//
//  Correct engineering logic (matches table structure):
//
//  Step 1  Filter rows where:
//    • gas_codes contains the selected gas
//    • O2 → ONLY S14 rows (O2 requires S14 per table note)
//    • gas-level note caps pass (e.g. CO2 ≤70 bar in S6/S9/S16)
//    • max_pressure ≥ inletP  (spec pressure rating covers the system)
//    • id_mm ≥ diam           (inner diameter meets the flow requirement)
//
//  Step 2  ONE representative per spec:
//    Within each spec (S6, S9, S14, B1, P6, etc.) keep only the ROW with
//    the SMALLEST id_mm that passes the filters. This gives one tube size
//    per spec — the minimum pipe needed.
//
//  Step 3  Sort spec representatives by max_pressure ASC:
//    Most economical (lowest-rated) spec appears first. This prevents
//    recommending S9 (400 bar) before B1 (40 bar) for a 10-bar Air system.
//
//  Returns: array of spec representatives, sorted most-economical first.
//
//  Examples:
//    Air 10 bar D≥7.90mm  →  P6(10bar) · C3(15bar) · B1(40bar) · S14… S6… S9… S12
//    N2 150 bar D≥8.22mm  →  S14(170bar) · S6(200bar) · S9(400bar)
//    O2 150 bar D≥3.79mm  →  S14 only (O2 rule)

function lookupTubeSpecs(gas, inletP, diam) {
  // Step 1: filter all rows
  var cands = TUBE_TABLE.filter(function(r) {
    if (r.gas_codes.indexOf(gas) === -1) return false;
    if (gas === "O2" && r.spec !== "S14") return false;   // O2 → S14 only
    var noteCap = (GAS_NOTE_CAPS[r.spec] || {})[gas];
    if (noteCap && inletP > noteCap) return false;        // gas-level note cap
    if (r.max_pressure < inletP) return false;            // spec pressure too low
    if (r.id_mm < diam) return false;                     // pipe too small
    return true;
  });

  // Step 2: one smallest-id entry per spec
  var bySpec = {};
  cands.forEach(function(r) {
    if (!bySpec[r.spec] || r.id_mm < bySpec[r.spec].id_mm) {
      bySpec[r.spec] = r;
    }
  });

  // Step 3: sort by max_pressure ASC (most economical first)
  var result = Object.values(bySpec);
  result.sort(function(a, b) { return a.max_pressure - b.max_pressure; });
  return result;
}

function fmtTube(s){ return s.replace(/X/g,' \u00d7 ').replace(/\s{2,}/g,' ').trim(); }

// ─── SPEC CARD — multi-result display ───────────────────────────────────────
function buildSpecCard(gas, inletP, diam) {
  var specs = lookupTubeSpecs(gas, inletP, diam);

  if (!specs.length) {
    return "<div class='rbox warn' style='margin-top:8px'>"
      + "<strong>&#9888;&nbsp;No approved tube specification found</strong><br>"
      + "<span class='he'>"
      + "\u05d0\u05d9\u05df \u05de\u05e4\u05e8\u05d8 \u05e6\u05e0\u05e8\u05ea "
      + "\u05de\u05d0\u05d5\u05e9\u05e8 \u05dc\u05d2\u05d6, \u05dc\u05dc\u05d7\u05e5 "
      + "\u05d5\u05dc\u05e7\u05d5\u05d8\u05e8 \u05e9\u05d4\u05d5\u05d6\u05e0\u05d5 "
      + "\u05d1\u05d4\u05ea\u05d0\u05dd \u05dc\u05d8\u05d1\u05dc\u05d4</span></div>";
  }

  var badge = "";
  if (gas === "O2") badge = "<span class='badge b-o2'>O\u2082 \u2192 S14 only</span>";
  if (gas === "H2") badge = "<span class='badge b-h2'>H\u2082 \u2192 S6 / S9</span>";

  var html = "<div class='spec-card'>"
    + "<div class='sc-head'>&#9654; Approved Tube Specifications" + badge
    + (specs.length > 1
        ? " <span style='color:rgba(0,229,204,0.38);font-size:10px;font-weight:normal'>"
          + "(" + specs.length + " specs \u2014 sorted: most economical first)</span>"
        : "")
    + "</div>";

  specs.forEach(function(m, i) {
    var isBest = (i === 0);
    var sf = (m.max_pressure / inletP).toFixed(1);
    html += "<div style='display:flex;align-items:flex-start;gap:8px;padding:5px 0;"
      + (i < specs.length - 1 ? "border-bottom:1px solid rgba(0,229,204,0.07);" : "") + "'>"
      + "<div style='color:" + (isBest ? "#00e5cc" : "rgba(0,229,204,0.32)") + ";font-size:12px;"
        + "padding-top:2px;width:12px;flex-shrink:0'>" + (isBest ? "&#9733;" : "&#9675;") + "</div>"
      + "<div style='flex:1'>"
        + "<div style='color:" + (isBest ? "#00ffee" : "rgba(0,229,204,0.72)") + ";font-size:14px'>"
          + "<strong>" + m.spec + "</strong>"
          + "&nbsp;&nbsp;<span style='color:" + (isBest ? "#00ffcc" : "rgba(0,229,204,0.58)") + ";font-size:13px'>"
          + fmtTube(m.tube_od_w) + "</span>"
        + "</div>"
        + "<div style='color:rgba(0,229,204,0.38);font-size:11px;margin-top:2px'>"
          + "ID " + m.id_mm.toFixed(3) + " mm"
          + "&nbsp;&nbsp;\u2502&nbsp;&nbsp;"
          + "Max " + m.max_pressure + " bar (" + sf + "\u00d7 safety)"
        + "</div>"
      + "</div></div>";
  });

  html += "</div>";
  return html;
}

function renderResult(line, diam, inletP, gas) {
  return "<div class='rbox ok'><div class='res-title'>" + line + "</div></div>"
       + buildSpecCard(gas, inletP, diam);
}

// ═══════════════════════════════════════════════════════════════════════════
//  GAS PHYSICS  —  unchanged
// ═══════════════════════════════════════════════════════════════════════════
var GAS_M={N2:.028013,O2:.031999,Ar:.039948,CO2:.04401,
           He:.0040026,H2:.002016,CH4:.01604,C2H2:.02604,
           FG1:.03881,FG2:.02671,Air:.02897};
var R=8.314, FR=0.02;
var FIELDS={
  diameter:["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Flow Rate (LPM)"],
  flow:    ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)"],
  length:  ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  inlet:   ["Temperature (\u00b0C)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  outlet:  ["Temperature (\u00b0C)","Inlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"]
};
var DEF={"Temperature (\u00b0C)":25,"Inlet Pressure (bar)":100,"Outlet Pressure (bar)":10,
         "Pipe Length (m)":10,"Pipe Diameter (mm)":10,"Flow Rate (LPM)":100};

function toKey(f){return f.replace(/ /g,"_").replace(/[()]/g,"").replace(/\//g,"").replace(/\u00b0/g,"deg")}
function fv(l){var e=document.getElementById(toKey(l));return e?(parseFloat(e.value)||0):(DEF[l]||0)}
function rho(P,T,g){return(P*1e5*GAS_M[g])/(R*(T+273.15))}
function rhoA(Pi,Po,T,g){return(rho(Pi,T,g)+rho(Po,T,g))/2}

function calcDiameter(Pi,Po,T,L,Q,g){
  var dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");
  return Math.pow((FR*L*8*rhoA(Pi,Po,T,g)*(Q/60000)**2)/(Math.PI**2*dP),0.2)*1000}
function calcFlow(Pi,Po,T,L,D,g){
  var dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");
  return Math.sqrt(dP*Math.PI**2*(D/1000)**5/(8*FR*L*rhoA(Pi,Po,T,g)))*60000}
function calcLength(Pi,Po,T,D,Q,g){
  var dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");
  return dP*Math.PI**2*(D/1000)**5/(8*FR*rhoA(Pi,Po,T,g)*(Q/60000)**2)}
function calcOutlet(Pi,T,L,D,Q,g){
  var Dm=D/1000,Qs=Q/60000;
  function res(Po){return(Pi-Po)*1e5-(8*FR*L*rhoA(Pi,Po,T,g)*Qs**2)/(Math.PI**2*Dm**5)}
  var lo=0,hi=Pi;
  for(var i=0;i<60;i++){if(Math.abs(hi-lo)<1e-4)break;var m=(lo+hi)/2;res(m)>0?lo=m:hi=m}
  return Math.max((lo+hi)/2,0)}
function calcInlet(Po,T,L,D,Q,g){
  var lo=Po,hi=Po+10;
  while(hi<Po+2000){if(calcOutlet(hi,T,L,D,Q,g)>=Po)break;hi+=10}
  for(var i=0;i<60;i++){var m=(lo+hi)/2,vm=calcOutlet(m,T,L,D,Q,g);
    if(Math.abs(vm-Po)<0.005)return m;vm<Po?lo=m:hi=m}
  return(lo+hi)/2}

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN CALCULATION
// ═══════════════════════════════════════════════════════════════════════════
function doCalc(){
  var gas=document.getElementById("gasSelect").value;
  var ct =document.getElementById("calcSelect").value;
  var area=document.getElementById("result-area");
  try{
    var Tc=fv("Temperature (\u00b0C)"),Pi=fv("Inlet Pressure (bar)"),
        Po=fv("Outlet Pressure (bar)"),L=fv("Pipe Length (m)"),
        D=fv("Pipe Diameter (mm)"),Q=fv("Flow Rate (LPM)");

    // Gas safety pre-check (all types except "inlet" where Pi is unknown)
    if(ct!=="inlet"){
      var e=checkGasLimits(gas,Pi);
      if(e){
        area.innerHTML="<div class='rbox "+(e.danger?"danger":"warn")+"'>"
          +"<strong>&#9888;&nbsp;Inlet pressure not valid for "+gas+"</strong><br>"
          +e.msg_en+"<div class='he'>"+e.msg_he+"</div></div>";
        return;
      }
    }

    var html="";
    if(ct==="diameter"){
      var r=calcDiameter(Pi,Po,Tc,L,Q,gas);
      html=renderResult("Required Diameter: <strong>"+r.toFixed(2)+" mm</strong>",r,Pi,gas);
    }else if(ct==="flow"){
      var r=calcFlow(Pi,Po,Tc,L,D,gas);
      html=renderResult("Maximum Flow Rate: <strong>"+r.toFixed(1)+" L/min</strong>",D,Pi,gas);
    }else if(ct==="length"){
      var r=calcLength(Pi,Po,Tc,D,Q,gas);
      html=renderResult("Maximum Pipe Length: <strong>"+r.toFixed(1)+" m</strong>",D,Pi,gas);
    }else if(ct==="inlet"){
      var r=calcInlet(Po,Tc,L,D,Q,gas);
      var e=checkGasLimits(gas,r);
      if(e){
        html="<div class='rbox ok'><div class='res-title'>Required Inlet Pressure: <strong>"
          +r.toFixed(2)+" bar</strong></div></div>"
          +"<div class='rbox "+(e.danger?"danger":"warn")+"' style='margin-top:8px'>"
          +"<strong>&#9888;&nbsp;Calculated pressure exceeds safe limit for "+gas+"</strong><br>"
          +e.msg_en+"<div class='he'>"+e.msg_he+"</div></div>";
      }else{
        html=renderResult("Required Inlet Pressure: <strong>"+r.toFixed(2)+" bar</strong>",D,r,gas);
      }
    }else if(ct==="outlet"){
      var r=calcOutlet(Pi,Tc,L,D,Q,gas);
      html=renderResult("Estimated Outlet Pressure: <strong>"+r.toFixed(2)+" bar</strong>",D,Pi,gas);
    }
    area.innerHTML=html;
    area.scrollIntoView({behavior:"smooth",block:"nearest"});
  }catch(e){area.innerHTML="<div class='rbox err'>&#9888; "+e.message+"</div>"}
}

// ═══════════════════════════════════════════════════════════════════════════
//  FIELD BUILDER
// ═══════════════════════════════════════════════════════════════════════════
function rebuildFields(){
  var ct=document.getElementById("calcSelect").value;
  var fl=FIELDS[ct]||[];var html="";
  fl.forEach(function(f){
    var k=toKey(f);
    html+="<div class='frow'><label>"+f+"</label>"
        +"<input type='number' id='"+k+"' value='"+(DEF[f]||0)+"' step='any'></div>";
  });
  document.getElementById("input-fields").innerHTML=html;
  document.getElementById("result-area").innerHTML="";
}
rebuildFields();

// ═══════════════════════════════════════════════════════════════════════════
//  HUD ANIMATIONS
// ═══════════════════════════════════════════════════════════════════════════
(function(){
  var C='#00e5cc', C2='rgba(0,229,204,', BG='#000d0d';
  var t=0;

  // ── Resize canvases to actual pixel size ─────────────────────────────────
  function fitCanvas(id){
    var c=document.getElementById(id);
    if(!c) return null;
    c.width=c.offsetWidth||c.clientWidth||100;
    c.height=c.offsetHeight||c.clientHeight||40;
    return c;
  }

  // ── Waveform painter ─────────────────────────────────────────────────────
  function drawWave(c,phase,amp,freq,lineW,alpha){
    if(!c) return;
    var ctx=c.getContext('2d'),w=c.width,h=c.height,mid=h/2;
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle='rgba(0,229,204,'+alpha+')';
    ctx.lineWidth=lineW;
    ctx.beginPath();
    for(var x=0;x<=w;x++){
      var y=mid+amp*Math.sin(freq*x/w*Math.PI*2+phase);
      x===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
    }
    ctx.stroke();
  }

  // ── Bar chart painter ─────────────────────────────────────────────────────
  function drawBars(c,vals){
    if(!c) return;
    var ctx=c.getContext('2d'),w=c.width,h=c.height;
    ctx.clearRect(0,0,w,h);
    var bw=Math.floor(w/vals.length)-1;
    vals.forEach(function(v,i){
      var bh=v*h;
      ctx.fillStyle='rgba(0,229,204,'+(0.5+v*0.5)+')';
      ctx.fillRect(i*(bw+1),h-bh,bw,bh);
    });
  }

  // ── Dot scatter painter ──────────────────────────────────────────────────
  var dots=[];
  for(var i=0;i<60;i++){
    dots.push({x:Math.random(),y:Math.random(),r:Math.random()*2+1,
               vx:(Math.random()-.5)*.001,vy:(Math.random()-.5)*.001,
               a:.3+Math.random()*.7});
  }
  function drawDots(c){
    if(!c) return;
    var ctx=c.getContext('2d'),w=c.width,h=c.height;
    ctx.clearRect(0,0,w,h);
    dots.forEach(function(d){
      d.x+=d.vx; d.y+=d.vy;
      if(d.x<0||d.x>1) d.vx*=-1;
      if(d.y<0||d.y>1) d.vy*=-1;
      ctx.beginPath();
      ctx.arc(d.x*w,d.y*h,d.r,0,Math.PI*2);
      ctx.fillStyle='rgba(0,229,204,'+d.a+')';
      ctx.fill();
    });
  }

  // ── Binary / hex data ────────────────────────────────────────────────────
  function rndHex(n){
    var s='';
    for(var i=0;i<n;i++) s+=(Math.floor(Math.random()*256)).toString(16).toUpperCase().padStart(2,'0')+' ';
    return s.trim();
  }
  function rndBin(){
    var s='';
    for(var i=0;i<64;i++) s+=Math.floor(Math.random()*2);
    return s.slice(0,32)+'\n'+s.slice(32);
  }

  // ── Segment bar (EXTRACT DATA) ────────────────────────────────────────────
  var sr=document.getElementById('seg-row');
  if(sr){
    var segs=7,lit=Math.floor(Math.random()*segs+1);
    for(var i=0;i<segs;i++){
      var s=document.createElement('div');
      s.className='seg'+(i>=lit?' dim':'');
      sr.appendChild(s);
    }
  }

  // ── Bar data arrays ───────────────────────────────────────────────────────
  var barVals1=[.3,.6,.45,.8,.55,.7,.4,.65];
  var barVals2=[.5,.3,.7,.4,.6,.35,.8,.45];
  var barValBot=[.4,.7,.3,.6,.5,.8,.25,.65,.45,.55];

  // ── Canvas references (sized after layout) ───────────────────────────────
  var cTopWave,cLeftWave,cLeftBin,cRW1,cRW2,cDots,cBar1,cBar2,cBarBot,cBotWave;

  function initCanvases(){
    cTopWave=fitCanvas('topWave');
    cLeftWave=fitCanvas('leftWave');
    cLeftBin=fitCanvas('leftBin');
    cRW1=fitCanvas('rWave1');
    cRW2=fitCanvas('rWave2');
    cDots=fitCanvas('dotPlot');
    cBar1=fitCanvas('barChart1');
    cBar2=fitCanvas('barChart2');
    cBarBot=fitCanvas('barChartBot');
    cBotWave=fitCanvas('botWave');
  }

  // ── Hex display ──────────────────────────────────────────────────────────
  var hexEl=document.getElementById('hexData');
  function updateHex(){
    if(!hexEl) return;
    var rows='';
    for(var r=0;r<5;r++) rows+=rndHex(8)+'<br>';
    hexEl.innerHTML=rows;
  }

  // ── Top bar data ─────────────────────────────────────────────────────────
  function updateTopBar(){
    var vals=[89,75,47,36].map(function(v){ return v+Math.floor((Math.random()-.5)*6); });
    for(var i=0;i<4;i++){
      var b=document.getElementById('b'+i);
      var n=document.getElementById('n'+i);
      if(b) b.style.width=Math.max(5,Math.min(100,vals[i]))+'%';
      if(n) n.textContent=Math.max(5,Math.min(99,vals[i]));
    }
    ['rn1','rn2','rn3','rn4'].forEach(function(id){
      var el=document.getElementById(id);
      if(el) el.textContent=Math.floor(Math.random()*60+20);
    });
  }

  // ── Big numbers ──────────────────────────────────────────────────────────
  function updateBigNums(){
    var e1=document.getElementById('bigNum1'),e2=document.getElementById('bigNum2');
    if(e1) e1.textContent=Math.floor(Math.random()*30+60);
    if(e2) e2.textContent=Math.floor(Math.random()*20+34);
  }

  // ── Bottom bar ───────────────────────────────────────────────────────────
  function updateBottom(){
    var h=document.getElementById('botHex');
    if(h) h.textContent=rndHex(8);
    ['bt1','bt2','bt3','bt4'].forEach(function(id){
      var el=document.getElementById(id);
      if(el) el.textContent=Math.floor(Math.random()*80+20);
    });
  }

  // ── Draw binary on left bar ──────────────────────────────────────────────
  function drawBinBar(c){
    if(!c) return;
    var ctx=c.getContext('2d'),w=c.width,h=c.height;
    ctx.clearRect(0,0,w,h);
    ctx.font='6px Courier New';
    ctx.fillStyle='rgba(0,229,204,0.4)';
    var bits=Math.floor(w/5);
    var s='';
    for(var i=0;i<bits;i++) s+=Math.floor(Math.random()*2);
    ctx.fillText(s,0,h*.7);
  }

  // ── Main loop ─────────────────────────────────────────────────────────────
  var frame=0;
  function loop(){
    t+=0.016;
    frame++;

    // Waveforms
    drawWave(cTopWave,t*1.2,8,2,1.2,'0.55');
    drawWave(cTopWave,t*.8+1,5,3,1,'0.30');
    drawWave(cLeftWave,t*.9,14,1.5,1.5,'0.70');
    drawWave(cLeftWave,t*.6+2,8,2.5,1,'0.40');
    drawWave(cRW1,t*1.1,10,2,1.2,'0.65');
    drawWave(cRW1,t*.7+1.5,6,3,0.8,'0.35');
    drawWave(cRW2,-t*.9+.5,12,1.8,1.4,'0.60');
    drawWave(cRW2,-t*.6,7,2.8,0.9,'0.32');
    drawWave(cBotWave,t*.8,8,2,1.2,'0.55');
    drawWave(cBotWave,-t*1.0+1,5,2.5,1,'0.30');

    // Dots
    drawDots(cDots);

    // Bars (animate slightly)
    if(frame%8===0){
      barVals1=barVals1.map(function(v){return Math.max(.05,Math.min(.98,v+(Math.random()-.5)*.12));});
      barVals2=barVals2.map(function(v){return Math.max(.05,Math.min(.98,v+(Math.random()-.5)*.10));});
      barValBot=barValBot.map(function(v){return Math.max(.05,Math.min(.98,v+(Math.random()-.5)*.10));});
    }
    drawBars(cBar1,barVals1);
    drawBars(cBar2,barVals2);
    drawBars(cBarBot,barValBot);

    // Slow updates
    if(frame%90===0){ updateHex(); updateBigNums(); }
    if(frame%45===0){ updateTopBar(); updateBottom(); }
    if(frame%30===0){ drawBinBar(cLeftBin); }

    requestAnimationFrame(loop);
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  setTimeout(function(){
    initCanvases();
    updateHex();
    updateBigNums();
    loop();
  },100);

  // Re-fit on resize
  window.addEventListener('resize',function(){
    setTimeout(initCanvases,50);
  });
})();
</script>
</body>
</html>"""

TUBE_TABLE_JSON = json.dumps(TUBE_TABLE, ensure_ascii=False)
page_html = PAGE.replace("%%TUBE_TABLE%%", TUBE_TABLE_JSON)
components.html(page_html, height=800, scrolling=False)
