# app.py
import streamlit as st
from processor import process_pdf

st.set_page_config(
    page_title="Konverter Kartu Persediaan", 
    page_icon="📦", 
    layout="centered"
)

st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
    .main-card {
        background: #ffffff;
        padding: 32px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        margin-top: 10px;
        margin-bottom: 25px;
    }
    .header-container {
        text-align: center;
        padding-bottom: 20px;
        border-bottom: 2px dashed #f1f5f9;
        margin-bottom: 25px;
    }
    .header-title {
        color: #0f172a;
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 6px;
    }
    .header-subtitle {
        color: #64748b;
        font-size: 14px;
    }
    .badge {
        background-color: #eff6ff;
        color: #1d4ed8;
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 10px;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
        color: #ffffff;
        font-weight: 700;
        font-size: 15px;
        padding: 12px 24px;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }
    .download-section {
        background-color: #f1f5f9;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-top: 20px;
    }
    .stDownloadButton > button {
        width: 100%;
        background-color: #16a34a;
        color: #ffffff;
        font-weight: 700;
        font-size: 14px;
        border: none;
        border-radius: 8px;
        padding: 12px;
    }
    .stDownloadButton > button:hover {
        background-color: #15803d;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

if "pdf_result" not in st.session_state:
    st.session_state["pdf_result"] = None

st.markdown('<div class="main-card">', unsafe_allow_html=True)

st.markdown("""
<div class="header-container">
    <span class="badge">Sistem Otomatisasi Imigrasi</span>
    <div class="header-title">📦 Konverter Kartu Persediaan</div>
    <div class="header-subtitle">Ekstraksi kilat PDF mentah menjadi Kartu Persediaan terformat</div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload PDF Mentah Laporan Lu", type=["pdf"])

if uploaded_file is not None:
    st.write("")
    if st.button("⚡ MULAI PROSES KILAT"):
        with st.spinner("Sedang mengekstrak data & membuat PDF..."):
            pdf_bytes = process_pdf(uploaded_file)
            
            if pdf_bytes:
                st.session_state["pdf_result"] = pdf_bytes
                st.success("✅ Berhasil! File siap diunduh.")
            else:
                st.error("❌ Tidak ditemukan transaksi bernilai pada file ini.")

if st.session_state["pdf_result"]:
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.download_button(
        label="📥 UNDUH KARTU PERSEDIAAN (PDF)",
        data=st.session_state["pdf_result"],
        file_name="Kartu_Persediaan_Hasil.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
