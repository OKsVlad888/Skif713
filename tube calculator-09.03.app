import math
import base64
import streamlit as st

# הגדרת העמוד: שם האפליקציה, אייקון ופריסה
st.set_page_config(page_title="מחשבון זרימת גז בלחץ גבוה (Darcy–Weisbach)",
                   page_icon="💨", layout="centered")

# פונקציה לטעינת תמונת רקע והמרתה למחרוזת Base64 (לשילוב ב-CSS)
@st.cache_data
def load_bg_image(file_path):
    with open(file_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return encoded

# טעינת תמונת הרקע והגדרה כ-CSS של רקע האפליקציה
bg_image_base64 = load_bg_image("app_background.png")
page_bg_style = f"""
<style>
.stApp {{
  background-image: url("data:image/png;base64,{bg_image_base64}");
  background-size: cover;
}}
</style>
"""
st.markdown(page_bg_style, unsafe_allow_html=True)

# נתוני הגזים: משקל מולקולרי [ק"ג/מול] עבור כל גז (כולל "אוויר" ותערובות Forming Gas)
GAS_DATA = {
    "N2": 0.028013,      # חנקן
    "O2": 0.031999,      # חמצן
    "Ar": 0.039948,      # ארגון
    "CO2": 0.04401,      # פחמן דו-חמצני
    "He": 0.0040026,     # הליום
    "H2": 0.002016,      # מימן
    "CH4": 0.01604,      # מתאן
    "C2H2": 0.02604,     # אצטילן
    "Forming Gas 1": 0.03881,  # H2 3% + Ar 97%
    "Forming Gas 2": 0.02671,  # H2 5% + N2 95%
    "Air": 0.02897       # אוויר (יבש)
}

# שמות הגזים לתצוגה (עם תיאור תערובות)
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
    "Air": "Air (Dry air: 78% N2, 21% O2)"
}

# רשימת סוגי הגזים הזמינים בתפריט הבחירה
GAS_TYPES = list(GAS_DATA.keys())

# מיפוי סוגי החישוב לשדות הקלט הנדרשים (שמות ויחידות באנגלית)
CALC_FIELDS = {
    "Pipe Diameter (mm)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Length (m)", "Flow Rate (LPM)"],
    "Flow Rate (LPM)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)"],
    "Pipe Length (m)": ["Temperature (°C)", "Inlet Pressure (bar)", "Outlet Pressure (bar)", "Pipe Diameter (mm)", "Flow Rate (LPM)"],
    "Inlet Pressure (bar)": ["Temperature (°C)", "Outlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)", "Flow Rate (LPM)"],
    "Outlet Pressure (bar)": ["Temperature (°C)", "Inlet Pressure (bar)", "Pipe Length (m)", "Pipe Diameter (mm)", "Flow Rate (LPM)"]
}

# מקדם החיכוך (f) קבוע בכל החישובים
FRICTION_FACTOR = 0.02

def ideal_gas_density(P_pa, T_k, gas_type):
    """מחזירה צפיפות הגז [ק\"ג/מ^3] בלחץ P (פסקל) וטמפרטורה T (קלווין) לפי חוק הגז האידיאלי."""
    R = 8.314  # קבוע הגזים [J/(mol*K)]
    M = GAS_DATA.get(gas_type)
    if M is None:
        raise ValueError(f"No data for gas type: {gas_type}")
    return (P_pa * M) / (R * T_k)

def calc_required_diameter(P_in_bar, P_out_bar, T_c, L_m, Q_lpm, gas_type):
    """חישוב קוטר פנימי דרוש [מ\"מ] לפי משוואת Darcy–Weisbach."""
    # המרת יחידות קלט ליחידות SI
    P_in_pa = P_in_bar * 100000.0   # bar -> Pa
    P_out_pa = P_out_bar * 100000.0 # bar -> Pa
    T_k = T_c + 273.15             # °C -> K
    Q_m3_s = Q_lpm / 1000.0 / 60.0  # L/min -> m^3/s
    # חישוב צפיפות ממוצעת לאורך הצינור (גז אידיאלי לדחיסות)
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    # הפרש לחצים (Pa)
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be greater than outlet pressure for flow to occur.")
    # פתרון משוואת Darcy–Weisbach עבור D (במטרים) -> המרה למ\"מ
    D_m = ((FRICTION_FACTOR * L_m * 8.0 * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * delta_p)) ** 0.2
    return D_m * 1000.0

