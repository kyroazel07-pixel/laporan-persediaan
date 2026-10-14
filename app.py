import io
import re
import pdfplumber
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

st.set_page_config(page_title="Konverter Kartu Persediaan Manual", layout="wide")

st.title("📄 Generator PDF Kartu Persediaan Manual (Portrait - Final)")
st.markdown(
    "Pembaruan pada indeks kolom **Saldo Nilai (Rp)** agar mengambil total"
    " nominal rupiah yang benar dari laporan SAKTI, serta penyesuaian lebar"
    " kolom agar tulisan tidak turun."
)

uploaded_file = st.file_uploader("Pilih file PDF Laporan Persediaan", type=["pdf"])


def extract_and_merge_inventory(pdf_file):
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

      m_nama = re.search(r"NAMA BARANG\s*:\s*(.*)", text)
      m_kode = re.search(r"KODE BARANG\s*:\s*(.*)", text)
      m_sat = re.search(r"SATUAN\s*:\s*(.*)", text)

      if m_kode:
        current_kode = m_kode.group(1).strip()
      if m_nama:
        current_nama = m_nama.group(1).strip()
      if m_sat:
        current_satuan = m_sat.group(1).strip()

      if current_kode not in items_dict:
        items_dict[current_kode] = {
            "nama_barang": current_nama,
            "kode_barang": current_kode,
            "satuan": current_satuan,
            "rows": [],
        }

      tables = page.extract_tables()
      for table in tables:
        for row in table:
          cleaned = [
              cell.replace("\n", " ").strip() if cell else "" for cell in row
          ]

          # Pastikan baris memiliki kolom data transaksi yang lengkap
          if len(cleaned) >= 12:
            no_raw = cleaned[0]
            tgl = cleaned[1]
            ket = cleaned[2]
            no_dok = cleaned[3] if len(cleaned) > 3 else ""

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

            # Ambil data transaksi Masuk & Keluar
            jml_masuk = cleaned[4] if len(cleaned) > 4 else "0"
            hrg_masuk = cleaned[5] if len(cleaned) > 5 else "0"
            jml_keluar = cleaned[7] if len(cleaned) > 7 else "0"
            hrg_keluar = cleaned[8] if len(cleaned) > 8 else "0"

            # Ambil Saldo Unit dan Total Saldo Nilai (Rupiah) yang benar
            saldo_unit = cleaned[10] if len(cleaned) > 10 else "0"
            # Indeks 12 adalah total nilai rupiah pada laporan SAKTI
            saldo_nilai = (
                cleaned[12]
                if len(cleaned) > 12
                else (cleaned[11] if len(cleaned) > 11 else "0")
            )

            # Harga satuan aktif
            harga_satuan = (
                hrg_masuk
                if hrg_masuk not in ["", "0", "0.00", "-"]
                else hrg_keluar
            )
            if not harga_satuan or harga_satuan in ["", "-"]:
              harga_satuan = "0"

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
                  "Harga Satuan": harga_satuan,
                  "Jumlah Keluar": jml_keluar,
                  "Harga Satuan Keluar": harga_satuan,
                  "Saldo Jumlah": saldo_unit,
                  "Saldo Nilai": saldo_nilai,
                  "Kondisi Barang": "Baik (B)",
              })

    progress_bar.empty()
    status_text.empty()

  return list(items_dict.values())


