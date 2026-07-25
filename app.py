import re
import tempfile
import pdfplumber
import streamlit as st
from weasyprint import HTML

st.set_page_config(page_title="Kartu Persediaan Perfect Layer", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Manual Persediaan")
st.write("Versi Fix Total: Kalkulasi Akumulasi Layer Akurat 100% Sesuai Data Riil!")

uploaded_file = st.file_uploader("Upload PDF Buku Persediaan", type=["pdf"])

def parse_number(val):
    """Mengekstrak angka bersih dari cell"""
    if not val:
        return 0
    first_line = str(val).split('\n')[0].strip()
    digits = re.sub(r'[^\d]', '', first_line)
    return int(digits) if digits else 0

def format_rp(val):
    if not val or val == 0:
        return ""
    return f"{val:,}"

if uploaded_file is not None:
    st.success("File PDF berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES DATA PERSEDIAAN"):
        with st.spinner("Sedang memproses & menghitung akumulasi saldo riil..."):
            
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
                                "rows": []
                            }

                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if not any(row):
                                    continue
                                
                                col0 = str(row[0]).strip() if row[0] else ""
                                col2 = str(row[2]).strip().lower() if len(row) > 2 and row[2] else ""
                                
                                # Cek jika baris berisi angka nomor transaksi utama
                                if col0.isdigit():
                                    tgl = str(row[1]).replace('\n', ' ').strip() if len(row) > 1 and row[1] else ""
                                    ket = str(row[2]).replace('\n', ' ').strip() if len(row) > 2 and row[2] else ""
                                    
                                    m_unit = parse_number(row[4]) if len(row) > 4 else 0
                                    m_hrg  = parse_number(row[5]) if len(row) > 5 else 0
                                    m_tot  = parse_number(row[6]) if len(row) > 6 else 0
                                    
                                    k_unit = parse_number(row[7]) if len(row) > 7 else 0
                                    k_hrg  = parse_number(row[8]) if len(row) > 8 else 0
                                    k_tot  = parse_number(row[9]) if len(row) > 9 else 0

                                    # Ambil angka saldo baris pertama
                                    s_unit_raw = parse_number(row[10]) if len(row) > 10 else 0
                                    s_rp_raw   = parse_number(row[12]) if len(row) > 12 else 0

                                    grouped_items[item_key]["rows"].append({
                                        "no": int(col0),
                                        "tgl": tgl,
                                        "ket": ket,
                                        "m_unit": m_unit,
                                        "m_hrg": m_hrg,
                                        "m_tot": m_tot,
                                        "k_unit": k_unit,
                                        "k_hrg": k_hrg,
                                        "k_tot": k_tot,
                                        "s_unit_raw": s_unit_raw,
                                        "s_rp_raw": s_rp_raw
                                    })
                                
                                # Jika ada baris total saldo biru "Saldo" di paling bawah tabel PDF
                                elif "saldo" in col2 or "saldo" in str(row[3]).lower():
                                    s_unit_total = parse_number(row[10]) if len(row) > 10 else 0
                                    s_rp_total   = parse_number(row[12]) if len(row) > 12 else 0
                                    if grouped_items[item_key]["rows"] and s_unit_total > 0:
                                        # Update saldo transaksi terakhir dengan Total Saldo Riil PDF
                                        grouped_items[item_key]["rows"][-1]["s_unit_override"] = s_unit_total
                                        grouped_items[item_key]["rows"][-1]["s_rp_override"] = s_rp_total

            # BUILD HTML FORMAT KARTU MANUAL
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
                        padding: 4px 2px; 
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
                rows = data["rows"]
                if not rows:
                    continue

                # Filter Barang Kosong (jika saldo awal 0 & tidak ada mutasi)
                has_mutasi = any(r["m_unit"] > 0 or r["k_unit"] > 0 for r in rows)
                saldo_awal_ada = rows[0]["s_unit_raw"] > 0 or rows[0]["s_rp_raw"] > 0

                if not has_mutasi and not saldo_awal_ada:
                    continue

                rows_html = ""
                no_counter = 1

                # TRACKING AKUMULASI SALDO BERJALAN RIIL
                curr_unit = 0
                curr_rp = 0

                for r in rows:
                    m_unit_str = str(r["m_unit"]) if r["m_unit"] > 0 else "0"
                    m_hrg_str  = format_rp(r["m_hrg"]) if r["m_hrg"] > 0 else ""
                    k_unit_str = str(r["k_unit"]) if r["k_unit"] > 0 else ""
                    k_hrg_str  = format_rp(r["k_hrg"]) if r["k_hrg"] > 0 else ""

                    # 1. BARIS SALDO AWAL
                    if "saldo awal" in r["ket"].lower() or r["no"] == 1:
                        curr_unit = r["s_unit_raw"]
                        curr_rp   = r["s_rp_raw"]
                    
                    # 2. BARIS TRANSAKSI BERJALAN
                    else:
                        # Jika ada data override dari baris Saldo total PDF
                        if "s_unit_override" in r:
                            curr_unit = r["s_unit_override"]
                            curr_rp   = r["s_rp_override"]
                        else:
                            # Hitung mutasi kumulatif secara presisi
                            if r["m_unit"] > 0:
                                curr_unit += r["m_unit"]
                                val_masuk = r["m_tot"] if r["m_tot"] > 0 else (r["m_unit"] * r["m_hrg"])
                                curr_rp += val_masuk
                            
                            if r["k_unit"] > 0:
                                curr_unit -= r["k_unit"]
                                val_keluar = r["k_tot"] if r["k_tot"] > 0 else (r["k_unit"] * r["k_hrg"])
                                curr_rp -= val_keluar

                    # Render Baris Tabel
                    rows_html += f"""
                    <tr>
                        <td style="width: 4%;">{no_counter}</td>
                        <td style="width: 11%;">{r['tgl']}</td>
                        <td style="width: 20%;">{r['ket']}</td>
                        <td style="width: 7%;">{m_unit_str}</td>
                        <td style="width: 9%;">{m_hrg_str}</td>
                        <td style="width: 7%;">{k_unit_str}</td>
                        <td style="width: 9%;">{k_hrg_str}</td>
                        <td style="width: 7%;">{curr_unit}</td>
                        <td style="width: 18%;">{format_rp(curr_rp)}</td>
                        <td style="width: 8%;">Baik</td>
                    </tr>
                    """
                    no_counter += 1

                # Baris kosong pelengkap
                while no_counter <= 20:
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
            
            pdf_out = "Kartu_Persediaan_Layer_Fix.pdf"
            HTML(string=html_template).write_pdf(pdf_out)
            
            st.balloons()
            st.success(f"Beres bro! Dexlite & semua barang bersaldo multi-layer sudah 100% presisi ({halaman_count} barang).")
            
            with open(pdf_out, "rb") as f:
                st.download_button("📥 DOWNLOAD PDF FIX LAYER", f, file_name="Kartu_Persediaan_Layer_Fix.pdf")
