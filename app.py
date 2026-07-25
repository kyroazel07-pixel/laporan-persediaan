import streamlit as st
import pdfplumber
from weasyprint import HTML
import tempfile

st.set_page_config(page_title="Buku Persediaan Manual", page_icon="📦", layout="centered")

st.title("📦 Konverter Buku Persediaan Manual")
st.write("Upload PDF mentah, robot bakal susun ke A4 Portrait berwarna & rapi sesuai format standar!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES & BERSIHKAN PDF"):
        with st.spinner("Lagi memproses & menyusun tabel berwarna... Tunggu sebentar ya!"):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            # DESAIN HTML/CSS: A4 PORTRAIT, BERWARNA, ELEGAN
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @page { 
                        size: A4 portrait; 
                        margin: 12mm 10mm; 
                    }
                    * {
                        box-sizing: border-box;
                    }
                    body { 
                        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; 
                        font-size: 8pt; 
                        color: #2c3e50;
                        margin: 0;
                        padding: 0;
                    }
                    .page { 
                        page-break-after: always; 
                    }
                    .page:last-child { 
                        page-break-after: avoid; 
                    }
                    
                    /* Info Header Box */
                    .meta-card {
                        background-color: #f8fafc;
                        border-left: 4px solid #1e3a8a;
                        padding: 8px 12px;
                        margin-bottom: 12px;
                        border-radius: 4px;
                    }
                    .meta-table {
                        width: 100%;
                        border-collapse: collapse;
                    }
                    .meta-table td {
                        border: none;
                        padding: 2px 0;
                        font-size: 8.5pt;
                        font-weight: bold;
                        color: #1e293b;
                        text-align: left;
                    }
                    
                    /* Title Style */
                    .title { 
                        text-align: center; 
                        font-size: 11pt; 
                        font-weight: bold; 
                        color: #0f172a;
                        margin-bottom: 10px; 
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    
                    /* Main Table Style */
                    table.main-table { 
                        width: 100%; 
                        border-collapse: collapse; 
                        table-layout: fixed;
                    }
                    table.main-table th, table.main-table td { 
                        border: 1px solid #94a3b8; 
                        padding: 5px 3px; 
                        text-align: center; 
                        word-wrap: break-word;
                    }
                    table.main-table th { 
                        font-weight: bold; 
                        background-color: #1e3a8a; 
                        color: #ffffff;
                        font-size: 7.5pt;
                    }
                    table.main-table th.sub-header {
                        background-color: #1e40af;
                    }
                    table.main-table tr:nth-child(even) {
                        background-color: #f1f5f9;
                    }
                    .text-left { text-align: left !important; }
                    .text-right { text-align: right !important; }
                </style>
            </head>
            <body>
            """
            
            halaman_lolos = 0
            
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    
                    # Filter halaman yang ada mutasi/transaksi
                    if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
                        
                        # Extract Header Data
                        nama_barang = "-"
                        kode_barang = "-"
                        satuan = "-"
                        
                        lines = text.split("\n")
                        for line in lines:
                            if "NAMA BARANG" in line.upper() or "NAMA" in line.upper():
                                if ":" in line:
                                    nama_barang = line.split(":")[-1].strip()
                            if "KODE BARANG" in line.upper() or "KODE" in line.upper():
                                if ":" in line:
                                    kode_barang = line.split(":")[-1].strip()
                            if "SATUAN" in line.upper():
                                if ":" in line:
                                    satuan = line.split(":")[-1].strip()

                        # Extract Table Data
                        tables = page.extract_tables()
                        rows_html = ""
                        no_counter = 1
                        
                        if tables:
                            for table in tables:
                                for row in table:
                                    if any(row):
                                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else '' for cell in row]
                                        row_str = " ".join(clean_row).lower()
                                        
                                        # Skip header bawaan PDF
                                        if "no" in clean_row[0].lower() or "tanggal" in row_str or "keterangan" in row_str or "satuan" in row_str:
                                            continue
                                            
                                        # Ambil data transaksi
                                        tgl = clean_row[1] if len(clean_row) > 1 else ""
                                        ket = clean_row[2] if len(clean_row) > 2 else ""
                                        
                                        # Mapping kolom sesuai PDF mentah lu
                                        m_jml = clean_row[4] if len(clean_row) > 4 else ""
                                        m_hrg = clean_row[5] if len(clean_row) > 5 else ""
                                        k_jml = clean_row[7] if len(clean_row) > 7 else ""
                                        k_hrg = clean_row[8] if len(clean_row) > 8 else ""
                                        s_jml = clean_row[10] if len(clean_row) > 10 else ""
                                        s_rp  = clean_row[11] if len(clean_row) > 11 else ""
                                        kond  = clean_row[12] if len(clean_row) > 12 else "Baik"

                                        if ket or tgl or m_jml or k_jml:
                                            rows_html += f"""
                                            <tr>
                                                <td style="width: 4%;">{no_counter}</td>
                                                <td style="width: 11%;">{tgl}</td>
                                                <td style="width: 20%;" class="text-left">{ket}</td>
                                                <td style="width: 8%;">{m_jml}</td>
                                                <td style="width: 10%;" class="text-right">{m_hrg}</td>
                                                <td style="width: 8%;">{k_jml}</td>
                                                <td style="width: 10%;" class="text-right">{k_hrg}</td>
                                                <td style="width: 8%;">{s_jml}</td>
                                                <td style="width: 12%;" class="text-right">{s_rp}</td>
                                                <td style="width: 9%;">{kond}</td>
                                            </tr>
                                            """
                                            no_counter += 1

                        # Jika kosong, buatkan 10 baris dummy rapi
                        if not rows_html:
                            for i in range(1, 11):
                                rows_html += f"""
                                <tr>
                                    <td>{i}</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
                                </tr>
                                """

                        html_template += f"""
                        <div class="page">
                            <div class="meta-card">
                                <table class="meta-table">
                                    <tr><td style="width: 15%;">Nama Barang</td><td style="width: 2%;">:</td><td>{nama_barang}</td></tr>
                                    <tr><td>Kode Barang</td><td>:</td><td>{kode_barang}</td></tr>
                                    <tr><td>Satuan</td><td>:</td><td>{satuan}</td></tr>
                                </table>
                            </div>
                            
                            <div class="title">Buku Persediaan Manual</div>
                            
                            <table class="main-table">
                                <thead>
                                    <tr>
                                        <th rowspan="2" style="width: 4%;">No</th>
                                        <th rowspan="2" style="width: 11%;">Tanggal</th>
                                        <th rowspan="2" style="width: 20%;">Keterangan</th>
                                        <th rowspan="2" style="width: 8%;">Jumlah Masuk</th>
                                        <th rowspan="2" style="width: 10%;">Harga Satuan</th>
                                        <th rowspan="2" style="width: 8%;">Jumlah Keluar</th>
                                        <th rowspan="2" style="width: 10%;">Harga Satuan</th>
                                        <th colspan="2" style="width: 20%;">Saldo</th>
                                        <th rowspan="2" style="width: 9%;">Kondisi Barang</th>
                                    </tr>
                                    <tr>
                                        <th class="sub-header" style="width: 8%;">Jumlah</th>
                                        <th class="sub-header" style="width: 12%;">Nilai (Rp)</th>
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
            
            pdf_out_path = "Buku_Persediaan_Manual_A4_Aesthetic.pdf"
            HTML(string=html_template).write_pdf(pdf_out_path)
            
            if halaman_lolos > 0:
                st.balloons()
                st.success(f"Selesai! Berhasil memproses {halaman_lolos} halaman ke format A4 Portrait Berwarna!")
                
                with open(pdf_out_path, "rb") as f:
                    st.download_button(
                        label="📥 DOWNLOAD PDF BUKU PERSEDIAAN ELEGANT",
                        data=f,
                        file_name="Buku_Persediaan_Manual_A4.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("Nggak ada transaksi valid yang ditemukan di file PDF ini, bro.")
