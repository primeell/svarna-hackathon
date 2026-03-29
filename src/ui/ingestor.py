import streamlit as st
import tempfile
import os
import subprocess
import shutil
from src.core.pipeline import SVARNAPipeline
from audiorecorder import audiorecorder

# Cache the pipeline initialization natively in Streamlit
@st.cache_resource(show_spinner="Sedang memuat pipeline model SVARNA...")
def get_pipeline():
    return SVARNAPipeline(config_path="AgentConfig.yaml")

def render():
    st.markdown("<h1 class='title-glow'>🎙️ Voice Ingestor (Uji Lapangan)</h1>", unsafe_allow_html=True)
    st.markdown("Demonstrasi input laporan petani melalui *Audio*. Sistem akan mengeksekusi urutan pipeline *Multi-Agent* dari menangkap suara hingga merumuskan tindakan inflasi/logistik.")
    
    pipeline = get_pipeline()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. 🎤 Mode Rekam Mic Langsung")
        st.info("Pilih ini untuk mensimulasikan petani merekam suara langsung.")
        audio = audiorecorder("Mulai Rekam Suara", "Hentikan Rekaman")
        
        audio_path_to_process = None
        
        if len(audio) > 0:
            st.success("✅ Rekaman Audio sukses tersimpan!")
            st.audio(audio.export().read())
            
            # Save temporarily
            tmp_path = os.path.join(tempfile.gettempdir(), "svarna_live_recording.wav")
            audio.export(tmp_path, format="wav")
            audio_path_to_process = tmp_path
            
    with col2:
        st.subheader("2. 📁 Atau Unggah File (.wav)")
        st.info("Gunakan fail berekstensi .wav, .mp3, atau .m4a jika sudah ada sampel rekaman.")
        uploaded_file = st.file_uploader("Unggah Laporan Voice Note", type=['wav', 'mp3', 'm4a', 'flac'])
        if uploaded_file is not None:
            st.audio(uploaded_file)
            
            # Save uploaded file
            tmp_path_up = os.path.join(tempfile.gettempdir(), f"svarna_uploaded_{uploaded_file.name}")
            with open(tmp_path_up, "wb") as f:
                f.write(uploaded_file.getbuffer())
            audio_path_to_process = tmp_path_up
            
    st.markdown("---")
    
    # Process Engine
    st.subheader("⚡ Eksekusi AI Pipeline")
    
    mock_mode = st.checkbox("Gunakan Mode Mock (Dummy Data) - Lewati *Inference* Berat", value=False)
    
    if st.button("🚀 Eksekusi Laporan!", type="primary", use_container_width=True):
        if mock_mode:
            run_analysis(pipeline, None)
        elif audio_path_to_process:
            run_analysis(pipeline, audio_path_to_process)
        else:
            st.warning("⚠️ Anda belum melampirkan audio. Rekam, unggah, atau centang 'Mode Mock' dulu.")

def run_analysis(pipeline, file_path):
    st.markdown("#### Proses Agen Berjalan...")
    with st.spinner("🤖 Menganalisa intonasi dan semantic ekonomi dari suara... (Mungkin butuh 20-40 detik)"):
        try:
            # === FFMPEG AUDIO NORMALIZER ===
            processed_file = file_path
            if file_path and shutil.which("ffmpeg"):
                safe_output = os.path.join(tempfile.gettempdir(), f"clean_16k_{os.path.basename(file_path)}.wav")
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", safe_output],
                        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    processed_file = safe_output
                except subprocess.CalledProcessError:
                    st.warning("⚠️ FFMPEG gagal memproses file ini. Melanjutkan dengan file asli.")
            elif file_path:
                st.warning("ℹ️ FFMPEG tidak terdeteksi di Windows Anda. Rekaman raw Web Audio mungkin ditolak oleh model AI. Disarankan install FFMPEG.")
            # ===============================
            
            results = pipeline.run(audio_file=processed_file)
            st.success("✅ Analisis Tuntas!")
            
            # Visualization Result
            colA, colB, colC = st.columns(3)
            
            with colA:
                st.markdown("### 🗣️ Agen 1: Acoustic Ingestor")
                if "transcription" in results:
                    st.info("📝 Hasil Transkripsi:")
                    st.code(results["transcription"].get("full_text", "Tidak ada transkripsi."), language="text")
                else:
                    st.error("Transkripsi tidak keluar.")
                    
            with colB:
                st.markdown("### 🧠 Agen 2: Semantic Parser")
                if "farmer_report" in results:
                    st.info("📦 Ekstraksi Entitas:")
                    st.json(results["farmer_report"])
                else:
                    st.error("Gagal melakukan parse struktur FarmerReport")
                    
            with colC:
                st.markdown("### 📈 Agen 3: Macro Strategist")
                if "economic_analysis" in results:
                    eco = results["economic_analysis"]
                    alerts = eco.get("alerts", [])
                    st.info("📊 Alert Kesimpulan:")
                    if alerts:
                        for act in alerts:
                            title = f"**{act['title']}**"
                            desc = act['description']
                            if act['risk_level'] in ['critical', 'high']:
                                st.error(f"{title}\n{desc}")
                            elif act['alert_type'] == 'surplus':
                                st.success(f"{title}\n{desc}")
                            else:
                                st.warning(f"{title}\n{desc}")
                    else:
                        st.success("Tidak terdeteksi deviasi ekstrem. Harga Aman dan Wajar.")
                        
                    st.write("Detail Hitungan Indeks:")
                    st.json(eco.get("iri_assessment", {}))
                else:
                    st.error("Analisis Strategi Gagal.")
        except Exception as e:
            st.error(f"❌ Pipeline Execution Error: {str(e)}")
