import streamlit as st
from src.ui import dashboard, ingestor, blackboard_audit

st.set_page_config(
    page_title="SVARNA - National Economic Intelligence",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Theme CSS Injection (Cyberpunk/Neon Agriculture Theme)
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
        font-family: 'Inter', sans-serif;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161a22 !important;
        border-right: 1px solid #30363d;
    }
    /* Metric Cards Glassmorphism */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    
    .glass-card {
        background: rgba(30, 35, 45, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(0, 255, 136, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 1rem;
    }
    
    .title-glow {
        color: #00FF88;
        text-shadow: 0 0 10px rgba(0,255,136,0.3);
    }
    
    .danger-glow {
        color: #FF3366 !important;
        text-shadow: 0 0 10px rgba(255,51,102,0.3) !important;
    }
    
    /* Overide Streamlit Base Metrics Red/Green coloring to our palette */
    div[data-testid="stMetricDelta"] svg {
        display: none; 
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.sidebar.markdown("<h2 class='title-glow'>🌾 SVARNA</h2>", unsafe_allow_html=True)
    st.sidebar.caption("National Economic Intelligence Engine")
    st.sidebar.markdown("---")
    
    # Navigation Menu
    menu_options = [
        "📊 Executive Dashboard", 
        "🎙️ Voice Ingestor (Uji Lapangan)", 
        "⛓️ Blackboard & Audit Trail"
    ]
    
    choice = st.sidebar.radio("Main Menu", menu_options)
    
    st.sidebar.markdown("---")
    st.sidebar.info("Sovereign Mode: 100% Local Inference & Analytics")

    if choice == "📊 Executive Dashboard":
        dashboard.render()
    elif choice == "🎙️ Voice Ingestor (Uji Lapangan)":
        ingestor.render()
    elif choice == "⛓️ Blackboard & Audit Trail":
        blackboard_audit.render()

if __name__ == '__main__':
    main()
