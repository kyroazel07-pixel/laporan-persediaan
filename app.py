import re
import tempfile
import pdfplumber
import streamlit as st
from weasyprint import HTML

st.set_page_config(page_title="Kartu Persediaan Auto-Calculate", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Manual Persediaan (Aturan Positif-Negatif)")
st.write("Prinsip Utama: Setiap unit MASUK bakal menaikkan saldo, setiap unit KELUAR otomatis mengurangi saldo.")

uploaded_file = st.file_uploader("Upload PDF Buku Persediaan", type=["pdf"])

def parse_all_numbers(row_list):
    """Mengambil semua angka bersih dari deretan cell PDF"""
    nums = []
    for item in row_list:
        if not item:
            continue
        for line in str(item).split('\n'):
            digits = re.sub(r'[^\d]', '', line.strip())
            if digits:
                nums.append(int(digits))
    return nums

def format_rp(val):
    if not val or val == 0:
        return ""
    return f"{val:,}"

if uploaded_file is not None:
    st.success("File PDF terdeteksi!")
    
    if st.button("🚀 PROSES KARTU PERSEDIAAN"):
        with st.spinner("Sedang menghitung mutasi & merunutkan data..."):
            
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
                                "flat_rows": []
                            }

                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if not any(row):
                                    continue
                                
                                col0 = str(row[0]).strip() if row[0] else ""
                                col_all_str = " ".join([str(c) for c in row if c]).upper()
                                
                                # Abaikan header
                                if "MASUK" in col_all_str and "KELUAR" in col_all_str:
                                    continue
                                if "NO" in col_all_str and "TANGGAL" in col_all_str:
                                    continue
                                
                                # Hanya ambil baris transaksi ber-Nomor
                                if col0.isdigit():
                                    tgl = str(row[1]).replace('\n', ' ').strip() if len(row) > 1 and row[1] else ""
                                    ket = str(row[2]).replace('\n', ' ').strip() if len(row) > 2 and row[2] else ""
                                    
                                    # Ekstrak angka dari kolom Masuk (indeks 4,5), Keluar (indeks 7,8), & Saldo (10,11)
                                    m_nums = parse_all_numbers(row[4:6]) if len(row) > 5 else []
                                    k_nums = parse_all_numbers(row[7:9]) if len(row) > 8 else []
                                    s_nums = parse_all_numbers(row[10:12]) if len(row) > 11 else []

                                    # 1. BILA INI BARIS SALDO AWAL
                                    if "saldo awal" in ket.lower() or col0 == "1":
                                        units = s_nums[::2] if s_nums else m_nums[::2]
                                        prices = s_nums[1::2] if s_nums else m_nums[1::2]
                                        
                                        for u, h in zip(units, prices if prices else [0]*len(units)):
                                            if u > 0:
                                                grouped_items[item_key]["flat_rows"].append({
                                                    "tgl": tgl, "ket": ket,
                                                    "m_unit": u, "m_hrg": h,
                                                    "k_unit": 0, "k_hrg": 0
                                                })

                                    # 2. BILA ADA ANGKA KELUAR (OTOMATIS POTONG SALDO)
                                    elif k_nums:
                                        u = k_nums[0]
                                        h = k_nums[1] if len(k_nums) > 1 else 0
                                        if u > 0:
                                            grouped_items[item_key]["flat_rows"].append({
                                                "tgl": tgl, "ket": ket,
                                                "m_unit": 0, "m_hrg": 0,
                                                "k_unit": u, "k_hrg": h
                                            })

                                    # 3. BILA ADA ANGKA MASUK (OTOMATIS TAMBAH SALDO)
                                    elif m_nums:
                                        u = m_nums[0]
                                        h = m_nums[1] if len(m_nums) > 1 else 0
                                        if u > 0:
                                            grouped_items[item_key]["flat_rows"].append({
                                                "tgl": tgl, "ket": ket,
                                                "m_unit": u, "m_hrg": h,
                                                "k_unit": 0, "k_hrg": 0
                                            })

            # BUILD TEMPLATE PDF
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
                    .header-title { text-align: center; font-size: 10pt; font-weight: bold; margin-bottom: 12px; line-height: 1.3; }
                    .meta-info { margin-bottom: 10px; font-size: 8.5pt; }
                    .meta-table { border-collapse: collapse; margin-bottom: 5px; }
                    .meta-table td { border: none !important; padding: 2px 0; vertical-align: top; }
                    .meta-label { width: 100px; font-weight: bold; }
                    .meta-colon { width: 15px; text-align: center; font-weight: bold; }
                    .meta-value { font-weight: bold; }
                    table.main-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
                    table.main-table th, table.main-table td { 
                        border: 1px solid #000; padding: 4px 2px; text-align: center; 
                        word-wrap: break-word; vertical-align: middle; font-size: 7.5pt;
                    }
                    table.main-table th { font-weight: normal; font-size: 8pt; }
                </style>
            </head>
            <body>
            """

            halaman_count = 0

            for item_key, data in grouped_items.items():
                flat_rows = data["flat_rows"]
                
                # Abaikan barang yang tidak ada mutasi sama sekali
                if not flat_rows:
                    continue

                rows_html = ""
                no_counter = 1
                running_saldo_unit = 0
                running_saldo_rp = 0

                for r in flat_rows:
                    m_u_str = str(r["m_unit"]) if r["m_unit"] > 0 else ""
                    m_h_str = format_rp(r["m_hrg"]) if r["m_hrg"] > 0 else ""
                    
                    k_u_str = str(r["k_unit"]) if r["k_unit"] > 0 else ""
                    k_h_str = format_rp(r["k_hrg"]) if r["k_hrg"] > 0 else ""

                    # LOGIKA UTAMA: Masuk Tambah, Keluar Kurang
                    if r["m_unit"] > 0:
                        running_saldo_unit += r["m_unit"]
                        running_saldo_rp += (r["m_unit"] * r["m_hrg"])
                    
                    if r["k_unit"] > 0:
                        running_saldo_unit -= r["k_unit"]
                        running_saldo_rp -= (r["k_unit"] * r["k_hrg"])

                    rows_html += f"""
                    <tr>
                        <td style="width: 4%;">{no_counter}</td>
                        <td style="width: 11%;">{r['tgl']}</td>
                        <td style="width: 20%;">{r['ket']}</td>
                        <td style="width: 7%;">{m_u_str}</td>
                        <td style="width: 9%;">{m_h_str}</td>
                        <td style="width: 7%;">{k_u_str}</td>
                        <td style="width: 9%;">{k_h_str}</td>
                        <td style="width: 7%;">{running_saldo_unit}</td>
                        <td style="width: 18%;">{format_rp(running_saldo_rp)}</td>
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
            
            pdf_out = "Kartu_Persediaan_Final.pdf"
            HTML(string=html_template).write_pdf(pdf_out)
            
            st.balloons()
            st.success(f"Selesai! Berhasil mengolah {halaman_count} barang secara presisi.")
            
            with open(pdf_out, "rb") as f:
                st.download_button("📥 DOWNLOAD PDF KARTU FINAL", f, file_name="Kartu_Persediaan_Final.pdf")
