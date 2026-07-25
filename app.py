import streamlit as st
from processor import process_pdf

# Set halaman dengan judul & icon
st.set_page_config(
    page_title="Konverter Kartu Persediaan", 
    page_icon="📦", 
    layout="centered"
)

# Custom Styling (CSS) Modern & Rapi
st.markdown("""
<style>
    /* Hilangkan padding berlebih & ubah background utama */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Wrapper Card Utama */
    .main-card {
        background: #ffffff;
        padding: 32px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
        margin-top: 10px;
        margin-bottom: 25px;
    }
    
    /* Header Styling */
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
        font-weight: 400;
    }
    .badge {
        background-color: #eff6ff;
        color: #1d4ed8;
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 10px;
    }

    /* Tombol Utama (Proses) */
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
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
        transform: translateY(-1px);
    }

    /* Section Unduh */
    .download-section {
        background-color: #f1f5f9;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-top: 20px;
    }
    .download-title {
        font-size: 15px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 12px;
    }
    
    /* Tombol Download */
    .stDownloadButton > button {
        width: 100%;
        background-color: #ffffff;
        color: #0f172a;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px;
        transition: all 0.2s ease;
    }
    .stDownloadButton > button:hover {
        background-color: #f8fafc;
        border-color: #94a3b8;
        color: #1e40af;
    }
</style>
""", unsafe_allow_html=True)

# Session state inisialisasi
if "pdf_digital" not in st.session_state:
    st.session_state["pdf_digital"] = None
if "pdf_manual" not in st.session_state:
    st.session_state["pdf_manual"] = None

# BUNGKUS DALAM CARD UI MEWAH
st.markdown('<div class="main-card">', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-container">
    <span class="badge">Sistem Otomatisasi Imigrasi</span>
    <div class="header-title">📦 Konverter Kartu Persediaan</div>
    <div class="header-subtitle">Rekap laporan PDF mentah menjadi dokumen Kartu Manual Persediaan terformat</div>
</div>
""", unsafe_allow_html=True)

# Form Upload
uploaded_file = st.file_uploader("Upload PDF Mentah Laporan Lu", type=["pdf"], help="Pilih file PDF laporan persediaan yang ingin diolah")

if uploaded_file is not None:
    st.write("")
    if st.button("🚀 MULAI PROSES DOKUMEN"):
        with st.spinner("Sedang memproses & menyusun 2 versi PDF..."):
            pdf_digital, pdf_manual = process_pdf(uploaded_file)
            
            if pdf_digital and pdf_manual:
                st.session_state["pdf_digital"] = pdf_digital
                st.session_state["pdf_manual"] = pdf_manual
                st.success("✅ Berhasil! Dokumen siap diunduh.")
            else:
                st.error("❌ Tidak ditemukan transaksi bernilai pada file ini.")

# Section Download Hasil
if st.session_state["pdf_digital"] and st.session_state["pdf_manual"]:
    st.markdown("""
    <div class="download-section">
        <div class="download-title">📥 Unduh Hasil Laporan PDF:</div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📄 Versi Digital (Rapi)",
            data=st.session_state["pdf_digital"],
            file_name="Kartu_Persediaan_Digital.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col2:
        st.download_button(
            label="✍️ Versi Cetak (Manual)",
            data=st.session_state["pdf_manual"],
            file_name="Kartu_Persediaan_Manual.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
