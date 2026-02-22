import math
import tkinter as tk
from tkinter import ttk

# צבעי עיצוב לממשק (ערכת צבעים כהה ונעימה לעין)
BG_COLOR = "#2b2b2b"
FG_COLOR = "#FFFFFF"
ENTRY_BG = "#3c3f41"
HIGHLIGHT_COLOR = "#4e94ce"
FONT = ("Segoe UI", 10)

# רשימת סוגי הגזים בתפריט הבחירה
GAS_LIST = ["N2", "O2", "Ar", "CO2", "He", "H2", "CH4", "C2H2", "Forming Gas 1", "Forming Gas 2"]

# מיפוי סוגי החישוב לשדות הקלט הנדרשים עבור כל סוג
CALC_FIELDS = {
    "קוטר צינור (מ\"מ)": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "לחץ יציאה (בר)", "אורך צינור (מ')", "ספיקה (ליטר/דקה)"],
    "ספיקה (ליטר/דקה)": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "לחץ יציאה (בר)", "אורך צינור (מ')", "קוטר צינור (מ\"מ)"],
    "אורך צינור (מ')": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "לחץ יציאה (בר)", "קוטר צינור (מ\"מ)", "ספיקה (ליטר/דקה)"],
    "לחץ כניסה (בר)": ["טמפרטורה (°C)", "לחץ יציאה (בר)", "אורך צינור (מ')", "קוטר צינור (מ\"מ)", "ספיקה (ליטר/דקה)"],
    "לחץ יציאה (בר)": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "אורך צינור (מ')", "קוטר צינור (מ\"מ)", "ספיקה (ליטר/דקה)"]
}

# נתוני הגזים: משקל מולקולרי [ק"ג/מול] עבור כל גז
GAS_DATA = {
    "N2": 0.028013, "O2": 0.031999, "Ar": 0.039948, "CO2": 0.04401,
    "He": 0.0040026, "H2": 0.002016, "CH4": 0.01604, "C2H2": 0.02604,
    "Forming Gas 1": 0.0380, "Forming Gas 2": 0.0387
}

def ideal_gas_density(P_pa, T_k, gas_type):
    """מחזירה צפיפות הגז [ק"ג/מ^3] בלחץ P (פסקל) וטמפרטורה T (קלווין) לפי חוק הגז האידיאלי."""
    R = 8.314  # קבוע הגזים [J/(mol*K)]
    M = GAS_DATA.get(gas_type)
    if M is None:
        raise ValueError(f"לא נמצאו נתוני גז עבור סוג: {gas_type}")
    return (P_pa * M) / (R * T_k)

def calc_required_diameter(P_in_bar, P_out_bar, T_c, L_m, Q_lpm, gas_type, f=0.02):
    """חישוב קוטר פנימי דרוש [מ\"מ] לפי משוואת דארסי–וייסבאך."""
    # המרת יחידות קלט ל-SI
    P_in_pa = P_in_bar * 100000       # בר -> פסקל
    P_out_pa = P_out_bar * 100000     # בר -> פסקל
    T_k = T_c + 273.15                # צלזיוס -> קלווין
    Q_m3_s = Q_lpm / 1000.0 / 60.0    # ליטר/דקה -> מ^3/שניה
    # חישוב צפיפות ממוצעת לאורך הצינור
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    # הפרש לחצים (פסקל)
    delta_p = abs(P_in_pa - P_out_pa)
    if delta_p <= 0:
        raise ValueError("לחץ כניסה חייב להיות גבוה מלחץ יציאה בכדי שתתרחש זרימה.")
    # פתרון משוואת דארסי–וייסבאך עבור D (מטר) והמרה למילימטרים
    D_m = ((f * L_m * 8.0 * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * delta_p)) ** 0.2
    return D_m * 1000.0

