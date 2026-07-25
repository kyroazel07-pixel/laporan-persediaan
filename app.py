import io
import re
import streamlit as st
import pdfplumber
from fpdf import FPDF

class KartuPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=False)
        self.set_margins(8, 10, 8)

    def generate_page(self, nama_barang, kode_barang, satuan, rows_data):
        self.add_page()
        
        # --- HEADER ---
        self.set_font("Arial", 'B', 10)
        self.cell(0, 4, "KARTU MANUAL PERSEDIAAN", ln=True, align='C')
        self.cell(0, 4, "KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL", ln=True, align='C')
        self.ln(3)

        # --- META INFO ---
        self.set_font("Arial", '', 8.5)
        self.cell(28, 4, "Nama Barang", ln=False)
        self.cell(4, 4, ":", ln=False)
        self.cell(0, 4, str(nama_barang), ln=True)

        self.cell(28, 4, "Kode Barang", ln=False)
        self.cell(4, 4, ":", ln=False)
        self.cell(0, 4, str(kode_barang), ln=True)

        self.cell(28, 4, "Satuan", ln=False)
        self.cell(4, 4, ":", ln=False)
        self.cell(0, 4, str(satuan), ln=True)
        self.ln(3)

        # --- TABEL HEADER ---
        col_w = [8, 20, 38, 14, 18, 14, 18, 14, 34, 16] 
        
        self.set_font("Arial", '', 7.5)
        
        x_start = self.get_x()
        y_start = self.get_y()

        self.cell(col_w[0], 12, "No", border=1, align='C')
        self.cell(col_w[1], 12, "Tanggal", border=1, align='C')
        self.cell(col_w[2], 12, "Keterangan", border=1, align='C')
        self.cell(col_w[3], 12, "Jml Masuk", border=1, align='C')
        self.cell(col_w[4], 12, "Hrg Satuan", border=1, align='C')
        self.cell(col_w[5], 12, "Jml Keluar", border=1, align='C')
        self.cell(col_w[6], 12, "Hrg Satuan", border=1, align='C')
        
        x_saldo = self.get_x()
        self.cell(col_w[7] + col_w[8], 6, "Saldo", border=1, align='C')
        self.cell(col_w[9], 12, "Kondisi", border=1, align='C')
        
        self.set_xy(x_saldo, y_start + 6)
        self.cell(col_w[7], 6, "Jumlah", border=1, align='C')
        self.cell(col_w[8], 6, "Nilai (Rp)", border=1, align='C')

        self.set_xy(x_start, y_start + 12)

        for i, w in enumerate(col_w):
            self.cell(w, 4, f"({i+1})", border=1, align='C')
        self.ln(4)

        # --- BODY TABEL ---
        self.set_font("Arial", '', 7)
        for row in rows_data:
            for i, val in enumerate(row):
                align_code = 'C'
                if i in [2]: 
                    align_code = 'L'
                elif i in [3, 4, 5, 6, 7, 8]: 
                    align_code = 'R'

                self.cell(col_w[i], 4.5, str(val), border=1, align=align_code)
            self.ln(4.5)

def clean_int(val):
    try:
        return int(re.sub(r'[^\d]', '', str(val)))
    except:
        return 0

def clean_float(val):
    try:
        clean_str = str(val).replace('.', '').replace(',', '.')
        return float(re.sub(r'[^\d\.]', '', clean_str))
    except:
        return 0.0

def fmt_num(val):
    if not val or val == 0:
        return ""
    return f"{int(val):,}".replace(",", ".")

st.set_page_config(page_title="Kartu Manual Persediaan", page_icon="⚡", layout="centered")

