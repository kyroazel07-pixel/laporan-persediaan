import streamlit as st
import pdfplumber
from weasyprint import HTML
import tempfile

st.set_page_config(page_title="Buku Persediaan Manual", page_icon="📦", layout="centered")

st.title("📦 Konverter Buku Persediaan Manual")
st.write("Upload PDF mentah, robot bakal langsung bikin tabel rincian persediaan lengkap seperti format Buku Persediaan Manual!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES & BERSIHKAN PDF"):
        with st.spinner("Lagi memproses & menyusun tabel rincian... Tunggu sebentar ya!"):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @page { size: A4 portrait; margin: 10mm; }
                    body { font-family: Arial, sans-serif; font-size: 8.5pt; }
                    .page { page-break-after: always; }
                    .page:last-child { page-break-after: avoid; }
                    .header-info { margin-bottom: 10px; font-weight: bold; line-height: 1.4; }
                    .title { text-align: center; font-size: 11pt; font-weight: bold; margin-bottom: 15px; }
                    table { width: 100%; border-collapse: collapse; margin-top: 5px; }
                    th, td { border: 1px solid #000; padding: 4px; text-align: center; }
                    th { font-weight: bold; background-color: #ffffff; }
                    .text-left { text-align: left !important; }
                </style>
            </head>
            <body>
            """
            
            halaman_lolos = 0
            
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    
                    # Cek transaksi (Buang yang kosong / mutasi 0)
                    if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
                        
                        # Ambil Metadata
                        nama_barang = "PENA"
                        kode_barang = "-"
                        satuan = "Pcs"
                        
                        lines = text.split("\n")
                        for line in lines:
                            if "NAMA BARANG" in line or "Nama Barang" in line:
                                nama_barang = line.split(":")[-1].strip() if ":" in line else line
                            if "KODE BARANG" in line or "Kode Barang" in line:
                                kode_barang = line.split(":")[-1].strip() if ":" in line else line
                            if "SATUAN" in line or "Satuan" in line:
                                satuan = line.split(":")[-1].strip() if ":" in line else line

                        # Ekstrak Tabel Asli dari PDF
                        tables = page.extract_tables()
                        rows_html = ""
                        
                        if tables:
                            for table in tables:
                                for row in table:
                                    # Ambil baris data yang bukan header
                                    if len(row) >= 5 and any(row):
                                        # Bersihkan None
                                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else '' for cell in row]
                                        
                                        # Bikin baris HTML sesuai data
                                        rows_html += "<tr>"
                                        for cell in clean_row:
                                            rows_html += f"<td>{cell}</td>"
                                        rows_html += "</tr>"
                        
                        # Jika ekstrak tabel default kosong, buatkan baris tabel kosong rapi sampai 12 baris seperti Gambar 2
                        if not rows_html:
                            for i in range(1, 13):
                                rows_html += f"""
                                <tr>
                                    <td>{i}</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
                                </tr>
                                """

                        html_template += f"""
                        <div class="page">
                            <div class="header-info">
                                Nama Barang &nbsp;&nbsp;&nbsp;&nbsp;: {nama_barang}<br>
                                Kode Barang &nbsp;&nbsp;&nbsp;&nbsp;: {kode_barang}<br>
                                Satuan &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {satuan}
                            </div>
                            
                            <div class="title">Buku Persediaan Manual</div>
                            
                            <table>
                                <thead>
                                    <tr>
                                        <th rowspan="2" style="width: 4%;">No</th>
                                        <th rowspan="2" style="width: 10%;">Tanggal</th>
                                        <th rowspan="2" style="width: 20%;">Keterangan</th>
                                        <th rowspan="2" style="width: 8%;">Jumlah Masuk</th>
                                        <th rowspan="2" style="width: 10%;">Harga Satuan</th>
                                        <th rowspan="2" style="width: 8%;">Jumlah Keluar</th>
                                        <th rowspan="2" style="width: 10%;">Harga Satuan</th>
                                        <th colspan="2">Saldo</th>
                                        <th rowspan="2" style="width: 10%;">Kondisi Barang</th>
                                    </tr>
                                    <tr>
                                        <th style="width: 8%;">Jumlah</th>
                                        <th style="width: 12%;">Nilai (Rp)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows_html}
                                </tbody>
                            </table>
                        </div>
                        """
                        halaman_lolos += 1
            
            html_template += "</body></html>"
            
            pdf_out_path = "Buku_Persediaan_Manual_Bersih.pdf"
            HTML(string=html_template).write_pdf(pdf_out_path)
            
            if halaman_lolos > 0:
                st.balloons()
                st.success(f"Selesai! Berhasil memproses {halaman_lolos} halaman barang ber-transaksi ke format Buku Persediaan Manual.")
                
                with open(pdf_out_path, "rb") as f:
                    st.download_button(
                        label="📥 DOWNLOAD PDF BUKU PERSEDIAAN MANUAL",
                        data=f,
                        file_name="Buku_Persediaan_Manual_Bersih.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("Nggak ada transaksi valid yang ditemukan di file PDF ini, bro.")