def calc_flow_rate(P_in_bar, P_out_bar, T_c, L_m, D_mm, gas_type, f=0.02):
    """חישוב ספיקה מירבית [ליטר/דקה] בצינור נתון לפי משוואת דארסי–וייסבאך."""
    P_in_pa = P_in_bar * 100000
    P_out_pa = P_out_bar * 100000
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = abs(P_in_pa - P_out_pa)
    if delta_p <= 0:
        raise ValueError("לחץ כניסה חייב להיות גבוה מלחץ יציאה לצורך חישוב ספיקה.")
    Q_m3_s = math.sqrt((delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * f * L_m * rho_avg))
    return Q_m3_s * 1000.0 * 60.0

def calc_max_length(P_in_bar, P_out_bar, T_c, D_mm, Q_lpm, gas_type, f=0.02):
    """חישוב אורך צינור מקסימלי [מ'] לפי משוואת דארסי–וייסבאך."""
    P_in_pa = P_in_bar * 100000
    P_out_pa = P_out_bar * 100000
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = abs(P_in_pa - P_out_pa)
    if delta_p <= 0:
        raise ValueError("לחץ כניסה צריך להיות גדול מלחץ יציאה כדי שתהיה זרימה.")
    Q_m3_s = Q_lpm / 1000.0 / 60.0
    L_m = (delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * f * rho_avg * (Q_m3_s ** 2))
    return L_m

def calc_outlet_pressure(P_in_bar, T_c, L_m, D_mm, Q_lpm, gas_type, f=0.02):
    """אמידת לחץ יציאה [בר] על פי דארסי–וייסבאך (איטרציה)."""
    P_in_pa = P_in_bar * 100000
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    Q_m3_s = Q_lpm / 1000.0 / 60.0
    P_out_guess_bar = P_in_bar
    for _ in range(20):
        P_out_pa = P_out_guess_bar * 100000
        rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
        rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
        rho_avg = (rho_in + rho_out) / 2.0
        delta_p_calc = (8.0 * f * L_m * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * (D_m ** 5))
        P_out_calc_bar = P_in_bar - (delta_p_calc / 100000)
        if abs(P_out_calc_bar - P_out_guess_bar) < 0.001:
            return max(P_out_calc_bar, 0.0)
        P_out_guess_bar = P_out_calc_bar
    return max(P_out_guess_bar, 0.0)

def calc_required_inlet_pressure(P_out_bar, T_c, L_m, D_mm, Q_lpm, gas_type, f=0.02):
    """חישוב לחץ כניסה דרוש [בר] להשגת לחץ יציאה יעד (חישוב נומרי)."""
    P_low = P_out_bar
    P_high = P_out_bar + 100.0
    while True:
        P_out_test = calc_outlet_pressure(P_high, T_c, L_m, D_mm, Q_lpm, gas_type, f)
        if P_out_test <= P_out_bar or P_high >= P_out_bar + 2000:
            break
        P_high += 100.0
    for _ in range(50):
        P_mid = (P_low + P_high) / 2.0
        P_out_mid = calc_outlet_pressure(P_mid, T_c, L_m, D_mm, Q_lpm, gas_type, f)
        if abs(P_out_mid - P_out_bar) < 0.01:
            return P_mid
        if P_out_mid > P_out_bar:
            P_low = P_mid
        else:
            P_high = P_mid
    return (P_low + P_high) / 2.0

def recommend_pipe(D_mm, P_bar):
    """המלצה על צינור מתאים לפי גודל ולחץ (מפרטי S6/S9/S12/S15/S16)."""
    if D_mm <= 4.0:
        if P_bar <= 200:
            return "צינור 1/4 אינץ' (מפרט S6)"
        elif P_bar <= 1379:
            return "צינור 1/4 אינץ' (מפרט S9)"
        else:
            return "צינור 1/4 אינץ' (מפרט S12)"
    elif D_mm <= 7.0:
        if P_bar <= 140:
            return "צינור 3/8 אינץ' (מפרט S16)"
        else:
            return "צינור 3/8 אינץ' (מפרט S9)"
    elif D_mm <= 21.0:
        if P_bar <= 20:
            return "צינור 3/4 אינץ' (מפרט S15)"
        else:
            return "צינור 1 אינץ' (מפרט S14)"
    else:
        return "צנרת מיוחדת (מחוץ לטווח התקן)"

