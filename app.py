import io
import re
import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(
    page_title="Konverter Kartu Persediaan BMN", layout="wide"
)

st.title("📦 Konverter Buku / Kartu Persediaan Manual BMN (Multi-Halaman)")
st.markdown(
    "Unggah file PDF Rincian Buku Persediaan (mendukung ratusan halaman). Aplikasi"
    " akan memisahkan tiap barang ke dalam Sheet Excel berbeda dengan format"
    " manual."
)

uploaded_file = st.file_uploader(
    "Pilih file PDF Laporan Persediaan SAKTI/SIMAN", type=["pdf"]
)


def process_pdf_data(pdf_file):
  all_items = []
  current_item = None

  with pdfplumber.open(pdf_file) as pdf:
    total_pages = len(pdf.pages)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, page in enumerate(pdf.pages):
      status_text.text(
          f"Memproses halaman {idx + 1} dari {total_pages}..."
      )
      progress_bar.progress((idx + 1) / total_pages)

      text = page.extract_text() or ""

      # Deteksi apakah ada informasi barang baru di halaman ini
      if "NAMA BARANG" in text or "KODE BARANG" in text:
        if current_item and current_item["rows"]:
          all_items.append(current_item)

        m_nama = re.search(r"NAMA BARANG\s*:\s*(.*)", text)
        m_kode = re.search(r"KODE BARANG\s*:\s*(.*)", text)
        m_sat = re.search(r"SATUAN\s*:\s*(.*)", text)

        nama_b = (
            m_nama.group(1).strip() if m_nama else f"Barang_{idx + 1}"
        )
        kode_b = m_kode.group(1).strip() if m_kode else "-"
        sat_b = m_sat.group(1).strip() if m_sat else "Buah"

        current_item = {
            "nama_barang": nama_b,
            "kode_barang": kode_b,
            "satuan": sat_b,
            "rows": [],
        }

      if not current_item:
        current_item = {
            "nama_barang": "Data Persediaan",
            "kode_barang": "-",
            "satuan": "-",
            "rows": [],
        }

      # Ekstraksi tabel transaksi per halaman
      tables = page.extract_tables()
      for table in tables:
        for row in table:
          cleaned = [
              cell.replace("\n", " ").strip() if cell else "" for cell in row
          ]

          # Filter baris valid (pastikan memiliki minimal kolom transaksi)
          if len(cleaned) >= 11:
            no = cleaned[0]
            tgl = cleaned[1]
            ket = cleaned[2]
            no_dok = cleaned[3] if len(cleaned) > 3 else ""

            # Lewati baris header tabel yang ikut terambil
            if (
                "No" in no
                or "Tanggal" in tgl
                or "Keterangan" in ket
                or "Saldo" in ket
            ):
              continue

            if no_dok and no_dok.lower() not in ["", "no dok", "-"]:
              ket_full = f"{ket} (No. Dok: {no_dok})"
            else:
              ket_full = ket

            # Ambil nilai Masuk, Keluar, dan Saldo sesuai standar layout SAKTI
            jml_masuk = cleaned[4] if len(cleaned) > 4 else "0"
            hrg_masuk = cleaned[5] if len(cleaned) > 5 else "0"

            jml_keluar = cleaned[7] if len(cleaned) > 7 else "0"
            hrg_keluar = cleaned[8] if len(cleaned) > 8 else "0"

            saldo_unit = cleaned[10] if len(cleaned) > 10 else "0"
            saldo_nilai = cleaned[11] if len(cleaned) > 11 else "0"

            # Ambil harga satuan aktif
            harga_satuan = (
                hrg_masuk
                if hrg_masuk not in ["", "0", "0.00", "-"]
                else hrg_keluar
            )
            if not harga_satuan or harga_satuan in ["", "-"]:
              harga_satuan = "0"

            # Masukkan ke baris data terstruktur format manual
            if no.isdigit() or "Saldo" in ket or "Pembelian" in ket or "Habis" in ket:
              current_item["rows"].append({
                  "No": no,
                  "Tanggal": tgl,
                  "Keterangan": ket_full,
                  "Jumlah Masuk": jml_masuk,
                  "Harga Satuan": harga_satuan,
                  "Jumlah Keluar": jml_keluar,
                  "Harga Satuan Keluar": harga_satuan,
                  "Saldo Jumlah": saldo_unit,
                  "Saldo Nilai (Rp)": saldo_nilai,
                  "Kondisi Barang": "Baik (B)",
              })

    if current_item and current_item["rows"]:
      all_items.append(current_item)

    progress_bar.empty()
    status_text.empty()

  return all_items


if uploaded_file is not None:
  if st.button("🚀 Proses Dokumen Sekarang"):
    with st.spinner(
        "Sedang membedah dokumen dan memisahkan data per barang..."
    ):
      items = process_pdf_data(uploaded_file)

      st.success(
          f"Berhasil! Ditemukan {len(items)} jenis barang dari file PDF Anda."
      )

      # Buat file Excel dengan multi-sheet per barang
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for item in items:
          df = pd.DataFrame(item["rows"])
          # Bersihkan karakter nama sheet yang dilarang Excel
          safe_title = (
              re.sub(r'[\\/*?:"<>|]', "", item["nama_barang"])[:28]
              .strip()
              .upper()
          )
          if not safe_title:
            safe_title = "BARANG"
          df.to_excel(writer, index=False, sheet_name=safe_title)

      excel_data = output.getvalue()

      st.download_button(
          label="📥 Download Hasil Excel (Format Kartu Manual Terpisah Per Sheet)",
          data=excel_data,
          file_name="Kartu_Persediaan_Manual_Lengkap.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )
