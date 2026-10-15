import streamlit as st
import swisseph as swe
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="Vedic Astrology & Backtesting Toolkit", layout="wide", page_icon="✨")

# 1. Setup Swiss Ephemeris for Lahiri Ayanamsa (Vedic)
swe.set_sid_mode(swe.SIDM_LAHIRI)

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
    "Uranus": swe.URANUS,
    "Herschel": swe.URANUS, # Alias for Uranus
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO
}

RASHIS = [
    "Mesha (Aries)", "Vrishabha (Taurus)", "Mithuna (Gemini)", "Karka (Cancer)",
    "Simha (Leo)", "Kanya (Virgo)", "Tula (Libra)", "Vrishchika (Scorpio)",
    "Dhanu (Sagittarius)", "Makara (Capricorn)", "Kumbha (Aquarius)", "Meena (Pisces)"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

ASSET_TICKERS = {
    "Sensex (₹ INR)": "^BSESN",
    "Gold ($ USD)": "GC=F",
    "Silver ($ USD)": "SI=F",
    "Copper ($ USD)": "HG=F",
    "Crude Oil ($ USD)": "CL=F"
}

@st.cache_data(ttl=86400)
def fetch_single_asset_series(ticker):
    """Safely fetch historical prices for a single ticker."""
    try:
        df = yf.download(ticker, start="1970-01-01", progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df['Close']
    except Exception:
        return None

def get_price_window_for_date(target_date_str, days_window=10):
    """Fetches ± N days price window for all assets around target date."""
    target_dt = pd.to_datetime(target_date_str)
    date_range = pd.date_range(target_dt - timedelta(days=days_window), target_dt + timedelta(days=days_window), freq='D')
    
    window_rows = []
    histories = {name: fetch_single_asset_series(ticker) for name, ticker in ASSET_TICKERS.items()}

    for d in date_range:
        row = {
            "Date": d.strftime("%Y-%m-%d"), 
            "Offset (Days)": (d.normalize() - target_dt.normalize()).days
        }
        for name, series in histories.items():
            if series is not None and not series.empty:
                try:
                    idx = series.index.get_indexer([d], method='nearest')[0]
                    val = series.iloc[idx]
                    row[name] = round(float(val), 2)
                except Exception:
                    row[name] = None
            else:
                row[name] = None
        window_rows.append(row)
        
    return pd.DataFrame(window_rows)

def calculate_vedic_details(lon):
    rashi_idx = int(lon / 30) % 12
    rashi_name = RASHIS[rashi_idx]
    rashi_deg = lon % 30
    
    deg = int(rashi_deg)
    minute = int((rashi_deg - deg) * 60)
    sec = int((((rashi_deg - deg) * 60) - minute) * 60)
    formatted_deg = f"{deg}° {minute}' {sec}\""

    nak_span = 360.0 / 27.0
    nak_idx = int(lon / nak_span) % 27
    nak_name = NAKSHATRAS[nak_idx]
    
    remainder_in_nak = lon % nak_span
    pada = int(remainder_in_nak / (nak_span / 4.0)) + 1

    return formatted_deg, rashi_name, nak_name, pada

def get_sidereal_lon(jd, planet_name):
    if planet_name == "Ketu":
        calc_result = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SIDEREAL)
        rahu_lon = calc_result[0][0]
        return (rahu_lon + 180.0) % 360.0
    else:
        p_id = PLANETS[planet_name]
        calc_result = swe.calc_ut(jd, p_id, swe.FLG_SIDEREAL)
        return calc_result[0][0]

def get_rashi_index(lon):
    return int(lon / 30) % 12

def get_yoga_type(rashi_a, rashi_b):
    """Calculates house distance yoga between two Rashi indices (0-11)."""
    diff = (rashi_b - rashi_a) % 12
    if diff == 0:
        return "1/1 (Samyuti / Conjunction)"
    elif diff == 6:
        return "1/7 (Saptama / Opposition)"
    elif diff in [3, 9]:
        return "4/10 (Kendra / Quadrant)"
    elif diff in [1, 11]:
        return "2/12 (Dwirdwadasa)"
    elif diff in [5, 7]:
        return "6/8 (Shashtashtaka)"
    elif diff in [2, 10]:
        return "3/11 (Sahaj / Labh)"
    elif diff in [4, 8]:
        return "5/9 (Trikona)"
    return None

# --- Modal Dialog Function ---
@st.dialog("📊 Global Asset Price Inspector (±10 Days)", width="large")
def render_price_modal(event_dict):
    st.markdown(f"### Event: **{event_dict.get('Source', event_dict.get('Planet', ''))}** & **{event_dict.get('Destination', '')}** — *{event_dict.get('Yoga', event_dict.get('Rashi', ''))}*")
    st.write(f"**Period Range:** `{event_dict.get('Start Date')}` to `{event_dict.get('End Date')}`")
    st.info("📌 **Currencies:** Sensex in **Indian Rupees (₹ INR)** | Gold, Silver, Copper, Crude Oil in **US Dollars ($ USD)**")
    
    start_date = event_dict.get('Start Date')
    
    with st.spinner(f"Fetching global asset prices around {start_date}..."):
        df_prices = get_price_window_for_date(start_date, days_window=10)
        
    st.dataframe(df_prices, use_container_width=True, hide_index=True)
    
    st.markdown("#### Quick Trend View")
    asset_to_chart = st.selectbox("Select Asset to Chart", list(ASSET_TICKERS.keys()))
    if asset_to_chart in df_prices.columns:
        chart_data = df_prices.set_index("Date")[[asset_to_chart]].dropna()
        st.line_chart(chart_data)

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("✨ Vedic Toolkit")
nav_option = st.sidebar.radio(
    "Navigation Menu",
    [
        "📅 Daily Calculator", 
        "🔍 Historical Transit Finder", 
        "🔥 Combust / Retrograde Finder",
        "✨ Planetary Yoga Matrix",
        "🔄 Planets Relation Backtester"
    ]
)
st.sidebar.divider()

ALL_PLANET_NAMES = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", 
    "Rahu", "Ketu", "Uranus", "Herschel", "Neptune", "Pluto"
]

