import math
import base64
import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(page_title="High-Pressure Gas Flow Calculator (Darcy–Weisbach)",
                   page_icon="💨", layout="centered")

# Load background image and prepare base64
@st.cache_data
def load_bg_image(image_name: str) -> str | None:
    base_dir = Path(__file__).resolve().parent
    image_path = base_dir / image_name
    if not image_path.exists():
        return None
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

bg_image_base64 = load_bg_image("app_background.png")

# Inject CSS for background, layout, and animations
if bg_image_base64:
    st.markdown(f"""
        <style>
        html, body, .stApp {{ height: 100%; margin: 0; padding: 0; }}
        .stApp {{
            background: url('data:image/png;base64,{bg_image_base64}') center/cover no-repeat fixed;
            display: flex; justify-content: center; align-items: center;
            color: #ffffff;
        }}
        .block-container {{
            width: 60%; max-width: 800px; min-width: 300px;
            max-height: 80vh; overflow-y: auto;
            background: rgba(0,0,0,0.9);
            padding: 20px;
            border: 1px solid #4e94ce;
            border-radius: 5px;
            box-shadow: 0 0 5px #4e94ce;
            animation: glow 2s infinite;
        }}
        @keyframes glow {{
            0%, 100% {{ box-shadow: 0 0 5px #4e94ce; }}
            50%       {{ box-shadow: 0 0 15px #4e94ce; }}
        }}
        .stApp::before {{
            content: '';
            position: fixed; top: 0; left: 0;
            width: 100%; height: 100%;
            background: repeating-linear-gradient(
                0deg,
                rgba(78,148,206, 0.1) 0px,
                rgba(78,148,206, 0.1) 1px,
                transparent 1px,
                transparent 2px
            );
            animation: scroll 10s linear infinite, flicker 1s infinite;
            pointer-events: none;
        }}
        @keyframes scroll {{
            0% {{ background-position: 0 0; }}
            100% {{ background-position: 0 100px; }}
        }}
        @keyframes flicker {{
            0% {{ opacity: 0.2; }}
            50% {{ opacity: 0.3; }}
            100% {{ opacity: 0.2; }}
        }}
        input, select, textarea {{
            background-color: #111 !important;
            color: #ffffff !important;
            border: 1px solid #4e94ce !important;
        }}
        button, .stButton>button {{
            background-color: #222 !important;
            color: #ffffff !important;
            border: 1px solid #4e94ce !important;
        }}
        </style>
    """, unsafe_allow_html=True)
else:
    st.warning("⚠️ Background image 'app_background.png' not found. Running without custom background.")

# Gas properties (molecular weight for each gas in kg/mol)
GAS_DATA = {
    "N2": 0.028013,      # Nitrogen
    "O2": 0.031999,      # Oxygen
    "Ar": 0.039948,      # Argon
    "CO2": 0.04401,      # Carbon Dioxide
    "He": 0.0040026,     # Helium
    "H2": 0.002016,      # Hydrogen
    "CH4": 0.01604,      # Methane
    "C2H2": 0.02604,     # Acetylene
    "Forming Gas 1": 0.03881,  # H2 3% + Ar 97%
    "Forming Gas 2": 0.02671,  # H2 5% + N2 95%
    "Air": 0.02897       # Dry Air (approximately 78% N2, 21% O2)
}

# Display names for gas options (with descriptions for mixtures)
GAS_DISPLAY_NAMES = {
    "N2": "N2 (Nitrogen)",
    "O2": "O2 (Oxygen)",
    "Ar": "Ar (Argon)",
    "CO2": "CO2 (Carbon Dioxide)",
    "He": "He (Helium)",
    "H2": "H2 (Hydrogen)",
    "CH4": "CH4 (Methane)",
    "C2H2": "C2H2 (Acetylene)",
    "Forming Gas 1": "(H2-3%+Ar-97%) Forming gas 1",
    "Forming Gas 2": "(H2-5%+N2-95%) Forming gas 2",
    "Air": "Air (Dry air)"
}

# Calculation types and required fields for each
CALC_FIELDS = {
    "Pipe Diameter (mm)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Length (m)", "Flow Rate (LPM)"],
    "Flow Rate (LPM)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)"],
    "Pipe Length (m)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Diameter (mm)", "Flow Rate (LPM)"],
    "Inlet Pressure (bar)": ["Temperature (°C)", "Outlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)", "Flow Rate (LPM)"],
    "Outlet Pressure (bar)": ["Temperature (°C)", "Inlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)", "Flow Rate (LPM)"]
}

