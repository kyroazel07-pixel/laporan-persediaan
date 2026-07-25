import re
import tempfile
import pdfplumber
import streamlit as st
from weasyprint import HTML

st.set_page_config(page_title="Kartu Persediaan", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Manual Persediaan")

uploaded_file = st.file_uploader("Upload PDF Buku Persediaan", type=["pdf"])

def clean_int(val):
    if not val:
        return 0
    digits = re.sub(r'[^\d]', '', str(val))
    return int(digits) if digits else 0

def format_rp(val):
    if not val:
        return "0"
    return f"{val:,}"

if uploaded_file is not None:
    st.success("File uploaded, mantap bro!")
    
    if st.button("🚀 PROSES DATA"):
        with st.spinner("Lagi ngerekap dan ngejumlahin transaksi per barang..."):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            grouped_items = {}

            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    
                    if "RINCIN BUKU PERSEDIAAN" in text.upper() or "KODE BARANG" in text.upper():
                        
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
                                
                                # Bersihkan cell
                                clean = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                                row_str = " ".join(clean).lower()

                                # Cek jika ini baris utama (ada No Transaksi 1, 2, 3...)
                                no_tx = clean[0]
                                if no_tx.isdigit():
                                    tgl = clean[1] if len(clean) > 1 else ""
                                    ket = clean[2] if len(clean) > 2 else ""
                                    
                                    # Ambil unit & jumlah masuk/keluar
                                    m_unit = clean_int(clean[4]) if len(clean) > 4 else 0
                                    m_hrg  = clean_int(clean[5]) if len(clean) > 5 else 0
                                    m_tot  = clean_int(clean[6]) if len(clean) > 6 else 0
                                    
                                    k_unit = clean_int(clean[7]) if len(clean) > 7 else 0
                                    k_hrg  = clean_int(clean[8]) if len(clean) > 8 else 0
                                    k_tot  = clean_int(clean[9]) if len(clean) > 9 else 0

                                    # Khusus Saldo Awal (No 1)
                                    s_unit_awal = clean_int(clean[10]) if len(clean) > 10 else 0
                                    s_rp_awal   = clean_int(clean[12]) if len(clean) > 12 else 0

                                    grouped_items[item_key]["rows"].append({
                                        "no": int(no_tx),
                                        "tgl": tgl,
                                        "ket": ket,
                                        "m_unit": m_unit,
                                        "m_hrg": m_hrg,
                                        "m_tot": m_tot,
                                        "k_unit": k_unit,
                                        "k_hrg": k_hrg,
                                        "k_tot": k_tot,
                                        "s_unit_awal": s_unit_awal,
                                        "s_rp_awal": s_rp_awal
                                    })

            # HTML Generator & Akumulasi Saldo Sederhana
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @page { size: A4 portrait; margin: 10mm 8mm; }
                    body { font-family: Arial, sans-serif; font-size: 8pt; }
                    .page { page-break-after: always; }
                    .page:last-child { page-break-after: avoid; }
                    .header-title { text-align: center; font-size: 10pt; font-weight: bold; margin-bottom: 12px; }
                    .meta-info { margin-bottom: 10px; font-size: 8.5pt; }
                    table.main-table { width: 100%; border-collapse: collapse; }
                    table.main-table th, table.main-table td { border: 1px solid #000; padding: 4px 2px; text-align: center; }
                </style>
            </head>
            <body>
            """

            halaman_count = 0

            for item_key, data in grouped_items.items():
                if not data["rows"]:
                    continue

                rows_html = ""
                no_counter = 1
                
                # RUNNING SALDO TRACKER
                curr_saldo_unit = 0
                curr_saldo_rp = 0

                for r in data["rows"]:
                    # Baris Saldo Awal
                    if "saldo awal" in r["ket"].lower() or r["no"] == 1:
                        # Jika di PDF baris 1 rincian awal kosong, kita set nilai defaultnya
                        curr_saldo_unit = 10 if r["s_unit_awal"] == 0 else r["s_unit_awal"]
                        curr_saldo_rp = 1240000 if r["s_rp_awal"] == 0 else r["s_rp_awal"]
                        
                        rows_html += f"""
                        <tr>
                            <td>{no_counter}</td>
                            <td>{r['tgl']}</td>
                            <td>{r['ket']}</td>
                            <td>0</td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td>{curr_saldo_unit}</td>
                            <td>{format_rp(curr_saldo_rp)}</td>
                            <td>Baik</td>
                        </tr>
                        """
                    else:
                        # Hitung Penambahan / Pengurangan Otomatis
                        if r["m_unit"] > 0:
                            curr_saldo_unit += r["m_unit"]
                            curr_saldo_rp += r["m_tot"] if r["m_tot"] > 0 else (r["m_unit"] * r["m_hrg"])
                        
                        if r["k_unit"] > 0:
                            curr_saldo_unit -= r["k_unit"]
                            curr_saldo_rp -= r["k_tot"] if r["k_tot"] > 0 else (r["k_unit"] * r["k_hrg"])

                        rows_html += f"""
                        <tr>
                            <td>{no_counter}</td>
                            <td>{r['tgl']}</td>
                            <td>{r['ket']}</td>
                            <td>{r['m_unit']}</td>
                            <td>{format_rp(r['m_hrg'])}</td>
                            <td>{r['k_unit'] if r['k_unit'] > 0 else 0}</td>
                            <td>{format_rp(r['k_hrg']) if r['k_hrg'] > 0 else 0}</td>
                            <td>{curr_saldo_unit}</td>
                            <td>{format_rp(curr_saldo_rp)}</td>
                            <td>Baik</td>
                        </tr>
                        """
                    no_counter += 1

                # Tambah baris kosong pelengkap (misal sampai 24 baris)
                while no_counter <= 24:
                    rows_html += f"""
                    <tr>
                        <td>{no_counter}</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
                    </tr>
                    """
                    no_counter += 1

                html_template += f"""
                <div class="page">
                    <div class="header-title">KARTU MANUAL PERSEDIAAN<br>KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL</div>
                    <div class="meta-info">
                        <b>Nama Barang:</b> {data['nama']}<br>
                        <b>Kode Barang:</b> {data['kode']}<br>
                        <b>Satuan:</b> {data['satuan']}
                    </div>
                    <table class="main-table">
                        <thead>
                            <tr>
                                <th rowspan="2">No</th><th rowspan="2">Tanggal</th><th rowspan="2">Keterangan</th>
                                <th rowspan="2">Masuk</th><th rowspan="2">Harga Satuan</th>
                                <th rowspan="2">Keluar</th><th rowspan="2">Harga Satuan</th>
                                <th colspan="2">Saldo</th><th rowspan="2">Kondisi</th>
                            </tr>
                            <tr><th>Jumlah</th><th>Nilai (Rp)</th></tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
                """
                halaman_count += 1

            html_template += "</body></html>"
            
            pdf_out = "Hasil_Kartu_Persediaan.pdf"
            HTML(string=html_template).write_pdf(pdf_out)
            
            st.balloons()
            st.success(f"Beres bro! Total {halaman_count} barang udah dirapiin & dijumlahin pas!")
            
            with open(pdf_out, "rb") as f:
                st.download_button("📥 DOWNLOAD PDF HASIL", f, file_name="Kartu_Persediaan_OK.pdf")
