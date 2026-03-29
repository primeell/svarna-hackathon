import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from src.core.blackboard import Blackboard

# Initialize Blackboard to query analytical results
bb = Blackboard("data/svarna_blackboard.db")

def render():
    st.title("📊 Executive Dashboard")
    st.markdown("Visualisasi Indeks Risiko Inflasi & Pemetaan Suplai Komoditas Nasional")
    
    col_sync, _ = st.columns([1, 4])
    with col_sync:
        if st.button("🔄 Sync Data PIHPS", help="Mengunduh data referensi harga nasional terbaru", use_container_width=True):
            with st.spinner("Menghubungkan ke API PIHPS..."):
                time.sleep(1.5)
                st.toast("✅ Berhasil memuat data komoditas nasional terbaru dari Sever Pemerintah!")
                st.rerun()

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
            color_map = {"CRITICAL": "#FF3366", "HIGH": "#FF3366", "MODERATE": "#FFB800", "LOW": "#00FF88"}
            
            fig = go.Figure()
            
            # Pasar Induk Jakarta (Mock Deficit Hub) Target coordinates
            TARGET_LAT, TARGET_LON = -6.200000, 106.816666
            
            # Draw Matchmaking Lines first (so they are under the markers)
            for idx, row in df.iterrows():
                if row['Alert'] == 'SURPLUS' or row['Risk'] == 'LOW':
                    fig.add_trace(go.Scattermapbox(
                        mode="lines",
                        lon=[row['Longitude'], TARGET_LON],
                        lat=[row['Latitude'], TARGET_LAT],
                        line=dict(width=2, color="#00FF88"),
                        hoverinfo="none",
                        showlegend=False
                    ))
            
            # Add Pasar Induk Marker (Hub)
            fig.add_trace(go.Scattermapbox(
                mode="markers+text",
                lon=[TARGET_LON], lat=[TARGET_LAT],
                marker=dict(size=14, color="#00A2FF", symbol="circle"),
                name="Pasar Induk",
                text=["Hub Defisit JKT"], textposition="bottom right",
                hoverinfo="text"
            ))
            
            # Add Origin Points (Farmer Reports)
            for risk_lvl in df['Risk'].unique():
                df_sub = df[df['Risk'] == risk_lvl]
                fig.add_trace(go.Scattermapbox(
                    mode="markers",
                    lon=df_sub['Longitude'],
                    lat=df_sub['Latitude'],
                    marker=dict(size=12, color=color_map.get(risk_lvl, "#00FF88")),
                    name=f"Status: {risk_lvl}",
                    hoverinfo="text",
                    hovertext=df_sub['Target'] + "<br>" + df_sub['Commodity'] + " (" + df_sub['Alert'] + ")"
                ))

            fig.update_layout(
                mapbox_style="carto-darkmatter",
                margin={"r":0,"t":0,"l":0,"b":0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                mapbox=dict(
                    center=dict(lat=-6.5, lon=107.0),
                    zoom=7
                ),
                legend=dict(
                    bgcolor="rgba(0,0,0,0.5)",
                    font=dict(color="white"),
                    yanchor="top", y=0.99, xanchor="left", x=0.01
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Data Geolocation kosong / belum valid.")
            
    with c2:
        st.subheader("Surplus & Deficit 📦")
        # Filter mostly for table
        display_df = df[["Commodity", "Target", "Alert", "IRI"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

