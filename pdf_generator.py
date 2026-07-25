# pdf_generator.py
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def build_pdf(pages_data):
    buffer = io.BytesIO()
    
    # Margin aman Kiri-Kanan 15pt
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15,
        leftMargin=15,
        topMargin=15,
        bottomMargin=15
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        alignment=1 # Center
    )
    
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )
    
    # Khusus untuk kolom Keterangan saja yang butuh auto-wrap
    ket_style = ParagraphStyle(
        'KetStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        leading=8,
        alignment=1 # Center
    )

    story = []

    for idx, item in enumerate(pages_data):
        # Header Laporan
        story.append(Paragraph("KARTU MANUAL PERSEDIAAN<br/>KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL", title_style))
        story.append(Spacer(1, 8))

        # Metadata
        meta_data = [
            [Paragraph("Nama Barang", meta_style), Paragraph(":", meta_style), Paragraph(str(item['nama_barang']), meta_style)],
            [Paragraph("Kode Barang", meta_style), Paragraph(":", meta_style), Paragraph(str(item['kode_barang']), meta_style)],
            [Paragraph("Satuan", meta_style), Paragraph(":", meta_style), Paragraph(str(item['satuan']), meta_style)]
        ]
        meta_table = Table(meta_data, colWidths=[75, 10, 470])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 6))

        # Header Tabel Utama (Pakai String Murni, BUKAN Paragraph, biar anti-crash!)
        table_data = [
            [
                "No", "Tanggal", "Keterangan", 
                "Jumlah\nMasuk", "Harga\nSatuan", 
                "Jumlah\nKeluar", "Harga\nSatuan", 
                "Saldo", "", "Kondisi\nBarang"
            ],
            [
                "", "", "", "", "", "", "",
                "Jumlah", "Nilai (Rp)", ""
            ],
            [
                "(1)", "(2)", "(3)", "(4)", "(5)", 
                "(6)", "(7)", "(8)", "(9)", "(10)"
            ]
        ]

        # Isi Baris Transaksi
        no_counter = 1
        for r in item["rows"]:
            table_data.append([
                str(r['no']),
                str(r['tgl']),
                Paragraph(str(r['ket']), ket_style), # Cuma Keterangan yang dimasukin Paragraph
                str(r['m_jml']),
                str(r['m_hrg']),
                str(r['k_jml']),
                str(r['k_hrg']),
                str(r['s_jml']),
                str(r['s_rp']),
                str(r['kondisi'])
            ])
            no_counter += 1

        # Pad sampai 24 baris
        while no_counter <= 24:
            table_data.append([
                str(no_counter), "", "", "", "", "", "", "", "", ""
            ])
            no_counter += 1

        # Ukuran Kolom Presisi Total = 550 pt (Aman banget dari batas 565 pt A4)
        col_widths = [20, 58, 115, 38, 48, 38, 48, 40, 100, 45]
        
        main_table = Table(table_data, colWidths=col_widths, repeatRows=3)

        t_style = [
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 6.5),
            
            # Font Bold khusus untuk 3 baris Header pertama
            ('FONTNAME', (0,0), (-1,2), 'Helvetica-Bold'),
            
            # Padding internal minimal
            ('LEFTPADDING', (0,0), (-1,-1), 1),
            ('RIGHTPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
            
            # SPAN Header
            ('SPAN', (0,0), (0,1)),
            ('SPAN', (1,0), (1,1)),
            ('SPAN', (2,0), (2,1)),
            ('SPAN', (3,0), (3,1)),
            ('SPAN', (4,0), (4,1)),
            ('SPAN', (5,0), (5,1)),
            ('SPAN', (6,0), (6,1)),
            ('SPAN', (7,0), (8,0)),
            ('SPAN', (9,0), (9,1)),
        ]
        main_table.setStyle(TableStyle(t_style))
        story.append(main_table)

        if idx < len(pages_data) - 1:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
