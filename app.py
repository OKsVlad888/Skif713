import math
import base64
import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(page_title="High-Pressure Gas Flow Calculator", page_icon="💨", layout="centered")

# Load background image and encode
@st.cache_data
def load_bg_image(image_name: str) -> str | None:
    path = Path(__file__).resolve().parent / image_name
    if not path.exists():
        return None
    with open(path, "rb") as img:
        return base64.b64encode(img.read()).decode("utf-8")

bg_base64 = load_bg_image("app_background.png")

# Define custom CSS with dynamic background and animations
css_style = (
    "<style>\n"
    "/* Full-page background with cover */\n"
    ".stApp {\n"
    f"   background: url('data:image/png;base64,{bg_base64 or ''}') no-repeat center center fixed;\n"
    "   background-size: cover;\n"
    "   position: relative;\n"
    "   overflow: hidden;\n"
    "   animation: flicker 1.5s infinite;\n"
    "}\n"
    "/* Moving scanline overlay for active effect */\n"
    ".stApp::after {\n"
    "   content: '';\n"
    "   position: absolute; top: 0; left: 0;\n"
    "   width: 100%; height: 100%;\n"
    "   background: linear-gradient(to bottom, transparent 90%, rgba(255,255,255,0.1) 95%, transparent 100%);\n"
    "   background-size: 100% 200%;\n"
    "   pointer-events: none;\n"
    "   animation: scan 5s linear infinite;\n"
    "}\n"
    "@keyframes scan {\n"
    "   0% { background-position: 0 -100%; }\n"
    "   100% { background-position: 0 100%; }\n"
    "}\n"
    "@keyframes flicker {\n"
    "   0%, 100% { opacity: 1; }\n"
    "   50% { opacity: 0.98; }\n"
    "}\n"
    "/* Centered black panel styling */\n"
    "section.main {\n"
    "   min-height: 100vh; display: flex;\n"
    "   justify-content: center; align-items: center;\n"
    "}\n"
    "section.main .block-container {\n"
    "   background-color: #000000; border: 2px solid #4e94ce;\n"
    "   border-radius: 5px; padding: 20px;\n"
    "   width: 80vw; max-width: 600px; min-width: 300px;\n"
    "   box-shadow: 0 0 5px #4e94ce; text-align: center;\n"
    "   animation: glow 2s ease-in-out infinite alternate;\n"
    "}\n"
    "@keyframes glow {\n"
    "   from { box-shadow: 0 0 5px #4e94ce; }\n"
    "   to { box-shadow: 0 0 15px #4e94ce; }\n"
    "}\n"
    "/* Input fields and button adjustments inside panel */\n"
    ".stNumberInput, .stSelectbox, .stTextInput, .stButton {\n"
    "   margin: 10px auto;\n"
    "}\n"
    ".stNumberInput input, .stTextInput input, .stSelectbox select {\n"
    "   max-width: 250px;\n"
    "}\n"
    "</style>\n"
)
if bg_base64:
    st.markdown(css_style, unsafe_allow_html=True)
else:
    st.warning("⚠️ Background image 'app_background.png' not found. Using default background.")

# Gas data (molecular weight kg/mol) including Air and Forming Gases
GAS_DATA = {
    "N2": 0.028013, "O2": 0.031999, "Ar": 0.039948, "CO2": 0.04401,
    "He": 0.0040026, "H2": 0.002016, "CH4": 0.01604, "C2H2": 0.02604,
    "Forming Gas 1": 0.03881, "Forming Gas 2": 0.02671, "Air": 0.02897
}
# Display names for gases
GAS_DISPLAY_NAMES = {
    "N2": "N2 (Nitrogen)",
    "O2": "O2 (Oxygen)",
    "Ar": "Ar (Argon)",
    "CO2": "CO2 (Carbon Dioxide)",
    "He": "He (Helium)",
    "H2": "H2 (Hydrogen)",
    "CH4": "CH4 (Methane)",
    "C2H2": "C2H2 (Acetylene)",
    "Forming Gas 1": "(H2-3% + Ar-97%) Forming Gas 1",
    "Forming Gas 2": "(H2-5% + N2-95%) Forming Gas 2",
    "Air": "Air (Dry Air)"
}
# Calculation types and fields
CALC_FIELDS = {
    "Pipe Diameter (mm)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Length (m)", "Flow Rate (LPM)"],
    "Flow Rate (LPM)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)"],
    "Pipe Length (m)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Diameter (mm)", "Flow Rate (LPM)"],
    "Inlet Pressure (bar)": ["Temperature (°C)", "Outlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)", "Flow Rate (LPM)"],
    "Outlet Pressure (bar)": ["Temperature (°C)", "Inlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)", "Flow Rate (LPM)"]
}
# Fixed friction factor
FRICTION_FACTOR = 0.02

