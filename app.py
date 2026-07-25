import streamlit as st
import pdfplumber
from weasyprint import HTML
import tempfile

st.set_page_config(page_title="Konverter Persediaan", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Persediaan Otomatis")
st.write("Upload PDF mentah dari aplikasi luar, lalu download versi Landscape yang sudah bersih dari barang kosong!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES & BERSIHKAN PDF"):
        with st.spinner("Lagi memproses & membuang halaman kosong... Tunggu bentar ya!"):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @page { size: A4 landscape; margin: 15mm; }
                    body { font-family: Arial, sans-serif; font-size: 9.5pt; }
                    .page { page-break-after: always; }
                    .page:last-child { page-break-after: avoid; }
                    .title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 15px; }
                    .meta { font-weight: bold; margin-bottom: 10px; font-size: 10pt; }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { border: 1px solid #000; padding: 6px; text-align: center; }
                    th { font-weight: bold; background-color: #f2f2f2; }
                    .text-left { text-align: left !important; }
                </style>
            </head>
            <body>
            """
            
            halaman_lolos = 0
            
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    
                    # FILTER: Membuang halaman yang tidak ada transaksi
                    if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
                        lines = text.split("\n")
                        nama_barang = "BARANG PERSEDIAAN"
                        for line in lines:
                            if "NAMA BARANG" in line or "NAMA" in line:
                                nama_barang = line.replace("NAMA BARANG", "").replace(":", "").strip()
                        
                        html_template += f"""
                        <div class="page">
                            <div class="title">KARTU PERSEDIAAN BARANG</div>
                            <div class="meta">NAMA BARANG : {nama_barang}</div>
                            <table>
                                <thead>
                                    <tr>
                                        <th rowspan="2">TANGGAL</th>
                                        <th rowspan="2">KETERANGAN</th>
                                        <th colspan="2">PERSEDIAAN MASUK</th>
                                        <th colspan="2">PERSEDIAAN KELUAR</th>
                                        <th colspan="2">SALDO</th>
                                    </tr>
                                    <tr>
                                        <th>JUMLAH</th><th>SATUAN</th>
                                        <th>JUMLAH</th><th>SATUAN</th>
                                        <th>JUMLAH</th><th>SATUAN</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>-</td>
                                        <td class="text-left">Rincian mutasi terlampir</td>
                                        <td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        """
                        halaman_lolos += 1
            
            html_template += "</body></html>"
            
            pdf_out_path = "Laporan_Persediaan_Landscape_Bersih.pdf"
            HTML(string=html_template).write_pdf(pdf_out_path)
            
            if halaman_lolos > 0:
                st.balloons()
                st.success(f"Selesai! Berhasil membuang halaman kosong & menyelamatkan {halaman_lolos} halaman barang ber-transaksi.")
                
                with open(pdf_out_path, "rb") as f:
                    st.download_button(
                        label="📥 DOWNLOAD PDF HASIL BERSIH",
                        data=f,
                        file_name="Laporan_Persediaan_Landscape_Bersih.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("Nggak ada transaksi valid yang ditemukan di file PDF ini, bro.")
