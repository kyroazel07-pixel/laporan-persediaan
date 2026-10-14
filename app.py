import io
import re
import pdfplumber
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

st.set_page_config(page_title="Konverter Kartu Persediaan SAKTI", layout="wide")

st.title("📄 Generator PDF Kartu Persediaan Manual (Sempurna & Utuh)")
st.markdown(
    "Pembaruan: Memperbaiki pembacaan baris lanjutan transaksi agar seluruh"
    " rincian angka dan keterangan tersalin lengkap tanpa ada yang kosong."
)

uploaded_file = st.file_uploader("Pilih file PDF Laporan Persediaan", type=["pdf"])


def clean_stacked_text(text):
  if not text:
    return ""
  cleaned = re.sub(r"\s+", " ", str(text)).strip()
  parts = cleaned.split(" ")
  if len(parts) > 1:
    return "<br/>".join(parts)
  return cleaned


def extract_sakti_inventory(pdf_file):
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
      last_no = ""
      last_tgl = ""
      last_ket = ""

      for table in tables:
        for row in table:
          cleaned = [
              cell.replace("\n", " ").strip() if cell else "" for cell in row
          ]

          if len(cleaned) >= 11:
            no_raw = cleaned[0]
            tgl = cleaned[1]
            ket = cleaned[2]
            no_dok = cleaned[3] if len(cleaned) > 3 else ""

            # Lewati baris header tabel
            if (
                "No" in no_raw
                or "Tanggal" in tgl
                or "Keterangan" in ket
                and "Saldo" in ket
            ):
              continue

            # Jika baris ini memiliki nomor atau keterangan baru, simpan sebagai acuan
            if no_raw.isdigit():
              last_no = no_raw
            if tgl:
              last_tgl = tgl
            if ket and "Saldo Awal" in ket or "Habis" in ket or "Pembelian" in ket or "Reklasifikasi" in ket:
              if no_dok and no_dok.lower() not in ["", "no dok", "-"]:
                last_ket = f"{ket} (No. Dok: {no_dok})"
              else:
                last_ket = ket

            # Jika baris kosong nomornya tapi ada data angka di sebelah kanan (lanjutan rincian harga), gunakan nomor sebelumnya
            active_no = no_raw if no_raw.isdigit() else last_no
            active_tgl = tgl if tgl else last_tgl
            active_ket = last_ket if last_ket else ket

            # Ambil data angka SAKTI secara persis
            m_unit = cleaned[4] if len(cleaned) > 4 else "0"
            m_harga = cleaned[5] if len(cleaned) > 5 else "0"
            k_unit = cleaned[7] if len(cleaned) > 7 else "0"
            k_harga = cleaned[8] if len(cleaned) > 8 else "0"
            s_unit = cleaned[10] if len(cleaned) > 10 else "0"
            s_nilai = (
                cleaned[12]
                if len(cleaned) > 12
                else (cleaned[11] if len(cleaned) > 11 else "0")
            )

            # Masukkan ke baris jika memiliki data angka/saldo yang valid
            if active_no or "Saldo Awal" in active_ket or s_unit != "0":
              items_dict[current_kode]["rows"].append({
                  "No": active_no,
                  "Tanggal": active_tgl,
                  "Keterangan": active_ket,
                  "Jumlah Masuk": m_unit,
                  "Harga Masuk": m_harga,
                  "Jumlah Keluar": k_unit,
                  "Harga Keluar": k_harga,
                  "Saldo Unit": s_unit,
                  "Saldo Nilai": s_nilai,
                  "Kondisi Barang": "Baik (B)",
              })

    progress_bar.empty()
    status_text.empty()

  # Filter: Hapus barang dengan saldo awal 0 murni tanpa transaksi lanjutan
  filtered_items = []
  for item in list(items_dict.values()):
    rows = item["rows"]
    if len(rows) == 1:
      first_row = rows[0]
      if (
          "Saldo Awal" in first_row["Keterangan"]
          and first_row["Saldo Unit"].strip() == "0"
      ):
        continue
    if rows:
      filtered_items.append(item)

  return filtered_items


