import streamlit as st
from processor import process_pdf

st.set_page_config(page_title="Konverter Kartu Persediaan", page_icon="📦", layout="centered")

st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stButton>button {
        width: 100%;
        background-color: #1e3a8a;
        color: white;
        border-radius: 8px;
        height: 48px;
        font-weight: bold;
        border: none;
    }
    .download-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📦 Konverter Kartu Persediaan")
st.caption("Sistem otomatisasi rekap kartu persediaan manual - Kantor Imigrasi")

if "pdf_digital" not in st.session_state:
    st.session_state["pdf_digital"] = None
if "pdf_manual" not in st.session_state:
    st.session_state["pdf_manual"] = None

uploaded_file = st.file_uploader("Upload PDF Mentah Laporan", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 PROSES DOKUMEN"):
        with st.spinner("Sedang mengekstrak & menyusun dokumen..."):
            pdf_digital, pdf_manual = process_pdf(uploaded_file)
            
            if pdf_digital and pdf_manual:
                st.session_state["pdf_digital"] = pdf_digital
                st.session_state["pdf_manual"] = pdf_manual
                st.success("Dokumen berhasil diproses!")
            else:
                st.error("Tidak ditemukan transaksi bernilai pada file ini.")

if st.session_state["pdf_digital"] and st.session_state["pdf_manual"]:
    st.markdown('<div class="download-card">', unsafe_allow_html=True)
    st.subheader("📥 Unduh Hasil Laporan")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📄 PDF Versi Digital (Rapi)",
            data=st.session_state["pdf_digital"],
            file_name="Kartu_Persediaan_Digital.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col2:
        st.download_button(
            label="✍️ PDF Versi Manual (Cetak)",
            data=st.session_state["pdf_manual"],
            file_name="Kartu_Persediaan_Manual.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
