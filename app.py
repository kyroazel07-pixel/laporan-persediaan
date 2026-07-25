import streamlit as st
import pdfplumber
from weasyprint import HTML
import tempfile

st.set_page_config(page_title="Kartu Manual Persediaan", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Manual Persediaan")
st.write("Upload PDF mentah, robot bakal langsung bikin persis seperti format instansi resmi!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES & BERSIHKAN PDF"):
        with st.spinner("Lagi memproses & menyusun tabel resmi... Tunggu sebentar ya!"):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

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
                        font-family: Arial, Helvetica, sans-serif; 
                        font-size: 8pt; 
                        color: #000;
                        margin: 0;
                        padding: 0;
                    }
                    .page { 
                        page-break-after: always; 
                    }
                    .page:last-child { 
                        page-break-after: avoid; 
                    }
                    
                    /* Title Style */
                    .header-title { 
                        text-align: center; 
                        font-size: 10pt; 
                        font-weight: bold; 
                        color: #000;
                        margin-bottom: 15px; 
                        line-height: 1.3;
                    }
                    
                    /* Meta Info */
                    .meta-info {
                        margin-bottom: 12px;
                        font-size: 8.5pt;
                        line-height: 1.4;
                    }
                    .meta-table {
                        border-collapse: collapse;
                    }
                    .meta-table td {
                        border: none;
                        padding: 1px 0;
                        vertical-align: top;
                    }
                    
                    /* Main Table Style */
                    table.main-table { 
                        width: 100%; 
                        border-collapse: collapse; 
                        table-layout: fixed;
                    }
                    table.main-table th, table.main-table td { 
                        border: 1px solid #000; 
                        padding: 4px 2px; 
                        text-align: center; 
                        word-wrap: break-word;
                        vertical-align: middle;
                    }
                    table.main-table th { 
                        font-weight: normal; 
                        background-color: #ffffff; 
                        font-size: 8pt;
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
                                        if "no" in clean_row[0].lower() or "tanggal" in row_str or "keterangan" in row_str or "satuan" in row_str or "unit" in row_str:
                                            continue
                                            
                                        # Ambil data transaksi & kunci posisi kolomnya
                                        tgl = clean_row[1] if len(clean_row) > 1 else ""
                                        ket = clean_row[2] if len(clean_row) > 2 else ""
                                        
                                        # Pemetaan Kolom Presisi Sesuai Data PDF Mentah
                                        m_jml = clean_row[4] if len(clean_row) > 4 else ""
                                        m_hrg = clean_row[5] if len(clean_row) > 5 else ""
                                        
                                        k_jml = clean_row[7] if len(clean_row) > 7 else ""
                                        k_hrg = clean_row[8] if len(clean_row) > 8 else ""
                                        
                                        s_jml = clean_row[10] if len(clean_row) > 10 else ""
                                        s_rp  = clean_row[11] if len(clean_row) > 11 else ""
                                        
                                        # Jika Saldo Awal, penyesuaian kolom
                                        if "saldo awal" in ket.lower():
                                            m_hrg = ""
                                            k_jml = ""
                                            k_hrg = ""

                                        if ket or tgl or m_jml or k_jml or s_jml:
                                            rows_html += f"""
                                            <tr>
                                                <td style="width: 5%;">{no_counter}</td>
                                                <td style="width: 12%;">{tgl}</td>
                                                <td style="width: 21%;">{ket}</td>
                                                <td style="width: 8%;">{m_jml}</td>
                                                <td style="width: 10%;">{m_hrg}</td>
                                                <td style="width: 8%;">{k_jml}</td>
                                                <td style="width: 10%;">{k_hrg}</td>
                                                <td style="width: 8%;">{s_jml}</td>
                                                <td style="width: 10%;">{s_rp}</td>
                                                <td style="width: 8%;">Baik</td>
                                            </tr>
                                            """
                                            no_counter += 1

                        html_template += f"""
                        <div class="page">
                            <div class="header-title">
                                KARTU MANUAL PERSEDIAAN<br>
                                KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL
                            </div>
                            
                            <div class="meta-info">
                                <table class="meta-table">
                                    <tr><td style="width: 110px;">Nama Barang</td><td style="width: 15px;">:</td><td>{nama_barang}</td></tr>
                                    <tr><td>Kode Barang</td><td>:</td><td>{kode_barang}</td></tr>
                                    <tr><td>Satuan</td><td>:</td><td>{satuan}</td></tr>
                                </table>
                            </div>
                            
                            <table class="main-table">
                                <thead>
                                    <tr>
                                        <th rowspan="2" style="width: 5%;">No</th>
                                        <th rowspan="2" style="width: 12%;">Tanggal</th>
                                        <th rowspan="2" style="width: 21%;">Keterangan</th>
                                        <th rowspan="2" style="width: 8%;">Jumlah Masuk</th>
                                        <th rowspan="2" style="width: 10%;">Harga Satuan</th>
                                        <th rowspan="2" style="width: 8%;">Jumlah Keluar</th>
                                        <th rowspan="2" style="width: 10%;">Harga Satuan</th>
                                        <th colspan="2" style="width: 18%;">Saldo</th>
                                        <th rowspan="2" style="width: 8%;">Kondisi Barang</th>
                                    </tr>
                                    <tr>
                                        <th style="width: 8%;">Jumlah</th>
                                        <th style="width: 10%;">Nilai (Rp)</th>
                                    </tr>
                                    <tr>
                                        <th>(1)</th>
                                        <th>(2)</th>
                                        <th>(3)</th>
                                        <th>(4)</th>
                                        <th>(5)</th>
                                        <th>(6)</th>
                                        <th>(7)</th>
                                        <th>(8)</th>
                                        <th>(9)</th>
                                        <th>(10)</th>
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
            
            pdf_out_path = "Kartu_Manual_Persediaan_Resmi.pdf"
            HTML(string=html_template).write_pdf(pdf_out_path)
            
            if halaman_lolos > 0:
                st.balloons()
                st.success(f"Selesai! Berhasil memproses {halaman_lolos} halaman ke format resmi Kanim Kuala Tungkal!")
                
                with open(pdf_out_path, "rb") as f:
                    st.download_button(
                        label="📥 DOWNLOAD PDF RESMI",
                        data=f,
                        file_name="Kartu_Manual_Persediaan_Resmi.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("Nggak ada transaksi valid yang ditemukan di file PDF ini, bro.")
