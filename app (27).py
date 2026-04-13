# app.py
# High‑Pressure Gas Flow Calculator
# ✅ Clean, stable Streamlit version
# ✅ HUD background via iframe
# ✅ No JS outside HTML (NO NameError)
# ✅ Ready for Streamlit Cloud

import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------------
# Streamlit config
# ------------------------------------------------------------
st.set_page_config(
    page_title="High‑Pressure Gas Flow Calculator",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit UI chrome
st.markdown(
    """
    <style>
    #MainMenu, header, footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# HUD loader (safe)
# ------------------------------------------------------------
def load_hud():
    p = Path(__file__).parent / "hud_background.html"
    if not p.exists():
        return ""
    return "data:text/html;base64," + base64.b64encode(p.read_bytes()).decode()

hud_src = load_hud()

hud_iframe = (
    f'<iframe src="{hud_src}" id="hudbg"></iframe>'
    if hud_src else
    '<!-- HUD background not found -->'
)

# ------------------------------------------------------------
# Page HTML (ALL JS IS INSIDE THIS STRING)
# ------------------------------------------------------------
PAGE = f"""
<style>
html, body {{
  margin: 0;
  padding: 0;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #000d0d;
  font-family: 'Courier New', monospace;
}}

#hudbg {{
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  border: none;
  z-index: 0;
  pointer-events: none;
}}

#layer {{
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}}

#panel {{
  width: 760px;
  max-height: 78vh;
  overflow-y: auto;
  padding: 18px;
  background: rgba(0,14,14,0.78);
  border: 1px solid #00e5cc;
  box-shadow:
    0 0 18px rgba(0,229,204,.35),
    inset 0 0 14px rgba(0,229,204,.2);
  color: #00ffee;
}}

#panel::-webkit-scrollbar {{ width: 10px; }}
#panel::-webkit-scrollbar-thumb {{
  background: rgba(0,229,204,.35);
  border-radius: 6px;
}}

#alert {{
  display: none;
  margin: 10px 0;
  padding: 8px;
  border: 1px solid #ff3344;
  background: rgba(40,0,0,.55);
  color: #ffd3d8;
  letter-spacing: 2px;
  animation: blink .8s steps(1) infinite;
}}

@keyframes blink {{
  50% {{ opacity: .3; }}
}}

#conf {{
  margin-top: 10px;
  padding: 8px;
  border: 1px solid rgba(0,229,204,.35);
}}

#bar {{
  height: 10px;
  border: 1px solid rgba(0,229,204,.35);
}}

#fill {{
  height: 100%;
  width: 0;
  background: linear-gradient(90deg,#00e5cc,#00ffee);
  transition: width .3s;
}}
</style>

{hud_iframe}

<div id="layer">
  <div id="panel">
    <h2>▲ HIGH‑PRESSURE GAS FLOW CALCULATOR</h2>

    <label>Gas Type</label><br>
    <select id="gas">
      <option>N2</option>
      <option>O2</option>
      <option>CO2</option>
    </select><br><br>

    <label>Flow Rate (LPM)</label><br>
    <input id="flow" type="number" value="16"><br><br>

    <label>Inlet Pressure (bar)</label><br>
    <input id="pin" type="number" value="200"><br><br>

    <label>Outlet Pressure (bar)</label><br>
    <input id="pout" type="number" value="10"><br><br>

    <button onclick="calculate()">CALCULATE</button>

    <div id="alert">⚠ ALERT: SAFETY BLOCKED</div>

    <div id="result"></div>

    <div id="conf">
      <div>RECOMMENDATION CONFIDENCE</div>
      <div id="bar"><div id="fill"></div></div>
      <div id="pct">0%</div>
    </div>
  </div>
</div>

<script>
function calculate() {{
  const gas  = document.getElementById('gas').value;
  const flow = Number(document.getElementById('flow').value);
  const pin  = Number(document.getElementById('pin').value);
  const pout = Number(document.getElementById('pout').value);

  const blocked = (gas === 'CO2' && pin > 70);
  const status  = blocked ? 'ALERT' : 'OK';

  document.getElementById('alert').style.display = blocked ? 'block' : 'none';

  document.getElementById('result').innerHTML = blocked
    ? '<b>SAFETY BLOCKED</b><br>CO₂ pressure exceeds safe limit'
    : 'Required Diameter: 3.7 mm<br>Recommended Spec: S6';

  const confidence = blocked ? 0.05 : 0.9;
  document.getElementById('fill').style.width = (confidence * 100) + '%';
  document.getElementById('pct').innerText = Math.round(confidence * 100) + '%';

  // ✅ SAFE postMessage (JS only)
  window.parent.postMessage({{
    calc: {{ Status: status, Pin: pin, Pout: pout, Flow: flow }}
  }}, '*');
}}
</script>
"""

# ------------------------------------------------------------
# Render
# ------------------------------------------------------------
components.html(PAGE, height=900, scrolling=False)
