import streamlit as st
import pdfplumber
from weasyprint import HTML
import tempfile

st.set_page_config(page_title="Kartu Manual Persediaan", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Manual Persediaan")
st.write("Otomatis hasilkan 2 versi PDF: Versi Digital Rapi & Versi Efek Tulisan Tangan / Scan!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES BIKIN 2 VERSI PDF"):
        with st.spinner("Lagi mengolah & memproses 2 versi PDF... Tunggu sebentar ya!"):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            # BASE CSS DENGAN PARAMETER FONT & STYLE
            def generate_css(is_handwritten=False):
                font_import = "@import url('https://fonts.googleapis.com/css2?family=Kalam:wght@400;700&display=swap');" if is_handwritten else ""
                font_family = "'Kalam', cursive" if is_handwritten else "Arial, Helvetica, sans-serif"
                text_color = "#111827" if is_handwritten else "#000000"
                font_size_body = "9pt" if is_handwritten else "8pt"
                font_size_table = "8.5pt" if is_handwritten else "7.5pt"
                
                return f"""
                <style>
                    {font_import}
                    @page {{ 
                        size: A4 portrait; 
                        margin: 10mm 8mm; 
                    }}
                    * {{
                        box-sizing: border-box;
                    }}
                    body {{ 
                        font-family: {font_family}; 
                        font-size: {font_size_body}; 
                        color: {text_color};
                        margin: 0;
                        padding: 0;
                    }}
                    .page {{ 
                        page-break-after: always; 
                    }}
                    .page:last-child {{ 
                        page-break-after: avoid; 
                    }}
                    
                    .header-title {{ 
                        text-align: center; 
                        font-size: 10.5pt; 
                        font-weight: bold; 
                        margin-bottom: 12px; 
                        line-height: 1.3;
                    }}
                    
                    .meta-info {{
                        margin-bottom: 10px;
                        font-size: 9pt;
                        line-height: 1.4;
                    }}
                    .meta-table {{
                        border-collapse: collapse;
                    }}
                    .meta-table td {{
                        border: none;
                        padding: 1px 0;
                        vertical-align: top;
                    }}
                    
                    table.main-table {{ 
                        width: 100%; 
                        border-collapse: collapse; 
                        table-layout: fixed;
                    }}
                    table.main-table th, table.main-table td {{ 
                        border: 1px solid #000; 
                        padding: 4px 2px; 
                        text-align: center; 
                        word-wrap: break-word;
                        vertical-align: middle;
                        font-size: {font_size_table};
                    }}
                    table.main-table th {{ 
                        font-weight: {'bold' if is_handwritten else 'normal'}; 
                        background-color: #ffffff; 
                        font-size: 8pt;
                    }}
                </style>
                """

            halaman_lolos = 0
            pages_data = []
            
            # EKSTRAKSI DATA DARI PDF MENTAH
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    
                    if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
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

                        tables = page.extract_tables()
                        rows_data = []
                        no_counter = 1
                        ada_transaksi_nyata = False
                        
                        if tables:
                            for table in tables:
                                row_idx = 0
                                while row_idx < len(table):
                                    row = table[row_idx]
                                    row_idx += 1
                                    
                                    if not any(row):
                                        continue
                                        
                                    clean_row = [str(cell).replace('\n', ' ').strip() if cell else '' for cell in row]
                                    row_str = " ".join(clean_row).lower()
                                    
                                    if "no" in clean_row[0].lower() or "tanggal" in row_str or "keterangan" in row_str or "satuan" in row_str or "unit" in row_str:
                                        continue
                                    
                                    if clean_row[0].strip().lower() == "saldo":
                                        continue
                                        
                                    ket = clean_row[2] if len(clean_row) > 2 else ""
                                    tgl = clean_row[1] if len(clean_row) > 1 else ""
                                    
                                    if ket or tgl:
                                        m_jml = clean_row[4] if len(clean_row) > 4 else ""
                                        m_hrg = clean_row[5] if len(clean_row) > 5 else ""
                                        k_jml = clean_row[7] if len(clean_row) > 7 else ""
                                        k_hrg = clean_row[8] if len(clean_row) > 8 else ""
                                        s_jml = clean_row[10] if len(clean_row) > 10 else ""
                                        s_rp = clean_row[11] if len(clean_row) > 11 else ""
                                        
                                        if row_idx < len(table):
                                            next_row = [str(cell).replace('\n', ' ').strip() if cell else '' for cell in table[row_idx]]
                                            if next_row[0].strip().lower() == "saldo":
                                                if len(next_row) > 11 and next_row[11]:
                                                    s_rp = next_row[11]
                                                row_idx += 1
                                        
                                        if "saldo awal" in ket.lower():
                                            m_hrg = ""
                                            k_jml = ""
                                            k_hrg = ""

                                        clean_s_jml = s_jml.replace(',', '').replace('.', '').strip()
                                        clean_m_jml = m_jml.replace(',', '').replace('.', '').strip()
                                        
                                        if "saldo awal" in ket.lower() and (clean_s_jml == "0" or clean_s_jml == "") and (clean_m_jml == "0" or clean_m_jml == ""):
                                            continue

                                        ada_transaksi_nyata = True
                                        rows_data.append({
                                            "no": no_counter,
                                            "tgl": tgl,
                                            "ket": ket,
                                            "m_jml": m_jml,
                                            "m_hrg": m_hrg,
                                            "k_jml": k_jml,
                                            "k_hrg": k_hrg,
                                            "s_jml": s_jml,
                                            "s_rp": s_rp,
                                            "kondisi": "Baik"
                                        })
                                        no_counter += 1

                        if ada_transaksi_nyata:
                            pages_data.append({
                                "nama_barang": nama_barang,
                                "kode_barang": kode_barang,
                                "satuan": satuan,
                                "rows": rows_data
                            })
                            halaman_lolos += 1

            # RENDER PEMBUATAN PDF KEDUA FORMAT
            def build_html_content(is_handwritten=False):
                html = f"<!DOCTYPE html><html><head>{generate_css(is_handwritten)}</head><body>"
                
                for item in pages_data:
                    rows_html = ""
                    no_counter = 1
                    
                    for r in item["rows"]:
                        rows_html += f"""
                        <tr>
                            <td style="width: 4%;">{r['no']}</td>
                            <td style="width: 11%;">{r['tgl']}</td>
                            <td style="width: 20%;">{r['ket']}</td>
                            <td style="width: 7%;">{r['m_jml']}</td>
                            <td style="width: 9%;">{r['m_hrg']}</td>
                            <td style="width: 7%;">{r['k_jml']}</td>
                            <td style="width: 9%;">{r['k_hrg']}</td>
                            <td style="width: 7%;">{r['s_jml']}</td>
                            <td style="width: 18%;">{r['s_rp']}</td>
                            <td style="width: 8%;">{r['kondisi']}</td>
                        </tr>
                        """
                        no_counter += 1
                        
                    while no_counter <= 24:
                        rows_html += f"""
                        <tr>
                            <td style="width: 4%;">{no_counter}</td>
                            <td style="width: 11%;"></td>
                            <td style="width: 20%;"></td>
                            <td style="width: 7%;"></td>
                            <td style="width: 9%;"></td>
                            <td style="width: 7%;"></td>
                            <td style="width: 9%;"></td>
                            <td style="width: 7%;"></td>
                            <td style="width: 18%;"></td>
                            <td style="width: 8%;"></td>
                        </tr>
                        """
                        no_counter += 1

                    html += f"""
                    <div class="page">
                        <div class="header-title">
                            KARTU MANUAL PERSEDIAAN<br>
                            KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL
                        </div>
                        
                        <div class="meta-info">
                            <table class="meta-table">
                                <tr><td style="width: 110px;">Nama Barang</td><td style="width: 15px;">:</td><td>{item['nama_barang']}</td></tr>
                                <tr><td>Kode Barang</td><td>:</td><td>{item['kode_barang']}</td></tr>
                                <tr><td>Satuan</td><td>:</td><td>{item['satuan']}</td></tr>
                            </table>
                        </div>
                        
                        <table class="main-table">
                            <thead>
                                <tr>
                                    <th rowspan="2" style="width: 4%;">No</th>
                                    <th rowspan="2" style="width: 11%;">Tanggal</th>
                                    <th rowspan="2" style="width: 20%;">Keterangan</th>
                                    <th rowspan="2" style="width: 7%;">Jumlah Masuk</th>
                                    <th rowspan="2" style="width: 9%;">Harga Satuan</th>
                                    <th rowspan="2" style="width: 7%;">Jumlah Keluar</th>
                                    <th rowspan="2" style="width: 9%;">Harga Satuan</th>
                                    <th colspan="2" style="width: 25%;">Saldo</th>
                                    <th rowspan="2" style="width: 8%;">Kondisi Barang</th>
                                </tr>
                                <tr>
                                    <th style="width: 7%;">Jumlah</th>
                                    <th style="width: 18%;">Nilai (Rp)</th>
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
                html += "</body></html>"
                return html

            if halaman_lolos > 0:
                # Bikin PDF Rapi
                pdf_rapi_path = "Kartu_Persediaan_Rapi_Digital.pdf"
                HTML(string=build_html_content(is_handwritten=False)).write_pdf(pdf_rapi_path)
                
                # Bikin PDF Tulisan Tangan / Scan
                pdf_scan_path = "Kartu_Persediaan_Efek_Tulisan_Tangan.pdf"
                HTML(string=build_html_content(is_handwritten=True)).write_pdf(pdf_scan_path)
                
                st.balloons()
                st.success(f"Berhasil memproses {halaman_lolos} barang! Pilih file yang mau didownload:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    with open(pdf_rapi_path, "rb") as f:
                        st.download_button(
                            label="📄 DOWNLOAD PDF DIGITAL RAPI",
                            data=f,
                            file_name="Kartu_Persediaan_Rapi_Digital.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                with col2:
                    with open(pdf_scan_path, "rb") as f:
                        st.download_button(
                            label="✍️ DOWNLOAD PDF TULISAN TANGAN / SCAN",
                            data=f,
                            file_name="Kartu_Persediaan_Efek_Scan.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
            else:
                st.error("Nggak ada transaksi bernilai yang ditemukan di file PDF ini, bro.")