# יצירת חלון GUI ראשי
root = tk.Tk()
root.title("מחשבון זרימת גז בלחץ גבוה (Darcy–Weisbach)")
root.configure(bg=BG_COLOR)
root.geometry("600x600")

# תווית כותרת עליונה
title_label = tk.Label(root, text="מחשבון זרימת גז בלחץ גבוה", font=("Segoe UI", 14, "bold"),
                       bg=BG_COLOR, fg=FG_COLOR)
title_label.pack(pady=10)

# מסגרת לבחירת סוג הגז וסוג החישוב
menu_frame = tk.Frame(root, bg=BG_COLOR)
menu_frame.pack(pady=5, padx=10, fill=tk.X)
tk.Label(menu_frame, text="סוג הגז:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=0, sticky="w", pady=5)
gas_var = tk.StringVar(value=GAS_LIST[0])
gas_menu = ttk.Combobox(menu_frame, textvariable=gas_var, values=GAS_LIST, font=FONT, state="readonly")
gas_menu.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
tk.Label(menu_frame, text="סוג החישוב:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=1, column=0, sticky="w", pady=5)
calc_var = tk.StringVar(value=list(CALC_FIELDS.keys())[0])
calc_menu = ttk.Combobox(menu_frame, textvariable=calc_var, values=list(CALC_FIELDS.keys()), font=FONT, state="readonly")
calc_menu.grid(row=1, column=1, pady=5, padx=5, sticky="ew")

# מסגרת לשדות הקלט הדינמיים
input_frame = tk.Frame(root, bg=BG_COLOR)
input_frame.pack(pady=10, padx=10, fill=tk.X)
input_entries = {}

def update_fields(event=None):
    """עדכון שדות הקלט בהתאם לסוג החישוב שנבחר."""
    for widget in input_frame.winfo_children():
        widget.destroy()
    input_entries.clear()
    calc_type = calc_var.get()
    if calc_type:
        fields = CALC_FIELDS[calc_type]
        for idx, field in enumerate(fields):
            tk.Label(input_frame, text=field + ":", bg=BG_COLOR, fg=FG_COLOR, font=FONT)\
                .grid(row=idx, column=0, sticky="w", pady=3)
            entry = tk.Entry(input_frame, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR,
                             font=FONT, relief="flat")
            entry.grid(row=idx, column=1, pady=3, padx=5, sticky="ew")
            input_entries[field] = entry
        # שדה למקדם חיכוך f עם ערך ברירת-מחדל 0.02
        idx = len(fields)
        tk.Label(input_frame, text="מקדם חיכוך f:", bg=BG_COLOR, fg=FG_COLOR, font=FONT)\
            .grid(row=idx, column=0, sticky="w", pady=3)
        f_entry = tk.Entry(input_frame, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR,
                           font=FONT, relief="flat")
        f_entry.insert(0, "0.02")
        f_entry.grid(row=idx, column=1, pady=3, padx=5, sticky="ew")
        input_entries["מקדם חיכוך f"] = f_entry

calc_menu.bind("<<ComboboxSelected>>", update_fields)
update_fields()  # אתחול שדות הקלט עבור החישוב ההתחלתי

# תווית כותרת לתוצאה
result_title_label = tk.Label(root, text="תוצאה:", font=("Segoe UI", 12, "bold"),
                              bg=BG_COLOR, fg=FG_COLOR)
result_title_label.pack(pady=(10, 0))
# תווית להצגת תוצאת החישוב
result_var = tk.StringVar()
result_label = tk.Label(root, textvariable=result_var, bg=BG_COLOR, fg=FG_COLOR, font=("Segoe UI", 12))
result_label.pack(pady=(0, 15))

def on_calculate_click():
    """הופעל בעת לחיצה על 'חשב' – מבצע חישוב ומציג תוצאה."""
    calc_type = calc_var.get()
    gas = gas_var.get()
    try:
        # קליטת הנתונים מכל שדות הקלט
        inputs = {label: float(entry.get()) for label, entry in input_entries.items()}
        f_val = inputs.get("מקדם חיכוך f", 0.02)
        # ביצוע החישוב בהתאם לסוג שנבחר:
        if calc_type == "קוטר צינור (מ\"מ)":
            D_req = calc_required_diameter(inputs["לחץ כניסה (בר)"], inputs["לחץ יציאה (בר)"],
                                           inputs["טמפרטורה (°C)"], inputs["אורך צינור (מ')"],
                                           inputs["ספיקה (ליטר/דקה)"], gas, f=f_val)
            P_work = max(inputs["לחץ כניסה (בר)"], inputs["לחץ יציאה (בר)"])
            pipe = recommend_pipe(D_req, P_work)
            result_text = f"הקוטר הפנימי הנדרש: {D_req:.2f} מ\"מ.\nהצינור המומלץ: {pipe}."
        elif calc_type == "ספיקה (ליטר/דקה)":
            Q_max = calc_flow_rate(inputs["לחץ כניסה (בר)"], inputs["לחץ יציאה (בר)"],
                                   inputs["טמפרטורה (°C)"], inputs["אורך צינור (מ')"],
                                   inputs["קוטר צינור (מ\"מ)"], gas, f=f_val)
            P_work = max(inputs["לחץ כניסה (בר)"], inputs["לחץ יציאה (בר)"])
            pipe = recommend_pipe(inputs["קוטר צינור (מ\"מ)"], P_work)
            result_text = f"ספיקה מירבית: {Q_max:.1f} ליטר/דקה.\nצינור מתאים: {pipe}."
        elif calc_type == "אורך צינור (מ')":
            L_max = calc_max_length(inputs["לחץ כניסה (בר)"], inputs["לחץ יציאה (בר)"],
                                    inputs["טמפרטורה (°C)"], inputs["קוטר צינור (מ\"מ)"],
                                    inputs["ספיקה (ליטר/דקה)"], gas, f=f_val)
            P_work = max(inputs["לחץ כניסה (בר)"], inputs["לחץ יציאה (בר)"])
            pipe = recommend_pipe(inputs["קוטר צינור (מ\"מ)"], P_work)
            result_text = f"אורך צינור מקסימלי: {L_max:.1f} מ'.\nצינור מתאים: {pipe}."
        elif calc_type == "לחץ כניסה (בר)":
            P_in_req = calc_required_inlet_pressure(inputs["לחץ יציאה (בר)"], inputs["טמפרטורה (°C)"],
                                                    inputs["אורך צינור (מ')"], inputs["קוטר צינור (מ\"מ)"],
                                                    inputs["ספיקה (ליטר/דקה)"], gas, f=f_val)
            pipe = recommend_pipe(inputs["קוטר צינור (מ\"מ)"], P_in_req)
            result_text = f"לחץ כניסה דרוש: {P_in_req:.2f} בר.\nצינור מתאים: {pipe}."
        elif calc_type == "לחץ יציאה (בר)":
            P_out_calc = calc_outlet_pressure(inputs["לחץ כניסה (בר)"], inputs["טמפרטורה (°C)"],
                                              inputs["אורך צינור (מ')"], inputs["קוטר צינור (מ\"מ)"],
                                              inputs["ספיקה (ליטר/דקה)"], gas, f=f_val)
            pipe = recommend_pipe(inputs["קוטר צינור (מ\"מ)"], inputs["לחץ כניסה (בר)"])
            result_text = f"לחץ יציאה משוער: {P_out_calc:.2f} בר.\nצינור מתאים: {pipe}."
        else:
            result_text = "שגיאה: סוג חישוב לא נתמך."
    except Exception as e:
        result_text = f"שגיאה בחישוב: {e}"
    # הצגת התוצאה
    result_var.set(result_text)

# כפתור "חשב"
calc_button = tk.Button(root, text="חשב", command=on_calculate_click,
                        bg=HIGHLIGHT_COLOR, fg=FG_COLOR, font=FONT, relief="flat")
calc_button.pack(pady=5)

# הרצת לולאת האירועים של ה-GUI
root.mainloop()

import math
import tkinter as tk
from tkinter import ttk

# צבעי עיצוב לממשק (ערכת צבעים כהה ונעימה לעין)
BG_COLOR = "#2b2b2b"
FG_COLOR = "#FFFFFF"
ENTRY_BG = "#3c3f41"
HIGHLIGHT_COLOR = "#4e94ce"
FONT = ("Segoe UI", 10)

# רשימת סוגי הגזים בתפריט הבחירה
GAS_LIST = ["N2", "O2", "Ar", "CO2", "He", "H2", "CH4", "C2H2", "Forming Gas 1", "Forming Gas 2"]

# מיפוי סוגי החישוב לשדות הקלט הנדרשים עבור כל סוג
CALC_FIELDS = {
    "קוטר צינור (מ\"מ)": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "לחץ יציאה (בר)", "אורך צינור (מ')", "ספיקה (ליטר/דקה)"],
    "ספיקה (ליטר/דקה)": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "לחץ יציאה (בר)", "אורך צינור (מ')", "קוטר צינור (מ\"מ)"],
    "אורך צינור (מ')": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "לחץ יציאה (בר)", "קוטר צינור (מ\"מ)", "ספיקה (ליטר/דקה)"],
    "לחץ כניסה (בר)": ["טמפרטורה (°C)", "לחץ יציאה (בר)", "אורך צינור (מ')", "קוטר צינור (מ\"מ)", "ספיקה (ליטר/דקה)"],
    "לחץ יציאה (בר)": ["טמפרטורה (°C)", "לחץ כניסה (בר)", "אורך צינור (מ')", "קוטר צינור (מ\"מ)", "ספיקה (ליטר/דקה)"]
}