YOGA_OPTIONS = [
    "1/7 (Saptama / Opposition)",
    "4/10 (Kendra / Quadrant)",
    "2/12 (Dwirdwadasa)",
    "6/8 (Shashtashtaka)",
    "3/11 (Sahaj / Labh)",
    "5/9 (Trikona)",
    "1/1 (Samyuti / Conjunction)"
]

# ==========================================
# VIEW 1: DAILY CALCULATOR
# ==========================================
if nav_option == "📅 Daily Calculator":
    st.title("📅 Daily Planetary Position Calculator")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        selected_date = st.date_input("Select Date", value=datetime.today())
    with col_c2:
        selected_planet = st.selectbox(
            "Select Planet View", 
            ["ALL"] + ALL_PLANET_NAMES
        )

    jd = swe.julday(selected_date.year, selected_date.month, selected_date.day, 12.0)
    
    unique_daily_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Uranus", "Neptune", "Pluto"]
    data = []
    jd_next = jd + 1.0
    for name in unique_daily_planets:
        lon = get_sidereal_lon(jd, name)
        lon_next = get_sidereal_lon(jd_next, name)
        delta = (lon_next - lon + 360.0) % 360.0
        is_retro = delta > 180.0
        if name in ["Sun", "Moon"]: 
            is_retro = False
        rel_deg, rashi, nak, pada = calculate_vedic_details(lon)
        data.append({
            "Planet": name, 
            "Degree in Sign": rel_deg, 
            "Rashi (Sign)": rashi, 
            "Nakshatra": nak, 
            "Pada": pada, 
            "Absolute Lon": round(lon, 2), 
            "Motion": "Retrograde (R)" if is_retro else "Direct"
        })
    
    ketu_lon = get_sidereal_lon(jd, "Ketu")
    k_deg, k_rashi, k_nak, k_pada = calculate_vedic_details(ketu_lon)
    data.append({
        "Planet": "Ketu", 
        "Degree in Sign": k_deg, 
        "Rashi (Sign)": k_rashi, 
        "Nakshatra": k_nak, 
        "Pada": k_pada, 
        "Absolute Lon": round(ketu_lon, 2), 
        "Motion": "Retrograde (R)"
    })
    df_planets = pd.DataFrame(data)

    st.subheader(f"Planetary Positions for: {selected_date.strftime('%d %B %Y')}")
    if selected_planet == "ALL":
        st.dataframe(df_planets, use_container_width=True, hide_index=True)
    else:
        search_target = "Uranus" if selected_planet == "Herschel" else selected_planet
        row = df_planets[df_planets["Planet"] == search_target].iloc[0]
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            st.metric(label="Planet", value=selected_planet)
            st.metric(label="Motion", value=row["Motion"])
        with mcol2:
            st.metric(label="Rashi (Zodiac Sign)", value=row["Rashi (Sign)"])
            st.metric(label="Degree in Sign", value=row["Degree in Sign"])
        with mcol3:
            st.metric(label="Nakshatra", value=row["Nakshatra"])
            st.metric(label="Absolute Longitude", value=f"{row['Absolute Lon']}°")

