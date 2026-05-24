"""
High-Pressure Gas Flow Calculator — v5 (FINAL FIX)
====================================================
Critical fixes vs previous broken version:
  • height=800 restored (was height=2 → iframe 2px tall → nothing visible)
  • iframe forced position:fixed via st.markdown CSS → covers full browser window
  • html,body overflow:hidden in BOTH Streamlit DOM and inside iframe
  • Panel wrapper: fixed to black zone (left:22%, right:39.7%, top:5.6%)
  • Panel: height:auto + max-height:100% → auto-sizes, never overflows zone
  • justify-content:center → panel vertically centered before result
  • toKey() correct: parens REMOVED (not replaced with _)
  • Math.pow() throughout — no ** operator (cross-browser safe)
  • Full CSS-var theming: ALL elements change color in warn/danger
  • Safety block: CO2>70, CH4>250, C2H2>17, H2S>20, any>2001 bar
  • Orange warning for dangerous gases O2,H2,CH4,C2H2,H2S
  • Live theme update on inlet pressure input
  • Recommendation Confidence bar in all modes

Files needed: app.py + hud_background.html in same folder
Run: streamlit run app.py
"""

import base64, json
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="High-Pressure Gas Flow Calculator",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Kill ALL Streamlit scroll + make iframe cover full browser viewport
st.markdown("""
<style>
  #MainMenu,footer,header,
  [data-testid="stToolbar"],[data-testid="stDecoration"],
  [data-testid="stStatusWidget"],[data-testid="collapsedControl"]
  {display:none!important}

  html,body{overflow:hidden!important;height:100vh!important;
    width:100vw!important;background:#010a08!important}

  .stApp,[data-testid="stAppViewContainer"],
  [data-testid="stMain"],[data-testid="stVerticalBlock"],
  [data-testid="element-container"],
  section.main,.block-container
  {overflow:hidden!important;padding:0!important;margin:0!important;
   max-width:100vw!important;height:100vh!important}

  iframe[title="streamlit_components_v1.html_v1"]{
    position:fixed!important;inset:0!important;
    width:100vw!important;height:100vh!important;
    border:none!important;z-index:9999!important}
</style>
""", unsafe_allow_html=True)