# נתוני הגזים: משקל מולקולרי [ק"ג/מול] עבור כל גז
GAS_DATA = {
    "N2": 0.028013, "O2": 0.031999, "Ar": 0.039948, "CO2": 0.04401,
    "He": 0.0040026, "H2": 0.002016, "CH4": 0.01604, "C2H2": 0.02604,
    "Forming Gas 1": 0.0380, "Forming Gas 2": 0.0387
}

def ideal_gas_density(P_pa, T_k, gas_type):
    """מחזירה צפיפות הגז [ק"ג/מ^3] בלחץ P (בפסקל) וטמפרטורה T (בקלווין) לפי חוק הגז האידיאלי."""
    R = 8.314  # קבוע הגזים [J/(mol*K)]
    M = GAS_DATA.get(gas_type)
    if M is None:
        raise ValueError(f"לא נמצאו נתוני גז עבור סוג: {gas_type}")
    return (P_pa * M) / (R * T_k)

def calc_required_diameter(P_in_bar, P_out_bar, T_c, L_m, Q_lpm, gas_type, f=0.02):
    """חישוב קוטר פנימי דרוש [מ\"מ] לפי משוואת דארסי–וייסבאך."""
    P_in_pa = P_in_bar * 100000       # בר -> פסקל
    P_out_pa = P_out_bar * 100000     # בר -> פסקל
    T_k = T_c + 273.15                # °C -> K
    Q_m3_s = Q_lpm / 1000.0 / 60.0    # ליטר/דקה -> מ^3/שניה
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = abs(P_in_pa - P_out_pa)
    if delta_p <= 0:
        raise ValueError("לחץ כניסה חייב להיות גבוה מלחץ יציאה בכדי שתתרחש זרימה.")
    D_m = ((f * L_m * 8.0 * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * delta_p)) ** 0.2
    return D_m * 1000.0

