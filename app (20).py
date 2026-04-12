"""
High-Pressure Gas Flow Calculator
===================================
Architecture:
  • Python reads the Excel tube-spec table at startup → JSON → embedded in JS
  • All TUBE SPEC recommendations are sourced ONLY from the table — no hard-coded rules
  • components.html() renders a full-viewport iframe
  • Panel is positioned over the HUD's black rectangle and flex-centred inside it
  • Internal scroll only on the panel — no outer scroll ever
  • All flow physics in JavaScript — instant calculation, no page reload

Run:  streamlit run app.py
Req:  hud_background.html                          (optional — HUD overlay)
      טבלת_ריכוז_לחצים_וסוגי_צנרת.xlsx  (required — tube-spec table)
"""

import base64
import json
import re
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="High-Pressure Gas Flow Calculator",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Strip Streamlit chrome; make the components iframe fill the viewport ──────
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
#  TUBE-SPEC TABLE  —  Parsed from Excel, embedded in JS as a const JSON array
# ══════════════════════════════════════════════════════════════════════════════

def parse_tube_table(excel_path: str) -> str:
    """
    Parse the engineering tube-spec Excel table into a flat JSON array.

    Each record:
        {
          "gas_codes":    [<UI gas codes>],   e.g. ["N2", "Ar", "He", ...]
          "spec":         str,                e.g. "S6"
          "id_mm":        float,              Inner diameter in mm
          "tube_od_w":    str,                e.g. '3/8"X0.049"'
          "max_pressure": float               Maximum allowed pressure [bar]
        }

    Lookup algorithm (enforced in JS):
        1. Filter records where gas code matches the selected gas
        2. Filter records where max_pressure >= inlet_pressure
        3. Filter records where id_mm >= requested_pipe_diameter
        4. Sort: id_mm ascending, then max_pressure ascending (most economical spec)
        5. Return first match — or null if no match exists
    """

    # Precise regex patterns per UI gas code.
    # Avoids false matches (e.g. "O2" inside "CO2", "Ar" inside "Carbone").
    # H2 (Hydrogen) is intentionally absent — not present in the Excel table.
    GAS_PATTERNS: dict = {
        "N2":   r"\bN2\b",
        "O2":   r"\bO2\b",
        "Ar":   r"\bAr\b",
        "CO2":  r"\bCO2\b",
        "He":   r"\bHe\b",
        "CH4":  r"\bCH4\b",
        "C2H2": r"\bC2H2\b",
        "FG1":  r"Forming Gas 1",
        "FG2":  r"Forming Gas 2",
        "Air":  r"\bAir\b",
        "H2S":  r"\bH2S\b",
    }

    def _parse_pressure(cell_str: str):
        """Extract numeric bar value from strings like '≤200', '≤400 bar'."""
        if not cell_str or cell_str in ("nan", "NaN", ""):
            return None
        m = re.search(r"(\d+(?:\.\d+)?)", cell_str)
        return float(m.group(1)) if m else None

    def _extract_gas_codes(gas_cell_str: str) -> list:
        """Return UI gas-codes whose regex pattern matches the Excel cell text."""
        return [code for code, pat in GAS_PATTERNS.items()
                if re.search(pat, gas_cell_str)]

    df = pd.read_excel(excel_path, header=None)
    records: list = []

    # Forward-fill state within each spec group
    current_gases: str = ""
    current_spec:  str = ""
    current_pressure   = None

    for idx, row in df.iterrows():
        if idx <= 1:
            continue  # skip blank row 0 and header row 1

        # Columns: 0=Notes  1=Gas type  2=ID(mm)  3=OD×W  4=Pressure  5=Spec
        raw_gas      = row[1]
        raw_id       = row[2]
        raw_od_w     = row[3]
        raw_pressure = row[4]
        raw_spec     = row[5]

        # ── Update group metadata when a new value appears in this row ────
        if pd.notna(raw_spec) and str(raw_spec).strip() not in ("nan", ""):
            current_spec = str(raw_spec).strip()
        if pd.notna(raw_gas) and str(raw_gas).strip() not in ("nan", ""):
            current_gases = str(raw_gas).strip()

        # Per-row pressure overrides group pressure (handles S14 / S16 pattern
        # where each diameter row carries its own individual pressure limit).
        p = _parse_pressure(str(raw_pressure)) if pd.notna(raw_pressure) else None
        if p is not None:
            current_pressure = p

        # ── Emit a record only when this row has a valid diameter + OD×W ──
        if not pd.notna(raw_id):
            continue
        try:
            id_mm = float(raw_id)
        except (ValueError, TypeError):
            continue

        od_w_str = str(raw_od_w).strip() if pd.notna(raw_od_w) else ""
        if not od_w_str or od_w_str in ("nan", ""):
            continue

        if not current_spec or current_pressure is None or not current_gases:
            continue

        gas_codes = _extract_gas_codes(current_gases)
        if not gas_codes:
            continue

        records.append({
            "gas_codes":    gas_codes,
            "spec":         current_spec,
            "id_mm":        round(id_mm, 5),
            "tube_od_w":    od_w_str,
            "max_pressure": current_pressure,
        })

    return json.dumps(records, ensure_ascii=False)