# Constant friction factor for Darcy–Weisbach calculations
FRICTION_FACTOR = 0.02

def ideal_gas_density(P_pa, T_k, gas_type):
    """Return gas density [kg/m^3] at pressure P (Pa) and temperature T (K) using the ideal gas law."""
    R = 8.314  # Universal gas constant [J/(mol*K)]
    M = GAS_DATA.get(gas_type)
    if M is None:
        raise ValueError(f"No data for gas type: {gas_type}")
    return (P_pa * M) / (R * T_k)

def calc_required_diameter(P_in_bar, P_out_bar, T_c, L_m, Q_lpm, gas_type):
    """Calculate required internal pipe diameter [mm] for given flow conditions using Darcy–Weisbach."""
    # Convert units to SI
    P_in_pa = P_in_bar * 100000.0    # bar -> Pa
    P_out_pa = P_out_bar * 100000.0  # bar -> Pa
    T_k = T_c + 273.15               # °C -> K
    Q_m3_s = Q_lpm / 1000.0 / 60.0   # L/min -> m^3/s
    # Calculate average gas density along the pipe
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    # Pressure drop (Pa)
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be greater than outlet pressure for flow to occur.")
    # Solve Darcy–Weisbach for D (meters) and convert to mm
    D_m = ((FRICTION_FACTOR * L_m * 8.0 * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * delta_p)) ** 0.2
    return D_m * 1000.0

def calc_flow_rate(P_in_bar, P_out_bar, T_c, L_m, D_mm, gas_type):
    """Calculate maximum flow rate [L/min] through a given pipe (Darcy–Weisbach)."""
    P_in_pa = P_in_bar * 100000.0
    P_out_pa = P_out_bar * 100000.0
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be higher than outlet pressure to calculate flow rate.")
    # Darcy–Weisbach for flow rate (m^3/s) and convert to L/min
    Q_m3_s = math.sqrt((delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * FRICTION_FACTOR * L_m * rho_avg))
    return Q_m3_s * 1000.0 * 60.0

def calc_max_length(P_in_bar, P_out_bar, T_c, D_mm, Q_lpm, gas_type):
    """Calculate maximum pipe length [m] for given flow conditions (Darcy–Weisbach)."""
    P_in_pa = P_in_bar * 100000.0
    P_out_pa = P_out_bar * 100000.0
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be greater than outlet pressure for flow to occur.")
    Q_m3_s = Q_lpm / 1000.0 / 60.0
    # Darcy–Weisbach for L (meters)
    L_m = (delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * FRICTION_FACTOR * rho_avg * (Q_m3_s ** 2))
    return L_m

def calc_outlet_pressure(P_in_bar, T_c, L_m, D_mm, Q_lpm, gas_type):
    """Estimate outlet pressure [bar] using Darcy–Weisbach (iteratively solving)."""
    P_in_pa = P_in_bar * 100000.0
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    Q_m3_s = Q_lpm / 1000.0 / 60.0
    P_out_guess_bar = P_in_bar
    # Iterate to solve for outlet pressure
    for _ in range(20):
        P_out_pa = P_out_guess_bar * 100000.0
        rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
        rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
        rho_avg = (rho_in + rho_out) / 2.0
        delta_p_calc = (8.0 * FRICTION_FACTOR * L_m * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * (D_m ** 5))
        P_out_calc_bar = P_in_bar - (delta_p_calc / 100000.0)
        if abs(P_out_calc_bar - P_out_guess_bar) < 0.001:
            return max(P_out_calc_bar, 0.0)
        P_out_guess_bar = P_out_calc_bar
    return max(P_out_guess_bar, 0.0)

def calc_required_inlet_pressure(P_out_bar, T_c, L_m, D_mm, Q_lpm, gas_type):
    """Calculate required inlet pressure [bar] to achieve a target outlet pressure (iterative)."""
    P_low = P_out_bar
    P_high = P_out_bar + 100.0
    # Find an upper bound for inlet pressure where outlet pressure is at or below target
    while True:
        P_out_test = calc_outlet_pressure(P_high, T_c, L_m, D_mm, Q_lpm, gas_type)
        if P_out_test <= P_out_bar or P_high >= P_out_bar + 2000:
            break
        P_high += 100.0
    # Binary search between bounds
    for _ in range(50):
        P_mid = (P_low + P_high) / 2.0
        P_out_mid = calc_outlet_pressure(P_mid, T_c, L_m, D_mm, Q_lpm, gas_type)
        if abs(P_out_mid - P_out_bar) < 0.01:
            return P_mid
        if P_out_mid > P_out_bar:
            P_low = P_mid
        else:
            P_high = P_mid
    return (P_low + P_high) / 2.0

