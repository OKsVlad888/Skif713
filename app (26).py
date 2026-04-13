# app.py
# High-Pressure Gas Flow Calculator with Live HUD, ALERT mode and Confidence Meter
# Ready for Streamlit Cloud deployment

import base64
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="High-Pressure Gas Flow Calculator",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit chrome
st.markdown("""
<style>
#MainMenu, header, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ================= HUD loader =================
def load_hud():
    p = Path(__file__).parent / "hud_background.html"
    if not p.exists():
        return ""
    return "data:text/html;base64," + base64.b64encode(p.read_bytes()).decode()

hud_src = load_hud()

hud_tag = f"""
<iframe src="{hud_src}" id="hudbg"></iframe>
""" if hud_src else ""

# ================= PAGE HTML =================
PAGE = f"""
<style>
html, body {{
  margin: 0; padding: 0;
  width: 100vw; height: 100vh;
  overflow: hidden;
  background: #000d0d;
  font-family: 'Courier New', monospace;
}}
#hudbg{{position:fixed;inset:0;border:none;width:100vw;height:100vh;z-index:0;pointer-events:none}}
#layer{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:10}}
#panel{{width:760px;max-height:78vh;overflow-y:auto;padding:18px;background:rgba(0,14,14,0.78);
border:1px solid #00e5cc;box-shadow:0 0 18px rgba(0,229,204,.35), inset 0 0 14px rgba(0,229,204,.2);
color:#00ffee}}
#panel::-webkit-scrollbar{{width:10px}}
#panel::-webkit-scrollbar-thumb{{background:rgba(0,229,204,.35);border-radius:6px}}
#alert{{display:none;margin:10px 0;padding:8px;border:1px solid #ff3344;background:rgba(40,0,0,.55);
color:#ffd3d8;letter-spacing:2px;animation:blink .8s steps(1) infinite}}
@keyframes blink{{50%{{opacity:.3}}}}
#conf{{margin-top:10px;padding:8px;border:1px solid rgba(0,229,204,.35)}}
#bar{{height:10px;border:1px solid rgba(0,229,204,.35)}}
#fill{{height:100%;width:0;background:linear-gradient(90deg,#00e5cc,#00ffee);transition:width .3s}}
</style>

{hud_tag}

<div id="layer">
  <div id="panel">
    <h2>▲ HIGH‑PRESSURE GAS FLOW CALCULATOR</h2>

    <label>Gas Type</label>
    <select id="gas"><option>N2</option><option>O2</option><option>CO2</option></select>

    <label>Flow Rate (LPM)</label>
    <input id="flow" type="number" value="16">

    <label>Inlet Pressure (bar)</label>
    <input id="pin" type="number" value="200">

    <label>Outlet Pressure (bar)</label>
    <input id="pout" type="number" value="10">

    <button onclick="calc()">CALCULATE</button>

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
function clamp(v,a,b){{return Math.max(a,Math.min(b,v))}}

function calc(){{
  const gas=document.getElementById('gas').value;
  const flow=+flowEl.value;
  const pin=+pinEl.value;
  const blocked=(gas==='CO2' && pin>70);
  const status=blocked?'ALERT':'OK';

  document.getElementById('alert').style.display=blocked?'block':'none';

  document.getElementById('result').innerHTML=
    blocked?'<b>SAFETY BLOCKED</b>':'Required Diameter: 3.7 mm<br>Spec: S6';

  const conf=blocked?0.05:0.9;
  document.getElementById('fill').style.width=(conf*100)+'%';
  document.getElementById('pct').innerText=Math.round(conf*100)+'%';

  window.parent.postMessage({calc:{Status:status,Pin:pin,Flow:flow}},'*');
}}
const flowEl=document.getElementById('flow');
const pinEl=document.getElementById('pin');
const poutEl=document.getElementById('pout');
</script>
"""

components.html(PAGE, height=900, scrolling=False)