# ==========================================
# VIEW 2: HISTORICAL TRANSIT FINDER
# ==========================================
elif nav_option == "🔍 Historical Transit Finder":
    st.title("🔍 Transit Range Backtester")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        search_planet = st.selectbox("Search Planet", ALL_PLANET_NAMES)
    with col_f2:
        search_rashi = st.selectbox("Search Rashi", RASHIS)
    with col_f3:
        search_nakshatra = st.selectbox("Search Nakshatra (Optional)", ["Any Nakshatra"] + NAKSHATRAS)
    with col_f4:
        time_horizon = st.selectbox("Time Horizon", ["Past 50 Years", "Next 2 Years (Future)"])

    if st.button("Find Transits", type="primary"):
        with st.spinner("Scanning ephemeris date ranges... Please wait."):
            end_date = datetime.today() + timedelta(days=2 * 365) if "Future" in time_horizon else datetime.today()
            start_date = datetime.today() if "Future" in time_horizon else end_date - timedelta(days=50 * 365)
            
            results = []
            curr_date = start_date
            in_range = False
            r_start, r_end, r_rashi, r_nak = None, None, "", ""
            
            while curr_date <= end_date:
                jd_scan = swe.julday(curr_date.year, curr_date.month, curr_date.day, 12.0)
                lon = get_sidereal_lon(jd_scan, search_planet)
                _, rashi_name, nak_name, pada = calculate_vedic_details(lon)
                
                matched = (rashi_name == search_rashi) and (True if search_nakshatra == "Any Nakshatra" else nak_name == search_nakshatra)
                
                if matched:
                    if not in_range:
                        in_range = True
                        r_start = curr_date
                        r_rashi = rashi_name
                        r_nak = f"{nak_name} (Pada {pada})"
                    r_end = curr_date
                else:
                    if in_range:
                        results.append({
                            "Start Date": r_start.strftime("%Y-%m-%d"),
                            "End Date": r_end.strftime("%Y-%m-%d"),
                            "Year": r_start.year,
                            "Planet": search_planet,
                            "Rashi": r_rashi,
                            "Nakshatra": r_nak
                        })
                        in_range = False
                curr_date += timedelta(days=1)
                
            if in_range and r_start is not None:
                results.append({
                    "Start Date": r_start.strftime("%Y-%m-%d"),
                    "End Date": r_end.strftime("%Y-%m-%d"),
                    "Year": r_start.year,
                    "Planet": search_planet,
                    "Rashi": r_rashi,
                    "Nakshatra": r_nak
                })

            if results:
                st.session_state.transit_results = results
            else:
                st.session_state.transit_results = None

    if "transit_results" in st.session_state and st.session_state.transit_results:
        results = st.session_state.transit_results
        df_results = pd.DataFrame(results).sort_values(by="Start Date", ascending=False)
        st.success(f"Found {len(df_results)} matching transit periods! **Check/select any row** in the table below to open the price inspector.")
        
        event = st.dataframe(
            df_results, 
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if event and event.selection.get("rows"):
            selected_row_idx = event.selection["rows"][0]
            selected_event = df_results.iloc[selected_row_idx].to_dict()
            render_price_modal(selected_event)

# ==========================================
# VIEW 3: COMBUST / RETROGRADE FINDER
# ==========================================
elif nav_option == "🔥 Combust / Retrograde Finder":
    st.title("🔥 Combust & Retrograde Backtester")

    cr_col1, cr_col2, cr_col3 = st.columns(3)
    with cr_col1:
        cr_planet = st.selectbox("Select Planet", ["Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Uranus", "Herschel", "Neptune", "Pluto"])
    with cr_col2:
        cr_status = st.selectbox("Select Status", ["Retrograde", "Combust"])
    with cr_col3:
        cr_horizon = st.selectbox("Time Horizon", ["Past 50 Years", "Next 2 Years (Future)"])

    if st.button("Scan Ranges", type="primary"):
        with st.spinner(f"Scanning data for {cr_planet} ({cr_status})... Please wait."):
            end_date = datetime.today() + timedelta(days=2 * 365) if "Future" in cr_horizon else datetime.today()
            start_date = datetime.today() if "Future" in cr_horizon else end_date - timedelta(days=50 * 365)
            
            results = []
            curr_date = start_date
            in_range = False
            r_start, r_end, r_rashi, r_nak, r_details = None, None, "", "", ""
            
            while curr_date <= end_date:
                jd_scan = swe.julday(curr_date.year, curr_date.month, curr_date.day, 12.0)
                jd_next = jd_scan + 1.0
                
                p_lon = get_sidereal_lon(jd_scan, cr_planet)
                p_lon_next = get_sidereal_lon(jd_next, cr_planet)
                
                delta = (p_lon_next - p_lon + 360.0) % 360.0
                is_retro = delta > 180.0
                
                matched = False
                detail_note = ""
                
                if cr_status == "Retrograde":
                    if is_retro:
                        matched = True
                        detail_note = "Retrograde (Vakra)"
                elif cr_status == "Combust":
                    sun_lon = get_sidereal_lon(jd_scan, "Sun")
                    diff = abs(sun_lon - p_lon)
                    if diff > 180: 
                        diff = 360 - diff
                    
                    if cr_planet == "Venus":
                        limit = 8.0 if is_retro else 10.0
                    elif cr_planet == "Mercury":
                        limit = 12.0 if is_retro else 14.0
                    elif cr_planet == "Mars":
                        limit = 17.0
                    elif cr_planet == "Jupiter":
                        limit = 11.0
                    elif cr_planet == "Saturn":
                        limit = 15.0
                    else:
                        limit = 10.0
                        
                    if diff <= limit:
                        matched = True
                        detail_note = f"Sun-Dist: {diff:.2f}°"
                
                if matched:
                    _, rashi_name, nak_name, _ = calculate_vedic_details(p_lon)
                    if not in_range:
                        in_range = True
                        r_start = curr_date
                        r_rashi = rashi_name
                        r_nak = nak_name
                        r_details = detail_note
                    r_end = curr_date
                else:
                    if in_range:
                        results.append({
                            "Start Date": r_start.strftime("%Y-%m-%d"),
                            "End Date": r_end.strftime("%Y-%m-%d"),
                            "Year": r_start.year,
                            "Planet": cr_planet,
                            "Status": cr_status,
                            "Rashi": r_rashi,
                            "Nakshatra": r_nak,
                            "Details": r_details
                        })
                        in_range = False
                curr_date += timedelta(days=1)
                
            if in_range and r_start is not None:
                results.append({
                    "Start Date": r_start.strftime("%Y-%m-%d"),
                    "End Date": r_end.strftime("%Y-%m-%d"),
                    "Year": r_start.year,
                    "Planet": cr_planet,
                    "Status": cr_status,
                    "Rashi": r_rashi,
                    "Nakshatra": r_nak,
                    "Details": r_details
                })

            if results:
                st.session_state.cr_results = results
            else:
                st.session_state.cr_results = None

    if "cr_results" in st.session_state and st.session_state.cr_results:
        results = st.session_state.cr_results
        df_cr_results = pd.DataFrame(results).sort_values(by="Start Date", ascending=False)
        st.success(f"Found {len(df_cr_results)} matching ranges! **Check/select any row** in the table below to open the price inspector.")
        
        event = st.dataframe(
            df_cr_results, 
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if event and event.selection.get("rows"):
            selected_row_idx = event.selection["rows"][0]
            selected_event = df_cr_results.iloc[selected_row_idx].to_dict()
            render_price_modal(selected_event)

# ==========================================
# VIEW 4: PLANETARY YOGA MATRIX
# ==========================================
elif nav_option == "✨ Planetary Yoga Matrix":
    st.title("✨ Planetary Yoga Matrix (1/7, 4/10, 2/12, 6/8, 3/11, 5/9)")
    st.write("Scan all active planet-to-planet yoga configurations for a selected date and frequency horizon.")

    ym_col1, ym_col2 = st.columns(2)
    with ym_col1:
        ym_date = st.date_input("Target Date", value=datetime.today())
    with ym_col2:
        ym_freq = st.selectbox("Scan Horizon / Interval", ["Daily View", "Weekly Snapshot", "Monthly Snapshot", "Yearly Snapshot"])

    if st.button("Generate Yoga Matrix", type="primary"):
        with st.spinner("Analyzing planetary angular relationships..."):
            base_dt = datetime(ym_date.year, ym_date.month, ym_date.day)
            
            if "Daily" in ym_freq:
                dates_to_check = [base_dt]
            elif "Weekly" in ym_freq:
                dates_to_check = [base_dt + timedelta(days=i*7) for i in range(5)]
            elif "Monthly" in ym_freq:
                dates_to_check = [base_dt + timedelta(days=i*30) for i in range(6)]
            else:
                dates_to_check = [base_dt + timedelta(days=i*365) for i in range(3)]

            all_yoga_records = []
            matrix_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu", "Uranus", "Neptune", "Pluto"]
            
            for dt in dates_to_check:
                jd_scan = swe.julday(dt.year, dt.month, dt.day, 12.0)
                
                positions = {}
                for p in matrix_planets:
                    lon = get_sidereal_lon(jd_scan, p)
                    positions[p] = {
                        "lon": lon,
                        "rashi_idx": get_rashi_index(lon),
                        "rashi_name": calculate_vedic_details(lon)[1]
                    }
                
                checked_pairs = set()
                for p1 in matrix_planets:
                    for p2 in matrix_planets:
                        if p1 == p2:
                            continue
                        pair_key = tuple(sorted([p1, p2]))
                        if pair_key in checked_pairs:
                            continue
                        checked_pairs.add(pair_key)
                        
                        r1 = positions[p1]["rashi_idx"]
                        r2 = positions[p2]["rashi_idx"]
                        
                        yoga = get_yoga_type(r1, r2)
                        if yoga:
                            all_yoga_records.append({
                                "Date": dt.strftime("%Y-%m-%d"),
                                "Planet A": p1,
                                "Sign A": positions[p1]["rashi_name"],
                                "Planet B": p2,
                                "Sign B": positions[p2]["rashi_name"],
                                "Yoga Relationship": yoga
                            })

            if all_yoga_records:
                df_yoga = pd.DataFrame(all_yoga_records)
                st.success(f"Found {len(df_yoga)} active yoga relationships!")
                st.dataframe(df_yoga, use_container_width=True, hide_index=True)
            else:
                st.warning("No significant yoga relationships found for this window.")

# ==========================================
# VIEW 5: PLANETS RELATION BACKTESTER
# ==========================================
elif nav_option == "🔄 Planets Relation Backtester":
    st.title("🔄 Planets Relation Backtester (50Y / 2Y)")
    st.write("Scan historical or future date ranges when a **Source Planet** and **Destination Planet** formed a specific yoga (1/7, 4/10, 2/12, 6/8, 3/11, 5/9).")

    pr_col1, pr_col2, pr_col3, pr_col4 = st.columns(4)
    with pr_col1:
        source_planet = st.selectbox("Source Planet", ALL_PLANET_NAMES, index=4)
    with pr_col2:
        dest_planet = st.selectbox("Destination Planet", ALL_PLANET_NAMES, index=6)
    with pr_col3:
        target_yoga = st.selectbox("Select Yoga", YOGA_OPTIONS)
    with pr_col4:
        pr_horizon = st.selectbox("Time Horizon", ["Past 50 Years", "Next 2 Years (Future)"], key="pr_horiz")

    if st.button("Scan Planet Relations", type="primary"):
        if source_planet == dest_planet:
            st.error("Source and Destination planets cannot be the same!")
        else:
            with st.spinner(f"Scanning relations between {source_planet} and {dest_planet} ({target_yoga})... Please wait."):
                end_date = datetime.today() + timedelta(days=2 * 365) if "Future" in pr_horizon else datetime.today()
                start_date = datetime.today() if "Future" in pr_horizon else end_date - timedelta(days=50 * 365)
                
                results = []
                curr_date = start_date
                in_range = False
                r_start, r_end, r_sig_a, r_sig_b = None, None, "", ""
                
                while curr_date <= end_date:
                    jd_scan = swe.julday(curr_date.year, curr_date.month, curr_date.day, 12.0)
                    
                    lon_s = get_sidereal_lon(jd_scan, source_planet)
                    lon_d = get_sidereal_lon(jd_scan, dest_planet)
                    
                    r_s = get_rashi_index(lon_s)
                    r_d = get_rashi_index(lon_d)
                    
                    current_yoga = get_yoga_type(r_s, r_d)
                    matched = (current_yoga == target_yoga)
                    
                    if matched:
                        _, name_s, _, _ = calculate_vedic_details(lon_s)
                        _, name_d, _, _ = calculate_vedic_details(lon_d)
                        if not in_range:
                            in_range = True
                            r_start = curr_date
                            r_sig_a = name_s
                            r_sig_b = name_d
                        r_end = curr_date
                    else:
                        if in_range:
                            results.append({
                                "Start Date": r_start.strftime("%Y-%m-%d"),
                                "End Date": r_end.strftime("%Y-%m-%d"),
                                "Year": r_start.year,
                                "Source": source_planet,
                                "Destination": dest_planet,
                                "Yoga": target_yoga,
                                "Source Sign": r_sig_a,
                                "Dest Sign": r_sig_b
                            })
                            in_range = False
                    curr_date += timedelta(days=1)
                    
                if in_range and r_start is not None:
                    results.append({
                        "Start Date": r_start.strftime("%Y-%m-%d"),
                        "End Date": r_end.strftime("%Y-%m-%d"),
                        "Year": r_start.year,
                        "Source": source_planet,
                        "Destination": dest_planet,
                        "Yoga": target_yoga,
                        "Source Sign": r_sig_a,
                        "Dest Sign": r_sig_b
                    })

                if results:
                    st.session_state.pr_results = results
                else:
                    st.session_state.pr_results = None

    if "pr_results" in st.session_state and st.session_state.pr_results:
        results = st.session_state.pr_results
        df_pr = pd.DataFrame(results).sort_values(by="Start Date", ascending=False)
        st.success(f"Found {len(df_pr)} matching relation periods! **Check/select any row** below to inspect global asset prices.")
        
        event = st.dataframe(
            df_pr, 
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if event and event.selection.get("rows"):
            selected_row_idx = event.selection["rows"][0]
            selected_event = df_pr.iloc[selected_row_idx].to_dict()
            render_price_modal(selected_event)
    elif "pr_results" in st.session_state and st.session_state.pr_results is None:
        st.warning("No matching planet relation periods found for the selected combination.")