import streamlit as st
import pandas as pd
import plotly.express as px
from src.core.blackboard import Blackboard

# Initialize Blackboard to query analytical results
bb = Blackboard("data/svarna_blackboard.db")

def render():
    st.title("📊 Executive Dashboard")
    st.markdown("Visualisasi Indeks Risiko Inflasi & Pemetaan Suplai Komoditas Nasional")
    
    # Let's get actual alerts from the Blackboard
    alerts = bb.query_history("economic_alerts", limit=50)
    
    # Process the latest valid alerts for metric cards
    if not alerts:
        st.info("💡 Belum ada data pelaporan. Silakan unggah suara petani di menu 'Voice Ingestor'.")
        return

    # Extract parsed metrics
    all_data = []
    for a in alerts:
        payload = a.get("payload", {})
        alert_type = payload.get("alert_type")
        commodity = payload.get("commodity", "")
        iri_score = payload.get("iri_assessment", {}).get("iri_score", 0.0)
        risk = payload.get("risk_level", "low")
        lat = payload.get("iri_assessment", {}).get("price_deviation", {}).get("p_local", 0) # Placeholder
        # Since geolocation might be missing in alerts directly, we can fetch from reports
        report_id = payload.get("report_id")
        
        # We fetch the exact farmer report for coordinates
        rep = bb.read_by_id(report_id) if report_id else None
        lat, lon, vill, kab = 0, 0, "Unknown", "Unknown"
        if rep and "payload" in rep:
            geo = rep["payload"].get("geo_location", {})
            lat = geo.get("latitude", -6.75)
            lon = geo.get("longitude", 107.0)
            vill = geo.get("village_name", "Unknown")
            kab = geo.get("district", "Unknown")
            
        all_data.append({
            "Commodity": commodity.capitalize(),
            "Alert": alert_type.upper() if alert_type else "INFO",
            "Risk": risk.upper(),
            "IRI": round(iri_score, 2),
            "Latitude": lat,
            "Longitude": lon,
            "Target": kab,
            "Date": a.get("created_at")[:10]
        })
        
    df = pd.DataFrame(all_data)
    
    # 1. Row of Metric Cards
    st.subheader("Tren Harga & Risiko Spikes")
    cols = st.columns(4)
    # Just show the top 4 latest indicators
    for i, row in enumerate(df.head(4).itertuples()):
        col = cols[i % 4]
        is_danger = row.IRI > 0.15
        color = "#FF3366" if is_danger else "#00FF88"
        arrow = "↑" if row.IRI > 0 else "↓"
        with col:
            st.markdown(f"""
            <div class="glass-card">
                <h4 style="margin:0; font-weight: normal; font-size: 1rem; color: #8B949E;">{row.Commodity} ({row.Target})</h4>
                <div style="font-size: 2.2rem; font-weight: 800; color: {color}; margin-top: 10px;">
                    {arrow} {abs(row.IRI)}
                </div>
                <div style="font-size: 0.8rem; color: #FAFAFA;">Risk Status: {row.Risk}</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("---")
    
    # 2. Map & Table Row
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("🗺️ Pemetaan Persebaran Komoditas")
        if not df.empty and df['Latitude'].sum() != 0:
            # We map colors based on risk
            color_map = {"CRITICAL": "#FF3366", "HIGH": "#FF3366", "MODERATE": "#FFB800", "LOW": "#00FF88"}
            df['Color'] = df['Risk'].map(lambda x: color_map.get(x, "#00FF88"))
            
            fig = px.scatter_mapbox(
                df, 
                lat="Latitude", 
                lon="Longitude", 
                hover_name="Target",
                hover_data=["Commodity", "IRI", "Risk"],
                color="Risk",
                color_discrete_map=color_map,
                zoom=6, height=500
            )
            fig.update_layout(
                mapbox_style="carto-darkmatter",
                margin={"r":0,"t":0,"l":0,"b":0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Data Geolocation kosong / belum valid.")
            
    with c2:
        st.subheader("Surplus & Deficit 📦")
        # Filter mostly for table
        display_df = df[["Commodity", "Target", "Alert", "IRI"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