def calc_flow_rate(P_in_bar, P_out_bar, T_c, L_m, D_mm, gas_type):
    """חישוב ספיקה מירבית [ליטר/דקה] בצינור נתון לפי משוואת Darcy–Weisbach."""
    P_in_pa = P_in_bar * 100000.0
    P_out_pa = P_out_bar * 100000.0
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0  # המרת קוטר מ\"מ -> מטר
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = P_in_pa - P_out_pa
    if delta_p <= 0:
        raise ValueError("Inlet pressure must be higher than outlet pressure to calculate flow rate.")
    # פתרון משוואת Darcy–Weisbach עבור ספיקה (מ\"ק/שנייה) -> המרה לליטר/דקה
    Q_m3_s = math.sqrt((delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * FRICTION_FACTOR * L_m * rho_avg))
    return Q_m3_s * 1000.0 * 60.0

def calc_max_length(P_in_bar, P_out_bar, T_c, D_mm, Q_lpm, gas_type):
    """חישוב אורך צינור מקסימלי [מ'] לפי משוואת Darcy–Weisbach."""
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
    # פתרון משוואת Darcy–Weisbach עבור L (מטרים)
    L_m = (delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * FRICTION_FACTOR * rho_avg * (Q_m3_s ** 2))
    return L_m

def calc_outlet_pressure(P_in_bar, T_c, L_m, D_mm, Q_lpm, gas_type):
    """אומדן לחץ יציאה [בר] לפי משוואת Darcy–Weisbach (באמצעות איטרציה)."""
    P_in_pa = P_in_bar * 100000.0
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    Q_m3_s = Q_lpm / 1000.0 / 60.0
    P_out_guess_bar = P_in_bar
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
    """חישוב לחץ כניסה דרוש [בר] כדי לקבל לחץ יציאה מבוקש (באמצעות חיפוש נומרי)."""
    P_low = P_out_bar
    P_high = P_out_bar + 100.0
    # מציאת גבול עליון שבו לחץ היציאה המחושב מגיע לערך היעד או נמוך ממנו
    while True:
        P_out_test = calc_outlet_pressure(P_high, T_c, L_m, D_mm, Q_lpm, gas_type)
        if P_out_test <= P_out_bar or P_high >= P_out_bar + 2000:
            break
        P_high += 100.0
    # חיפוש בינארי להתכנסות ללחץ הנדרש
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
    """מחזירה רשימת מפרטי צינור אפשריים וצינור מומלץ, לפי קוטר פנימי [מ\"מ], לחץ [בר] וסוג הגז."""
    # טיפול מיוחד לחמצן (O2): מומלץ רק מפרט S14 ללא קשר לקוטר/לחץ
    if gas_type == "O2":
        return (["1\" tube (Spec S14) – (required for O2)"], "1\" tube (Spec S14)")
    possible = []
    recommended = None
    # בחירת קטגוריית צינור לפי הקוטר הפנימי הדרוש/נתון
    if D_mm <= 4.0:  # קטגוריית 1/4"
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
    elif D_mm <= 7.0:  # קטגוריית 3/8"
        if P_bar <= 140:
            possible = [
                "3/8\" tube (Spec S16) – rated up to 140 bar",
                "3/8\" tube (Spec S9) – rated for >140 bar"
            ]
            recommended = "3/8\" tube (Spec S16)"
        else:
            possible = ["3/8\" tube (Spec S9) – rated for >140 bar"]
            recommended = "3/8\" tube (Spec S9)"
    elif D_mm <= 21.0:  # קטגוריית 3/4" או 1"
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

# כותרת והסבר למשתמש (עברית עם מונחים טכניים באנגלית בהתאם לדרישות)
st.title("מחשבון זרימת גז בלחץ גבוה – Darcy–Weisbach")
st.markdown("""
אפליקציה אינטראקטיבית לחישובי **קוטר צינור**, **ספיקה**, **אורך צינור** ו**לחצים** עבור זרימת גז בלחץ גבוה, על בסיס משוואת **Darcy–Weisbach**.  
בחרו סוג הגז וסוג החישוב, הזינו את נתוני הקלט לפי הצורך (טמפרטורה, לחצי כניסה/יציאה, אורך, קוטר או ספיקה), ולחצו על **Calculate** לקבלת התוצאות.  
התוצאות כוללות את הערך המחושב, **המלצת צינור מתאימה** לתנאים שהוזנו, וכן **רשימת מפרטי צינורות אפשריים** (סדרת S) העומדים בדרישות הקוטר, הלחץ וסוג הגז שבחרתם.  
*הערה: מקדם החיכוך f קבוע בערך 0.02 בכל החישובים.*
""")

