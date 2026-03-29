import streamlit as st
import pandas as pd
from src.core.blackboard import Blackboard
import json

bb = Blackboard("data/svarna_blackboard.db")

def render():
    st.markdown("<h1 class='title-glow'>⛓️ Blackboard & Audit Trail</h1>", unsafe_allow_html=True)
    st.markdown("Ruang transparan memantau Database _Blackboard_ Log Inter-Agent AI.")
    
    st.markdown("---")
    
    tab_audit, tab_alert = st.tabs(["📓 Log Transaksi (Raw JSON)", "🔗 Hubungan Entitas"])
    
    with tab_audit:
        st.subheader("Data Mentah Pelaporan (Parser & Ingestor)")
        
        # Pull data based on selected type
        entry_type = st.selectbox("Pilih Jenis Data", ["transcriptions", "parsed_reports", "economic_alerts", "audit_log"])
        limit = st.slider("Jumlah Batasan", 5, 200, 20)
        
        if st.button("Query Data", type="primary"):
            if entry_type == "audit_log":
                # Special table for audit_log which is just history rows
                data = bb.query_history(entry_type, limit=limit)
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            else:
                data = bb.query_history(entry_type, limit=limit)
                for d in data:
                    with st.expander(f"Data ID: {d['payload'].get('id', d.get('id'))} ({d['created_at'][:19]})"):
                        st.json(d["payload"])

    with tab_alert:
        st.subheader("Analisis Deteksi Anomali")
        st.info("Logik dari perhitungan Agent 3 (Macro Strategist)")
        
        alerts = bb.query_history("economic_alerts", limit=50)
        if alerts:
            df_lists = []
            for a in alerts:
                pl = a.get("payload", {})
                alert_type = pl.get("alert_type")
                if alert_type: # if it is an alert object
                    iri_score = pl.get("iri_assessment", {}).get("iri_score", 0)
                    title = pl.get("title", "")
                    
                    df_lists.append({
                        "Time": a.get("created_at")[:19],
                        "Commodity": pl.get("commodity", "").upper(),
                        "Type": alert_type.upper(),
                        "IRI": round(iri_score, 2),
                        "Risk": pl.get("risk_level", "").upper(),
                        "Alert Headline": title
                    })
            if df_lists:
                st.dataframe(pd.DataFrame(df_lists), use_container_width=True)
            else:
                st.write("Belum ada alarm/indikasi yang memicu Alert.")
        else:
            st.write("Belum ada data Alert Historis di SQLite.")
