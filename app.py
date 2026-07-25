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
    "Filter mutasi 0 otomatis dibuang, penggabungan barang & kalkulasi saldo"
    " akurat!"
)

uploaded_file = st.file_uploader("Upload File PDF Mentah Lu Di Sini", type=["pdf"])


def clean_int(val):
  """Mengubah string angka PDF (termasuk koma/titik) jadi integer bersih"""
  if not val:
    return 0
  # Ambil hanya digit angka
  digits = re.sub(r"[^\d]", "", str(val))
  return int(digits) if digits else 0


def format_rupiah(val):
  """Format integer ke penulisan Rupiah standar (contoh: 1,240,000)"""
  if not val:
    return "0"
  return f"{val:,}"


if uploaded_file is not None:
  st.success("File berhasil di-upload, bro!")

  if st.button("🚀 PROSES & BERSIHKAN PDF"):
    with st.spinner("Lagi memproses, menghitung saldo & merapikan data..."):

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

      grouped_items = {}

      with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
          text = page.extract_text() or ""

          if (
              "Pembelian" in text
              or "Habis Pakai" in text
              or "Saldo Awal" in text
          ):

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
                for row in table:
                  if not any(row):
                    continue

                  clean_row = [
                      str(cell).replace("\n", " ").strip() if cell else ""
                      for cell in row
                  ]
                  row_str = " ".join(clean_row).lower()

                  # Skip header & baris footer tidak penting
                  if (
                      "no" in clean_row[0].lower()
                      or "tanggal" in row_str
                      or "keterangan" in row_str
                      or "satuan" in row_str
                      or "unit" in row_str
                      or clean_row[0].strip().lower() == "saldo"
                  ):
                    continue

                  ket = clean_row[2] if len(clean_row) > 2 else ""
                  tgl = clean_row[1] if len(clean_row) > 1 else ""

                  if ket or tgl:
                    m_jml = clean_int(
                        clean_row[4] if len(clean_row) > 4 else 0
                    )
                    m_hrg = clean_int(
                        clean_row[5] if len(clean_row) > 5 else 0
                    )
                    k_jml = clean_int(
                        clean_row[7] if len(clean_row) > 7 else 0
                    )
                    k_hrg = clean_int(
                        clean_row[8] if len(clean_row) > 8 else 0
                    )

                    # Ambil angka mentah Saldo Awal jika ini baris Saldo Awal
                    s_jml_raw = clean_int(
                        clean_row[10] if len(clean_row) > 10 else 0
                    )
                    s_rp_raw = clean_int(
                        clean_row[11] if len(clean_row) > 11 else 0
                    )

                    # Buang jika Saldo Awal nilainya 0 dan tak ada mutasi
                    if (
                        "saldo awal" in ket.lower()
                        and s_jml_raw == 0
                        and m_jml == 0
                    ):
                      continue

                    grouped_items[item_key]["rows"].append({
                        "tgl": tgl,
                        "ket": ket,
                        "m_jml": m_jml,
                        "m_hrg": m_hrg,
                        "k_jml": k_jml,
                        "k_hrg": k_hrg,
                        "s_jml_raw": s_jml_raw,
                        "s_rp_raw": s_rp_raw,
                    })

      # KALKULASI SALDO OTOMATIS & GENERATE HTML
      halaman_lolos = 0

      for item_key, data in grouped_items.items():
        if not data["rows"]:
          continue

        rows_html = ""
        no_counter = 1

        # Variable Tracker Saldo Otomatis
        running_saldo_qty = 0
        running_saldo_rp = 0
        last_known_harga = 0

        for r in data["rows"]:
          ket_lower = r["ket"].lower()

          # 1. Jika Baris Saldo Awal
          if "saldo awal" in ket_lower:
            running_saldo_qty = r[
                "s_jml_raw"
            ]  # Ambil jumlah awal asli dari PDF
            running_saldo_rp = r["s_rp_raw"]
            if running_saldo_qty > 0:
              last_known_harga = running_saldo_rp // running_saldo_qty

            m_jml_str = (
                str(r["m_jml"]) if r["m_jml"] > 0 else ""
            )  # Kadang saldo awal di kolom masuk
            m_hrg_str = ""
            k_jml_str = ""
            k_hrg_str = ""

          # 2. Jika Baris Transaksi Masuk / Keluar
          else:
            if r["m_hrg"] > 0:
              last_known_harga = r["m_hrg"]
            elif r["k_hrg"] > 0:
              last_known_harga = r["k_hrg"]

            # Hitung Saldo Baru secara Matematis
            running_saldo_qty = (
                running_saldo_qty + r["m_jml"] - r["k_jml"]
            )
            running_saldo_rp = running_saldo_qty * last_known_harga

            m_jml_str = str(r["m_jml"]) if r["m_jml"] > 0 else "0"
            m_hrg_str = format_rupiah(r["m_hrg"]) if r["m_hrg"] > 0 else "0"
            k_jml_str = str(r["k_jml"]) if r["k_jml"] > 0 else "0"
            k_hrg_str = format_rupiah(r["k_hrg"]) if r["k_hrg"] > 0 else "0"

          rows_html += f"""
                    <tr>
                        <td style="width: 4%;">{no_counter}</td>
                        <td style="width: 11%;">{r['tgl']}</td>
                        <td style="width: 20%;">{r['ket']}</td>
                        <td style="width: 7%;">{m_jml_str}</td>
                        <td style="width: 9%;">{m_hrg_str}</td>
                        <td style="width: 7%;">{k_jml_str}</td>
                        <td style="width: 9%;">{k_hrg_str}</td>
                        <td style="width: 7%;">{running_saldo_qty}</td>
                        <td style="width: 18%;">{format_rupiah(running_saldo_rp)}</td>
                        <td style="width: 8%;">Baik</td>
                    </tr>
                    """
          no_counter += 1

        # Isi baris kosong pelengkap sampai 24 baris (kondisi barang kosong)
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

      pdf_out_path = "Kartu_Manual_Persediaan_Fixed.pdf"
      HTML(string=html_template).write_pdf(pdf_out_path)

      if halaman_lolos > 0:
        st.balloons()
        st.success(
            f"Selesai! Berhasil merapikan {halaman_lolos} barang dengan"
            " kalkulasi saldo akurat!"
        )

        with open(pdf_out_path, "rb") as f:
          st.download_button(
              label="📥 DOWNLOAD PDF HASIL BARU",
              data=f,
              file_name="Kartu_Manual_Persediaan_Fix.pdf",
              mime="application/pdf",
          )
      else:
        st.error(
            "Nggak ada transaksi bernilai yang ditemukan di file PDF ini, bro."
        )