# בחירת סוג הגז (כולל "Air" ואפשרויות Forming Gas עם תיאור) וסוג החישוב
gas_type = st.selectbox("Gas type:", options=GAS_TYPES, format_func=lambda x: GAS_DISPLAY_NAMES[x])
calc_type = st.selectbox("Calculation type:", options=list(CALC_FIELDS.keys()), index=0)

# יצירת שדות קלט דינמיים בהתאם לסוג החישוב
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

# הצגת מקדם החיכוך (f) – קבוע, ללא אפשרות שינוי
st.caption(f"Friction factor (f) = {FRICTION_FACTOR:.2f} (fixed)")

# משתני מצב (Session State) לשימור התוצאה והרשימות בין ריצות מרובות
if "last_result" not in st.session_state:
    st.session_state.last_result = None
    st.session_state.last_is_error = False
    st.session_state.last_possible_pipes = None

# כפתור לחישוב התוצאה
if st.button("Calculate"):
    try:
        # קריאת ערכי הקלט מהשדות הדינמיים
        T_c = float(input_values.get("Temperature (°C)", 0.0))
        P_in = float(input_values.get("Inlet Pressure (bar)", 0.0))
        P_out = float(input_values.get("Outlet Pressure (bar)", 0.0))
        L_m = float(input_values.get("Pipe Length (m)", 0.0))
        D_mm = float(input_values.get("Pipe Diameter (mm)", 0.0))
        Q_lpm = float(input_values.get("Flow Rate (LPM)", 0.0))
        # אתחול משתנים לפלט
        result_text = ""
        possible_pipes_list = []
        # ביצוע החישוב התואם לסוג הנבחר
        if calc_type == "Pipe Diameter (mm)":
            D_required = calc_required_diameter(P_in, P_out, T_c, L_m, Q_lpm, gas_type)
            P_work = max(P_in, P_out)  # לחץ העבודה (הגבוה מבין הלחצים)
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
            P_work = P_in  # לחץ הכניסה הוא הגבוה בתרחיש זה
            possible_pipes_list, recommended_pipe = determine_pipe_options(D_mm, P_work, gas_type)
            result_text = f"**Estimated outlet pressure:** {P_out_est:.2f} bar  \n**Recommended pipe spec:** {recommended_pipe}"
        else:
            result_text = "Error: Unsupported calculation type."
            possible_pipes_list = []
        # שמירת התוצאה והרשימות במשתני מצב
        st.session_state.last_result = result_text
        st.session_state.last_is_error = False
        st.session_state.last_possible_pipes = possible_pipes_list
    except Exception as e:
        # טיפול בשגיאות – למשל, אם הלחץ נכנס קטן או שווה ללחץ יציאה, או קלט לא מספרי
        st.session_state.last_result = f"Error: {e}"
        st.session_state.last_is_error = True
        st.session_state.last_possible_pipes = None

# הצגת התוצאה והמלצות הצנרת, או הודעת שגיאה
if st.session_state.last_result is not None:
    if st.session_state.last_is_error:
        st.error(st.session_state.last_result)
    else:
        st.success(st.session_state.last_result)
        # הצגת רשימת כל מפרטי הצינור האפשריים התואמים לתנאים שהוזנו
        if st.session_state.last_possible_pipes:
            st.markdown("**Possible pipe specifications for these conditions:**")
            # הכנת נתונים לטבלה: עמודות עבור המפרט ותיאור הטווח/הערה
            table_data = []
            for spec_entry in st.session_state.last_possible_pipes:
                if "–" in spec_entry:
                    spec_name, spec_desc = spec_entry.split("–", 1)
                    table_data.append({"Pipe Spec": spec_name.strip(), "Pressure/Service": spec_desc.strip()})
                else:
                    table_data.append({"Pipe Spec": spec_entry, "Pressure/Service": ""})
            st.table(table_data)