def determine_pipe_options(D_mm, P_bar, gas_type):
    """Determine possible and recommended pipe specifications for a given diameter [mm], pressure [bar] and gas type."""
    # Special case for Oxygen (O2): recommend only Spec S14
    if gas_type == "O2":
        return (["1\" tube (Spec S14) – (required for O2)"], "1\" tube (Spec S14)")
    possible = []
    recommended = None
    # 1/4" tube category
    if D_mm <= 4.0:
        if P_bar <= 200:
            possible = [
                "1/4\" tube (Spec S6) – rated up to 200 bar",
                "1/4\" tube (Spec S9) – rated up to 1379 bar",
                "1/4\" tube (Spec S12) – rated for >1379 bar"
            ]
            recommended = "1/4\" tube (Spec S6)"
        elif P_bar <= 1379:
            possible = [
                "1/4\" tube (Spec S9) – rated up to 1379 bar",
                "1/4\" tube (Spec S12) – rated for >1379 bar"
            ]
            recommended = "1/4\" tube (Spec S9)"
        else:
            possible = ["1/4\" tube (Spec S12) – rated for >1379 bar"]
            recommended = "1/4\" tube (Spec S12)"
    # 3/8" tube category
    elif D_mm <= 7.0:
        if P_bar <= 140:
            possible = [
                "3/8\" tube (Spec S16) – rated up to 140 bar",
                "3/8\" tube (Spec S9) – rated for >140 bar"
            ]
            recommended = "3/8\" tube (Spec S16)"
        else:
            possible = ["3/8\" tube (Spec S9) – rated for >140 bar"]
            recommended = "3/8\" tube (Spec S9)"
    # 3/4" or 1" tube category
    elif D_mm <= 21.0:
        if P_bar <= 20:
            possible = [
                "3/4\" tube (Spec S15) – rated up to 20 bar",
                "1\" tube (Spec S14) – rated for >20 bar"
            ]
            recommended = "3/4\" tube (Spec S15)"
        else:
            possible = ["1\" tube (Spec S14) – rated for >20 bar"]
            recommended = "1\" tube (Spec S14)"
    else:
        possible = ["Special piping required (outside standard range)"]
        recommended = "Special piping (outside standard range)"
    return (possible, recommended)

# Title and description
st.title("High-Pressure Gas Flow Calculator – Darcy–Weisbach")
st.markdown("""
This interactive app calculates **pipe diameter**, **flow rate**, **pipe length**, and **pressures** for high-pressure gas flow based on the **Darcy–Weisbach** equation.  
Select the **gas type** and **calculation type**, enter the input parameters (temperature, pressures, length, diameter, or flow rate), then click **Calculate** to get the results.  
The results will include the calculated value and a **recommended pipe specification** for the given conditions, as well as a **list of possible tube specs** that meet the diameter, pressure, and gas requirements.  
*Note: The friction factor f is fixed at 0.02 in all calculations.*
""")

# Gas type and calculation type selectors
gas_type = st.selectbox("Gas type:", options=GAS_DATA.keys(), format_func=lambda x: GAS_DISPLAY_NAMES[x])
calc_type = st.selectbox("Calculation type:", options=list(CALC_FIELDS.keys()), index=0)

# Dynamic input fields for selected calculation type
input_values = {}
for field in CALC_FIELDS.get(calc_type, []):
    if field == "Temperature (°C)":
        input_values[field] = st.number_input(field, value=25.0, step=1.0, format="%.2f")
    elif field == "Inlet Pressure (bar)":
        input_values[field] = st.number_input(field, value=100.0, step=1.0, format="%.2f")
    elif field == "Outlet Pressure (bar)":
        input_values[field] = st.number_input(field, value=10.0, step=1.0, format="%.2f")
    elif field == "Pipe Length (m)":
        input_values[field] = st.number_input(field, value=10.0, step=1.0, format="%.2f")
    elif field == "Pipe Diameter (mm)":
        input_values[field] = st.number_input(field, value=10.0, step=0.1, format="%.2f")
    elif field == "Flow Rate (LPM)":
        input_values[field] = st.number_input(field, value=100.0, step=1.0, format="%.1f")
    else:
        input_values[field] = st.number_input(field, value=0.0, step=1.0, format="%.2f")