st.title("⚡ Konverter Kartu Manual Persediaan (Auto Recalculate)")
st.write("Menghitung ulang Saldo Jumlah & Nilai secara otomatis biar nggak tumpuk-tumpuk!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES & HITUNG ULANG SALDO"):
        with st.spinner("Sedang memproses & menghitung ulang saldo..."):
            
            pdf_bytes = uploaded_file.read()
            pdf_plumber_obj = pdfplumber.open(io.BytesIO(pdf_bytes))

            grouped_data = {}

            for page in pdf_plumber_obj.pages:
                text_full = page.extract_text() or ""
                top_text = page.crop((0, 0, page.width, 180)).extract_text() or ""
                
                nama_barang = "-"
                kode_barang = "-"
                satuan = "-"
                
                for line in top_text.split("\n"):
                    if ":" in line:
                        parts = line.split(":", 1)
                        label = parts[0].upper()
                        val = parts[1].strip()
                        
                        if "NAMA" in label and "BARANG" in label:
                            nama_barang = val
                        elif "KODE" in label and "BARANG" in label:
                            kode_barang = val
                        elif "SATUAN" in label:
                            satuan = re.sub(r'SATUAN$', '', val, flags=re.IGNORECASE).strip()

                if kode_barang == "-":
                    m = re.search(r'Kode\s*Barang\s*:\s*([\d\.]+)', text_full, re.IGNORECASE)
                    if m: kode_barang = m.group(1).strip()

                if kode_barang == "-":
                    continue

                if kode_barang not in grouped_data:
                    grouped_data[kode_barang] = {
                        'nama': nama_barang,
                        'satuan': satuan,
                        'rows': []
                    }

                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 3:
                            continue
                        
                        row_text = " ".join([str(c) for c in row if c]).lower()
                        
                        if any(k in row_text for k in ["pembelian", "habis pakai", "saldo awal", "reklasifikasi", "epson"]):
                            c = [str(cell).strip() if cell is not None else "" for cell in row]
                            
                            tgl = ""
                            for cell_val in c:
                                tgl_match = re.search(r'\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{2}-[A-Za-z]{3}-\d{2,4}', cell_val)
                                if tgl_match:
                                    tgl = tgl_match.group(0)
                                    break

                            # Menentukan keterangan & tipe transaksi
                            ket = "Transaksi"
                            if "saldo awal" in row_text:
                                ket = c[2] if len(c) > 2 and "saldo" in c[2].lower() else "Saldo Awal"
                            elif "pembelian" in row_text or "epson" in row_text:
                                ket = c[2] if len(c) > 2 and c[2] else "Pembelian"
                            elif "habis pakai" in row_text:
                                ket = "Habis Pakai"
                            elif "reklasifikasi" in row_text:
                                ket = "Reklasifikasi Masuk" if "masuk" in row_text else "Reklasifikasi"

                            # Cari angka-angka nominal
                            all_nums = []
                            for cell_val in c:
                                nums = re.findall(r'[\d\.\,]+', cell_val)
                                for num in nums:
                                    if num != tgl and len(num) <= 10:
                                        all_nums.append(num)

                            m_jml = 0
                            m_hrg = 0.0
                            k_jml = 0
                            k_hrg = 0.0
                            s_awal_jml = 0
                            s_awal_rp = 0.0

                            is_saldo_awal = "saldo awal" in row_text

                            if is_saldo_awal:
                                if len(all_nums) >= 2:
                                    s_awal_jml = clean_int(all_nums[-2])
                                    s_awal_rp = clean_float(all_nums[-1])
                                elif len(all_nums) == 1:
                                    s_awal_jml = clean_int(all_nums[0])
                            else:
                                if len(all_nums) >= 2:
                                    m_jml = clean_int(all_nums[0])
                                    m_hrg = clean_float(all_nums[1])

                            grouped_data[kode_barang]['rows'].append({
                                'tgl': tgl,
                                'ket': ket,
                                'is_saldo_awal': is_saldo_awal,
                                'm_jml': m_jml,
                                'm_hrg': m_hrg,
                                'k_jml': k_jml,
                                'k_hrg': k_hrg,
                                's_awal_jml': s_awal_jml,
                                's_awal_rp': s_awal_rp
                            })

            pdf_plumber_obj.close()

            # --- GENERATE PDF + HITUNG OTOMATIS LOGIKA SALDO ---
            pdf_out = KartuPDF()
            halaman_lolos = 0

            for kode_barang, info in grouped_data.items():
                raw_rows = info['rows']
                
                if not raw_rows:
                    continue

                # LOGIKA KALKULASI REKAP SALDO
                running_saldo_jml = 0
                running_saldo_rp = 0.0

                calculated_rows = []

                for r in raw_rows:
                    if r['is_saldo_awal']:
                        running_saldo_jml = r['s_awal_jml']
                        running_saldo_rp = r['s_awal_rp']
                        calculated_rows.append([
                            r['tgl'], r['ket'],
                            "", "", "", "",
                            fmt_num(running_saldo_jml),
                            fmt_num(running_saldo_rp)
                        ])
                    else:
                        m_jml = r['m_jml']
                        m_hrg = r['m_hrg']
                        k_jml = r['k_jml']
                        k_hrg = r['k_hrg']

                        # Hitung saldo baru
                        running_saldo_jml = running_saldo_jml + m_jml - k_jml
                        running_saldo_rp = running_saldo_rp + (m_jml * m_hrg) - (k_jml * k_hrg)

                        calculated_rows.append([
                            r['tgl'], r['ket'],
                            fmt_num(m_jml), fmt_num(m_hrg),
                            fmt_num(k_jml), fmt_num(k_hrg),
                            fmt_num(running_saldo_jml),
                            fmt_num(running_saldo_rp)
                        ])

                # Layouting per 24 baris
                chunk_size = 24
                for i in range(0, len(calculated_rows), chunk_size):
                    chunk = calculated_rows[i:i + chunk_size]
                    
                    rows_table = []
                    no_counter = 1
                    
                    for r in chunk:
                        rows_table.append([
                            no_counter, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], "Baik"
                        ])
                        no_counter += 1

                    while no_counter <= 24:
                        rows_table.append([no_counter, "", "", "", "", "", "", "", "", ""])
                        no_counter += 1

                    pdf_out.generate_page(info['nama'], kode_barang, info['satuan'], rows_table)
                    halaman_lolos += 1

            if halaman_lolos > 0:
                pdf_bytes_output = pdf_out.output()
                st.balloons()
                st.success(f"Selesai! Berhasil merapikan & menghitung ulang saldo menjadi {halaman_lolos} halaman!")
                
                st.download_button(
                    label="📥 DOWNLOAD PDF PERFECT RESULT",
                    data=bytes(pdf_bytes_output),
                    file_name="Kartu_Manual_Persediaan_Cleaned.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Nggak ada transaksi yang terdeteksi, bro.")
