import re
import tempfile
import pdfplumber
import streamlit as st
from weasyprint import HTML

st.set_page_config(page_title="Kartu Persediaan Direct Copy", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Manual Persediaan")
st.write("Versi Direct Copy: Merekam & menampilkan SELURUH layer rincian persediaan persis sesuai PDF sumber!")

uploaded_file = st.file_uploader("Upload PDF Buku Persediaan", type=["pdf"])

def parse_number(val):
    if not val:
        return 0
    digits = re.sub(r'[^\d]', '', str(val).strip())
    return int(digits) if digits else 0

def format_rp(val):
    if val is None or val == "" or val == 0:
        return ""
    if isinstance(val, int):
        return f"{val:,}"
    return str(val)

if uploaded_file is not None:
    st.success("File PDF berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES DATA PERSEDIAAN"):
        with st.spinner("Sedang membaca seluruh layer data riil dari PDF..."):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            grouped_items = {}

            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    
                    if "KODE BARANG" in text.upper() or "NAMA BARANG" in text.upper():
                        
                        nama_barang = "-"
                        kode_barang = "-"
                        satuan = "-"

                        for line in text.split("\n"):
                            up = line.upper()
                            if "NAMA BARANG" in up and ":" in line:
                                nama_barang = line.split(":")[-1].strip()
                            if "KODE BARANG" in up and ":" in line:
                                kode_barang = line.split(":")[-1].strip()
                            if "SATUAN" in up and ":" in line:
                                satuan = line.split(":")[-1].strip()

                        item_key = kode_barang if kode_barang != "-" else nama_barang

                        if item_key not in grouped_items:
                            grouped_items[item_key] = {
                                "nama": nama_barang,
                                "kode": kode_barang,
                                "satuan": satuan,
                                "raw_rows": []
                            }

                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if not any(row):
                                    continue
                                
                                # Ambil data mentah per baris / layer
                                col0 = str(row[0]).strip() if row[0] else ""
                                col1 = str(row[1]).replace('\n', ' ').strip() if len(row) > 1 and row[1] else ""
                                col2 = str(row[2]).replace('\n', ' ').strip() if len(row) > 2 and row[2] else ""
                                
                                # Cek jika ini baris header / subheader
                                col_all_str = " ".join([str(c) for c in row if c]).upper()
                                if "NO" in col_all_str and "TANGGAL" in col_all_str:
                                    continue
                                if "MASUK" in col_all_str and "KELUAR" in col_all_str:
                                    continue
                                
                                m_unit = str(row[4]).strip() if len(row) > 4 and row[4] else ""
                                m_hrg  = str(row[5]).strip() if len(row) > 5 and row[5] else ""
                                m_tot  = str(row[6]).strip() if len(row) > 6 and row[6] else ""
                                
                                k_unit = str(row[7]).strip() if len(row) > 7 and row[7] else ""
                                k_hrg  = str(row[8]).strip() if len(row) > 8 else ""
                                k_tot  = str(row[9]).strip() if len(row) > 9 else ""

                                s_unit = str(row[10]).strip() if len(row) > 10 and row[10] else ""
                                s_hrg  = str(row[11]).strip() if len(row) > 11 else ""
                                s_tot  = str(row[12]).strip() if len(row) > 12 and row[12] else ""

                                grouped_items[item_key]["raw_rows"].append({
                                    "no": col0,
                                    "tgl": col1,
                                    "ket": col2,
                                    "m_unit": m_unit,
                                    "m_hrg": m_hrg,
                                    "m_tot": m_tot,
                                    "k_unit": k_unit,
                                    "k_hrg": k_hrg,
                                    "k_tot": k_tot,
                                    "s_unit": s_unit,
                                    "s_hrg": s_hrg,
                                    "s_tot": s_tot
                                })

            # BUILD HTML FORMAT KARTU MANUAL DIRECT COPY
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @page { size: A4 portrait; margin: 10mm 8mm; }
                    * { box-sizing: border-box; }
                    body { font-family: Arial, Helvetica, sans-serif; font-size: 8pt; color: #000; margin: 0; padding: 0; }
                    .page { page-break-after: always; }
                    .page:last-child { page-break-after: avoid; }
                    
                    .header-title { 
                        text-align: center; 
                        font-size: 10pt; 
                        font-weight: bold; 
                        margin-bottom: 12px; 
                        line-height: 1.3;
                    }
                    
                    .meta-info { margin-bottom: 10px; font-size: 8.5pt; }
                    .meta-table { border-collapse: collapse; margin-bottom: 5px; }
                    .meta-table td { border: none !important; padding: 2px 0; vertical-align: top; }
                    .meta-label { width: 100px; font-weight: bold; }
                    .meta-colon { width: 15px; text-align: center; font-weight: bold; }
                    .meta-value { font-weight: bold; }
                    
                    table.main-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
                    table.main-table th, table.main-table td { 
                        border: 1px solid #000; 
                        padding: 3px 2px; 
                        text-align: center; 
                        word-wrap: break-word;
                        vertical-align: middle;
                        font-size: 7.5pt;
                    }
                    table.main-table th { font-weight: normal; font-size: 8pt; }
                </style>
            </head>
            <body>
            """

            halaman_count = 0

            for item_key, data in grouped_items.items():
                raw_rows = data["raw_rows"]
                if not raw_rows:
                    continue

                # Filter barang kosong (apabila tidak ada saldo/mutasi sama sekali)
                has_any_data = False
                for r in raw_rows:
                    if parse_number(r["m_unit"]) > 0 or parse_number(r["k_unit"]) > 0 or parse_number(r["s_unit"]) > 0:
                        has_any_data = True
                        break
                
                if not has_any_data:
                    continue

                rows_html = ""
                display_no = 1
                curr_no = ""
                curr_tgl = ""
                curr_ket = ""

                for r in raw_rows:
                    m_u = parse_number(r["m_unit"])
                    m_h = parse_number(r["m_hrg"])
                    k_u = parse_number(r["k_unit"])
                    k_h = parse_number(r["k_hrg"])
                    s_u = parse_number(r["s_unit"])
                    s_t = parse_number(r["s_tot"])

                    # Abaikan baris "Saldo" rangkuman total jika ada di paling bawah
                    if "SALDO" in r["ket"].upper() and not r["no"] and not r["tgl"]:
                        continue

                    # Update nomor transaksi utama jika ada
                    if r["no"].isdigit():
                        curr_no = str(display_no)
                        display_no += 1
                        curr_tgl = r["tgl"]
                        curr_ket = r["ket"]
                    else:
                        # Baris rincian layer anak
                        curr_no = ""
                        curr_tgl = ""
                        curr_ket = ""

                    m_u_str = str(m_u) if m_u > 0 else ""
                    m_h_str = format_rp(m_h) if m_h > 0 else ""
                    k_u_str = str(k_u) if k_u > 0 else ""
                    k_h_str = format_rp(k_h) if k_h > 0 else ""
                    s_u_str = str(s_u) if (s_u > 0 or s_t > 0) else ("0" if curr_no and "saldo awal" in curr_ket.lower() else "")
                    s_t_str = format_rp(s_t) if s_t > 0 else ""

                    rows_html += f"""
                    <tr>
                        <td style="width: 4%;">{curr_no}</td>
                        <td style="width: 11%;">{curr_tgl}</td>
                        <td style="width: 20%;">{curr_ket}</td>
                        <td style="width: 7%;">{m_u_str}</td>
                        <td style="width: 9%;">{m_h_str}</td>
                        <td style="width: 7%;">{k_u_str}</td>
                        <td style="width: 9%;">{k_h_str}</td>
                        <td style="width: 7%;">{s_u_str}</td>
                        <td style="width: 18%;">{s_t_str}</td>
                        <td style="width: 8%;">Baik</td>
                    </tr>
                    """

                html_template += f"""
                <div class="page">
                    <div class="header-title">
                        KARTU MANUAL PERSEDIAAN<br>
                        KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL
                    </div>
                    
                    <div class="meta-info">
                        <table class="meta-table">
                            <tr>
                                <td class="meta-label">Nama Barang</td>
                                <td class="meta-colon">:</td>
                                <td class="meta-value">{data['nama']}</td>
                            </tr>
                            <tr>
                                <td class="meta-label">Kode Barang</td>
                                <td class="meta-colon">:</td>
                                <td class="meta-value">{data['kode']}</td>
                            </tr>
                            <tr>
                                <td class="meta-label">Satuan</td>
                                <td class="meta-colon">:</td>
                                <td class="meta-value">{data['satuan']}</td>
                            </tr>
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
                                <th>(1)</th><th>(2)</th><th>(3)</th><th>(4)</th><th>(5)</th>
                                <th>(6)</th><th>(7)</th><th>(8)</th><th>(9)</th><th>(10)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
                """
                halaman_count += 1

            html_template += "</body></html>"
            
            pdf_out = "Kartu_Persediaan_Direct_Copy.pdf"
            HTML(string=html_template).write_pdf(pdf_out)
            
            st.balloons()
            st.success(f"Selesai bro! Seluruh {halaman_count} barang berhasil dikonversi persis sesuai layer asli!")
            
            with open(pdf_out, "rb") as f:
                st.download_button("📥 DOWNLOAD PDF DIRECT COPY", f, file_name="Kartu_Persediaan_Direct_Copy.pdf")