# Calculation functions
def ideal_gas_density(P_pa, T_k, gas):
    R = 8.314
    M = GAS_DATA.get(gas)
    if M is None:
        raise ValueError(f"No data for gas: {gas}")
    return (P_pa * M) / (R * T_k)

def calc_required_diameter(P_in, P_out, T_c, L, Q, gas):
    P_in_pa = P_in * 1e5
    P_out_pa = P_out * 1e5
    T_k = T_c + 273.15
    Q_m3_s = Q / 1000.0 / 60.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be greater than outlet pressure.")
    D_m = ((FRICTION_FACTOR * L * 8.0 * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * delta_p)) ** 0.2
    return D_m * 1000.0

def calc_flow_rate(P_in, P_out, T_c, L, D, gas):
    P_in_pa = P_in * 1e5
    P_out_pa = P_out * 1e5
    T_k = T_c + 273.15
    D_m = D / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be higher than outlet pressure.")
    Q_m3_s = math.sqrt((delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * FRICTION_FACTOR * L * rho_avg))
    return Q_m3_s * 1000.0 * 60.0

def calc_max_length(P_in, P_out, T_c, D, Q, gas):
    P_in_pa = P_in * 1e5
    P_out_pa = P_out * 1e5
    T_k = T_c + 273.15
    D_m = D / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be greater than outlet pressure.")
    Q_m3_s = Q / 1000.0 / 60.0
    L = (delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * FRICTION_FACTOR * rho_avg * (Q_m3_s ** 2))
    return L

def calc_outlet_pressure(P_in, T_c, L, D, Q, gas):
    P_in_pa = P_in * 1e5
    T_k = T_c + 273.15
    D_m = D / 1000.0
    Q_m3_s = Q / 1000.0 / 60.0
    P_out_guess = P_in
    for _ in range(20):
        P_out_pa = P_out_guess * 1e5
        rho_in = ideal_gas_density(P_in_pa, T_k, gas)
        rho_out = ideal_gas_density(P_out_pa, T_k, gas)
        rho_avg = (rho_in + rho_out) / 2.0
        delta_p_calc = (8.0 * FRICTION_FACTOR * L * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * (D_m ** 5))
        P_out_calc = P_in - (delta_p_calc / 100000.0)
        if abs(P_out_calc - P_out_guess) < 0.001:
            return max(P_out_calc, 0.0)
        P_out_guess = P_out_calc
    return max(P_out_guess, 0.0)

def calc_required_inlet_pressure(P_out, T_c, L, D, Q, gas):
    P_low = P_out
    P_high = P_out + 100.0
    while True:
        P_out_test = calc_outlet_pressure(P_high, T_c, L, D, Q, gas)
        if P_out_test <= P_out or P_high >= P_out + 2000:
            break
        P_high += 100.0
    for _ in range(50):
        P_mid = (P_low + P_high) / 2.0
        P_out_mid = calc_outlet_pressure(P_mid, T_c, L, D, Q, gas)
        if abs(P_out_mid - P_out) < 0.01:
            return P_mid
        if P_out_mid > P_out:
            P_low = P_mid
        else:
            P_high = P_mid
    return (P_low + P_high) / 2.0

def determine_pipe_options(D, P, gas):
    if gas == "O2":
        return (["1\" tube (Spec S14) – required for O2"], "1\" tube (Spec S14)")
    opts = []; rec = None
    if D <= 4.0:
        if P <= 200:
            opts = [
                "1/4\" tube (Spec S6) – up to 200 bar",
                "1/4\" tube (Spec S9) – up to 1379 bar",
                "1/4\" tube (Spec S12) – above 1379 bar"
            ]; rec = "1/4\" tube (Spec S6)"
        elif P <= 1379:
            opts = [
                "1/4\" tube (Spec S9) – up to 1379 bar",
                "1/4\" tube (Spec S12) – above 1379 bar"
            ]; rec = "1/4\" tube (Spec S9)"
        else:
            opts = ["1/4\" tube (Spec S12) – above 1379 bar"]; rec = "1/4\" tube (Spec S12)"
    elif D <= 7.0:
        if P <= 140:
            opts = [
                "3/8\" tube (Spec S16) – up to 140 bar",
                "3/8\" tube (Spec S9) – above 140 bar"
            ]; rec = "3/8\" tube (Spec S16)"
        else:
            opts = ["3/8\" tube (Spec S9) – above 140 bar"]; rec = "3/8\" tube (Spec S9)"
    elif D <= 21.0:
        if P <= 20:
            opts = [
                "3/4\" tube (Spec S15) – up to 20 bar",
                "1\" tube (Spec S14) – above 20 bar"
            ]; rec = "3/4\" tube (Spec S15)"
        else:
            opts = ["1\" tube (Spec S14) – above 20 bar"]; rec = "1\" tube (Spec S14)"
    else:
        opts = ["Special piping required (outside standard range)"]; rec = "Special piping (outside range)"
    return (opts, rec)