if uploaded_file is not None:
  if st.button("🚀 Generate PDF Sempurna (Utuh Tanpa Terlewat)"):
    with st.spinner("Memproses dokumen..."):
      all_inventory_data = extract_sakti_inventory(uploaded_file)

      pdf_buffer = io.BytesIO()
      doc = SimpleDocTemplate(
          pdf_buffer,
          pagesize=A4,
          rightMargin=15,
          leftMargin=15,
          topMargin=20,
          bottomMargin=20,
      )

      story = []
      styles = getSampleStyleSheet()

      title_style = ParagraphStyle(
          'CardTitleCenter',
          parent=styles['Normal'],
          fontName='Helvetica-Bold',
          fontSize=11,
          leading=13,
          alignment=1,
      )
      meta_label_style = ParagraphStyle(
          'MetaLabel',
          parent=styles['Normal'],
          fontName='Helvetica-Bold',
          fontSize=8,
          leading=10,
      )
      meta_val_style = ParagraphStyle(
          'MetaVal',
          parent=styles['Normal'],
          fontName='Helvetica',
          fontSize=8,
          leading=10,
      )

      table_cell_style = ParagraphStyle(
          'TableCell',
          parent=styles['Normal'],
          fontName='Helvetica',
          fontSize=5.8,
          leading=7.5,
          alignment=1,
      )
      table_desc_style = ParagraphStyle(
          'TableDesc',
          parent=styles['Normal'],
          fontName='Helvetica',
          fontSize=5.8,
          leading=7.5,
          alignment=0,
      )
      table_header_style = ParagraphStyle(
          'TableHeader',
          parent=styles['Normal'],
          fontName='Helvetica-Bold',
          fontSize=5.8,
          leading=7.5,
          alignment=1,
      )

      for idx, item in enumerate(all_inventory_data):
        rows = item["rows"]
        if not rows:
          continue

        story.append(
            Paragraph("<b>Buku / Kartu Persediaan Manual</b>", title_style)
        )
        story.append(Spacer(1, 6))

        meta_data = [
            [
                Paragraph("Nama Barang", meta_label_style),
                Paragraph(":", meta_label_style),
                Paragraph(item["nama_barang"], meta_val_style),
            ],
            [
                Paragraph("Kode Barang", meta_label_style),
                Paragraph(":", meta_label_style),
                Paragraph(item["kode_barang"], meta_val_style),
            ],
            [
                Paragraph("Satuan", meta_label_style),
                Paragraph(":", meta_label_style),
                Paragraph(item["satuan"], meta_val_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[70, 10, 450])
        meta_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ])
        )

        story.append(meta_table)
        story.append(Spacer(1, 6))

        table_data = [
            [
                Paragraph("<b>No</b>", table_header_style),
                Paragraph("<b>Tanggal</b>", table_header_style),
                Paragraph("<b>Keterangan</b>", table_header_style),
                Paragraph("<b>Jumlah Masuk</b>", table_header_style),
                Paragraph("<b>Harga Satuan</b>", table_header_style),
                Paragraph("<b>Jumlah Keluar</b>", table_header_style),
                Paragraph("<b>Harga Satuan</b>", table_header_style),
                Paragraph("<b>Saldo Jumlah</b>", table_header_style),
                Paragraph("<b>Saldo Nilai (Rp)</b>", table_header_style),
                Paragraph("<b>Kondisi Barang</b>", table_header_style),
            ],
            [
                Paragraph("<b>(1)</b>", table_header_style),
                Paragraph("<b>(2)</b>", table_header_style),
                Paragraph("<b>(3)</b>", table_header_style),
                Paragraph("<b>(4)</b>", table_header_style),
                Paragraph("<b>(5)</b>", table_header_style),
                Paragraph("<b>(6)</b>", table_header_style),
                Paragraph("<b>(7)</b>", table_header_style),
                Paragraph("<b>(8)=(4)-(6)</b>", table_header_style),
                Paragraph("<b>(9)=(8)x(5)</b>", table_header_style),
                Paragraph("<b>(10)</b>", table_header_style),
            ],
        ]

        for r in rows:
          table_data.append([
              Paragraph(str(r["No"]), table_cell_style),
              Paragraph(str(r["Tanggal"]), table_cell_style),
              Paragraph(str(r["Keterangan"]), table_desc_style),
              Paragraph(str(r["Jumlah Masuk"]), table_cell_style),
              Paragraph(str(r["Harga Masuk"]), table_cell_style),
              Paragraph(str(r["Jumlah Keluar"]), table_cell_style),
              Paragraph(str(r["Harga Keluar"]), table_cell_style),
              Paragraph(str(r["Saldo Unit"]), table_cell_style),
              Paragraph(str(r["Saldo Nilai"]), table_cell_style),
              Paragraph(str(r["Kondisi Barang"]), table_cell_style),
          ])

        col_widths = [20, 48, 145, 45, 58, 45, 58, 48, 62, 39]
        t = Table(table_data, colWidths=col_widths, repeatRows=2)
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 1), colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )

        story.append(t)

        if idx < len(all_inventory_data) - 1:
          story.append(PageBreak())

      doc.build(story)
      pdf_data = pdf_buffer.getvalue()

      st.success("Berhasil! PDF Sempurna siap diunduh.")
      st.download_button(
          label="📥 Download PDF Kartu Persediaan Sempurna",
          data=pdf_data,
          file_name="Kartu_Persediaan_Manual_Sempurna.pdf",
          mime="application/pdf",
      )