# TUBE TABLE
TUBE_TABLE = [
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":4.9,"tube_od_w":'1/4"X0.028"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":7.036,"tube_od_w":'3/8"X0.049"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":9.398,"tube_od_w":'1/2"X0.065"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":12.573,"tube_od_w":'5/8"X0.065"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":14.834,"tube_od_w":'3/4"X0.083"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":17.399,"tube_od_w":'7/8"X0.095"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S6","id_mm":19.863,"tube_od_w":'1"X0.109"',"max_pressure":200.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":3.86,"tube_od_w":'1/4"X0.049"',"max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":6.223,"tube_od_w":'3/8"X0.065"',"max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":8.468,"tube_od_w":'1/2"X0.083"',"max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":9.119,"tube_od_w":'9/16"X0.10175"',"max_pressure":400.0},
    {"gas_codes":["N2","Ar","CO2","He","CH4","C2H2","H2","FG1","FG2","Air"],"spec":"S9","id_mm":13.106,"tube_od_w":'3/4"X0.117"',"max_pressure":400.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S11","id_mm":2.108,"tube_od_w":'1/4"X0.083"',"max_pressure":2000.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S11","id_mm":3.1753,"tube_od_w":'3/8"X0.125"',"max_pressure":2000.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S12","id_mm":2.6786,"tube_od_w":'1/4"X0.705"',"max_pressure":1380.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S12","id_mm":5.516,"tube_od_w":'3/8"X0.0860"',"max_pressure":1380.0},
    {"gas_codes":["N2","Ar","He","FG1","FG2","Air"],"spec":"S12","id_mm":7.925,"tube_od_w":'9/16"X0.12525"',"max_pressure":1380.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":4.572,"tube_od_w":'1/4"X0.035"',"max_pressure":238.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":7.747,"tube_od_w":'3/8"X0.035"',"max_pressure":170.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":10.21,"tube_od_w":'1/2"X0.049"',"max_pressure":170.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":15.748,"tube_od_w":'3/4"X0.065"',"max_pressure":170.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":22.1,"tube_od_w":'1"X0.065"',"max_pressure":102.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":34.8,"tube_od_w":'1.5"X0.065"',"max_pressure":68.0},
    {"gas_codes":["N2","O2","Ar","He","Air"],"spec":"S14","id_mm":47.5,"tube_od_w":'2"X0.065"',"max_pressure":61.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":4.572,"tube_od_w":'1/4"X0.035"',"max_pressure":204.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":7.747,"tube_od_w":'3/8"X0.035"',"max_pressure":170.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":10.21,"tube_od_w":'1/2"X0.049"',"max_pressure":170.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":13.38585,"tube_od_w":'5/8"X0.049"',"max_pressure":170.0},
    {"gas_codes":["CO2","CH4","C2H2","H2S"],"spec":"S16","id_mm":15.748,"tube_od_w":'3/4"X0.065"',"max_pressure":170.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":4.572,"tube_od_w":'1/4"X0.035"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":7.0358,"tube_od_w":'3/8"X0.049"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":10.2108,"tube_od_w":'1/2"X0.049"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":13.3858,"tube_od_w":'5/8"X0.049"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":15.748,"tube_od_w":'3/4"X0.065"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":18.923,"tube_od_w":'7/8"X0.065"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":22.098,"tube_od_w":'1"X0.065"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":28.448,"tube_od_w":'1.25"X0.065"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":34.4424,"tube_od_w":'1.5"X0.072"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":46.5836,"tube_od_w":'2"X0.083"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":58.674,"tube_od_w":'2.5"X0.095"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":70.6628,"tube_od_w":'3"X0.109"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"B1","id_mm":94.7928,"tube_od_w":'4"X0.134"',"max_pressure":40.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":11.6,"tube_od_w":"16mmX2.2mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":14.4,"tube_od_w":"20mmX2.8mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":18.0,"tube_od_w":"25mmX3.5mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":23.2,"tube_od_w":"32mmX4.4mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":29.0,"tube_od_w":"40mmX5.5mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":36.2,"tube_od_w":"50mmX6.9mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":45.8,"tube_od_w":"63mmX8.6mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":54.4,"tube_od_w":"75mmX10.3mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":65.4,"tube_od_w":"90mmX12.3mm","max_pressure":10.0},
    {"gas_codes":["N2","Ar","Air"],"spec":"P6","id_mm":79.8,"tube_od_w":"110mmX15.1mm","max_pressure":10.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":15.8,"tube_od_w":'1/2" SCH40',"max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":15.59,"tube_od_w":'3/4" SCH40',"max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":26.24,"tube_od_w":'1" SCH40',"max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":35.04,"tube_od_w":'1.25" SCH40',"max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":40.9,"tube_od_w":'1.5" SCH40',"max_pressure":15.0},
    {"gas_codes":["Air"],"spec":"C3","id_mm":52.51,"tube_od_w":'2" SCH40',"max_pressure":15.0},
]
TT_JSON = json.dumps(TUBE_TABLE, ensure_ascii=False)

def hud_iframe() -> str:
    p = Path(__file__).resolve().parent / "hud_background.html"
    if not p.exists():
        return "<div style='position:fixed;inset:0;background:#010a08;z-index:1'></div>"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return (
        "<iframe id='hud-bg' src='data:text/html;base64," + b64 + "'"
        " sandbox='allow-scripts'"
        " style='position:fixed;inset:0;width:100%;height:100%;"
        "border:none;z-index:1;pointer-events:none'></iframe>"
    )

HUD = hud_iframe()

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;overflow:hidden;background:#010a08;font-family:'Courier New',monospace}
:root{
  --tc:#00e5cc;--tc2:#00ffee;--tc3:rgba(0,229,204,.38);--tc4:rgba(0,229,204,.20);
  --lc:rgba(0,229,204,.80);--pbg:rgba(0,6,6,.97);--ibg:rgba(0,12,10,.99);
  --bbg:rgba(0,229,204,.08);--bh:rgba(0,229,204,.22);
  --gs:rgba(0,229,204,.32);--ge:rgba(0,229,204,.78);--rbg:rgba(0,229,204,.04);}
.W{--tc:#ff8c00;--tc2:#ffcc66;--tc3:rgba(255,140,0,.48);--tc4:rgba(255,140,0,.24);
   --lc:rgba(255,195,65,.88);--pbg:rgba(18,7,0,.98);--ibg:rgba(26,10,0,.99);
   --bbg:rgba(255,140,0,.07);--bh:rgba(255,140,0,.24);
   --gs:rgba(255,140,0,.32);--ge:rgba(255,140,0,.85);--rbg:rgba(255,140,0,.04);}
.D{--tc:#ff2222;--tc2:#ff7777;--tc3:rgba(255,40,40,.48);--tc4:rgba(255,40,40,.24);
   --lc:rgba(255,120,120,.88);--pbg:rgba(18,0,0,.99);--ibg:rgba(24,2,2,.99);
   --bbg:rgba(255,40,40,.07);--bh:rgba(255,40,40,.24);
   --gs:rgba(255,40,40,.32);--ge:rgba(255,40,40,.90);--rbg:rgba(255,40,40,.04);}
#wrapper{
  position:fixed;left:22%;right:39.7%;top:5.6%;bottom:2%;
  z-index:500;display:flex;flex-direction:column;
  align-items:stretch;justify-content:center;
  padding:8px 10px;pointer-events:none;
  overflow:visible;}
