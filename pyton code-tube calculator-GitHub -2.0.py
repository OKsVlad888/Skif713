import streamlit as st
import math

# 🟢 `st.set_page_config` חייב להיות השורה הראשונה אחרי הייבוא
st.set_page_config(page_title="Tube Calculator", layout="centered")

# Apply custom styling
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

# Gas molecular weights (M) in g/mol, converted to kg/mol for correct SI calculations
forming_gas1_ratio = (0.95 * 0.028) + (0.05 * 0.002)
forming_gas2_ratio = (0.97 * 0.040) + (0.03 * 0.002)

M = {
    "N2": 0.028,   # Nitrogen
    "Ar": 0.040,   # Argon
    "He": 0.004,   # Helium
    "O2": 0.032,   # Oxygen
    "H2": 0.002,   # Hydrogen
    "C2H2": 0.026, # Acetylene
    "CH4": 0.016,  # Methane
    "Air": 0.02897,# Air (approximate)
    "CO2": 0.044,  # Carbon Dioxide
    "Forming Gas1": forming_gas1_ratio,
    "Forming Gas2": forming_gas2_ratio,
}

R = 8.314  # Universal gas constant

# Streamlit Web Application
st.title("Tube Calculator (GitHub Deployment Ready)")

with st.sidebar:
    st.header("Input Parameters")
    gas_type = st.selectbox("Select Gas Type:", list(M.keys()))
    calculation_type = st.radio("Select Calculation Type:", ("Diameter", "Flow Rate", "Tube Length", "Inlet Pressure", "Outlet Pressure"))

    # הצגת השדות בהתאם לסוג החישוב
    T_C = st.number_input("Temperature (°C):", min_value=-50.0, value=30.0)
    
    if calculation_type in ["Diameter", "Flow Rate", "Tube Length", "Inlet Pressure", "Outlet Pressure"]:
        Pin_bar = st.number_input("Inlet Pressure (bar):", min_value=0.1, value=25.0)
        Pout_bar = st.number_input("Outlet Pressure (bar):", min_value=0.1, value=10.0)
    
    if calculation_type in ["Diameter", "Flow Rate", "Tube Length"]:
        L = st.number_input("Tube Length (m):", min_value=0.1, value=50.0)
    else:
        L = None
    
    if calculation_type in ["Flow Rate", "Tube Length"]:
        d_mm = st.number_input("Tube Diameter (mm):", min_value=0.1, value=10.0)
    else:
        d_mm = None
    
    if calculation_type in ["Diameter", "Tube Length"]:
        Q_LPM = st.number_input("Flow Rate (LPM):", min_value=0.1, value=16.0)
    else:
        Q_LPM = None

if st.button("Calculate"):
    Pin_Pa = Pin_bar * 100000 if Pin_bar is not None else None
    Pout_Pa = Pout_bar * 100000 if Pout_bar is not None else None
    f = 0.02
    result = None

    if calculation_type == "Diameter" and None not in [Q_LPM, T_C, Pin_Pa, Pout_Pa, L]:
        result = ((8 * f * L * ((Pin_Pa + Pout_Pa) / 2) * (Q_LPM / 60000) ** 2) / (math.pi ** 2 * (Pin_Pa - Pout_Pa))) ** (1/5) * 1000
    elif calculation_type == "Flow Rate" and None not in [d_mm, T_C, Pin_Pa, Pout_Pa, L]:
        result = ((math.pi ** 2 * (Pin_Pa - Pout_Pa) * (d_mm / 1000) ** 5) / (8 * f * L * ((Pin_Pa + Pout_Pa) / 2))) ** 0.5 * 60000
    elif calculation_type == "Tube Length" and None not in [Q_LPM, d_mm, T_C, Pin_Pa, Pout_Pa]:
        result = (math.pi ** 2 * (Pin_Pa - Pout_Pa) * (d_mm / 1000) ** 5) / (8 * f * ((Pin_Pa + Pout_Pa) / 2) * (Q_LPM / 60000) ** 2)
    
    if result is not None:
        st.success(f"Result: {result:.2f}")
    else:
        st.error("Invalid input parameters. Ensure that all required fields are filled.")

st.markdown("**This application is ready for GitHub deployment with Streamlit Cloud.**")
