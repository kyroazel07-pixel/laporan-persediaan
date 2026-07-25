# processor.py
import pdfplumber
from pdf_generator import build_pdf

def process_pdf(pdf_file_bytes):
    pages_data = []
    
    with pdfplumber.open(pdf_file_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            
            if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
                nama_barang, kode_barang, satuan = "-", "-", "-"
                
                for line in text.split("\n"):
                    if "NAMA" in line.upper() and ":" in line:
                        nama_barang = line.split(":")[-1].strip()
                    if "KODE" in line.upper() and ":" in line:
                        kode_barang = line.split(":")[-1].strip()
                    if "SATUAN" in line.upper() and ":" in line:
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
                            if not any(row): continue
                                
                            clean_row = [str(cell).replace('\n', ' ').strip() if cell else '' for cell in row]
                            row_str = " ".join(clean_row).lower()
                            
                            if "no" in clean_row[0].lower() or "tanggal" in row_str or "keterangan" in row_str or "unit" in row_str:
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
                                    m_hrg, k_jml, k_hrg = "", "", ""

                                clean_s_jml = s_jml.replace(',', '').replace('.', '').strip()
                                clean_m_jml = m_jml.replace(',', '').replace('.', '').strip()
                                
                                if "saldo awal" in ket.lower() and (clean_s_jml in ["0", ""]) and (clean_m_jml in ["0", ""]):
                                    continue

                                ada_transaksi_nyata = True
                                rows_data.append({
                                    "no": no_counter, "tgl": tgl, "ket": ket,
                                    "m_jml": m_jml, "m_hrg": m_hrg, "k_jml": k_jml, "k_hrg": k_hrg,
                                    "s_jml": s_jml, "s_rp": s_rp, "kondisi": "Baik"
                                })
                                no_counter += 1

                if ada_transaksi_nyata:
                    pages_data.append({
                        "nama_barang": nama_barang, "kode_barang": kode_barang,
                        "satuan": satuan, "rows": rows_data
                    })

    if not pages_data:
        return None

    # Generate PDF dengan ReportLab (Instant Mode)
    return build_pdf(pages_data)