#panel{
  pointer-events:all;width:100%;height:auto;
  overflow:visible;
  background:var(--pbg);border:1.5px solid var(--tc);border-radius:4px;
  padding:12px 20px 14px;position:relative;
  transition:background .35s,border-color .35s;
  animation:pglow 2.5s ease-in-out infinite alternate;}
@keyframes pglow{
  from{box-shadow:0 0 10px var(--gs),inset 0 0 30px rgba(0,0,0,.5)}
  to  {box-shadow:0 0 40px var(--ge),inset 0 0 55px rgba(0,0,0,.25)}}
#panel::after{content:"";position:absolute;inset:0;pointer-events:none;border-radius:4px;
  background:repeating-linear-gradient(to bottom,transparent 0,transparent 3px,
    rgba(0,229,204,.006) 3px,rgba(0,229,204,.006) 4px)}
#alhdr{display:none;align-items:center;justify-content:center;gap:9px;
  padding:6px 12px;margin-bottom:9px;background:var(--rbg);
  border:1px solid var(--tc3);border-radius:3px;position:relative;z-index:1;
  animation:ahp 1.2s ease-in-out infinite alternate;transition:border-color .35s}
.W #alhdr,.D #alhdr{display:flex}
@keyframes ahp{from{box-shadow:0 0 4px var(--gs)}to{box-shadow:0 0 22px var(--ge)}}
.ai{font-size:16px;color:var(--tc);transition:color .35s}
.at{font-size:12px;font-weight:bold;letter-spacing:2.5px;text-transform:uppercase;
  color:var(--tc);text-shadow:0 0 10px var(--gs);transition:color .35s,text-shadow .35s}
#panel h1{position:relative;z-index:1;color:var(--tc2);text-shadow:0 0 14px var(--gs);
  font-size:13px;letter-spacing:4px;text-transform:uppercase;text-align:center;
  margin-bottom:10px;line-height:1.4;transition:color .35s,text-shadow .35s}
.tri{color:var(--tc);margin-right:7px;transition:color .35s}
#body{position:relative;z-index:1;display:flex;flex-direction:column;gap:7px}
.sr{display:flex;flex-direction:column;gap:3px}
.sr label{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--lc);transition:color .35s}
.sr select{background:var(--ibg);color:var(--tc2);border:1px solid var(--tc3);border-radius:2px;
  padding:5px 28px 5px 9px;font-family:'Courier New',monospace;font-size:14px;
  width:100%;cursor:pointer;outline:none;-webkit-appearance:none;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2300e5cc'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
  transition:background-color .35s,border-color .35s,color .35s}
