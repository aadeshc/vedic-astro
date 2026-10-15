import streamlit as st
import swisseph as swe
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="Vedic Astrology Toolkit", layout="wide", page_icon="✨")

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
    "Rahu": swe.MEAN_NODE
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

# --- Modal Dialog Function ---
@st.dialog("📊 Global Asset Price Inspector (±10 Days)", width="large")
def render_price_modal(event_dict):
    st.markdown(f"### Event: **{event_dict.get('Planet', '')}** — *{event_dict.get('Rashi', '')}*")
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
    ["📅 Daily Calculator", "🔍 Historical Transit Finder", "🔥 Combust / Retrograde Finder"]
)
st.sidebar.divider()

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
            ["ALL", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        )

    jd = swe.julday(selected_date.year, selected_date.month, selected_date.day, 12.0)
    
    data = []
    jd_next = jd + 1.0
    for name, p_id in PLANETS.items():
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
        row = df_planets[df_planets["Planet"] == selected_planet].iloc[0]
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            st.metric(label="Planet", value=row["Planet"])
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
        search_planet = st.selectbox("Search Planet", ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
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
            r_start, r_rashi, r_nak = None, "", ""
            
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
                
            if in_range:
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
        
        # DataFrame with interactive row selection checkboxes enabled
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
        cr_planet = st.selectbox("Select Planet", ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"])
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
            r_start, r_rashi, r_nak, r_details = None, "", "", ""
            
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

            if results:
                st.session_state.cr_results = results
            else:
                st.session_state.cr_results = None

    if "cr_results" in st.session_state and st.session_state.cr_results:
        results = st.session_state.cr_results
        df_cr_results = pd.DataFrame(results).sort_values(by="Start Date", ascending=False)
        st.success(f"Found {len(df_cr_results)} matching ranges! **Check/select any row** in the table below to open the price inspector.")
        
        # DataFrame with interactive row selection checkboxes enabled
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