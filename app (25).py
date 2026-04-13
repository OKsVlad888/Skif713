"""
High-Pressure Gas Flow Calculator - HUD Edition
Run:  streamlit run app.py
"""

import json
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Gas Flow Calculator",page_icon="💨",
    layout="wide",initial_sidebar_state="collapsed")

st.markdown("""<style>
  #MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],
  [data-testid="stStatusWidget"],[data-testid="collapsedControl"]{display:none!important}
  .stApp{background:#000d0d!important}
  section.main,.block-container{padding:0!important;margin:0!important;max-width:100vw!important}
  iframe[title="streamlit_components_v1.html_v1"]{
    position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;
    border:none!important;z-index:100!important;display:block!important}
</style>""",unsafe_allow_html=True)

TUBE_TABLE=[
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
TJ = json.dumps(TUBE_TABLE, ensure_ascii=False)

