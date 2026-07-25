import io
import re
import streamlit as st
from pypdf import PdfReader
from weasyprint import HTML

st.set_page_config(page_title="Kartu Manual Persediaan", page_icon="📦", layout="centered")

st.title("📦 Konverter Kartu Manual Persediaan")
st.write("Filter mutasi 0 otomatis dibuang & baris kosong bersih tanpa teks 'Baik' nempel!")

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])

if uploaded_file is not None:
    st.success("File berhasil di-upload, bro!")
    
    if st.button("🚀 PROSES & BERSIHKAN PDF"):
        with st.spinner("Lagi memproses & memfilter barang aktif... Tunggu sebentar ya!"):
            
            # Read direct in-memory
            pdf_bytes = uploaded_file.read()
            reader = PdfReader(io.BytesIO(pdf_bytes))

            html_parts = ["""<!DOCTYPE html>
<html>
<head>
    <style>
        @page { 
            size: A4 portrait; 
            margin: 10mm 8mm; 
        }
        * { box-sizing: border-box; }
        body { 
            font-family: Arial, Helvetica, sans-serif; 
            font-size: 8pt; 
            color: #000;
            margin: 0; padding: 0;
        }
        .page { page-break-after: always; }
        .page:last-child { page-break-after: avoid; }
        
        .header-title { 
            text-align: center; 
            font-size: 10pt; 
            font-weight: bold; 
            color: #000;
            margin-bottom: 12px; 
            line-height: 1.3;
        }
        
        .meta-info {
            margin-bottom: 10px;
            font-size: 8.5pt;
            line-height: 1.4;
        }
        .meta-table { border-collapse: collapse; }
        .meta-table td {
            border: none;
            padding: 1px 0;
            vertical-align: top;
        }
        
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
            font-size: 7.5pt;
        }
        table.main-table th { 
            font-weight: normal; 
            background-color: #ffffff; 
            font-size: 8pt;
        }
    </style>
</head>
<body>"""]
            
            halaman_lolos = 0
            
            for page in reader.pages:
                text = page.extract_text() or ""
                
                # FILTER 1: Cek transaksi
                if "Pembelian" in text or "Habis Pakai" in text or "Saldo Awal" in text:
                    
                    nama_barang = "-"
                    kode_barang = "-"
                    satuan = "-"
                    
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    
                    # Extract Metadata
                    for line in lines:
                        line_upper = line.upper()
                        if ("NAMA BARANG" in line_upper or "NAMA" in line_upper) and ":" in line:
                            nama_barang = line.split(":")[-1].strip()
                        elif ("KODE BARANG" in line_upper or "KODE" in line_upper) and ":" in line:
                            kode_barang = line.split(":")[-1].strip()
                        elif "SATUAN" in line_upper and ":" in line:
                            satuan = line.split(":")[-1].strip()

                    rows_html = []
                    no_counter = 1
                    ada_transaksi_nyata = False
                    
                    for line in lines:
                        line_lower = line.lower()
                        
                        # Skip header/footer/unnecessary text
                        if any(k in line_lower for k in ["kantor imigrasi", "kartu manual", "nama barang", "kode barang", "satuan", "halaman", "kondisi barang", "jumlah masuk"]):
                            continue
                            
                        # Cek baris transaksi (biasanya diawali nomor atau tanggal)
                        parts = re.split(r'\s{2,}', line) # Split berdasar spasi ganda/tab
                        if len(parts) < 3:
                            parts = line.split(" ")
                        
                        # Deteksi kata kunci transaksi
                        if "saldo awal" in line_lower or "pembelian" in line_lower or "habis pakai" in line_lower:
                            
                            # Ekstraksi komponen transaksi
                            ket = ""
                            if "saldo awal" in line_lower:
                                ket = "Saldo Awal"
                            elif "pembelian" in line_lower:
                                ket = "Pembelian"
                            elif "habis pakai" in line_lower:
                                ket = "Habis Pakai"
                            
                            # Ambil angka-angka dari baris ini
                            numbers = re.findall(r'[\d\.\,]+', line)
                            
                            # Filter angka versi ringkas
                            tgl = ""
                            m_jml = m_hrg = k_jml = k_hrg = s_jml = s_rp = ""
                            
                            # Cari tanggal (format dd/mm/yyyy atau sejenis)
                            tgl_match = re.search(r'\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}', line)
                            if tgl_match:
                                tgl = tgl_match.group(0)

                            if "saldo awal" in line_lower:
                                # Biasanya Saldo Awal cuma punya saldo jml & saldo rp
                                if len(numbers) >= 2:
                                    s_jml = numbers[-2]
                                    s_rp = numbers[-1]
                                elif len(numbers) == 1:
                                    s_jml = numbers[0]
                                
                                clean_s_jml = s_jml.replace(',', '').replace('.', '').strip()
                                if clean_s_jml in ["0", ""]:
                                    continue # Skip saldo awal 0
                                    
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

                            rows_html.append(f"""
                            <tr>
                                <td style="width: 4%;">{no_counter}</td>
                                <td style="width: 11%;">{tgl}</td>
                                <td style="width: 20%;">{ket}</td>
                                <td style="width: 7%;">{m_jml}</td>
                                <td style="width: 9%;">{m_hrg}</td>
                                <td style="width: 7%;">{k_jml}</td>
                                <td style="width: 9%;">{k_hrg}</td>
                                <td style="width: 7%;">{s_jml}</td>
                                <td style="width: 18%;">{s_rp}</td>
                                <td style="width: 8%;">Baik</td>
                            </tr>""")
                            no_counter += 1

                    if not ada_transaksi_nyata:
                        continue

                    # Fill sisa baris kosong sampai 24
                    while no_counter <= 24:
                        rows_html.append(f"""
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
                        </tr>""")
                        no_counter += 1

                    # Append halaman
                    html_parts.append(f"""
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
                                {"".join(rows_html)}
                            </tbody>
                        </table>
                    </div>""")
                    halaman_lolos += 1

            html_parts.append("</body></html>")
            full_html = "".join(html_parts)
            
            # Weasyprint compile directly to byte buffer
            pdf_out_buffer = io.BytesIO()
            HTML(string=full_html).write_pdf(pdf_out_buffer)
            pdf_bytes = pdf_out_buffer.getvalue()
            
            if halaman_lolos > 0:
                st.balloons()
                st.success(f"Selesai! Berhasil memproses {halaman_lolos} barang aktif secara instan!")
                
                st.download_button(
                    label="📥 DOWNLOAD PDF PERFECT RESULT",
                    data=pdf_bytes,
                    file_name="Kartu_Manual_Persediaan_Perfect.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Nggak ada transaksi bernilai yang ditemukan di file PDF ini, bro.")
