import io
import re
import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(
    page_title="Konverter Kartu Persediaan Manual BMN", layout="wide"
)

st.title("📦 Generator Kartu Persediaan Manual BMN (Sesuai Format Baku)")
st.markdown(
    "Unggah PDF Laporan Persediaan SAKTI/SIMAN (300+ halaman). Aplikasi akan"
    " menggabungkan barang yang terpecah di banyak halaman, merunut nomor"
    " urutnya, dan menyusun format sesuai kartu manual."
)

uploaded_file = st.file_uploader(
    "Pilih file PDF Laporan Persediaan", type=["pdf"]
)


def extract_and_merge_inventory(pdf_file):
  # Dictionary untuk menampung data berdasarkan Kode Barang
  items_dict = {}

  with pdfplumber.open(pdf_file) as pdf:
    total_pages = len(pdf.pages)
    progress_bar = st.progress(0)
    status_text = st.empty()

    current_kode = "UMUM"
    current_nama = "Persediaan Umum"
    current_satuan = "Buah"

    for idx, page in enumerate(pdf.pages):
      status_text.text(
          f"Menganalisis halaman {idx + 1} dari {total_pages}..."
      )
      progress_bar.progress((idx + 1) / total_pages)

      text = page.extract_text() or ""

      # Deteksi metadata barang jika ada di halaman ini
      m_nama = re.search(r"NAMA BARANG\s*:\s*(.*)", text)
      m_kode = re.search(r"KODE BARANG\s*:\s*(.*)", text)
      m_sat = re.search(r"SATUAN\s*:\s*(.*)", text)

      if m_kode:
        current_kode = m_kode.group(1).strip()
      if m_nama:
        current_nama = m_nama.group(1).strip()
      if m_sat:
        current_satuan = m_sat.group(1).strip()

      # Jika barang belum ada di kamus, buat wadahnya
      if current_kode not in items_dict:
        items_dict[current_kode] = {
            "nama_barang": current_nama,
            "kode_barang": current_kode,
            "satuan": current_satuan,
            "rows": [],
        }

      # Ambil tabel transaksi di halaman ini
      tables = page.extract_tables()
      for table in tables:
        for row in table:
          cleaned = [
              cell.replace("\n", " ").strip() if cell else "" for cell in row
          ]

          # Pastikan baris memiliki kolom data transaksi yang valid
          if len(cleaned) >= 11:
            no_raw = cleaned[0]
            tgl = cleaned[1]
            ket = cleaned[2]
            no_dok = cleaned[3] if len(cleaned) > 3 else ""

            # Lewati baris header tabel yang berulang
            if (
                "No" in no_raw
                or "Tanggal" in tgl
                or "Keterangan" in ket
                or "Saldo" in ket
            ):
              continue

            if no_dok and no_dok.lower() not in ["", "no dok", "-"]:
              ket_full = f"{ket} (No. Dok: {no_dok})"
            else:
              ket_full = ket

            jml_masuk = cleaned[4] if len(cleaned) > 4 else "0"
            hrg_masuk = cleaned[5] if len(cleaned) > 5 else "0"
            jml_keluar = cleaned[7] if len(cleaned) > 7 else "0"
            hrg_keluar = cleaned[8] if len(cleaned) > 8 else "0"
            saldo_unit = cleaned[10] if len(cleaned) > 10 else "0"
            saldo_nilai = cleaned[11] if len(cleaned) > 11 else "0"

            # Ambil harga satuan yang aktif
            harga_satuan = (
                hrg_masuk
                if hrg_masuk not in ["", "0", "0.00", "-"]
                else hrg_keluar
            )
            if not harga_satuan or harga_satuan in ["", "-"]:
              harga_satuan = "0"

            # Masukkan ke baris barang aktif
            if (
                no_raw.isdigit()
                or "Saldo Awal" in ket
                or "Pembelian" in ket
                or "Habis" in ket
            ):
              items_dict[current_kode]["rows"].append({
                  "Tanggal": tgl,
                  "Keterangan": ket_full,
                  "Jumlah Masuk": jml_masuk,
                  "Harga Satuan (Masuk)": harga_satuan,
                  "Jumlah Keluar": jml_keluar,
                  "Harga Satuan (Keluar)": harga_satuan,
                  "Saldo Jumlah": saldo_unit,
                  "Saldo Nilai (Rp)": saldo_nilai,
                  "Kondisi Barang": "Baik (B)",
              })

    progress_bar.empty()
    status_text.empty()

  return list(items_dict.values())


if uploaded_file is not None:
  if st.button("🚀 Proses dan Format Dokumen"):
    with st.spinner(
        "Sedang menggabungkan halaman terpecah dan merunut perhitungan..."
    ):
      all_inventory_data = extract_and_merge_inventory(uploaded_file)

      st.success(
          f"Berhasil merunut data! Ditemukan {len(all_inventory_data)} jenis"
          " barang."
      )

      # Buat file Excel dengan format rapi dan penomoran berurutan
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for item in all_inventory_data:
          rows = item["rows"]
          if not rows:
            continue

          # Berikan nomor urut yang dirunut ulang dari 1 secara otomatis
          for i, r in enumerate(rows, start=1):
            r["No"] = i

          # Susun urutan kolom persis seperti format manual
          df = pd.DataFrame(rows)
          df = df[[
              "No",
              "Tanggal",
              "Keterangan",
              "Jumlah Masuk",
              "Harga Satuan (Masuk)",
              "Jumlah Keluar",
              "Harga Satuan (Keluar)",
              "Saldo Jumlah",
              "Saldo Nilai (Rp)",
              "Kondisi Barang",
          ]]

          # Buat nama sheet aman (maksimal 28 karakter)
          safe_title = (
              re.sub(r'[\\/*?:"<>|]', "", item["nama_barang"])[:28]
              .strip()
              .upper()
          )
          if not safe_title:
            safe_title = "BARANG"

          # Tulis header informasi barang di atas tabel Excel
          header_info = pd.DataFrame([
              ["Buku / Kartu Persediaan Manual", "", "", "", "", "", "", "", "", ""],
              [f"Nama Barang : {item['nama_barang']}", "", "", "", "", "", "", "", "", ""],
              [f"Kode Barang : {item['kode_barang']}", "", "", "", "", "", "", "", "", ""],
              [f"Satuan : {item['satuan']}", "", "", "", "", "", "", "", "", ""],
              ["", "", "", "", "", "", "", "", "", ""],
          ])
          header_info.to_excel(
              writer,
              sheet_name=safe_title,
              index=False,
              header=False,
              startrow=0,
          )

          # Tulis data tabel transaksi di bawah header
          df.to_excel(writer, sheet_name=safe_title, index=False, startrow=5)

      excel_data = output.getvalue()

      st.download_button(
          label="📥 Download Excel (Format Kartu Manual Sesuai Gambar)",
          data=excel_data,
          file_name="Kartu_Persediaan_Manual_Terformat.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )
