"""
High-Pressure Gas Flow Calculator
===================================
Architecture:
  • components.html() renders a full-viewport iframe (height=100vh via JS resize trick)
  • Inside the iframe: HUD background + calculator panel
  • Panel is flex-centred inside a full-viewport wrapper (no hard-coded offsets)
  • Internal scroll only on the panel — no outer scroll ever
  • All physics in JavaScript — instant calculation, no page reload
  • All text: 16px

Run:  streamlit run app.py
Req:  hud_background.html in same folder (optional)
"""

import base64
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="High-Pressure Gas Flow Calculator",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Strip Streamlit chrome and make the components iframe fill the viewport
st.markdown("""
<style>
  #MainMenu,footer,header,
  [data-testid="stToolbar"],[data-testid="stDecoration"],
  [data-testid="stStatusWidget"],[data-testid="collapsedControl"]{display:none!important}
  .stApp{background:#000d0d!important}
  section.main,.block-container{padding:0!important;margin:0!important;max-width:100vw!important}
  /* Make the iframe fill the full viewport */
  iframe[title="streamlit_components_v1.html_v1"]{
    position:fixed!important;inset:0!important;
    width:100vw!important;height:100vh!important;
    border:none!important;z-index:100!important;
    display:block!important}
</style>
""", unsafe_allow_html=True)


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

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* The iframe's own document fills its container exactly */
html, body {
  width:  100%;
  height: 100%;
  overflow: hidden;          /* ← NO outer scroll, ever */
  background: #000d0d;
  font-family: 'Courier New', monospace;
  font-size: 16px;
  color: #00e5cc;
}

/* HUD: full-screen background layer, pointer-events off so it never blocks */
#hud {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  border: none;
  pointer-events: none;
  z-index: 1;
}

/*
  WRAPPER — ממוקם בדיוק מעל המלבן השחור של ה-HUD (תמונה 2).
  הקואורדינטות מבוססות על מיקום החלון השחור בתוך ה-HUD:
    top  ≈ 18%  (מתחת לסרגל העליון של ה-HUD)
    left ≈ 1%   (שוליים קטנים משמאל)
    width≈ 73%  (עד לפני הפאנלים הימניים)
    height≈ 49% (עד לפני הגרפיקה התחתונה)
  flex-center → המחשבון תמיד מרוכז בתוך המלבן השחור בדיוק.
  pointer-events:none → הגרפיקה מאחור לא נחסמת.
*/
#wrapper {
  position: fixed;
  top:    18%;
  left:   1%;
  width:  73%;
  height: 49%;
  display: flex;
  align-items:     center;   /* מרכז אנכי בתוך החלון השחור  */
  justify-content: center;   /* מרכז אופקי בתוך החלון השחור */
  z-index: 500;
  pointer-events: none;
  /* uncomment for debug: outline: 2px dashed red; */
}

/*
  CALCULATOR PANEL
  מוגבל לגודל ה-wrapper — לא יוצא מהחלון השחור לעולם.
  overflow-y:auto  → גלילה פנימית בלבד.
  overflow-x:hidden → ללא גלילה אופקית.
  pointer-events:all → מחזיר אינטראקציה לפאנל עצמו.
*/
#panel {
  pointer-events: all;
  width:      min(96%, 580px);    /* מקסימום 96% מהעטיפה, לא יוצא מהמלבן */
  max-height: 92%;                /* לא יוצא אנכית מהחלון השחור             */
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

/* Scanline overlay */
#panel::after {
  content: ""; position: absolute; inset: 0;
  pointer-events: none; border-radius: 4px; z-index: 0;
  background: repeating-linear-gradient(
    to bottom, transparent 0, transparent 3px,
    rgba(0,229,204,0.009) 3px, rgba(0,229,204,0.009) 4px);
}

/* ── Panel contents ── */
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

.rbox { padding: 10px 14px; border-radius: 2px; font-size: 16px; line-height: 1.75; word-break: break-word; }
.rbox.ok {
  background: rgba(0,56,28,0.94); border: 1px solid rgba(0,200,100,0.42);
  border-left: 3px solid #00e87a; color: #00ffcc; font-weight: bold;
}
.rbox.ok small { font-weight: normal; font-size: 14px; color: rgba(0,255,200,0.72); }
.rbox.err {
  background: rgba(38,0,0,0.96); border: 1px solid rgba(255,60,60,0.32);
  border-left: 3px solid #ff4444; color: #ff9090;
}

