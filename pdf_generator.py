# pdf_generator.py
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def build_pdf(pages_data):
    buffer = io.BytesIO()
    
    # Margin Kiri-Kanan 15 pt -> Lebar area cetak A4 = 595.27 - 30 = 565.27 pt
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
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        leading=8,
        alignment=1 # Center
    )
    
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=cell_style,
        fontName='Helvetica-Bold'
    )

    story = []

    for idx, item in enumerate(pages_data):
        # Header
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

        # Header Tabel Utama (Dipecah pakai <br/> biar gak bikin crash)
        table_data = [
            [
                Paragraph("No", cell_bold), 
                Paragraph("Tanggal", cell_bold), 
                Paragraph("Keterangan", cell_bold),
                Paragraph("Jumlah<br/>Masuk", cell_bold), 
                Paragraph("Harga<br/>Satuan", cell_bold),
                Paragraph("Jumlah<br/>Keluar", cell_bold), 
                Paragraph("Harga<br/>Satuan", cell_bold),
                Paragraph("Saldo", cell_bold), "", 
                Paragraph("Kondisi<br/>Barang", cell_bold)
            ],
            [
                "", "", "", "", "", "", "",
                Paragraph("Jumlah", cell_bold), Paragraph("Nilai (Rp)", cell_bold), ""
            ],
            [
                Paragraph("(1)", cell_bold), Paragraph("(2)", cell_bold), Paragraph("(3)", cell_bold),
                Paragraph("(4)", cell_bold), Paragraph("(5)", cell_bold), Paragraph("(6)", cell_bold),
                Paragraph("(7)", cell_bold), Paragraph("(8)", cell_bold), Paragraph("(9)", cell_bold),
                Paragraph("(10)", cell_bold)
            ]
        ]

        # Rows
        no_counter = 1
        for r in item["rows"]:
            table_data.append([
                Paragraph(str(r['no']), cell_style), Paragraph(str(r['tgl']), cell_style),
                Paragraph(str(r['ket']), cell_style), Paragraph(str(r['m_jml']), cell_style),
                Paragraph(str(r['m_hrg']), cell_style), Paragraph(str(r['k_jml']), cell_style),
                Paragraph(str(r['k_hrg']), cell_style), Paragraph(str(r['s_jml']), cell_style),
                Paragraph(str(r['s_rp']), cell_style), Paragraph(str(r['kondisi']), cell_style)
            ])
            no_counter += 1

        # Pad sampai 24 baris
        while no_counter <= 24:
            table_data.append([
                Paragraph(str(no_counter), cell_style), "", "", "", "", "", "", "", "", ""
            ])
            no_counter += 1

        # Total Lebar = 550 pt (Sangat aman dari batas 565 pt)
        col_widths = [20, 58, 115, 38, 48, 38, 48, 40, 100, 45]
        
        main_table = Table(table_data, colWidths=col_widths, repeatRows=3)

        t_style = [
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            
            # Padding diset 0.5 pt biar lega
            ('LEFTPADDING', (0,0), (-1,-1), 0.5),
            ('RIGHTPADDING', (0,0), (-1,-1), 0.5),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            
            # SPAN
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
