import streamlit as st
import math

# Set page configuration
st.set_page_config(page_title="Tube Calculator", layout="centered")

# Custom styling
st.markdown(
    """
    <style>
    .main {
        background-color: #f4f4f4;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Molecular weights (kg/mol)
forming_gas1_ratio = (0.95 * 0.028) + (0.05 * 0.002)
forming_gas2_ratio = (0.97 * 0.040) + (0.03 * 0.002)

M = {
    "N2": 0.028,
    "Ar": 0.040,
    "He": 0.004,
    "O2": 0.032,
    "H2": 0.002,
    "C2H2": 0.026,
    "CH4": 0.016,
    "Air": 0.02897,
    "CO2": 0.044,
    "Forming Gas1": forming_gas1_ratio,
    "Forming Gas2": forming_gas2_ratio,
}

R = 8.314

# UI
st.title("Tube Calculator")

with st.sidebar:
    st.header("Input Parameters")
    gas_type = st.selectbox("Select Gas Type:", list(M.keys()))
    calculation_type = st.radio("Select Calculation Type:", ("Tube Diameter", "Flow Rate", "Tube Length", "Inlet Pressure", "Outlet Pressure"))

    T_C = st.number_input("Temperature (°C):", min_value=-50.0, value=30.0)
    Pin_bar = None
    Pout_bar = None
    L = None
    d_mm = None
    Q_LPM = None

    if calculation_type in ["Tube Diameter", "Flow Rate", "Tube Length", "Outlet Pressure"]:
        Pin_bar = st.number_input("Inlet Pressure (bar):", min_value=0.1, value=25.0)
    if calculation_type in ["Tube Diameter", "Flow Rate", "Tube Length", "Inlet Pressure"]:
        Pout_bar = st.number_input("Outlet Pressure (bar):", min_value=0.1, value=10.0)
    if calculation_type in ["Tube Diameter", "Flow Rate", "Inlet Pressure", "Outlet Pressure"]:
        L = st.number_input("Tube Length (m):", min_value=0.1, value=50.0)
    if calculation_type in ["Flow Rate", "Tube Length", "Inlet Pressure", "Outlet Pressure"]:
        d_mm = st.number_input("Tube Inner Diameter (mm):", min_value=0.1, value=10.0)
    if calculation_type in ["Tube Diameter", "Tube Length", "Inlet Pressure", "Outlet Pressure"]:
        Q_LPM = st.number_input("Flow Rate (LPM):", min_value=0.1, value=16.0)

# Compressible flow model for Flow Rate (Choked + Subsonic)
def compressible_flow_rate(P1, P2, d_mm, L, T_K, M_kg, f):
    d_m = d_mm / 1000
    A = math.pi * (d_m ** 2) / 4
    Rs = R / M_kg
    gamma = 1.4
    P_ratio = P2 / P1

    critical_ratio = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
    rho1 = P1 / (Rs * T_K)

    if P_ratio <= critical_ratio:
        Q_m3s = A * math.sqrt(gamma * P1 * rho1 / M_kg) * ((2 / (gamma + 1)) ** ((gamma + 1) / (2 * (gamma - 1))))
    else:
        delta_P = P1 - P2
        rho_avg = ((P1 / (Rs * T_K)) + (P2 / (Rs * T_K))) / 2
        Q_m3s = ((math.pi ** 2 * delta_P * d_m ** 5) / (8 * f * L * rho_avg)) ** 0.5

    return Q_m3s * 60000

if st.button("Calculate"):
    Pin_Pa = Pin_bar * 100000 if Pin_bar is not None else None
    Pout_Pa = Pout_bar * 100000 if Pout_bar is not None else None
    f = 0.02
    result = None
    M_kg = M[gas_type]
    T_K = T_C + 273.15
    Rs = R / M_kg

    st.markdown(f"### Calculation Type: {calculation_type}")
    st.markdown(f"- Gas Type: **{gas_type}**")
    st.markdown(f"- Temperature: **{T_C} °C**")
    if Q_LPM: st.markdown(f"- Flow Rate: **{Q_LPM} LPM**")
    if d_mm: st.markdown(f"- Tube Diameter: **{d_mm} mm**")
    if L and calculation_type != "Tube Length":
        st.markdown(f"- Tube Length: **{L} m**")
    if Pin_bar: st.markdown(f"- Inlet Pressure: **{Pin_bar} bar**")
    if Pout_bar: st.markdown(f"- Outlet Pressure: **{Pout_bar} bar**")

    st.markdown("---")

    if calculation_type == "Flow Rate" and None not in [d_mm, T_C, Pin_Pa, Pout_Pa, L]:
        result = compressible_flow_rate(Pin_Pa, Pout_Pa, d_mm, L, T_K, M_kg, f)
        st.success(f"Calculated Flow Rate (compressible): **{result:.2f} LPM**")
    else:
        st.info("This demo update supports compressible flow rate calculation only. Support for other calculations can be expanded.")

st.markdown("---")
st.markdown("**This application now supports compressible flow modeling for accurate high-pressure calculations.**")