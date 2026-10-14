import io
import re
import pdfplumber
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

st.set_page_config(page_title="Konverter Kartu Persediaan SAKTI", layout="wide")

st.title("📄 Generator PDF Kartu Persediaan Manual (Fix Kolom Keluar)")
st.markdown(
    "Pembaruan: Memperbaiki pemetaan kolom transaksi Keluar (Unit & Harga)"
    " agar tidak kosong."
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
      for table in tables:
        for row in table:
          cleaned = [
              cell.replace("\n", " ").strip() if cell else "" for cell in row
          ]

          # SAKTI standar tabel rincian memiliki minimal 12 kolom
          if len(cleaned) >= 12:
            no_raw = cleaned[0]
            tgl = cleaned[1]
            ket = cleaned[2]
            no_dok = cleaned[3] if len(cleaned) > 3 else ""

            if (
                "No" in no_raw
                or "Tanggal" in tgl
                or "Keterangan" in ket
                and "Saldo" in ket
            ):
              continue

            if no_dok and no_dok.lower() not in ["", "no dok", "-"]:
              ket_full = f"{ket} (No. Dok: {no_dok})"
            else:
              ket_full = ket

            # Pemetaan indeks kolom SAKTI yang lebih fleksibel & akurat
            # Masuk (Unit di 4/5, Harga di 5/6)
            jml_masuk_unit = cleaned[4] if len(cleaned) > 4 else "0"
            hrg_masuk = cleaned[5] if len(cleaned) > 5 else "0"
            if jml_masuk_unit == "" and len(cleaned) > 5:
              jml_masuk_unit = cleaned[5]
              hrg_masuk = cleaned[6] if len(cleaned) > 6 else "0"

            # Keluar (Unit biasanya di index 7 atau 8, Harga di 8 atau 9)
            jml_keluar_unit = "0"
            hrg_keluar = "0"
            for idx_col in [7, 6, 8]:
              if (
                  idx_col < len(cleaned)
                  and cleaned[idx_col]
                  and cleaned[idx_col] != "0"
                  and not cleaned[idx_col].replace(",", "").isdigit() is False
              ):
                # Cek apakah ini angka unit keluar (biasanya kecil < 1000)
                val_test = cleaned[idx_col].replace(",", "")
                if val_test.isdigit() and int(val_test) < 10000:
                  jml_keluar_unit = cleaned[idx_col]
                  if idx_col + 1 < len(cleaned):
                    hrg_keluar = cleaned[idx_col + 1]
                  break

            # Fallback posisi standar SAKTI jika pencarian dinamis kosong
            if jml_keluar_unit == "0" and len(cleaned) > 7:
              jml_keluar_unit = cleaned[7] if cleaned[7] else "0"
              hrg_keluar = (
                  cleaned[8]
                  if len(cleaned) > 8 and cleaned[8]
                  else "0"
              )

            # Saldo Persediaan (Unit di belakang, Nilai Total di ujung)
            saldo_unit = cleaned[10] if len(cleaned) > 10 else "0"
            saldo_nilai = cleaned[12] if len(cleaned) > 12 else (cleaned[11] if len(cleaned) > 11 else "0")

            if (
                no_raw.isdigit()
                or "Saldo Awal" in ket
                or "Pembelian" in ket
                or "Habis" in ket
                or "Reklasifikasi" in ket
            ):
              items_dict[current_kode]["rows"].append({
                  "No": no_raw if no_raw else "",
                  "Tanggal": tgl,
                  "Keterangan": ket_full,
                  "Jumlah Masuk": clean_stacked_text(jml_masuk_unit),
                  "Harga Masuk": clean_stacked_text(hrg_masuk),
                  "Jumlah Keluar": clean_stacked_text(jml_keluar_unit),
                  "Harga Keluar": clean_stacked_text(hrg_keluar),
                  "Saldo Unit": clean_stacked_text(saldo_unit),
                  "Saldo Nilai": clean_stacked_text(saldo_nilai),
                  "Kondisi Barang": "Baik (B)",
              })

    progress_bar.empty()
    status_text.empty()

  filtered_items = []
  for item in list(items_dict.values()):
    rows = item["rows"]
    if len(rows) == 1:
      first_row = rows[0]
      if (
          "Saldo Awal" in first_row["Keterangan"]
          and first_row["Saldo Unit"].replace("<br/>", "").strip() == "0"
      ):
        continue
    if rows:
      filtered_items.append(item)

  return filtered_items


if uploaded_file is not None:
  if st.button("🚀 Generate PDF Sempurna (Fix Kolom Keluar)"):
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

      st.success("Berhasil! PDF Kartu Persediaan siap diunduh.")
      st.download_button(
          label="📥 Download PDF Kartu Persediaan",
          data=pdf_data,
          file_name="Kartu_Persediaan_Manual_Fixed.pdf",
          mime="application/pdf",
      )
