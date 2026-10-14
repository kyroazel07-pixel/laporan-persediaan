import io
import re
import pdfplumber
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

st.set_page_config(page_title="Konverter Kartu Persediaan SAKTI", layout="wide")

st.title("📄 Generator PDF Kartu Persediaan Manual (Akurat & Rapi)")
st.markdown(
    "Aplikasi disempurnakan untuk memunculkan baris nomor **1 (Saldo Awal)**"
    " serta menyusun multi-layer saldo ke bawah secara vertikal persis seperti"
    " laporan SAKTI."
)

uploaded_file = st.file_uploader("Pilih file PDF Laporan Persediaan", type=["pdf"])


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

      # Ekstraksi tabel menggunakan pdfplumber
      tables = page.extract_tables()
      for table in tables:
        for row in table:
          cleaned = [
              cell.replace("\n", " ").strip() if cell else "" for cell in row
          ]

          if len(cleaned) >= 12:
            no_raw = cleaned[0]
            tgl = cleaned[1]
            ket = cleaned[2]
            no_dok = cleaned[3] if len(cleaned) > 3 else ""

            # Lewati baris header tabel yang berulang
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

            # Ambil data transaksi Masuk & Keluar
            jml_masuk = cleaned[4] if len(cleaned) > 4 else "0"
            hrg_masuk = cleaned[5] if len(cleaned) > 5 else "0"
            jml_keluar = cleaned[7] if len(cleaned) > 7 else "0"
            hrg_keluar = cleaned[8] if len(cleaned) > 8 else "0"

            # Ambil data Saldo Persediaan (mendukung multi-layer berderet ke bawah di PDF)
            saldo_unit = cleaned[10] if len(cleaned) > 10 else "0"
            saldo_harga = cleaned[11] if len(cleaned) > 11 else "0"
            saldo_nilai = cleaned[12] if len(cleaned) > 12 else "0"

            # Tangkap baris transaksi valid (termasuk nomor 1 Saldo Awal dan baris-baris lanjutannya)
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
                  "Jumlah Masuk": jml_masuk,
                  "Harga Masuk": hrg_masuk,
                  "Jumlah Keluar": jml_keluar,
                  "Harga Keluar": hrg_keluar,
                  "Saldo Unit": saldo_unit,
                  "Saldo Harga": saldo_harga,
                  "Saldo Nilai": saldo_nilai,
                  "Kondisi Barang": "Baik (B)",
              })

    progress_bar.empty()
    status_text.empty()

  return list(items_dict.values())


if uploaded_file is not None:
  if st.button("🚀 Generate PDF Sempurna (Nomor 1 & Stacked Rows)"):
    with st.spinner("Sedang memproses dokumen..."):
      all_inventory_data = extract_sakti_inventory(uploaded_file)

      pdf_buffer = io.BytesIO()
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

        # Tabel 10 Kolom Format Manual
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

        for r in rows:
          # Ubah pemisah baris newline menjadi tag <br/> agar teks multi-layer tersusun ke bawah secara rapi
          s_unit = str(r["Saldo Unit"]).replace("\n", "<br/>")
          s_harga = str(r["Saldo Harga"]).replace("\n", "<br/>")
          s_nilai = str(r["Saldo Nilai"]).replace("\n", "<br/>")

          table_data.append([
              Paragraph(str(r["No"]), center_style),
              Paragraph(str(r["Tanggal"]), center_style),
              Paragraph(str(r["Keterangan"]), normal_style),
              Paragraph(str(r["Jumlah Masuk"]), center_style),
              Paragraph(str(r["Harga Masuk"]), center_style),
              Paragraph(str(r["Jumlah Keluar"]), center_style),
              Paragraph(str(r["Harga Keluar"]), center_style),
              Paragraph(s_unit, center_style),
              Paragraph(s_nilai, center_style),
              Paragraph(str(r["Kondisi Barang"]), center_style),
          ])

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

      st.success("Berhasil! PDF Sempurna siap diunduh.")
      st.download_button(
          label="📥 Download PDF Kartu Persediaan Sempurna",
          data=pdf_data,
          file_name="Kartu_Persediaan_Manual_Sempurna.pdf",
          mime="application/pdf",
      )
