def get_pdf_css(is_handwritten=False):
    font_family = "'Courier New', Courier, monospace" if is_handwritten else "Arial, Helvetica, sans-serif"
    font_size_body = "8.5pt" if is_handwritten else "8pt"
    
    return f"""
    <style>
        @page {{ 
            size: A4 portrait; 
            margin: 10mm 8mm; 
        }}
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: {font_family}; 
            font-size: {font_size_body}; 
            color: #000;
            margin: 0; padding: 0;
        }}
        .page {{ page-break-after: always; }}
        .page:last-child {{ page-break-after: avoid; }}
        .header-title {{ 
            text-align: center; 
            font-size: 10.5pt; 
            font-weight: bold; 
            margin-bottom: 12px; 
            line-height: 1.3;
        }}
        .meta-info {{ margin-bottom: 10px; font-size: 9pt; }}
        .meta-table {{ border-collapse: collapse; }}
        .meta-table td {{ border: none; padding: 1px 0; vertical-align: top; }}
        table.main-table {{ 
            width: 100%; border-collapse: collapse; table-layout: fixed; 
        }}
        table.main-table th, table.main-table td {{ 
            border: 1px solid #000; padding: 4px 2px; text-align: center; 
            word-wrap: break-word; vertical-align: middle; font-size: 7.5pt;
        }}
        table.main-table th {{ font-weight: bold; background-color: #ffffff; }}
    </style>
    """

def render_pdf_html(pages_data, is_handwritten=False):
    css = get_pdf_css(is_handwritten)
    html = f"<!DOCTYPE html><html><head>{css}</head><body>"
    
    for item in pages_data:
        rows_html = ""
        no_counter = 1
        
        for r in item["rows"]:
            rows_html += f"""
            <tr>
                <td style="width: 4%;">{r['no']}</td>
                <td style="width: 11%;">{r['tgl']}</td>
                <td style="width: 20%;">{r['ket']}</td>
                <td style="width: 7%;">{r['m_jml']}</td>
                <td style="width: 9%;">{r['m_hrg']}</td>
                <td style="width: 7%;">{r['k_jml']}</td>
                <td style="width: 9%;">{r['k_hrg']}</td>
                <td style="width: 7%;">{r['s_jml']}</td>
                <td style="width: 18%;">{r['s_rp']}</td>
                <td style="width: 8%;">{r['kondisi']}</td>
            </tr>
            """
            no_counter += 1
            
        while no_counter <= 24:
            rows_html += f"""
            <tr>
                <td style="width: 4%;">{no_counter}</td>
                <td style="width: 11%;"></td><td style="width: 20%;"></td>
                <td style="width: 7%;"></td><td style="width: 9%;"></td>
                <td style="width: 7%;"></td><td style="width: 9%;"></td>
                <td style="width: 7%;"></td><td style="width: 18%;"></td>
                <td style="width: 8%;"></td>
            </tr>
            """
            no_counter += 1

        html += f"""
        <div class="page">
            <div class="header-title">
                KARTU MANUAL PERSEDIAAN<br>KANTOR IMIGRASI KELAS II TPI KUALA TUNGKAL
            </div>
            <div class="meta-info">
                <table class="meta-table">
                    <tr><td style="width: 110px;">Nama Barang</td><td style="width: 15px;">:</td><td>{item['nama_barang']}</td></tr>
                    <tr><td>Kode Barang</td><td>:</td><td>{item['kode_barang']}</td></tr>
                    <tr><td>Satuan</td><td>:</td><td>{item['satuan']}</td></tr>
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
                        <th>(1)</th><th>(2)</th><th>(3)</th><th>(4)</th><th>(5)</th>
                        <th>(6)</th><th>(7)</th><th>(8)</th><th>(9)</th><th>(10)</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """
    html += "</body></html>"
    return html