# Title (centered inside the black panel)
st.title("High-Pressure Gas Flow Calculator")

# Selection inputs for gas and calc type
gas_type = st.selectbox("Gas type:", list(GAS_DATA.keys()), format_func=lambda x: GAS_DISPLAY_NAMES[x])
calc_type = st.selectbox("Calculation type:", list(CALC_FIELDS.keys()))

# Input fields based on selection
values = {}
for field in CALC_FIELDS.get(calc_type, []):
    default = 0.0
    if field == "Temperature (°C)": default = 25.0
    if field == "Inlet Pressure (bar)": default = 100.0
    if field == "Outlet Pressure (bar)": default = 10.0
    if field == "Pipe Length (m)": default = 10.0
    if field == "Pipe Diameter (mm)": default = 10.0
    if field == "Flow Rate (LPM)": default = 100.0
    values[field] = st.number_input(field, value=float(default))

# Show constant friction factor
st.caption(f"Friction factor (f) = {FRICTION_FACTOR:.2f} (fixed constant)")

# Session state for output
if "result" not in st.session_state:
    st.session_state.result = None
    st.session_state.error = False
    st.session_state.specs = []

# Calculate when button pressed
if st.button("Calculate"):
    try:
        T_c = float(values.get("Temperature (°C)", 0.0))
        P_in = float(values.get("Inlet Pressure (bar)", 0.0))
        P_out = float(values.get("Outlet Pressure (bar)", 0.0))
        L_val = float(values.get("Pipe Length (m)", 0.0))
        D_val = float(values.get("Pipe Diameter (mm)", 0.0))
        Q_val = float(values.get("Flow Rate (LPM)", 0.0))
        msg = ""; options = []
        if calc_type == "Pipe Diameter (mm)":
            D_req = calc_required_diameter(P_in, P_out, T_c, L_val, Q_val, gas_type)
            P_work = max(P_in, P_out)
            options, rec = determine_pipe_options(D_req, P_work, gas_type)
            msg = f"Required Diameter: **{D_req:.2f} mm**  \nRecommended: **{rec}**"
        elif calc_type == "Flow Rate (LPM)":
            Q_max = calc_flow_rate(P_in, P_out, T_c, L_val, D_val, gas_type)
            P_work = max(P_in, P_out)
            options, rec = determine_pipe_options(D_val, P_work, gas_type)
            msg = f"Maximum Flow Rate: **{Q_max:.1f} L/min**  \nRecommended: **{rec}**"
        elif calc_type == "Pipe Length (m)":
            L_max = calc_max_length(P_in, P_out, T_c, D_val, Q_val, gas_type)
            P_work = max(P_in, P_out)
            options, rec = determine_pipe_options(D_val, P_work, gas_type)
            msg = f"Maximum Pipe Length: **{L_max:.1f} m**  \nRecommended: **{rec}**"
        elif calc_type == "Inlet Pressure (bar)":
            P_req = calc_required_inlet_pressure(P_out, T_c, L_val, D_val, Q_val, gas_type)
            P_work = max(P_req, P_out)
            options, rec = determine_pipe_options(D_val, P_work, gas_type)
            msg = f"Required Inlet Pressure: **{P_req:.2f} bar**  \nRecommended: **{rec}**"
        elif calc_type == "Outlet Pressure (bar)":
            P_est = calc_outlet_pressure(P_in, T_c, L_val, D_val, Q_val, gas_type)
            P_work = P_in
            options, rec = determine_pipe_options(D_val, P_work, gas_type)
            msg = f"Estimated Outlet Pressure: **{P_est:.2f} bar**  \nRecommended: **{rec}**"
        else:
            msg = "Error: Unsupported calculation type."
            options = []
        st.session_state.result = msg
        st.session_state.error = False
        st.session_state.specs = options
    except Exception as e:
        st.session_state.result = f"Error: {e}"
        st.session_state.error = True
        st.session_state.specs = []

# Output result and options
if st.session_state.result is not None:
    if st.session_state.error:
        st.error(st.session_state.result)
    else:
        st.success(st.session_state.result)
        if st.session_state.specs:
            st.markdown("**Possible pipe specifications:**")
            data = []
            for spec in st.session_state.specs:
                if "–" in spec:
                    name, detail = spec.split("–", 1)
                    data.append({"Pipe Spec": name.strip(), "Details": detail.strip()})
                else:
                    data.append({"Pipe Spec": spec, "Details": ""})
            st.table(data)