def calc_flow_rate(P_in_bar, P_out_bar, T_c, L_m, D_mm, gas_type, f=0.02):
    """חישוב ספיקה מירבית [ליטר/דקה] בצינור נתון לפי דארסי–וייסבאך."""
    P_in_pa = P_in_bar * 100000
    P_out_pa = P_out_bar * 100000
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = abs(P_in_pa - P_out_pa)
    if delta_p <= 0:
        raise ValueError("לחץ כניסה חייב להיות גבוה מלחץ יציאה לצורך חישוב ספיקה.")
    Q_m3_s = math.sqrt((delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * f * L_m * rho_avg))
    return Q_m3_s * 1000.0 * 60.0

def calc_max_length(P_in_bar, P_out_bar, T_c, D_mm, Q_lpm, gas_type, f=0.02):
    """חישוב אורך צינור מקסימלי [מ'] לפי משוואת דארסי–וייסבאך."""
    P_in_pa = P_in_bar * 100000
    P_out_pa = P_out_bar * 100000
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
    rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
    rho_avg = (rho_in + rho_out) / 2.0
    delta_p = abs(P_in_pa - P_out_pa)
    if delta_p <= 0:
        raise ValueError("לחץ כניסה צריך להיות גבוה מלחץ יציאה כדי שתתקבל זרימה.")
    Q_m3_s = Q_lpm / 1000.0 / 60.0
    L_m = (delta_p * (math.pi ** 2) * (D_m ** 5)) / (8.0 * f * rho_avg * (Q_m3_s ** 2))
    return L_m