if uploaded_file is not None:
  if st.button("🚀 Generate PDF Final (Portrait & Akurat)"):
    with st.spinner("Sedang menyusun PDF..."):
      all_inventory_data = extract_and_merge_inventory(uploaded_file)

      pdf_buffer = io.BytesIO()
      # Orientasi Portrait A4 dengan margin optimal (20 pt)
      doc = SimpleDocTemplate(
          pdf_buffer,
          pagesize=A4,
          rightMargin=20,
          leftMargin=20,
          topMargin=25,
          bottomMargin=25,
      )

      story = []
      styles = getSampleStyleSheet()

      title_style = ParagraphStyle(
          'CardTitle',
          parent=styles['Normal'],
          fontName='Helvetica-Bold',
          fontSize=11,
          leading=13,
      )
      normal_style = ParagraphStyle(
          'CardNormal',
          parent=styles['Normal'],
          fontName='Helvetica',
          fontSize=7,
          leading=8.5,
      )
      center_style = ParagraphStyle(
          'CardCenter',
          parent=styles['Normal'],
          fontName='Helvetica',
          fontSize=7,
          leading=8.5,
          alignment=1,
      )
      header_cell_style = ParagraphStyle(
          'CardHeader',
          parent=styles['Normal'],
          fontName='Helvetica-Bold',
          fontSize=7,
          leading=8.5,
          alignment=1,
      )

      for idx, item in enumerate(all_inventory_data):
        rows = item["rows"]
        if not rows:
          continue

        # Header Identitas Barang
        story.append(
            Paragraph("<b>Buku / Kartu Persediaan Manual</b>", title_style)
        )
        story.append(Spacer(1, 3))
        story.append(
            Paragraph(
                f"<b>Nama Barang :</b> {item['nama_barang']}", normal_style
            )
        )
        story.append(
            Paragraph(
                f"<b>Kode Barang :</b> {item['kode_barang']}", normal_style
            )
        )
        story.append(
            Paragraph(f"<b>Satuan :</b> {item['satuan']}", normal_style)
        )
        story.append(Spacer(1, 5))

        # Tabel 10 Kolom
        table_data = [
            [
                Paragraph("<b>No</b>", header_cell_style),
                Paragraph("<b>Tanggal</b>", header_cell_style),
                Paragraph("<b>Keterangan</b>", header_cell_style),
                Paragraph("<b>Jumlah Masuk</b>", header_cell_style),
                Paragraph("<b>Harga Satuan</b>", header_cell_style),
                Paragraph("<b>Jumlah Keluar</b>", header_cell_style),
                Paragraph("<b>Harga Satuan</b>", header_cell_style),
                Paragraph("<b>Saldo Jumlah</b>", header_cell_style),
                Paragraph("<b>Saldo Nilai (Rp)</b>", header_cell_style),
                Paragraph("<b>Kondisi Barang</b>", header_cell_style),
            ],
            [
                Paragraph("<b>(1)</b>", center_style),
                Paragraph("<b>(2)</b>", center_style),
                Paragraph("<b>(3)</b>", center_style),
                Paragraph("<b>(4)</b>", center_style),
                Paragraph("<b>(5)</b>", center_style),
                Paragraph("<b>(6)</b>", center_style),
                Paragraph("<b>(7)</b>", center_style),
                Paragraph("<b>(8)=(4)-(6)</b>", center_style),
                Paragraph("<b>(9)=(8)x(5)</b>", center_style),
                Paragraph("<b>(10)</b>", center_style),
            ],
        ]

        for i, r in enumerate(rows, start=1):
          table_data.append([
              Paragraph(str(i), center_style),
              Paragraph(str(r["Tanggal"]), center_style),
              Paragraph(str(r["Keterangan"]), normal_style),
              Paragraph(str(r["Jumlah Masuk"]), center_style),
              Paragraph(str(r["Harga Satuan"]), center_style),
              Paragraph(str(r["Jumlah Keluar"]), center_style),
              Paragraph(str(r["Harga Satuan Keluar"]), center_style),
              Paragraph(str(r["Saldo Jumlah"]), center_style),
              Paragraph(str(r["Saldo Nilai"]), center_style),
              Paragraph(str(r["Kondisi Barang"]), center_style),
          ])

        # Lebar proporsional pas untuk A4 Portrait (Total ~555 pt) agar teks tidak turun
        col_widths = [22, 52, 135, 45, 55, 45, 55, 45, 65, 37]
        t = Table(table_data, colWidths=col_widths, repeatRows=2)
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 1), colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ])
        )

        story.append(t)

        if idx < len(all_inventory_data) - 1:
          story.append(PageBreak())

      doc.build(story)
      pdf_data = pdf_buffer.getvalue()

      st.success("Berhasil! PDF Final siap diunduh.")
      st.download_button(
          label="📥 Download PDF Kartu Persediaan Final",
          data=pdf_data,
          file_name="Kartu_Persediaan_Manual_Final.pdf",
          mime="application/pdf",
      )