.sp-title { font-size: 16px; letter-spacing: 1px; color: #00e5cc; text-transform: uppercase; margin: 6px 0 4px; font-weight: bold; }
.stbl { width: 100%; border-collapse: collapse; font-size: 15px; }
.stbl th {
  color: #00e5cc; background: rgba(0,229,204,0.07);
  border-bottom: 1px solid rgba(0,229,204,0.28);
  padding: 5px 9px; text-align: left; letter-spacing: 1px; font-size: 13px; text-transform: uppercase;
}
.stbl td { color: rgba(0,229,204,0.84); border-bottom: 1px solid rgba(0,229,204,0.1); padding: 4px 9px; font-size: 15px; }
.stbl tr:last-child td { border-bottom: none; }
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
const GAS_M={N2:.028013,O2:.031999,Ar:.039948,CO2:.04401,He:.0040026,H2:.002016,CH4:.01604,C2H2:.02604,FG1:.03881,FG2:.02671,Air:.02897};
const R=8.314,FR=0.02;
const FIELDS={
  diameter:["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Flow Rate (LPM)"],
  flow:    ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)"],
  length:  ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  inlet:   ["Temperature (\u00b0C)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  outlet:  ["Temperature (\u00b0C)","Inlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"]
};
const DEF={"Temperature (\u00b0C)":25,"Inlet Pressure (bar)":100,"Outlet Pressure (bar)":10,"Pipe Length (m)":10,"Pipe Diameter (mm)":10,"Flow Rate (LPM)":100};

function toKey(f){return f.replace(/ /g,"_").replace(/[()]/g,"").replace(/\//g,"").replace(/\u00b0/g,"deg");}
function fv(label){const el=document.getElementById(toKey(label));return el?(parseFloat(el.value)||0):(DEF[label]||0);}

function rho(Pbar,Tc,gas){return(Pbar*1e5*GAS_M[gas])/(R*(Tc+273.15));}
function rhoAvg(Pi,Po,Tc,gas){return(rho(Pi,Tc,gas)+rho(Po,Tc,gas))/2;}

function calcDiameter(Pi,Po,Tc,L,Q,gas){
  const dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");
  return Math.pow((FR*L*8*rhoAvg(Pi,Po,Tc,gas)*(Q/60000)**2)/(Math.PI**2*dP),0.2)*1000;}
function calcFlow(Pi,Po,Tc,L,D,gas){
  const dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");
  return Math.sqrt(dP*Math.PI**2*(D/1000)**5/(8*FR*L*rhoAvg(Pi,Po,Tc,gas)))*60000;}
function calcLength(Pi,Po,Tc,D,Q,gas){
  const dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");
  return dP*Math.PI**2*(D/1000)**5/(8*FR*rhoAvg(Pi,Po,Tc,gas)*(Q/60000)**2);}
function calcOutlet(Pi,Tc,L,D,Q,gas){
  const Dm=D/1000,Qs=Q/60000;
  function res(Po){return(Pi-Po)*1e5-(8*FR*L*rhoAvg(Pi,Po,Tc,gas)*Qs**2)/(Math.PI**2*Dm**5);}
  let lo=0,hi=Pi;
  for(let i=0;i<60;i++){if(Math.abs(hi-lo)<1e-4)break;const m=(lo+hi)/2;res(m)>0?lo=m:hi=m;}
  return Math.max((lo+hi)/2,0);}
function calcInlet(Po,Tc,L,D,Q,gas){
  let lo=Po,hi=Po+10;
  while(hi<Po+2000){if(calcOutlet(hi,Tc,L,D,Q,gas)>=Po)break;hi+=10;}
  for(let i=0;i<60;i++){const m=(lo+hi)/2,vm=calcOutlet(m,Tc,L,D,Q,gas);
    if(Math.abs(vm-Po)<0.005)return m;vm<Po?lo=m:hi=m;}
  return(lo+hi)/2;}

function pipeSpec(D,P,gas){
  if(gas==="O2")return{rec:'1" (S14)',rows:[['1" (S14)','Required for O2']]};
  let rec="",rows=[];
  if(D<=4){
    if(P<=200){rows=[['1/4" (S6)','&le;200 bar'],['1/4" (S9)','&le;1379 bar'],['1/4" (S12)','>1379 bar']];rec='1/4" (S6)';}
    else if(P<=1379){rows=[['1/4" (S9)','&le;1379 bar'],['1/4" (S12)','>1379 bar']];rec='1/4" (S9)';}
    else{rows=[['1/4" (S12)','>1379 bar']];rec='1/4" (S12)';}
  }else if(D<=7){
    if(P<=140){rows=[['3/8" (S16)','&le;140 bar'],['3/8" (S9)','>140 bar']];rec='3/8" (S16)';}
    else{rows=[['3/8" (S9)','>140 bar']];rec='3/8" (S9)';}
  }else if(D<=21){
    if(P<=20){rows=[['3/4" (S15)','&le;20 bar'],['1" (S14)','>20 bar']];rec='3/4" (S15)';}
    else{rows=[['1" (S14)','>20 bar']];rec='1" (S14)';}
  }else{rows=[['Special piping','Outside standard range']];rec='Special';}
  return{rec,rows};}

function renderResult(mainLine,D,P,gas){
  const{rec,rows}=pipeSpec(D,P,gas);
  const tr=rows.map(r=>"<tr><td>"+r[0]+"</td><td>"+r[1]+"</td></tr>").join("");
  return "<div class='rbox ok'>"+mainLine+"<br><small>Recommended: "+rec+"</small></div>"
        +"<p class='sp-title'>Possible pipe specifications:</p>"
        +"<table class='stbl'><thead><tr><th>Pipe Spec</th><th>Range</th></tr></thead>"
        +"<tbody>"+tr+"</tbody></table>";}

function doCalc(){
  const gas=document.getElementById("gasSelect").value;
  const ct=document.getElementById("calcSelect").value;
  const area=document.getElementById("result-area");
  try{
    const Tc=fv("Temperature (\u00b0C)"),Pi=fv("Inlet Pressure (bar)"),
          Po=fv("Outlet Pressure (bar)"),L=fv("Pipe Length (m)"),
          D=fv("Pipe Diameter (mm)"),Q=fv("Flow Rate (LPM)");
    let html="";
    if(ct==="diameter"){const r=calcDiameter(Pi,Po,Tc,L,Q,gas);html=renderResult("Required Diameter: <strong>"+r.toFixed(2)+" mm</strong>",r,Math.max(Pi,Po),gas);}
    else if(ct==="flow")   {const r=calcFlow(Pi,Po,Tc,L,D,gas);    html=renderResult("Maximum Flow Rate: <strong>"+r.toFixed(1)+" L/min</strong>",D,Math.max(Pi,Po),gas);}
    else if(ct==="length") {const r=calcLength(Pi,Po,Tc,D,Q,gas);  html=renderResult("Maximum Pipe Length: <strong>"+r.toFixed(1)+" m</strong>",D,Math.max(Pi,Po),gas);}
    else if(ct==="inlet")  {const r=calcInlet(Po,Tc,L,D,Q,gas);    html=renderResult("Required Inlet Pressure: <strong>"+r.toFixed(2)+" bar</strong>",D,Math.max(r,Po),gas);}
    else if(ct==="outlet") {const r=calcOutlet(Pi,Tc,L,D,Q,gas);   html=renderResult("Estimated Outlet Pressure: <strong>"+r.toFixed(2)+" bar</strong>",D,Pi,gas);}
    area.innerHTML=html;
    area.scrollIntoView({behavior:"smooth",block:"nearest"});
  }catch(e){area.innerHTML="<div class='rbox err'>&#9888; "+e.message+"</div>";}
}

function rebuildFields(){
  const ct=document.getElementById("calcSelect").value;
  const fl=FIELDS[ct]||[];
  let html="";
  fl.forEach(function(f){
    const k=toKey(f);
    html+="<div class='frow'><label>"+f+"</label><input type='number' id='"+k+"' value='"+(DEF[f]||0)+"' step='any'></div>";
  });
  document.getElementById("input-fields").innerHTML=html;
  document.getElementById("result-area").innerHTML="";
}

rebuildFields();
</script>
</body>
</html>"""

page_html = PAGE.replace("%%HUD%%", hud_tag)

# Render as a full-viewport iframe.
components.html(page_html, height=800, scrolling=False)