def calc_outlet_pressure(P_in_bar, T_c, L_m, D_mm, Q_lpm, gas_type, f=0.02):
    """אמידת לחץ יציאה [בר] לפי דארסי–וייסבאך (באמצעות איטרציה)."""
    P_in_pa = P_in_bar * 100000
    T_k = T_c + 273.15
    D_m = D_mm / 1000.0
    Q_m3_s = Q_lpm / 1000.0 / 60.0
    P_out_guess_bar = P_in_bar
    for _ in range(20):
        P_out_pa = P_out_guess_bar * 100000
        rho_in = ideal_gas_density(P_in_pa, T_k, gas_type)
        rho_out = ideal_gas_density(P_out_pa, T_k, gas_type)
        rho_avg = (rho_in + rho_out) / 2.0
        delta_p_calc = (8.0 * f * L_m * rho_avg * (Q_m3_s ** 2)) / ((math.pi ** 2) * (D_m ** 5))
        P_out_calc_bar = P_in_bar - (delta_p_calc / 100000)
        if abs(P_out_calc_bar - P_out_guess_bar) < 0.001:
            return max(P_out_calc_bar, 0.0)
        P_out_guess_bar = P_out_calc_bar
    return max(P_out_guess_bar, 0.0)

def calc_required_inlet_pressure(P_out_bar, T_c, L_m, D_mm, Q_lpm, gas_type, f=0.02):
    """חישוב לחץ כניסה דרוש [בר] להשגת לחץ יציאה יעד (פתרון נומרי)."""
    P_low = P_out_bar
    P_high = P_out_bar + 100.0
    # מציאת גבול עליון שבו לחץ היציאה המחושב מגיע אל/מתחת ליעד
    while True:
        P_out_test = calc_outlet_pressure(P_high, T_c, L_m, D_mm, Q_lpm, gas_type, f)
        if P_out_test <= P_out_bar or P_high >= P_out_bar + 2000:
            break
        P_high += 100.0
    # חיפוש בינארי בין הגבולות
    for _ in range(50):
        P_mid = (P_low + P_high) / 2.0
        P_out_mid = calc_outlet_pressure(P_mid, T_c, L_m, D_mm, Q_lpm, gas_type, f)
        if abs(P_out_mid - P_out_bar) < 0.01:
            return P_mid
        if P_out_mid > P_out_bar:
            P_low = P_mid
        else:
            P_high = P_mid
    return (P_low + P_high) / 2.0

def recommend_pipe(D_mm, P_bar):
    """המלצה על צינור מתאים לפי קוטר מחושב ולחץ עבודה (בהתאם למפרטי צנרת)."""
    if D_mm <= 4.0:
        if P_bar <= 200:
            return "צינור 1/4 אינץ' (מפרט S6)"
        elif P_bar <= 1379:  # 1379 בר ≈ 20,000 PSI
            return "צינור 1/4 אינץ' (מפרט S9)"
        else:
            return "צינור 1/4 אינץ' (מפרט S12)"
    elif D_mm <= 7.0:
        if P_bar <= 140:
            return "צינור 3/8 אינץ' (מפרט S16)"
        else:
            return "צינור 3/8 אינץ' (מפרט S9)"
    elif D_mm <= 21.0:
        if P_bar <= 20:
            return "צינור 3/4 אינץ' (מפרט S15)"
        else:
            return "צינור 1 אינץ' (מפרט S14)"
    else:
        return "צנרת מיוחדת (מחוץ לטווח התקן)"

