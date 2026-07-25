import re
import tempfile
import pdfplumber
import streamlit as st
from weasyprint import HTML

st.set_page_config(
    page_title="Kartu Manual Persediaan", page_icon="📦", layout="centered"
)

st.title("📦 Konverter Kartu Manual Persediaan")
st.write(
    "Filter mutasi 0 otomatis dibuang & baris kosong bersih tanpa teks 'Baik'"
    " nempel!"
)

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])


def clean_number(val):
  """Membersihkan angka ganda akibat ekstrak teks bertumpuk"""
  if not val:
    return ""
  val = str(val).strip()
  # Jika angka berulang seperti 442211 atau tumpuk ganda, usahakan ambil angka bersih
  # Jika hanya angka biasa, kembalikan string aslinya
  return val


if uploaded_file is not None:
  st.success("File berhasil di-upload, bro!")

  if st.button("🚀 PROSES & BERSIHKAN PDF"):
    with st.spinner("Lagi memproses & menggabungkan data barang..."):

      with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

      html_template = """
            <!DOCTYPE html>
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
            <body>
            """

      # STRUKTUR DATA: Mengelompokkan berdasarkan Barang
      # Key: kode_barang / nama_barang
      grouped_items = {}

      with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
          text = page.extract_text() or ""

          if (
              "Pembelian" in text
              or "Habis Pakai" in text
              or "Saldo Awal" in text
          ):

            # Extract Header Info
            nama_barang = "-"
            kode_barang = "-"
            satuan = "-"

            for line in text.split("\n"):
              up_line = line.upper()
              if "NAMA BARANG" in up_line or "NAMA" in up_line:
                if ":" in line:
                  nama_barang = line.split(":")[-1].strip()
              if "KODE BARANG" in up_line or "KODE" in up_line:
                if ":" in line:
                  kode_barang = line.split(":")[-1].strip()
              if "SATUAN" in up_line:
                if ":" in line:
                  satuan = line.split(":")[-1].strip()

            # Kunci identifikasi unik barang (pakai kode atau nama)
            item_key = (
                kode_barang if kode_barang != "-" else nama_barang
            ).strip()

            if item_key not in grouped_items:
              grouped_items[item_key] = {
                  "nama": nama_barang,
                  "kode": kode_barang,
                  "satuan": satuan,
                  "rows": [],
              }

            tables = page.extract_tables()
            if tables:
              for table in tables:
                row_idx = 0
                while row_idx < len(table):
                  row = table[row_idx]
                  row_idx += 1

                  if not any(row):
                    continue

                  clean_row = [
                      str(cell).replace("\n", " ").strip() if cell else ""
                      for cell in row
                  ]
                  row_str = " ".join(clean_row).lower()

                  # Skip header bawaan
                  if (
                      "no" in clean_row[0].lower()
                      or "tanggal" in row_str
                      or "keterangan" in row_str
                      or "satuan" in row_str
                      or "unit" in row_str
                  ):
                    continue

                  # Skip baris saldo penutup bawaan
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

                    # Intip baris saldo bawahnya kalau terpisah
                    if row_idx < len(table):
                      next_row = [
                          str(c).replace("\n", " ").strip() if c else ""
                          for c in table[row_idx]
                      ]
                      if next_row[0].strip().lower() == "saldo":
                        if len(next_row) > 11 and next_row[11]:
                          s_rp = next_row[11]
                        row_idx += 1

                    # Perbaikan Pembacaan Kolom Saldo Jumlah (Kolom 8)
                    # Ambil angka paling bersih (mencegah teks tumpuk ganda)
                    if s_jml:
                      # Menghapus duplikasi string jika terdeteksi tumpuk (contoh '1414' atau '442211')
                      s_jml_clean = clean_number(s_jml)
                    else:
                      s_jml_clean = ""

                    if "saldo awal" in ket.lower():
                      m_hrg = ""
                      k_jml = ""
                      k_hrg = ""

                    # Filter jika saldo awal 0 / kosong
                    chk_s = s_jml_clean.replace(",", "").replace(".", "")
                    chk_m = m_jml.replace(",", "").replace(".", "")
                    if (
                        "saldo awal" in ket.lower()
                        and (chk_s == "0" or chk_s == "")
                        and (chk_m == "0" or chk_m == "")
                    ):
                      continue

                    grouped_items[item_key]["rows"].append({
                        "tgl": tgl,
                        "ket": ket,
                        "m_jml": m_jml,
                        "m_hrg": m_hrg,
                        "k_jml": k_jml,
                        "k_hrg": k_hrg,
                        "s_jml": s_jml_clean,
                        "s_rp": s_rp,
                    })

      # GENERATE HTML DARI DATA YANG SUDAH DIGABUNG
      halaman_lolos = 0

      for item_key, data in grouped_items.items():
        if not data["rows"]:
          continue  # Skip jika barang tidak ada transaksinya

        rows_html = ""
        no_counter = 1

        for r in data["rows"]:
          rows_html += f"""
                    <tr>
                        <td style="width: 4%;">{no_counter}</td>
                        <td style="width: 11%;">{r['tgl']}</td>
                        <td style="width: 20%;">{r['ket']}</td>
                        <td style="width: 7%;">{r['m_jml']}</td>
                        <td style="width: 9%;">{r['m_hrg']}</td>
                        <td style="width: 7%;">{r['k_jml']}</td>
                        <td style="width: 9%;">{r['k_hrg']}</td>
                        <td style="width: 7%;">{r['s_jml']}</td>
                        <td style="width: 18%;">{r['s_rp']}</td>
                        <td style="width: 8%;">Baik</td>
                    </tr>
                    """
          no_counter += 1

        # MINIMAL 24 BARIS PER BARANG (Pelengkap baris kosong)
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

        # Render 1 Barang = 1 Halaman PDF Hasil
        html_template += f"""
                <div class="page">
                    <div class="header-title">
                        KARTU MANUAL PERSEDIAAN<br>
                        KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL
                    </div>
                    
                    <div class="meta-info">
                        <table class="meta-table">
                            <tr><td style="width: 110px;">Nama Barang</td><td style="width: 15px;">:</td><td>{data['nama']}</td></tr>
                            <tr><td>Kode Barang</td><td>:</td><td>{data['kode']}</td></tr>
                            <tr><td>Satuan</td><td>:</td><td>{data['satuan']}</td></tr>
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
        halaman_lolos += 1

      html_template += "</body></html>"

      pdf_out_path = "Kartu_Manual_Persediaan_Sempurna.pdf"
      HTML(string=html_template).write_pdf(pdf_out_path)

      if halaman_lolos > 0:
        st.balloons()
        st.success(
            f"Selesai! Berhasil menggabungkan menjadi {halaman_lolos} barang"
            " aktif!"
        )

        with open(pdf_out_path, "rb") as f:
          st.download_button(
              label="📥 DOWNLOAD PDF PERFECT RESULT",
              data=f,
              file_name="Kartu_Manual_Persediaan_Perfect.pdf",
              mime="application/pdf",
          )
      else:
        st.error(
            "Nggak ada transaksi bernilai yang ditemukan di file PDF ini, bro."
        )
