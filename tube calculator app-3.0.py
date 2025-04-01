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
st.title("מחשבון צנרת - Tube Calculator")

with st.sidebar:
    st.header("הזן נתונים")
    gas_type = st.selectbox("בחר סוג גז:", list(M.keys()))
    calculation_type = st.radio("בחר סוג חישוב:", ("קוטר צינור", "ספיקה", "אורך צינור", "לחץ כניסה", "לחץ יציאה"))

    T_C = st.number_input("טמפרטורת עבודה (°C):", min_value=-50.0, value=30.0)
    Pin_bar = None
    Pout_bar = None
    L = None
    d_mm = None
    Q_LPM = None

    if calculation_type in ["קוטר צינור", "ספיקה", "אורך צינור", "לחץ יציאה"]:
        Pin_bar = st.number_input("לחץ כניסה (בר):", min_value=0.1, value=25.0)
    if calculation_type in ["קוטר צינור", "ספיקה", "אורך צינור", "לחץ כניסה"]:
        Pout_bar = st.number_input("לחץ יציאה (בר):", min_value=0.1, value=10.0)
    if calculation_type in ["קוטר צינור", "ספיקה", "אורך צינור", "לחץ כניסה", "לחץ יציאה"]:
        L = st.number_input("אורך צינור (מטר):", min_value=0.1, value=50.0)
    if calculation_type in ["ספיקה", "אורך צינור", "לחץ כניסה", "לחץ יציאה"]:
        d_mm = st.number_input("קוטר פנימי של צינור (מ""מ):", min_value=0.1, value=10.0)
    if calculation_type in ["קוטר צינור", "אורך צינור", "לחץ כניסה", "לחץ יציאה"]:
        Q_LPM = st.number_input("ספיקה (ליטר/דקה):", min_value=0.1, value=16.0)

if st.button("חשב"):
    Pin_Pa = Pin_bar * 100000 if Pin_bar is not None else None
    Pout_Pa = Pout_bar * 100000 if Pout_bar is not None else None
    f = 0.02
    result = None
    M_kg = M[gas_type]
    T_K = T_C + 273.15
    Rs = R / M_kg

    st.markdown(f"### חישוב עבור: {calculation_type}")
    st.markdown(f"- סוג הגז: **{gas_type}**")
    st.markdown(f"- טמפרטורה: **{T_C}°C**")
    if Q_LPM: st.markdown(f"- ספיקה: **{Q_LPM} LPM**")
    if d_mm: st.markdown(f"- קוטר צינור: **{d_mm} מ""מ**")
    if L: st.markdown(f"- אורך צינור: **{L} מטר**")
    if Pin_bar: st.markdown(f"- לחץ כניסה: **{Pin_bar} בר**")
    if Pout_bar: st.markdown(f"- לחץ יציאה: **{Pout_bar} בר**")

    st.markdown("---")

    if calculation_type == "קוטר צינור" and None not in [Q_LPM, T_C, Pin_Pa, Pout_Pa, L]:
        rho_avg = (Pin_Pa / (Rs * T_K) + Pout_Pa / (Rs * T_K)) / 2
        result = ((8 * f * L * rho_avg * (Q_LPM / 60000) ** 2) / (math.pi ** 2 * (Pin_Pa - Pout_Pa))) ** (1 / 5) * 1000
        st.success(f"קוטר נדרש: **{result:.2f} מ""מ**")

    elif calculation_type == "ספיקה" and None not in [d_mm, T_C, Pin_Pa, Pout_Pa, L]:
        rho_avg = (Pin_Pa / (Rs * T_K) + Pout_Pa / (Rs * T_K)) / 2
        result = ((math.pi ** 2 * (Pin_Pa - Pout_Pa) * (d_mm / 1000) ** 5) / (8 * f * L * rho_avg)) ** 0.5 * 60000
        st.success(f"ספיקה מחושבת: **{result:.2f} LPM**")

    elif calculation_type == "אורך צינור" and None not in [Q_LPM, d_mm, T_C, Pin_Pa, Pout_Pa]:
        rho_avg = (Pin_Pa / (Rs * T_K) + Pout_Pa / (Rs * T_K)) / 2
        result = (math.pi ** 2 * (Pin_Pa - Pout_Pa) * (d_mm / 1000) ** 5) / (8 * f * rho_avg * (Q_LPM / 60000) ** 2)
        st.success(f"אורך נדרש: **{result:.2f} מטר**")

    elif calculation_type == "לחץ כניסה" and None not in [Q_LPM, d_mm, T_C, Pout_Pa, L]:
        rho_out = Pout_Pa / (Rs * T_K)
        result = Pout_Pa + ((8 * f * L * rho_out * (Q_LPM / 60000) ** 2) / (math.pi ** 2 * (d_mm / 1000) ** 5))
        st.success(f"לחץ כניסה נדרש: **{result / 100000:.2f} בר**")

    elif calculation_type == "לחץ יציאה" and None not in [Q_LPM, d_mm, T_C, Pin_Pa, L]:
        rho_in = Pin_Pa / (Rs * T_K)
        result = Pin_Pa - ((8 * f * L * rho_in * (Q_LPM / 60000) ** 2) / (math.pi ** 2 * (d_mm / 1000) ** 5))
        st.success(f"לחץ יציאה נדרש: **{result / 100000:.2f} בר**")

    else:
        st.error("אנא ודא שכל הפרמטרים הנדרשים מולאו בצורה תקינה.")

st.markdown("---")
st.markdown("**האפליקציה מותאמת לפריסה בענן Streamlit ולשיתוף מהיר.**")
