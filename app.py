import io
import re
import streamlit as st
from pypdf import PdfReader
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
        # Total Lebar = 194 mm
        col_w = [8, 20, 38, 14, 18, 14, 18, 14, 34, 16] 
        
        self.set_font("Arial", '', 7.5)
        
        # Row 1 Header
        x_start = self.get_x()
        y_start = self.get_y()

        # Cell dengan rowspan manual (tinggi 12mm)
        self.cell(col_w[0], 12, "No", border=1, align='C')
        self.cell(col_w[1], 12, "Tanggal", border=1, align='C')
        self.cell(col_w[2], 12, "Keterangan", border=1, align='C')
        self.cell(col_w[3], 12, "Jml Masuk", border=1, align='C')
        self.cell(col_w[4], 12, "Hrg Satuan", border=1, align='C')
        self.cell(col_w[5], 12, "Jml Keluar", border=1, align='C')
        self.cell(col_w[6], 12, "Hrg Satuan", border=1, align='C')
        
        # Saldo Group Header (colspan 2)
        x_saldo = self.get_x()
        self.cell(col_w[7] + col_w[8], 6, "Saldo", border=1, align='C')
        
        # Kondisi Barang
        self.cell(col_w[9], 12, "Kondisi", border=1, align='C')
        
        # Sub-header Saldo
        self.set_xy(x_saldo, y_start + 6)
        self.cell(col_w[7], 6, "Jumlah", border=1, align='C')
        self.cell(col_w[8], 6, "Nilai (Rp)", border=1, align='C')

        # Reset posisi ke baris berikutnya
        self.set_xy(x_start, y_start + 12)

        # Sub-header Nomor Kolom (1)-(10)
        for i, w in enumerate(col_w):
            self.cell(w, 4, f"({i+1})", border=1, align='C')
        self.ln(4)

        # --- BODY TABEL (24 BARIS) ---
        self.set_font("Arial", '', 7)
        for row in rows_data:
            for i, val in enumerate(row):
                # Alignment khusus
                align_code = 'C'
                if i in [2]: # Keterangan rata kiri
                    align_code = 'L'
                elif i in [3, 4, 5, 6, 7, 8]: # Angka rata kanan
                    align_code = 'R'

                self.cell(col_w[i], 4.5, str(val), border=1, align=align_code)
            self.ln(4.5)


st.set_page_config(page_title="Kartu Manual Persediaan", page_icon="⚡", layout="centered")

st.title("⚡ Konverter Kartu Manual Persediaan (Ultra Fast)")
st.write("Versi paling cepat & ringan. Filter mutasi 0 otomatis dibuang!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES KILAT (INSTANT)"):
        with st.spinner("Sedang memproses secara instan..."):
            
            pdf_bytes = uploaded_file.read()
            reader = PdfReader(io.BytesIO(pdf_bytes))

            pdf_out = KartuPDF()
            halaman_lolos = 0
            
            for page in reader.pages:
                text = page.extract_text() or ""
                
                # FILTER 1: Cek transaksi
                if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
                    
                    nama_barang = "-"
                    kode_barang = "-"
                    satuan = "-"
                    
                    # Regex Header Extraction
                    nama_match = re.search(r'Nama\s*Barang\s*:\s*([^:\n]+?)(?=\s*(?:Kode|Satuan|No|Tanggal|\n|$))', text, re.IGNORECASE)
                    if nama_match:
                        raw_nama = nama_match.group(1).strip()
                        raw_nama = re.sub(r'KANTOR\s+IMIGRASI.*$', '', raw_nama, flags=re.IGNORECASE).strip()
                        if raw_nama:
                            nama_barang = raw_nama

                    kode_match = re.search(r'Kode\s*Barang\s*:\s*([\d\.]+)', text, re.IGNORECASE)
                    if kode_match:
                        kode_barang = kode_match.group(1).strip()

                    satuan_match = re.search(r'Satuan\s*:\s*([A-Za-z0-9]+)', text, re.IGNORECASE)
                    if satuan_match:
                        raw_satuan = satuan_match.group(1).strip()
                        satuan = re.sub(r'SATUAN$', '', raw_satuan, flags=re.IGNORECASE).strip()

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

            if halaman_lolos > 0:
                # Output PDF ke Bytes Buffer
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