.sr select:focus{border-color:var(--tc);box-shadow:0 0 7px var(--gs)}
.sr select option{background:#000d0d;color:#00e5cc}
/* Options list colors per theme */
.W .sr select option{background:#1a0700;color:#ff8c00}
.D .sr select option{background:#160000;color:#ff4444}
/* Dropdown arrow: orange in warn, red in danger */
.W .sr select{
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23ff8c00'/%3E%3C/svg%3E");}
.D .sr select{
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23ff2222'/%3E%3C/svg%3E");}
/* Layout stays SINGLE-COLUMN in all modes — only color changes */
.hdiv{border:none;border-top:1px solid var(--tc4);margin:2px 0;transition:border-color .35s}
#ifields{display:flex;flex-direction:column;gap:5px}
.frow{display:flex;flex-direction:column;gap:2px}
.frow label{font-size:13px;color:var(--lc);transition:color .35s}
.frow input{width:100%;background:var(--ibg);color:var(--tc2);
  border:1px solid var(--tc3);border-radius:2px;
  padding:5px 9px;font-family:'Courier New',monospace;font-size:14px;
  outline:none;transition:background-color .35s,border-color .35s,color .35s}
.frow input:focus{border-color:var(--tc);box-shadow:0 0 6px var(--gs)}
.frow input::-webkit-inner-spin-button,.frow input::-webkit-outer-spin-button{-webkit-appearance:none}
.frow input[type=number]{-moz-appearance:textfield}
/* Input fields: single-column in all modes — only color changes */
.cap{font-size:11px;color:var(--lc);opacity:.42;letter-spacing:.8px}
#cbtn{width:100%;background:var(--bbg);color:var(--tc2);border:1.5px solid var(--tc);
  border-radius:2px;padding:8px 0;font-family:'Courier New',monospace;font-size:14px;
  letter-spacing:4px;cursor:pointer;text-transform:uppercase;
  transition:background .2s,box-shadow .2s,border-color .35s,color .35s}
#cbtn:hover{background:var(--bh);box-shadow:0 0 18px var(--ge)}
#cbtn:active{filter:brightness(1.3)}
.D #cbtn{opacity:.38;cursor:not-allowed;pointer-events:none}
.rbox{padding:8px 12px;border-radius:2px;font-size:13px;line-height:1.7;
  word-break:break-word;animation:fi .28s ease both}
@keyframes fi{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.ok{background:rgba(0,50,26,.96);border:1px solid rgba(0,200,100,.40);
  border-left:3px solid #00e87a;color:#00ffcc}
.ok .rt{font-size:15px;font-weight:bold}
.blk{background:rgba(46,0,0,.98);border:1px solid rgba(255,40,40,.42);
  border-left:3px solid #ff2222;color:#ff7777;font-weight:bold;
  animation:bp 1.4s ease-in-out infinite alternate}
@keyframes bp{from{box-shadow:0 0 4px rgba(255,40,40,.2)}to{box-shadow:0 0 16px rgba(255,40,40,.6)}}
.er{background:rgba(34,0,0,.96);border:1px solid rgba(255,50,50,.30);
  border-left:3px solid #ff4444;color:#ff9090}
.spc{margin-top:6px;padding:8px 12px;border-radius:2px;background:rgba(0,24,20,.98);
  border:1px solid var(--tc4);border-left:3px solid var(--tc);
  transition:border-color .35s;animation:fi .3s ease both}
.sh{color:var(--lc);opacity:.55;font-size:10px;letter-spacing:2px;
  text-transform:uppercase;margin-bottom:5px}
.sr2{color:var(--tc2);font-size:13px;line-height:1.9;transition:color .35s}
.sn{color:var(--lc);opacity:.45;font-size:11px;margin-top:2px}
.badge{display:inline-block;border-radius:2px;font-size:9px;letter-spacing:1.5px;
  padding:1px 6px;margin-left:6px;vertical-align:middle;text-transform:uppercase}
.bo2{background:rgba(255,100,0,.14);border:1px solid rgba(255,120,0,.4);color:#ffaa44}
.bh2{background:rgba(0,180,255,.11);border:1px solid rgba(0,200,255,.35);color:#66ddff}
#res-sec{display:none;padding:8px 12px;border-radius:2px;
  background:var(--ibg);border:1px solid var(--tc4);
  transition:background .35s,border-color .35s;animation:fi .28s ease both}
.W #res-sec,.D #res-sec{display:block}
.rl{font-size:9px;letter-spacing:2.5px;text-transform:uppercase;
  color:var(--lc);opacity:.75;margin-bottom:5px}
#rc{font-size:13px;color:var(--tc2);line-height:1.85;transition:color .35s}
#cw{display:none;margin-top:5px;animation:fi .35s ease both}
#cw.show{display:block}
.crow{display:flex;align-items:center;gap:10px}
.cl{font-size:9px;letter-spacing:2px;text-transform:uppercase;
  color:var(--lc);white-space:nowrap;opacity:.8;transition:color .35s}
.ct{flex:1;height:12px;background:rgba(0,0,0,.35);border:1px solid var(--tc4);
  border-radius:1px;overflow:hidden;position:relative;transition:border-color .35s}
.cf{height:100%;background:var(--tc);position:absolute;left:0;top:0;
  transition:width .75s ease,background .35s}
.cf::before{content:'';position:absolute;inset:0;
  background:repeating-linear-gradient(90deg,transparent 0,transparent calc(10% - 1px),
    rgba(0,0,0,.40) calc(10% - 1px),rgba(0,0,0,.40) 10%)}
.cp{font-size:13px;font-weight:bold;color:var(--tc);
  min-width:42px;text-align:right;transition:color .35s}
</style>
</head>
<body>
%%HUD%%
<div id="wrapper">
<div id="panel">
<div id="alhdr"><span class="ai">&#9888;</span><span class="at" id="at">WARNING</span></div>
<h1><span class="tri">&#9651;</span>HIGH-PRESSURE GAS FLOW CALCULATOR</h1>
<div id="body">
<div class="sr"><label>Gas Type</label>
<select id="gs2" onchange="rebuild()">
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
</select></div>
<div class="sr"><label>Calculation Type</label>
<select id="cs2" onchange="rebuild()">
<option value="diameter">Pipe Diameter (mm)</option>
<option value="flow">Flow Rate (LPM)</option>
<option value="length">Pipe Length (m)</option>
<option value="inlet">Inlet Pressure (bar)</option>
<option value="outlet">Outlet Pressure (bar)</option>
</select></div>
<hr class="hdiv">
<div id="ifields"></div>
<p class="cap">Friction factor (f) = 0.02 &nbsp;&middot;&nbsp; fixed constant</p>
<button id="cbtn" onclick="calc()">&#9658;&nbsp;&nbsp;Calculate</button>
<div id="rn"></div>
<div id="res-sec"><div class="rl">Results</div><div id="rc"></div></div>
<div id="cw"><div class="crow">
  <span class="cl">Recommendation Confidence</span>
  <div class="ct"><div class="cf" id="cf" style="width:0%"></div></div>
  <span class="cp" id="cp">0%</span>
</div></div>
</div></div></div>
<script>
var TT=%%TT%%;
var BLK={
  "CO2":{max:69.9,hdr:"ALERT: SAFETY / LIMIT CONDITION",msg:"Risk: Liquid Phase CO\u2082\nPressure Exceeds Limit!"},
  "CH4":{max:250,hdr:"ALERT: SAFETY / LIMIT CONDITION",msg:"Risk: Flammable Gas\nPressure Exceeds Safe Limit!"},
  "C2H2":{max:17,hdr:"ALERT: SAFETY / LIMIT CONDITION",msg:"Risk: Decomposition Hazard\nMax 17 bar for Acetylene!"},
  "H2S":{max:20,hdr:"ALERT: SAFETY / LIMIT CONDITION",msg:"Risk: Toxic Gas\nPressure Exceeds Safe Limit!"}
};
var GMAX=2001;
var WG=["O2","H2","CH4","C2H2","H2S"];
var WM={
  "O2":"O\u2082 \u2014 Oxidizing gas. S14 (O\u2082-cleaned) equipment only.",
  "H2":"H\u2082 \u2014 Highly flammable. S6 (\u2264200 bar) or S9 (\u2264400 bar) only.",
  "CH4":"CH\u2084 \u2014 Flammable. Max 250 bar. S16 double-contained required.",
  "C2H2":"C\u2082H\u2082 \u2014 Unstable above 17 bar. Decomposition risk!",
  "H2S":"H\u2082S \u2014 Highly toxic. Max 20 bar. PPE and gas detection mandatory."
};
function evalM(gas,Pi){
  if(Pi>GMAX)return{m:"D",hdr:"ALERT: SAFETY / LIMIT CONDITION",blocked:true,msg:"Risk: Pressure >2001 bar\nExceeds Maximum Limit!"};
  var l=BLK[gas];if(l&&Pi>l.max)return{m:"D",hdr:l.hdr,blocked:true,msg:l.msg};
  if(WG.indexOf(gas)!==-1)return{m:"W",hdr:"WARNING: PRESSURE LIMIT REACHED",blocked:false};
  return{m:"N",blocked:false};
}
function setM(m,hdr){
  document.getElementById("panel").className=m==="W"?"W":m==="D"?"D":"";
  var ah=document.getElementById("alhdr"),at=document.getElementById("at");
  ah.style.display=m==="N"?"none":"flex";if(at&&hdr)at.textContent=hdr;
}
function toKey(f){return f.replace(/ /g,"_").replace(/[()]/g,"").replace(/\//g,"").replace(/\u00b0/g,"deg");}
function fv(l){var e=document.getElementById(toKey(l));return e?(parseFloat(e.value)||0):(DEF[l]||0);}
function getPI(){var e=document.getElementById(toKey("Inlet Pressure (bar)"));return e?(parseFloat(e.value)||0):0;}
function getAllMatches(gas,inP,diam){
  /* Material tier: SS316 (S-spec) and Copper (B-spec) = tier 0 (preferred engineering choice).
     PPR plastic (P-spec) and Galvanized (C-spec) = tier 1 (low-cost alternative, listed last). */
  function tier(spec){return(spec[0]==='S'||spec[0]==='B')?0:1;}
  /* Step 1: basic filter — gas + pressure rating covers inlet + diameter fits */
  var raw=TT.filter(function(r){
    return r.gas_codes.indexOf(gas)!==-1&&r.max_pressure>=inP&&r.id_mm>=diam;
  });
  if(!raw.length)return[];
  /* Step 2: sort TIER first (SS/Copper before plastic/galvanized),
             then PRESSURE ASC (closest to inlet = best match),
             then DIAMETER ASC (smallest tube within same pressure tier).
     Pressure is the primary engineering criterion WITHIN each material tier. */
  raw.sort(function(a,b){
    var td=tier(a.spec)-tier(b.spec);
    if(td!==0)return td;
    return(a.max_pressure-b.max_pressure)||(a.id_mm-b.id_mm);
  });
  /* Step 3: find minimum covering pressure from preferred (tier-0) specs only.
     If no tier-0 spec exists, fall back to tier-1. */
  var t0=raw.filter(function(r){return tier(r.spec)===0;});
  var minP=(t0.length?t0:raw)[0].max_pressure;
  /* Step 4: exclude specs that are excessively over-rated (> 5x the minimum covering pressure).
     Example: inlet=200 bar, minP=200 (S6), cutoff=1000.
     S9(400)✓ S12(1380)✗  |  inlet=10 bar, minP=40(B1), cutoff=200: S6(200)✓ S11(2000)✗ */
  var cutoff=Math.max(minP*5,minP+200);
  return raw.filter(function(r){return r.max_pressure<=cutoff;});
}
function lk(gas,inP,diam){
  var all=getAllMatches(gas,inP,diam);
  return all.length?all[0]:null;
}
function ft(s){return s.replace(/X/g," \u00d7 ").replace(/\s{2,}/g," ").trim();}
function sc(gas,inP,diam){
  var matches=getAllMatches(gas,inP,diam);
  if(!matches.length)return"<div class='rbox er'>\u26a0 No approved tube specification found</div>";
  /* Build unique spec list — already sorted by pressure match (best first) */
  var seen={},specs=[],perSpec={};
  matches.forEach(function(r){
    if(!seen[r.spec]){seen[r.spec]=true;specs.push(r.spec);}
    if(!perSpec[r.spec])perSpec[r.spec]=r; /* first entry = smallest tube for that spec */
  });
  /* Optimal = first match in pressure-sorted list = best pressure match + smallest diam for that pressure */
  var opt=matches[0];
  var badge="";
  if(gas==="O2")badge="<span class='badge bo2'>O\u2082 \u2192 S14 only</span>";
  if(gas==="H2")badge="<span class='badge bh2'>H\u2082 \u2192 S6/S9</span>";
  /* Build per-spec rows — ordered best pressure match first */
  var specRows="";
  specs.forEach(function(s,i){
    var t=perSpec[s];
    var isOpt=(s===opt.spec);
    var star=isOpt?"<span style='color:var(--tc);margin-right:4px'>\u2605</span>":"<span style='margin-right:4px;opacity:.4'>\u25cb</span>";
    var pDiff=t.max_pressure-inP;
    var pLabel=pDiff===0?"(exact match)":pDiff<inP?"(+"+pDiff+" bar margin)":"";
    specRows+=star+"<strong>"+s+"</strong>&nbsp;\u2014&nbsp;"+ft(t.tube_od_w)
      +"<span style='opacity:.52;font-size:11px'> &nbsp;ID "+t.id_mm.toFixed(2)+" mm &nbsp;\u2502&nbsp; \u2264"+t.max_pressure+" bar"
      +(pLabel?" &nbsp;<em>"+pLabel+"</em>":"")+"</span><br>";
  });
  return"<div class='spc'><div class='sh'>\u25ba Tube Spec Recommendations&nbsp;<span style='font-size:9px;opacity:.55;font-weight:normal;letter-spacing:1px'>sorted: pressure match first</span>"+badge+"</div>"
    +"<div class='sr2' style='line-height:2.1'>"+specRows+"</div>"
    +"<div style='margin-top:8px;padding:7px 12px;background:rgba(0,229,204,.07);border-left:3px solid var(--tc);border-radius:2px;animation:fi .3s ease both'>"
    +"<span style='font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--lc);opacity:.75'>\u2605 Optimal Tube Size &mdash; best pressure match</span><br>"
    +"<span style='color:var(--tc2);font-size:15px;font-weight:bold'>"+ft(opt.tube_od_w)+"</span>"
    +"<span style='color:var(--lc);font-size:11px;opacity:.62'> &nbsp; "+opt.spec+" &nbsp;\u2502&nbsp; ID "+opt.id_mm.toFixed(3)+" mm &nbsp;\u2502&nbsp; \u2264"+opt.max_pressure+" bar</span>"
    +"</div></div>";
}
function cf2(gas,inP,diam,spec){
  if(!spec)return 5;
  var dr=Math.min((spec.id_mm-diam)/spec.id_mm,1);
  var pr=Math.max((spec.max_pressure-inP)/spec.max_pressure,0);
  var sf=WG.indexOf(gas)!==-1?0.72:1.0;
  return Math.max(5,Math.min(100,Math.round((dr*.35+pr*.65)*sf*100)));
}
function showC(pct){var w=document.getElementById("cw");w.className="show";
  setTimeout(function(){document.getElementById("cf").style.width=pct+"%";document.getElementById("cp").textContent=pct+"%";},80);}
function hideC(){var w=document.getElementById("cw");if(w)w.className="";}
var GM={N2:.028013,O2:.031999,Ar:.039948,CO2:.04401,He:.0040026,H2:.002016,CH4:.01604,C2H2:.02604,FG1:.03881,FG2:.02671,Air:.02897};
var R=8.314,FR=0.02;
function rho(P,T,g){return(P*1e5*GM[g])/(R*(T+273.15));}
function rhoA(Pi,Po,T,g){return(rho(Pi,T,g)+rho(Po,T,g))/2;}
function calcD(Pi,Po,T,L,Q,g){var dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");var Qs=Q/60000;return Math.pow((FR*L*8*rhoA(Pi,Po,T,g)*Qs*Qs)/(Math.pow(Math.PI,2)*dP),0.2)*1000;}
function calcF(Pi,Po,T,L,D,g){var dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");var Dm=D/1000;return Math.sqrt(dP*Math.pow(Math.PI,2)*Math.pow(Dm,5)/(8*FR*L*rhoA(Pi,Po,T,g)))*60000;}
function calcL(Pi,Po,T,D,Q,g){var dP=(Pi-Po)*1e5;if(dP<=0)throw new Error("Inlet pressure must exceed outlet pressure.");var Dm=D/1000,Qs=Q/60000;return dP*Math.pow(Math.PI,2)*Math.pow(Dm,5)/(8*FR*rhoA(Pi,Po,T,g)*Qs*Qs);}
function calcO(Pi,T,L,D,Q,g){var Dm=D/1000,Qs=Q/60000;function res(Po){return(Pi-Po)*1e5-(8*FR*L*rhoA(Pi,Po,T,g)*Qs*Qs)/(Math.pow(Math.PI,2)*Math.pow(Dm,5));}var lo=0,hi=Pi;for(var i=0;i<60;i++){if(Math.abs(hi-lo)<1e-4)break;var m=(lo+hi)/2;res(m)>0?lo=m:hi=m;}return Math.max((lo+hi)/2,0);}
function calcI(Po,T,L,D,Q,g){var lo=Po,hi=Po+10;while(hi<Po+2000){if(calcO(hi,T,L,D,Q,g)>=Po)break;hi+=10;}for(var i=0;i<60;i++){var m=(lo+hi)/2,vm=calcO(m,T,L,D,Q,g);if(Math.abs(vm-Po)<0.005)return m;vm<Po?lo=m:hi=m;}return(lo+hi)/2;}
var FIELDS={
  diameter:["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Flow Rate (LPM)"],
  flow:    ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)"],
  length:  ["Temperature (\u00b0C)","Inlet Pressure (bar)","Outlet Pressure (bar)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  inlet:   ["Temperature (\u00b0C)","Outlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"],
  outlet:  ["Temperature (\u00b0C)","Inlet Pressure (bar)","Pipe Length (m)","Pipe Diameter (mm)","Flow Rate (LPM)"]
};
var DEF={"Temperature (\u00b0C)":25,"Inlet Pressure (bar)":200,"Outlet Pressure (bar)":10,"Pipe Length (m)":100,"Pipe Diameter (mm)":10,"Flow Rate (LPM)":16};
function calc(){
  var gas=document.getElementById("gs2").value;
  var ct=document.getElementById("cs2").value;
  var rn=document.getElementById("rn"),rc=document.getElementById("rc");
  var Pi=ct==="inlet"?0:getPI();
  var th=evalM(gas,Pi);setM(th.m,th.hdr);
  if(th.blocked&&ct!=="inlet"){rn.innerHTML="";rc.innerHTML="<div class='rbox blk'>\u26a0\ufe0f SAFETY BLOCKED<br><span style='font-weight:normal;font-size:12px'>"+th.msg.replace(/\n/g,"<br>")+"</span></div>";showC(5);return;}
  try{
    var Tc=fv("Temperature (\u00b0C)"),Pi2=fv("Inlet Pressure (bar)"),Po=fv("Outlet Pressure (bar)"),L=fv("Pipe Length (m)"),D=fv("Pipe Diameter (mm)"),Q=fv("Flow Rate (LPM)");
    var diam,inP,line;
    if(ct==="diameter"){var r=calcD(Pi2,Po,Tc,L,Q,gas);diam=r;inP=Pi2;line="Required Diameter: <strong>"+r.toFixed(2)+" mm</strong>";}
    else if(ct==="flow"){var r=calcF(Pi2,Po,Tc,L,D,gas);diam=D;inP=Pi2;line="Maximum Flow Rate: <strong>"+r.toFixed(1)+" L/min</strong>";}
    else if(ct==="length"){var r=calcL(Pi2,Po,Tc,D,Q,gas);diam=D;inP=Pi2;line="Maximum Pipe Length: <strong>"+r.toFixed(1)+" m</strong>";}
    else if(ct==="inlet"){
      var r=calcI(Po,Tc,L,D,Q,gas);diam=D;inP=r;
      var th2=evalM(gas,r);setM(th2.m,th2.hdr);
      if(th2.blocked){rn.innerHTML="";rc.innerHTML="<div style='font-size:13px;color:var(--tc2)'>Required Inlet: <strong>"+r.toFixed(2)+" bar</strong></div><div class='rbox blk' style='margin-top:5px'>\u26a0\ufe0f SAFETY BLOCKED<br><span style='font-weight:normal;font-size:12px'>"+th2.msg.replace(/\n/g,"<br>")+"</span></div>";showC(10);return;}
      line="Required Inlet Pressure: <strong>"+r.toFixed(2)+" bar</strong>";
    }else{var r=calcO(Pi2,Tc,L,D,Q,gas);diam=D;inP=Pi2;line="Estimated Outlet Pressure: <strong>"+r.toFixed(2)+" bar</strong>";}
    var spec=lk(gas,inP,diam);var pct=cf2(gas,inP,diam,spec);
    if(th.m==="N"){rn.innerHTML="<div class='rbox ok'><div class='rt'>"+line+"</div></div>"+sc(gas,inP,diam);rc.innerHTML="";}
    else{var allM=getAllMatches(gas,inP,diam);var seen3={},specs3=[];allM.forEach(function(r){if(!seen3[r.spec]){seen3[r.spec]=true;specs3.push(r.spec);}});var specStr3=specs3.length?specs3.join(', '):'N/A';rn.innerHTML="";rc.innerHTML="<div style='font-size:13px;color:var(--tc2);line-height:1.85'>"+line+"<br>Tube Spec: <strong>"+specStr3+"</strong><br>"+(spec?"Optimal: <strong>"+ft(spec.tube_od_w)+"<\/strong> <span style='font-size:11px;opacity:.7'>(ID "+spec.id_mm.toFixed(2)+" mm)<\/span>":"")+"<\/div>";}
    showC(pct);
  }catch(e){document.getElementById("rn").innerHTML="<div class='rbox er'>\u26a0 "+e.message+"</div>";document.getElementById("rc").innerHTML="";}
}
function rebuild(){
  var gas=document.getElementById("gs2").value;
  var ct=document.getElementById("cs2").value;
  var fl=FIELDS[ct]||[];var html="";
  fl.forEach(function(f){var k=toKey(f);var ex=(f==="Inlet Pressure (bar)")?" oninput='onpi()'":"";html+="<div class='frow'><label>"+f+"</label><input type='number' id='"+k+"' value='"+(DEF[f]||0)+"' step='any'"+ex+"></div>";});
  document.getElementById("ifields").innerHTML=html;
  document.getElementById("rn").innerHTML="";document.getElementById("rc").innerHTML="";hideC();
  var Pi=ct==="inlet"?0:(DEF["Inlet Pressure (bar)"]||0);
  var th=evalM(gas,Pi);setM(th.m,th.hdr);
  if(th.m==="W"&&!th.blocked&&WM[gas])document.getElementById("rc").innerHTML="<div style='font-size:12px;color:var(--tc2);opacity:.88'>"+WM[gas]+"</div>";
}
function onpi(){var gas=document.getElementById("gs2").value;var ct=document.getElementById("cs2").value;if(ct==="inlet")return;var th=evalM(gas,getPI());setM(th.m,th.hdr);}
/* ── Auto-fit: keep panel vertically centered; push top up if it overflows ── */
(function(){
  var W=document.getElementById("wrapper");
  var P=document.getElementById("panel");
  function fit(){
    var vp=window.innerHeight;
    var ph=P.offsetHeight;
    var zoneTop=vp*0.056;   /* matches CSS top:5.6% */
    var zoneBot=vp*0.02;    /* matches CSS bottom:2% */
    var zone=vp-zoneTop-zoneBot;
    if(ph<=zone){
      /* panel fits — center it in zone (original behaviour) */
      W.style.justifyContent="center";
      W.style.top="5.6%";
    }else{
      /* panel taller than zone — align to top, shrink top margin so it starts higher */
      var topPx=Math.max(4, (vp-ph)/2);
      W.style.justifyContent="flex-start";
      W.style.top=topPx+"px";
    }
  }
  var ro=new ResizeObserver(fit);
  ro.observe(P);
  window.addEventListener("resize",fit);
  fit();
})();
rebuild();
</script>
</body></html>"""

page_html = PAGE.replace("%%HUD%%", HUD).replace("%%TT%%", TT_JSON)
# height=900 — iframe covers full viewport via position:fixed CSS.
# Panel has no internal scroll; it auto-sizes to content via ResizeObserver.
components.html(page_html, height=900, scrolling=False)