# ── Load tube table (fail gracefully if file is missing) ─────────────────────
_TABLE_PATH = Path(__file__).resolve().parent / "טבלת_ריכוז_לחצים_וסוגי_צנרת.xlsx"
try:
    TUBE_TABLE_JSON = parse_tube_table(str(_TABLE_PATH))
except FileNotFoundError:
    TUBE_TABLE_JSON = "[]"
    st.warning("⚠️ Tube spec table not found. Pipe recommendations will be unavailable.")


# ── Load optional HUD background ─────────────────────────────────────────────
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
#  PAGE HTML  (CSS unchanged; JS logic updated to use TUBE_TABLE)
# ══════════════════════════════════════════════════════════════════════════════

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  width:  100%;
  height: 100%;
  overflow: hidden;
  background: #000d0d;
  font-family: 'Courier New', monospace;
  font-size: 16px;
  color: #00e5cc;
}

#hud {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  border: none;
  pointer-events: none;
  z-index: 1;
}

/* Wrapper positioned over the HUD's black rectangle */
#wrapper {
  position: fixed;
  top:    18%;
  left:   1%;
  width:  73%;
  height: 49%;
  display: flex;
  align-items:     center;
  justify-content: center;
  z-index: 500;
  pointer-events: none;
}

#panel {
  pointer-events: all;
  width:      min(96%, 580px);
  max-height: 92%;
  overflow-y: auto;
  overflow-x: hidden;
  background: rgba(0,8,8,0.94);
  border: 1.5px solid #00e5cc;
  border-radius: 4px;
  padding: 14px 22px 18px;
  box-shadow: 0 0 22px rgba(0,229,204,0.42), inset 0 0 40px rgba(0,229,204,0.04);
  animation: panelGlow 2.5s ease-in-out infinite alternate;
  position: relative;
  scrollbar-width: thin;
  scrollbar-color: #00e5cc rgba(0,229,204,0.08);
}
#panel::-webkit-scrollbar       { width: 6px; }
#panel::-webkit-scrollbar-track { background: rgba(0,229,204,0.04); border-radius: 3px; }
#panel::-webkit-scrollbar-thumb { background: #00e5cc; border-radius: 3px; }

@keyframes panelGlow {
  from { box-shadow: 0 0  8px rgba(0,229,204,0.26), inset 0 0 22px rgba(0,229,204,0.03); }
  to   { box-shadow: 0 0 30px rgba(0,229,204,0.68), inset 0 0 52px rgba(0,229,204,0.07); }
}

#panel::after {
  content: ""; position: absolute; inset: 0;
  pointer-events: none; border-radius: 4px; z-index: 0;
  background: repeating-linear-gradient(
    to bottom, transparent 0, transparent 3px,
    rgba(0,229,204,0.009) 3px, rgba(0,229,204,0.009) 4px);
}

#panel h1 {
  position: relative; z-index: 1;
  color: #00ffee; text-shadow: 0 0 14px #00e5cc;
  font-size: 16px; letter-spacing: 4px;
  text-transform: uppercase; text-align: center;
  margin-bottom: 12px; line-height: 1.45;
}
#panel h1 .tri { color: #00e5cc; margin-right: 8px; }

#body { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 9px; }

