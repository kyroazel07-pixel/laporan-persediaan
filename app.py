import io
import re
import streamlit as st
from pypdf import PdfReader
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


st.set_page_config(page_title="Kartu Manual Persediaan", page_icon="⚡", layout="centered")

st.title("⚡ Konverter Kartu Manual Persediaan (Ultra Fast)")
st.write("Versi kilat + Ekstraksi Header Akurat!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES KILAT (INSTANT)"):
        with st.spinner("Sedang memproses secara instan..."):
            
            pdf_bytes = uploaded_file.read()
            
            # Kita panggil pdfplumber & pypdf sekaligus
            pdf_plumber_obj = pdfplumber.open(io.BytesIO(pdf_bytes))
            reader = PdfReader(io.BytesIO(pdf_bytes))

            pdf_out = KartuPDF()
            halaman_lolos = 0
            
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                
                if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
                    
                    nama_barang = "-"
                    kode_barang = "-"
                    satuan = "-"
                    
                    # LOGIKA HEADER 1: Pakai pdfplumber khusus bagian atas halaman (pasti akurat & ga telat)
                    try:
                        plumber_page = pdf_plumber_obj.pages[idx]
                        top_text = plumber_page.crop((0, 0, plumber_page.width, 200)).extract_text() or ""
                        
                        for line in top_text.split("\n"):
                            line_clean = line.strip()
                            if ":" in line_clean:
                                parts = line_clean.split(":", 1)
                                label = parts[0].upper()
                                val = parts[1].strip()
                                
                                if "NAMA" in label and "BARANG" in label:
                                    nama_barang = val
                                elif "KODE" in label and "BARANG" in label:
                                    kode_barang = val
                                elif "SATUAN" in label:
                                    # Bersihkan kata SATUAN jika nempel di nilai
                                    satuan = re.sub(r'SATUAN$', '', val, flags=re.IGNORECASE).strip()
                    except Exception:
                        pass
                    
                    # FALLBACK 2: Jika pdfplumber tetep ga dapet, pake Regex Luas
                    if nama_barang == "-":
                        m = re.search(r'Nama\s*Barang\s*:\s*(.+)', text, re.IGNORECASE)
                        if m: nama_barang = m.group(1).split("Kode")[0].strip()
                        
                    if kode_barang == "-":
                        m = re.search(r'Kode\s*Barang\s*:\s*([\d\.]+)', text, re.IGNORECASE)
                        if m: kode_barang = m.group(1).strip()
                        
                    if satuan == "-":
                        m = re.search(r'Satuan\s*:\s*([A-Za-z0-9]+)', text, re.IGNORECASE)
                        if m: satuan = m.group(1).strip()

                    lines = [l.strip() for l in text.split("\n") if l.strip()]

                    rows_data = []
                    no_counter = 1
                    ada_transaksi_nyata = False
                    
                    for line in lines:
                        line_lower = line.lower()
                        
                        if any(k in line_lower for k in ["kantor imigrasi", "kartu manual", "nama barang", "kode barang", "halaman", "kondisi barang", "jumlah masuk"]):
                            continue
                            
                        if "saldo awal" in line_lower or "pembelian" in line_lower or "habis pakai" in line_lower:
                            
                            ket = ""
                            if "saldo awal" in line_lower:
                                ket = "Saldo Awal"
                            elif "pembelian" in line_lower:
                                ket = "Pembelian"
                            elif "habis pakai" in line_lower:
                                ket = "Habis Pakai"
                            
                            numbers = re.findall(r'[\d\.\,]+', line)
                            
                            tgl = ""
                            m_jml = m_hrg = k_jml = k_hrg = s_jml = s_rp = ""
                            
                            tgl_match = re.search(r'\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}', line)
                            if tgl_match:
                                tgl = tgl_match.group(0)

                            if "saldo awal" in line_lower:
                                if len(numbers) >= 2:
                                    s_jml = numbers[-2]
                                    s_rp = numbers[-1]
                                elif len(numbers) == 1:
                                    s_jml = numbers[0]
                                
                                clean_s_jml = s_jml.replace(',', '').replace('.', '').strip()
                                if clean_s_jml in ["0", ""]:
                                    continue
                                    
                            else:
                                if "pembelian" in line_lower:
                                    if len(numbers) >= 4:
                                        m_jml = numbers[0]
                                        m_hrg = numbers[1]
                                        s_jml = numbers[-2]
                                        s_rp = numbers[-1]
                                elif "habis pakai" in line_lower:
                                    if len(numbers) >= 4:
                                        k_jml = numbers[0]
                                        k_hrg = numbers[1]
                                        s_jml = numbers[-2]
                                        s_rp = numbers[-1]

                            ada_transaksi_nyata = True
                            rows_data.append([no_counter, tgl, ket, m_jml, m_hrg, k_jml, k_hrg, s_jml, s_rp, "Baik"])
                            no_counter += 1

                    if not ada_transaksi_nyata:
                        continue

                    # Pad baris kosong sampai 24
                    while no_counter <= 24:
                        rows_data.append([no_counter, "", "", "", "", "", "", "", "", ""])
                        no_counter += 1

                    # Generate Halaman PDF
                    pdf_out.generate_page(nama_barang, kode_barang, satuan, rows_data)
                    halaman_lolos += 1

            pdf_plumber_obj.close()

            if halaman_lolos > 0:
                pdf_bytes_output = pdf_out.output()
                
                st.balloons()
                st.success(f"Selesai! Berhasil memproses {halaman_lolos} barang aktif secara instan!")
                
                st.download_button(
                    label="📥 DOWNLOAD PDF ULTRA FAST RESULT",
                    data=bytes(pdf_bytes_output),
                    file_name="Kartu_Manual_Persediaan_Fast.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Nggak ada transaksi bernilai yang ditemukan di file PDF ini, bro.")
