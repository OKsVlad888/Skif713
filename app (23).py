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


# ── Optional HUD background ───────────────────────────────────────────────────
def load_hud() -> str:
    p = Path(__file__).resolve().parent / "hud_background.html"
    if not p.exists():
        return ""
    return "data:text/html;base64," + base64.b64encode(p.read_bytes()).decode()

hud_src = load_hud()
hud_tag = (
    f"<iframe id='hud' src='{hud_src}' sandbox='allow-scripts'></iframe>"
    if hud_src else
    "<div style='position:fixed;inset:0;background:#000d0d;z-index:1'></div>"
)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE HTML
# ══════════════════════════════════════════════════════════════════════════════

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{
  width:100%;height:100%;overflow:hidden;
  background:#000d0d;font-family:'Courier New',monospace;
  font-size:16px;color:#00e5cc;
}
#hud{position:fixed;inset:0;width:100%;height:100%;border:none;pointer-events:none;z-index:1}
#wrapper{
  position:fixed;top:18%;left:1%;width:73%;height:49%;
  display:flex;align-items:center;justify-content:center;
  z-index:500;pointer-events:none;
}
#panel{
  pointer-events:all;width:min(96%,580px);max-height:92%;
  overflow-y:auto;overflow-x:hidden;
  background:rgba(0,8,8,0.94);border:1.5px solid #00e5cc;border-radius:4px;
  padding:14px 22px 18px;position:relative;
  animation:panelGlow 2.5s ease-in-out infinite alternate;
  scrollbar-width:thin;scrollbar-color:#00e5cc rgba(0,229,204,0.08);
}
#panel::-webkit-scrollbar{width:6px}
#panel::-webkit-scrollbar-track{background:rgba(0,229,204,0.04);border-radius:3px}
#panel::-webkit-scrollbar-thumb{background:#00e5cc;border-radius:3px}
@keyframes panelGlow{
  from{box-shadow:0 0 8px rgba(0,229,204,0.26),inset 0 0 22px rgba(0,229,204,0.03)}
  to  {box-shadow:0 0 30px rgba(0,229,204,0.68),inset 0 0 52px rgba(0,229,204,0.07)}
}
#panel::after{
  content:"";position:absolute;inset:0;pointer-events:none;border-radius:4px;z-index:0;
  background:repeating-linear-gradient(
    to bottom,transparent 0,transparent 3px,
    rgba(0,229,204,0.009) 3px,rgba(0,229,204,0.009) 4px);
}
#panel h1{
  position:relative;z-index:1;color:#00ffee;text-shadow:0 0 14px #00e5cc;
  font-size:16px;letter-spacing:4px;text-transform:uppercase;text-align:center;
  margin-bottom:12px;line-height:1.45;
}
#panel h1 .tri{color:#00e5cc;margin-right:8px}
#body{position:relative;z-index:1;display:flex;flex-direction:column;gap:9px}
.sr{display:flex;flex-direction:column;gap:4px}
.sr label{font-size:16px;letter-spacing:1.5px;text-transform:uppercase;color:rgba(0,229,204,0.75)}
.sr select{
  background:rgba(0,14,12,0.98);color:#00ffee;
  border:1px solid rgba(0,229,204,0.42);border-radius:2px;
  padding:6px 28px 6px 9px;font-family:'Courier New',monospace;font-size:16px;
  width:100%;cursor:pointer;outline:none;
  -webkit-appearance:none;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2300e5cc'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
}
.sr select:focus{border-color:#00e5cc;box-shadow:0 0 7px rgba(0,229,204,0.38)}
.sr select option{background:#000d0d;color:#00e5cc}
.hdiv{border:none;border-top:1px solid rgba(0,229,204,0.2);margin:2px 0}
.frow{display:flex;flex-direction:column;gap:3px}
.frow label{font-size:16px;color:rgba(0,229,204,0.88);letter-spacing:0.2px}
.frow input{
  width:100%;background:rgba(0,14,12,0.98);color:#00ffee;
  border:1px solid rgba(0,229,204,0.4);border-radius:2px;
  padding:6px 9px;font-family:'Courier New',monospace;font-size:16px;outline:none;
}
.frow input:focus{border-color:#00e5cc;box-shadow:0 0 6px rgba(0,229,204,0.38)}
.frow input::-webkit-inner-spin-button,
.frow input::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}
.frow input[type=number]{-moz-appearance:textfield}
.cap{font-size:12px;color:rgba(0,229,204,0.42);letter-spacing:1px}
#cbtn{
  width:100%;background:rgba(0,229,204,0.07);color:#00ffee;
  border:1.5px solid #00e5cc;border-radius:2px;padding:8px 0;
  font-family:'Courier New',monospace;font-size:16px;
  letter-spacing:4px;cursor:pointer;text-transform:uppercase;
  transition:background .18s,box-shadow .18s;
}
#cbtn:hover {background:rgba(0,229,204,0.18);box-shadow:0 0 16px rgba(0,229,204,0.52)}
#cbtn:active{background:rgba(0,229,204,0.30)}
.rbox{padding:10px 14px;border-radius:2px;font-size:15px;line-height:1.75;word-break:break-word}
.rbox.ok{
  background:rgba(0,56,28,0.94);border:1px solid rgba(0,200,100,0.42);
  border-left:3px solid #00e87a;color:#00ffcc;
}
.rbox.ok .res-title{font-size:16px;font-weight:bold}
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
.rbox .he{direction:rtl;font-size:13px;opacity:.82;margin-top:4px}
.spec-card{
  margin-top:8px;padding:10px 14px;border-radius:2px;
  background:rgba(0,28,22,0.98);
  border:1px solid rgba(0,229,204,0.22);
  border-left:3px solid #00e5cc;
}
.spec-card .sc-head{
  color:rgba(0,229,204,0.52);font-size:11px;
  letter-spacing:2px;text-transform:uppercase;margin-bottom:7px;
}
.spec-card .sc-row{color:#00ffee;font-size:15px;line-height:2}
.spec-card .sc-note{color:rgba(0,229,204,0.45);font-size:12px;margin-top:3px}
.badge{
  display:inline-block;border-radius:2px;font-size:10px;
  letter-spacing:1.5px;padding:1px 6px;margin-left:6px;
  vertical-align:middle;text-transform:uppercase;
}
.b-o2{background:rgba(255,100,0,0.15);border:1px solid rgba(255,120,0,0.4);color:#ffaa44}
.b-h2{background:rgba(0,180,255,0.12);border:1px solid rgba(0,200,255,0.35);color:#66ddff}
</style>
</head>
<body>

%%HUD%%

<div id="wrapper">
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
// Example: Air 10 bar, D≥7.90mm
//   S12 (1380 bar, id=7.925): 1380 > 10×5=50 → EXCLUDED  ❌
//   B1  ( 40 bar, id=10.21): 40  ≤ 50          → included  → wins (smallest id after cap) ✅
var OVER_ENG_CAP = 5;  // max_pressure must not exceed 5× the working pressure

function lookupTubeSpec(gas, inletP, diam) {
  var all = TUBE_TABLE.filter(function(r){
    return r.gas_codes.indexOf(gas)!==-1 && r.max_pressure>=inletP && r.id_mm>=diam;
  });
  if (!all.length) return null;

  // Apply 5× cap; fall back to full set if nothing survives (edge-case safety)
  var capped = all.filter(function(r){ return r.max_pressure <= inletP * OVER_ENG_CAP; });
  var c = capped.length ? capped : all;

  // Smallest pipe first; among ties, cheapest spec (lowest pressure rating)
  c.sort(function(a,b){ return (a.id_mm-b.id_mm)||(a.max_pressure-b.max_pressure); });
  return c[0];
}

function fmtTube(s){return s.replace(/X/g,' \u00d7 ').replace(/\s{2,}/g,' ').trim();}

function buildSpecCard(gas, inletP, diam) {
  var m = lookupTubeSpec(gas, inletP, diam);
  if (!m) {
    return "<div class='rbox warn' style='margin-top:8px'>"
      +"<strong>&#9888;&nbsp;No approved tube specification found</strong><br>"
      +"<span class='he'>"
      +"\u05d0\u05d9\u05df \u05de\u05e4\u05e8\u05d8 \u05e6\u05e0\u05e8\u05ea "
      +"\u05de\u05d0\u05d5\u05e9\u05e8 \u05dc\u05d2\u05d6, \u05dc\u05dc\u05d7\u05e5 "
      +"\u05d5\u05dc\u05e7\u05d5\u05d8\u05e8 \u05e9\u05d4\u05d5\u05d6\u05e0\u05d5 "
      +"\u05d1\u05d4\u05ea\u05d0\u05dd \u05dc\u05d8\u05d1\u05dc\u05d4</span></div>";
  }
  var badge = "";
  if (gas==="O2") badge="<span class='badge b-o2'>O\u2082 \u2192 S14 only</span>";
  if (gas==="H2") badge="<span class='badge b-h2'>H\u2082 \u2192 S6 / S9</span>";
  return "<div class='spec-card'>"
    +"<div class='sc-head'>&#9654; Recommended Tube Specification"+badge+"</div>"
    +"<div class='sc-row'>"
    +"&#10003;&nbsp;<strong>Tube Spec:&nbsp;&nbsp;&nbsp;&nbsp;</strong>"+m.spec+"<br>"
    +"&#10003;&nbsp;<strong>Min. Tube Size:&nbsp;</strong>"+fmtTube(m.tube_od_w)
    +"</div>"
    +"<div class='sc-note'>"
    +"ID "+m.id_mm.toFixed(3)+" mm"
    +"&nbsp;&nbsp;\u2502&nbsp;&nbsp;"
    +"Max pressure rated: "+m.max_pressure+" bar"
    +"</div></div>";
}

function renderResult(line, diam, inletP, gas) {
  return "<div class='rbox ok'><div class='res-title'>"+line+"</div></div>"
        +buildSpecCard(gas, inletP, diam);
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
</script>
</body>
</html>"""

page_html = PAGE.replace("%%HUD%%", hud_tag).replace("%%TUBE_TABLE%%", TUBE_TABLE_JSON)
components.html(page_html, height=800, scrolling=False)