.sr { display: flex; flex-direction: column; gap: 4px; }
.sr label {
  font-size: 16px; letter-spacing: 1.5px;
  text-transform: uppercase; color: rgba(0,229,204,0.75);
}
.sr select {
  background: rgba(0,14,12,0.98); color: #00ffee;
  border: 1px solid rgba(0,229,204,0.42); border-radius: 2px;
  padding: 6px 28px 6px 9px;
  font-family: 'Courier New', monospace; font-size: 16px;
  width: 100%; cursor: pointer; outline: none;
  -webkit-appearance: none; appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2300e5cc'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 10px center;
}
.sr select:focus { border-color: #00e5cc; box-shadow: 0 0 7px rgba(0,229,204,0.38); }
.sr select option { background: #000d0d; color: #00e5cc; }

.hdiv { border: none; border-top: 1px solid rgba(0,229,204,0.2); margin: 2px 0; }

.frow { display: flex; flex-direction: column; gap: 3px; }
.frow label { font-size: 16px; color: rgba(0,229,204,0.88); letter-spacing: 0.2px; }
.frow input {
  width: 100%; background: rgba(0,14,12,0.98); color: #00ffee;
  border: 1px solid rgba(0,229,204,0.4); border-radius: 2px;
  padding: 6px 9px; font-family: 'Courier New', monospace; font-size: 16px; outline: none;
}
.frow input:focus { border-color: #00e5cc; box-shadow: 0 0 6px rgba(0,229,204,0.38); }
.frow input::-webkit-inner-spin-button,
.frow input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.frow input[type=number] { -moz-appearance: textfield; }

.cap { font-size: 12px; color: rgba(0,229,204,0.42); letter-spacing: 1px; }

#cbtn {
  width: 100%; background: rgba(0,229,204,0.07); color: #00ffee;
  border: 1.5px solid #00e5cc; border-radius: 2px; padding: 8px 0;
  font-family: 'Courier New', monospace; font-size: 16px;
  letter-spacing: 4px; cursor: pointer; text-transform: uppercase;
  transition: background .18s, box-shadow .18s;
}
#cbtn:hover  { background: rgba(0,229,204,0.18); box-shadow: 0 0 16px rgba(0,229,204,0.52); }
#cbtn:active { background: rgba(0,229,204,0.30); }

/* ── Result boxes ── */
.rbox {
  padding: 10px 14px; border-radius: 2px;
  font-size: 15px; line-height: 1.75; word-break: break-word;
}
.rbox.ok {
  background: rgba(0,56,28,0.94); border: 1px solid rgba(0,200,100,0.42);
  border-left: 3px solid #00e87a; color: #00ffcc;
}
.rbox.ok .res-title { font-size:16px; font-weight:bold; }
.rbox.warn {
  background: rgba(40,30,0,0.96); border: 1px solid rgba(255,200,50,0.32);
  border-left: 3px solid #ffcc00; color: #ffe080; font-size:14px;
}
.rbox.err {
  background: rgba(38,0,0,0.96); border: 1px solid rgba(255,60,60,0.32);
  border-left: 3px solid #ff4444; color: #ff9090;
}
.spec-card {
  margin-top: 8px; padding: 10px 14px; border-radius: 2px;
  background: rgba(0,30,20,0.98);
  border: 1px solid rgba(0,229,204,0.25);
  border-left: 3px solid #00e5cc;
}
.spec-card .sc-header {
  color: rgba(0,229,204,0.55); font-size:12px;
  letter-spacing:1.5px; text-transform:uppercase; margin-bottom:6px;
}
.spec-card .sc-body {
  color:#00ffee; font-size:15px; line-height:1.9;
}
.spec-card .sc-meta {
  color:rgba(0,229,204,0.5); font-size:13px; margin-top:2px;
}
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
//  TUBE SPEC TABLE — injected from Python / Excel at startup.
//  Authority: Excel table only. No hard-coded rules below.
// ═══════════════════════════════════════════════════════════════════════════
const TUBE_TABLE = %%TUBE_TABLE%%;

/**
 * lookupTubeSpec(gasCode, inletPressure_bar, pipeDiameter_mm)
 *
 * Single source of truth for pipe spec selection.
 * Algorithm:
 *   1. Filter rows where gas_codes contains gasCode
 *   2. Filter rows where max_pressure >= inletPressure
 *   3. Filter rows where id_mm >= pipeDiameter
 *   4. Sort: id_mm asc, then max_pressure asc  →  smallest pipe, lightest spec
 *   5. Return first match, or null if no record survives filtering
 */
function lookupTubeSpec(gasCode, inletPressure, pipeDiameter) {
  var candidates = TUBE_TABLE.filter(function(r) {
    return r.gas_codes.indexOf(gasCode) !== -1
        && r.max_pressure >= inletPressure
        && r.id_mm        >= pipeDiameter;
  });
  if (candidates.length === 0) return null;
  candidates.sort(function(a, b) {
    return (a.id_mm - b.id_mm) || (a.max_pressure - b.max_pressure);
  });
  return candidates[0];
}

/** Format tube size string: 'X' separator → ' × ' for display */
function fmtTube(s) {
  return s.replace(/X/g, ' \u00d7 ').replace(/\s{2,}/g, ' ').trim();
}

// ═══════════════════════════════════════════════════════════════════════════
//  GAS PHYSICS  — unchanged from original
// ═══════════════════════════════════════════════════════════════════════════
var GAS_M = {
  N2:.028013, O2:.031999, Ar:.039948, CO2:.04401,
  He:.0040026, H2:.002016, CH4:.01604, C2H2:.02604,
  FG1:.03881, FG2:.02671, Air:.02897
};
var R = 8.314, FR = 0.02;

var FIELDS = {
  diameter: ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Flow Rate (LPM)"],
  flow:     ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)"],
  length:   ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  inlet:    ["Temperature (\u00b0C)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  outlet:   ["Temperature (\u00b0C)","Inlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"]
};
var DEF = {
  "Temperature (\u00b0C)":25, "Inlet Pressure (bar)":100,
  "Outlet Pressure (bar)":10, "Pipe Length (m)":10,
  "Pipe Diameter (mm)":10,    "Flow Rate (LPM)":100
};

function toKey(f) {
  return f.replace(/ /g,"_").replace(/[()]/g,"").replace(/\//g,"").replace(/\u00b0/g,"deg");
}
function fv(label) {
  var el = document.getElementById(toKey(label));
  return el ? (parseFloat(el.value) || 0) : (DEF[label] || 0);
}

function rho(Pbar, Tc, gas) {
  return (Pbar * 1e5 * GAS_M[gas]) / (R * (Tc + 273.15));
}
function rhoAvg(Pi, Po, Tc, gas) {
  return (rho(Pi, Tc, gas) + rho(Po, Tc, gas)) / 2;
}
function calcDiameter(Pi, Po, Tc, L, Q, gas) {
  var dP = (Pi - Po) * 1e5;
  if (dP <= 0) throw new Error("Inlet pressure must exceed outlet pressure.");
  return Math.pow((FR*L*8*rhoAvg(Pi,Po,Tc,gas)*(Q/60000)**2) / (Math.PI**2*dP), 0.2) * 1000;
}
function calcFlow(Pi, Po, Tc, L, D, gas) {
  var dP = (Pi - Po) * 1e5;
  if (dP <= 0) throw new Error("Inlet pressure must exceed outlet pressure.");
  return Math.sqrt(dP * Math.PI**2 * (D/1000)**5 / (8*FR*L*rhoAvg(Pi,Po,Tc,gas))) * 60000;
}
function calcLength(Pi, Po, Tc, D, Q, gas) {
  var dP = (Pi - Po) * 1e5;
  if (dP <= 0) throw new Error("Inlet pressure must exceed outlet pressure.");
  return dP * Math.PI**2 * (D/1000)**5 / (8*FR*rhoAvg(Pi,Po,Tc,gas)*(Q/60000)**2);
}
function calcOutlet(Pi, Tc, L, D, Q, gas) {
  var Dm = D/1000, Qs = Q/60000;
  function res(Po) {
    return (Pi-Po)*1e5 - (8*FR*L*rhoAvg(Pi,Po,Tc,gas)*Qs**2) / (Math.PI**2*Dm**5);
  }
  var lo = 0, hi = Pi;
  for (var i = 0; i < 60; i++) {
    if (Math.abs(hi - lo) < 1e-4) break;
    var m = (lo + hi) / 2;
    res(m) > 0 ? lo = m : hi = m;
  }
  return Math.max((lo + hi) / 2, 0);
}
function calcInlet(Po, Tc, L, D, Q, gas) {
  var lo = Po, hi = Po + 10;
  while (hi < Po + 2000) {
    if (calcOutlet(hi, Tc, L, D, Q, gas) >= Po) break;
    hi += 10;
  }
  for (var i = 0; i < 60; i++) {
    var m = (lo + hi) / 2, vm = calcOutlet(m, Tc, L, D, Q, gas);
    if (Math.abs(vm - Po) < 0.005) return m;
    vm < Po ? lo = m : hi = m;
  }
  return (lo + hi) / 2;
}

// ═══════════════════════════════════════════════════════════════════════════
//  RESULT RENDERING
// ═══════════════════════════════════════════════════════════════════════════

/**
 * renderResult(mainLine, pipeDiam_mm, inletPressure_bar, gasCode)
 *
 * mainLine      — HTML for the computed engineering value
 * pipeDiam      — diameter used for table lookup (input OR calculated)
 * inletP        — inlet pressure used for table lookup (input OR calculated)
 * gasCode       — UI select value, e.g. "N2"
 */
function renderResult(mainLine, pipeDiam, inletP, gasCode) {
  var match = lookupTubeSpec(gasCode, inletP, pipeDiam);

  var specBlock = "";
  if (match === null) {
    specBlock =
      "<div class='rbox warn' style='margin-top:8px'>" +
        "&#9888;&nbsp;<strong>No approved tube specification found</strong><br>" +
        "<span style='font-size:13px;opacity:.85'>" +
          "אין מפרט צנרת מאושר לגז, ללחץ ולקוטר שהוזנו בהתאם לטבלה" +
        "</span>" +
      "</div>";
  } else {
    specBlock =
      "<div class='spec-card'>" +
        "<div class='sc-header'>&#9654; Recommended Tube Specification</div>" +
        "<div class='sc-body'>" +
          "&#10003;&nbsp;<strong>Tube Spec:&nbsp;&nbsp;</strong>" + match.spec + "<br>" +
          "&#10003;&nbsp;<strong>Min. Tube Size:&nbsp;</strong>" + fmtTube(match.tube_od_w) +
        "</div>" +
        "<div class='sc-meta'>" +
          "ID " + match.id_mm.toFixed(3) + " mm" +
          "&nbsp;&nbsp;|&nbsp;&nbsp;Max pressure: " + match.max_pressure + " bar" +
        "</div>" +
      "</div>";
  }

  return "<div class='rbox ok'><div class='res-title'>" + mainLine + "</div></div>" + specBlock;
}

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN CALCULATION
// ═══════════════════════════════════════════════════════════════════════════
function doCalc() {
  var gas  = document.getElementById("gasSelect").value;
  var ct   = document.getElementById("calcSelect").value;
  var area = document.getElementById("result-area");
  try {
    var Tc = fv("Temperature (\u00b0C)"),
        Pi = fv("Inlet Pressure (bar)"),
        Po = fv("Outlet Pressure (bar)"),
        L  = fv("Pipe Length (m)"),
        D  = fv("Pipe Diameter (mm)"),
        Q  = fv("Flow Rate (LPM)");
    var html = "";

    // renderResult(mainLine, diameterForLookup, inletPressureForLookup, gas)
    if (ct === "diameter") {
      var r = calcDiameter(Pi, Po, Tc, L, Q, gas);
      html = renderResult(
        "Required Diameter: <strong>" + r.toFixed(2) + " mm</strong>",
        r, Pi, gas            // r = calculated diameter
      );
    } else if (ct === "flow") {
      var r = calcFlow(Pi, Po, Tc, L, D, gas);
      html = renderResult(
        "Maximum Flow Rate: <strong>" + r.toFixed(1) + " L/min</strong>",
        D, Pi, gas            // D = input diameter
      );
    } else if (ct === "length") {
      var r = calcLength(Pi, Po, Tc, D, Q, gas);
      html = renderResult(
        "Maximum Pipe Length: <strong>" + r.toFixed(1) + " m</strong>",
        D, Pi, gas
      );
    } else if (ct === "inlet") {
      var r = calcInlet(Po, Tc, L, D, Q, gas);
      html = renderResult(
        "Required Inlet Pressure: <strong>" + r.toFixed(2) + " bar</strong>",
        D, r, gas             // r = calculated inlet pressure
      );
    } else if (ct === "outlet") {
      var r = calcOutlet(Pi, Tc, L, D, Q, gas);
      html = renderResult(
        "Estimated Outlet Pressure: <strong>" + r.toFixed(2) + " bar</strong>",
        D, Pi, gas
      );
    }

    area.innerHTML = html;
    area.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch(e) {
    area.innerHTML = "<div class='rbox err'>&#9888; " + e.message + "</div>";
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  FIELD BUILDER  — unchanged
// ═══════════════════════════════════════════════════════════════════════════
function rebuildFields() {
  var ct = document.getElementById("calcSelect").value;
  var fl = FIELDS[ct] || [];
  var html = "";
  fl.forEach(function(f) {
    var k = toKey(f);
    html += "<div class='frow'><label>" + f + "</label>" +
            "<input type='number' id='" + k + "' value='" + (DEF[f]||0) + "' step='any'></div>";
  });
  document.getElementById("input-fields").innerHTML = html;
  document.getElementById("result-area").innerHTML  = "";
}

rebuildFields();
</script>
</body>
</html>"""

# ── Inject HUD tag and tube-spec JSON table, then render ─────────────────────
page_html = (PAGE
             .replace("%%HUD%%",        hud_tag)
             .replace("%%TUBE_TABLE%%", TUBE_TABLE_JSON))

components.html(page_html, height=800, scrolling=False)