# יצירת חלון ראשי של האפליקציה
root = tk.Tk()
root.title("מחשבון זרימת גז בלחץ גבוה – Darcy–Weisbach")
root.configure(bg=BG_COLOR)
root.geometry("600x600")

# כותרת עליונה
title_label = tk.Label(root, text="מחשבון זרימת גז בלחץ גבוה", font=("Segoe UI", 14, "bold"),
                       bg=BG_COLOR, fg=FG_COLOR)
title_label.pack(pady=10)

# מסגרת בחירה: סוג גז וסוג חישוב
menu_frame = tk.Frame(root, bg=BG_COLOR)
menu_frame.pack(pady=5, padx=10, fill=tk.X)
tk.Label(menu_frame, text="סוג הגז:", bg=BG_COLOR, fg=FG_COLOR, font=FONT)\
    .grid(row=0, column=0, sticky="w", pady=5)
gas_var = tk.StringVar(value=GAS_LIST[0])
gas_menu = ttk.Combobox(menu_frame, textvariable=gas_var, values=GAS_LIST, font=FONT, state="readonly")
gas_menu.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
tk.Label(menu_frame, text="סוג החישוב:", bg=BG_COLOR, fg=FG_COLOR, font=FONT)\
    .grid(row=1, column=0, sticky="w", pady=5)
calc_var = tk.StringVar(value=list(CALC_FIELDS.keys())[0])
calc_menu = ttk.Combobox(menu_frame, textvariable=calc_var, values=list(CALC_FIELDS.keys()), font=FONT, state="readonly")
calc_menu.grid(row=1, column=1, pady=5, padx=5, sticky="ew")

# מסגרת לשדות הקלט
input_frame = tk.Frame(root, bg=BG_COLOR)
input_frame.pack(pady=10, padx=10, fill=tk.X)
input_entries = {}

def update_fields(event=None):
    """עדכון השדות בהתאם לסוג החישוב הנבחר."""
    for widget in input_frame.winfo_children():
        widget.destroy()
    input_entries.clear()
    calc_type = calc_var.get()
    if calc_type:
        fields = CALC_FIELDS[calc_type]
        for idx, field in enumerate(fields):
            tk.Label(input_frame, text=field + ":", bg=BG_COLOR, fg=FG_COLOR, font=FONT)\
                .grid(row=idx, column=0, sticky="w", pady=3)
            entry = tk.Entry(input_frame, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR,
                             font=FONT, relief="flat")
            entry.grid(row=idx, column=1, pady=3, padx=5, sticky="ew")
            input_entries[field] = entry
        # הוספת שדה למקדם חיכוך f (ברירת מחדל 0.02)
        idx = len(fields)
        tk.Label(input_frame, text="מקדם חיכוך f:", bg=BG_COLOR, fg=FG_COLOR, font=FONT)\
            .grid(row=idx, column=0, sticky="w", pady=3)
        f_entry = tk.Entry(input_frame, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR,
                           font=FONT, relief="flat")
        f_entry.insert(0, "0.02")
        f_entry.grid(row=idx, column=1, pady=3, padx=5, sticky="ew")
        input_entries["מקדם חיכוך f"] = f_entry

calc_menu.bind("<<ComboboxSelected>>", update_fields)
update_fields()  # אתחול שדות הקלט עבור סוג החישוב המוגדר כברירת מחדל

# כותרת לתוצאת החישוב
result_title_label = tk.Label(root, text="תוצאה:", font=("Segoe UI", 12, "bold"),
                              bg=BG_COLOR, fg=FG_COLOR)
result_title_label.pack(pady=(10, 0))
# תווית תוצאה, להצגת תוצאת החישוב וההמלצה
result_var = tk.StringVar()
result_label = tk.Label(root, textvariable=result_var, bg=BG_COLOR, fg=FG_COLOR, font=("Segoe UI", 12))
result_label.pack(pady=(0, 15))