# Display fixed friction factor
st.caption(f"Friction factor (f) = {FRICTION_FACTOR:.2f} (fixed)")

# Initialize session state for result persistence
if "last_result" not in st.session_state:
    st.session_state.last_result = None
    st.session_state.last_is_error = False
    st.session_state.last_possible_pipes = None

# Calculation button
if st.button("Calculate"):
    try:
        # Retrieve inputs
        T_c = float(input_values.get("Temperature (°C)", 0.0))
        P_in = float(input_values.get("Inlet Pressure (bar)", 0.0))
        P_out = float(input_values.get("Outlet Pressure (bar)", 0.0))
        L_m = float(input_values.get("Pipe Length (m)", 0.0))
        D_mm = float(input_values.get("Pipe Diameter (mm)", 0.0))
        Q_lpm = float(input_values.get("Flow Rate (LPM)", 0.0))
        result_text = ""
        possible_pipes_list = []
        # Perform calculation based on selected type
        if calc_type == "Pipe Diameter (mm)":
            D_required = calc_required_diameter(P_in, P_out, T_c, L_m, Q_lpm, gas_type)
            P_work = max(P_in, P_out)
            possible_pipes_list, recommended_pipe = determine_pipe_options(D_required, P_work, gas_type)
            result_text = f"**Required pipe diameter:** {D_required:.2f} mm  \n**Recommended pipe spec:** {recommended_pipe}"
        elif calc_type == "Flow Rate (LPM)":
            Q_max = calc_flow_rate(P_in, P_out, T_c, L_m, D_mm, gas_type)
            P_work = max(P_in, P_out)
            possible_pipes_list, recommended_pipe = determine_pipe_options(D_mm, P_work, gas_type)
            result_text = f"**Maximum flow rate:** {Q_max:.1f} L/min  \n**Recommended pipe spec:** {recommended_pipe}"
        elif calc_type == "Pipe Length (m)":
            L_max = calc_max_length(P_in, P_out, T_c, D_mm, Q_lpm, gas_type)
            P_work = max(P_in, P_out)
            possible_pipes_list, recommended_pipe = determine_pipe_options(D_mm, P_work, gas_type)
            result_text = f"**Maximum pipe length:** {L_max:.1f} m  \n**Recommended pipe spec:** {recommended_pipe}"
        elif calc_type == "Inlet Pressure (bar)":
            P_in_required = calc_required_inlet_pressure(P_out, T_c, L_m, D_mm, Q_lpm, gas_type)
            P_work = max(P_in_required, P_out)
            possible_pipes_list, recommended_pipe = determine_pipe_options(D_mm, P_work, gas_type)
            result_text = f"**Required inlet pressure:** {P_in_required:.2f} bar  \n**Recommended pipe spec:** {recommended_pipe}"
        elif calc_type == "Outlet Pressure (bar)":
            P_out_est = calc_outlet_pressure(P_in, T_c, L_m, D_mm, Q_lpm, gas_type)
            P_work = P_in
            possible_pipes_list, recommended_pipe = determine_pipe_options(D_mm, P_work, gas_type)
            result_text = f"**Estimated outlet pressure:** {P_out_est:.2f} bar  \n**Recommended pipe spec:** {recommended_pipe}"
        else:
            result_text = "Error: Unsupported calculation type."
            possible_pipes_list = []
        st.session_state.last_result = result_text
        st.session_state.last_is_error = False
        st.session_state.last_possible_pipes = possible_pipes_list
    except Exception as e:
        # Handle any exceptions (e.g., invalid input or flow condition)
        st.session_state.last_result = f"Error: {e}"
        st.session_state.last_is_error = True
        st.session_state.last_possible_pipes = None

# Output result or error message
if st.session_state.last_result is not None:
    if st.session_state.last_is_error:
        st.error(st.session_state.last_result)
    else:
        st.success(st.session_state.last_result)
        if st.session_state.last_possible_pipes:
            st.markdown("**Possible pipe specifications for these conditions:**")
            table_data = []
            for spec_entry in st.session_state.last_possible_pipes:
                if "–" in spec_entry:
                    spec_name, spec_desc = spec_entry.split("–", 1)
                    table_data.append({"Pipe Spec": spec_name.strip(), "Pressure/Service": spec_desc.strip()})
                else:
                    table_data.append({"Pipe Spec": spec_entry, "Pressure/Service": ""})
            st.table(table_data)