def on_calculate_click():
    """קולט נתונים, מבצע חישוב ומעדכן את תוצאת החישוב."""
    calc_type = calc_var.get()
    gas = gas_var.get()
    try:
        data = {label: float(entry.get()) for label, entry in input_entries.items()}
        f_val = data.get("מקדם חיכוך f", 0.02)
        if calc_type == "קוטר צינור (מ\"מ)":
            D_req = calc_required_diameter(data["לחץ כניסה (בר)"], data["לחץ יציאה (בר)"],
                                           data["טמפרטורה (°C)"], data["אורך צינור (מ')"],
                                           data["ספיקה (ליטר/דקה)"], gas, f=f_val)
            P_work = max(data["לחץ כניסה (בר)"], data["לחץ יציאה (בר)"])
            pipe = recommend_pipe(D_req, P_work)
            result_text = f"הקוטר הפנימי הנדרש: {D_req:.2f} מ\"מ.\nהצינור המומלץ: {pipe}."
        elif calc_type == "ספיקה (ליטר/דקה)":
            Q_max = calc_flow_rate(data["לחץ כניסה (בר)"], data["לחץ יציאה (בר)"],
                                   data["טמפרטורה (°C)"], data["אורך צינור (מ')"],
                                   data["קוטר צינור (מ\"מ)"], gas, f=f_val)
            P_work = max(data["לחץ כניסה (בר)"], data["לחץ יציאה (בר)"])
            pipe = recommend_pipe(data["קוטר צינור (מ\"מ)"], P_work)
            result_text = f"ספיקה מירבית: {Q_max:.1f} ליטר/דקה.\nצינור מתאים: {pipe}."
        elif calc_type == "אורך צינור (מ')":
            L_max = calc_max_length(data["לחץ כניסה (בר)"], data["לחץ יציאה (בר)"],
                                    data["טמפרטורה (°C)"], data["קוטר צינור (מ\"מ)"],
                                    data["ספיקה (ליטר/דקה)"], gas, f=f_val)
            P_work = max(data["לחץ כניסה (בר)"], data["לחץ יציאה (בר)"])
            pipe = recommend_pipe(data["קוטר צינור (מ\"מ)"], P_work)
            result_text = f"אורך צינור מקסימלי: {L_max:.1f} מ'.\nצינור מתאים: {pipe}."
        elif calc_type == "לחץ כניסה (בר)":
            P_in_req = calc_required_inlet_pressure(data["לחץ יציאה (בר)"], data["טמפרטורה (°C)"],
                                                    data["אורך צינור (מ')"], data["קוטר צינור (מ\"מ)"],
                                                    data["ספיקה (ליטר/דקה)"], gas, f=f_val)
            pipe = recommend_pipe(data["קוטר צינור (מ\"מ)"], P_in_req)
            result_text = f"לחץ כניסה דרוש: {P_in_req:.2f} בר.\nצינור מתאים: {pipe}."
        elif calc_type == "לחץ יציאה (בר)":
            P_out_calc = calc_outlet_pressure(data["לחץ כניסה (בר)"], data["טמפרטורה (°C)"],
                                              data["אורך צינור (מ')"], data["קוטר צינור (מ\"מ)"],
                                              data["ספיקה (ליטר/דקה)"], gas, f=f_val)
            pipe = recommend_pipe(data["קוטר צינור (מ\"מ)"], data["לחץ כניסה (בר)"])
            result_text = f"לחץ יציאה משוער: {P_out_calc:.2f} בר.\nצינור מתאים: {pipe}."
        else:
            result_text = "שגיאה: סוג חישוב לא נתמך."
    except Exception as e:
        result_text = f"שגיאה בחישוב: {e}"
    result_var.set(result_text)

# כפתור "חשב" לביצוע החישוב
calc_button = tk.Button(root, text="חשב", command=on_calculate_click,
                        bg=HIGHLIGHT_COLOR, fg=FG_COLOR, font=FONT, relief="flat")
calc_button.pack(pady=5)

root.mainloop()