"""Server-side PDF renderer for the periodic media analysis report.

The PDF is generated from the exact same summary dictionary as the Laporan UI,
so downloaded numbers cannot drift from what the analyst reviewed on screen.
"""
from html import escape
from io import BytesIO
from unicodedata import category

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


NAVY = colors.HexColor("#0B1F33")
TEAL = colors.HexColor("#0E7C86")
POSITIVE = colors.HexColor("#2E7D5B")
NEGATIVE = colors.HexColor("#C6483F")
MUTED = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#E8EEF2")


def _text(value):
    raw = str(value or "")
    # Built-in Helvetica has no emoji glyphs. Keep the source text in the database/UI,
    # but omit pictographs and joiner/variation marks from the PDF instead of rendering
    # misleading black boxes.
    raw = "".join(
        character
        for character in raw
        if category(character) != "So" and character not in {"\u200d", "\ufe0f"}
    )
    return escape(raw).replace("\n", "<br/>")


def _pct(row, sentiment):
    return next(
        (item["pct"] for item in row["sentiment_breakdown"] if item["key"] == sentiment),
        0,
    )


def _local_date(value):
    if not value:
        return "-"
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%d/%m/%Y")


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        name="ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=NAVY, alignment=TA_CENTER, spaceAfter=7,
    ))
    base.add(ParagraphStyle(
        name="ReportSubtitle", parent=base["Normal"], fontName="Helvetica",
        fontSize=9.5, leading=13, textColor=MUTED, alignment=TA_CENTER, spaceAfter=14,
    ))
    base.add(ParagraphStyle(
        name="Section", parent=base["Heading2"], fontName="Helvetica-Bold",
        fontSize=12.5, leading=15, textColor=NAVY, spaceBefore=12, spaceAfter=7,
    ))
    base.add(ParagraphStyle(
        name="Subsection", parent=base["Heading3"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=13, textColor=TEAL, spaceBefore=8, spaceAfter=5,
    ))
    base.add(ParagraphStyle(
        name="BodySmall", parent=base["BodyText"], fontName="Helvetica",
        fontSize=8.5, leading=12, textColor=colors.HexColor("#243447"), spaceAfter=4,
    ))
    base.add(ParagraphStyle(
        name="Tiny", parent=base["BodyText"], fontName="Helvetica",
        fontSize=7, leading=9, textColor=MUTED,
    ))
    base.add(ParagraphStyle(
        name="Callout", parent=base["BodyText"], fontName="Helvetica-Bold",
        fontSize=9.5, leading=13, textColor=NAVY, backColor=colors.HexColor("#EAF5F6"),
        borderColor=TEAL, borderWidth=0.6, borderPadding=7, spaceAfter=10,
    ))
    return base


def _table(data, widths, header=True, font_size=7.5):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2.5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    table.setStyle(TableStyle(commands))
    return table


def _bullet(story, styles, value):
    story.append(Paragraph(f"&#8226;&nbsp; {_text(value)}", styles["BodySmall"]))


def _header_footer(canvas, doc, title):
    canvas.saveState()
    page_width, page_height = A4
    canvas.setStrokeColor(LIGHT)
    canvas.line(18 * mm, page_height - 13 * mm, page_width - 18 * mm, page_height - 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, page_height - 10 * mm, title[:90])
    canvas.drawRightString(page_width - 18 * mm, 10 * mm, f"Halaman {doc.page}")
    canvas.drawString(18 * mm, 10 * mm, "PANTAU - Analisis berbasis korpus terkoleksi; wajib ditinjau analis.")
    canvas.restoreState()


def build(summary, *, institution, project_name, generated_by):
    stream = BytesIO()
    styles = _styles()
    period = (
        f"{summary['period_start'].strftime('%d/%m/%Y')} - "
        f"{summary['period_end'].strftime('%d/%m/%Y')}"
    )
    title = f"Analisis Sentimen Media - {institution} | {period}"
    document = SimpleDocTemplate(
        stream, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=19 * mm, bottomMargin=17 * mm,
        title=title, author=generated_by, subject=project_name,
    )
    story = [
        Spacer(1, 5 * mm),
        Paragraph("LAPORAN ANALISIS SENTIMEN MEDIA", styles["ReportTitle"]),
        Paragraph(
            f"{_text(institution)}<br/>{_text(project_name)}<br/>Periode: {_text(period)}",
            styles["ReportSubtitle"],
        ),
        Paragraph(
            "<b>DRAF ANALITIS - WAJIB TINJAUAN MANUSIA.</b> "
            "Persentase berasal dari data yang benar-benar terkoleksi; klaim tanpa URL "
            "sumber tidak digunakan sebagai kutipan bukti.",
            styles["Callout"],
        ),
    ]

    story.append(Paragraph("1. Ringkasan Eksekutif", styles["Section"]))
    dominant = summary["dominant_sentiment"]
    story.append(Paragraph(
        f"Pada periode ini PANTAU menganalisis <b>{summary['total_mentions']}</b> unit "
        f"konten dari <b>{summary['unique_authors']}</b> akun/penulis. Sentimen dominan "
        f"adalah <b>{_text(dominant['label'])}</b> ({dominant['pct']}%). "
        f"Korpus terdiri dari {summary['quality']['post_count']} posting/artikel dan "
        f"{summary['quality']['comment_count']} komentar publik.",
        styles["BodySmall"],
    ))
    if summary["issue_rows"]:
        issue = summary["issue_rows"][0]
        story.append(Paragraph(
            f"Isu dengan volume terbesar adalah <b>{_text(issue['name'])}</b> "
            f"({issue['count']} sebutan; {issue['negative_pct']}% negatif).",
            styles["BodySmall"],
        ))

    story.append(Paragraph("Distribusi Sentimen per Kanal", styles["Subsection"]))
    channel_data = [["Kanal", "N", "Positif", "Netral", "Negatif"]]
    for row in summary["channel_rows"]:
        channel_data.append([
            row["label"], str(row["count"]),
            f"{_pct(row, 'positive')}%", f"{_pct(row, 'neutral')}%",
            f"{_pct(row, 'negative')}%",
        ])
    story.append(_table(channel_data, [58 * mm, 18 * mm, 25 * mm, 25 * mm, 25 * mm]))

    story.append(Paragraph("2. Metodologi dan Batasan", styles["Section"]))
    for note in summary["methodology_notes"]:
        _bullet(story, styles, note)
    story.append(Paragraph("Kualitas dan keterlacakan data", styles["Subsection"]))
    quality_data = [
        ["Indikator", "Nilai"],
        ["URL sumber dapat diverifikasi", f"{summary['quality']['source_coverage_pct']}%"],
        ["Cakupan label topik", f"{summary['quality']['taxonomy_coverage_pct']}%"],
        ["Rata-rata keyakinan sentimen", f"{summary['quality']['avg_sentiment_confidence_pct']}%"],
        ["URL sumber unik", str(summary["quality"]["unique_urls"])],
        ["Cakupan post untuk analisis komentar", f"{summary['quality']['comment_parent_coverage_pct']}%"],
        ["Sebutan hasil koleksi", str(summary["quality"]["collected_count"])],
        ["Sebutan fixture/demo", str(summary["quality"]["seeded_count"])],
    ]
    story.append(_table(quality_data, [85 * mm, 65 * mm]))
    story.append(Paragraph("Batasan", styles["Subsection"]))
    for limitation in summary["limitations"]:
        _bullet(story, styles, limitation)

    story.append(Paragraph("3. Ikhtisar Isu Utama", styles["Section"]))
    issue_data = [["Isu", "Volume", "Porsi", "Positif", "Netral", "Negatif", "Bukti"]]
    for issue in summary["issue_rows"]:
        cited = sum(1 for item in issue["evidence"] if item["clickable"])
        issue_data.append([
            Paragraph(_text(issue["name"]), styles["Tiny"]),
            str(issue["count"]), f"{issue['share_pct']}%",
            f"{issue['positive_pct']}%",
            f"{next(x['pct'] for x in issue['sentiment_breakdown'] if x['key'] == 'neutral')}%",
            f"{issue['negative_pct']}%", str(cited),
        ])
    if len(issue_data) == 1:
        issue_data.append(["Belum ada isu terlabel", "0", "-", "-", "-", "-", "0"])
    story.append(_table(
        issue_data,
        [55 * mm, 15 * mm, 15 * mm, 18 * mm, 18 * mm, 18 * mm, 14 * mm],
        font_size=7,
    ))

    for number, issue in enumerate(summary["issue_rows"][:4], start=1):
        story.append(Paragraph(
            f"3.{number} {_text(issue['name'])}", styles["Subsection"]
        ))
        story.append(Paragraph(
            f"{issue['count']} sebutan; {issue['negative_pct']}% negatif dan "
            f"{issue['positive_pct']}% positif. Teramati "
            f"{_local_date(issue['first_seen'])} "
            f"sampai {_local_date(issue['last_seen'])}.",
            styles["BodySmall"],
        ))
        for evidence in issue["evidence"]:
            source = evidence["domain"] or evidence["platform"]
            suffix = f" - {source}"
            if evidence["clickable"]:
                suffix += f" ({evidence['source_url']})"
            _bullet(story, styles, f"{evidence['snippet'][:280]}{suffix}")

    story.append(Paragraph("4. Analisis Komentar Publik", styles["Section"]))
    comments = summary["comment_analysis"]
    story.append(Paragraph(
        f"PANTAU menganalisis <b>{comments['count']}</b> komentar dari "
        f"<b>{comments['parent_count']}</b> posting induk. Cakupan posting yang "
        f"melaporkan komentar adalah <b>{comments['parent_coverage_pct']}%</b>. "
        "Komentar dihitung dari isi yang berhasil diambil, bukan dari angka comment count.",
        styles["BodySmall"],
    ))
    comment_data = [["Sentimen Komentar", "Jumlah", "Proporsi"]]
    for row in comments["sentiment_breakdown"]:
        comment_data.append([row["label"], str(row["count"]), f"{row['pct']}%"])
    story.append(_table(comment_data, [70 * mm, 35 * mm, 45 * mm]))
    for evidence in comments["evidence"]:
        suffix = f" - {evidence['platform']}"
        if evidence["clickable"]:
            suffix += f" ({evidence['source_url']})"
        _bullet(
            story, styles,
            f"{evidence['snippet'][:260]}{suffix}"
        )
    if not comments["count"]:
        story.append(Paragraph(
            "Belum ada isi komentar yang terkoleksi pada periode ini. "
            "Laporan tidak mengasumsikan sentimen komentar dari jumlah komentar saja.",
            styles["Callout"],
        ))

    story.append(Paragraph("5. Perbandingan Aktor/Objek Pantauan", styles["Section"]))
    actor_data = [["Aktor/Organisasi", "N", "Positif", "Netral", "Negatif", "Topik utama"]]
    for row in summary["actor_rows"]:
        actor_data.append([
            Paragraph(_text(row["actor"].name), styles["Tiny"]),
            str(row["count"]),
            f"{_pct(row, 'positive')}%", f"{_pct(row, 'neutral')}%",
            f"{_pct(row, 'negative')}%",
            Paragraph(_text(row["top_issue"] or "-"), styles["Tiny"]),
        ])
    if len(actor_data) == 1:
        actor_data.append(["Belum ada aktor terkonfigurasi", "0", "-", "-", "-", "-"])
    story.append(_table(
        actor_data, [48 * mm, 12 * mm, 19 * mm, 19 * mm, 19 * mm, 42 * mm],
        font_size=7,
    ))
    story.append(Paragraph(
        "Catatan: sentimen disimpan per pasangan sebutan-aktor. Nilai otomatis dapat "
        "dikoreksi analis pada Umpan Sebutan; sebutan multi-aktor tetap wajib diperiksa.",
        styles["Tiny"],
    ))

    story.append(PageBreak())
    story.append(Paragraph("6. Rekomendasi Strategi Komunikasi Publik", styles["Section"]))
    for index, recommendation in enumerate(summary["recommendations"], start=1):
        story.append(Paragraph(
            f"<b>{index}. {_text(recommendation['title'])}</b><br/>"
            f"{_text(recommendation['detail'])}<br/>"
            f"<font color='#64748B'>Dasar: {_text(recommendation['basis'])}</font>",
            styles["BodySmall"],
        ))

    story.append(Paragraph("7. Daftar Sumber Rujukan", styles["Section"]))
    source_data = [["Domain", "Item", "Platform", "Contoh URL"]]
    for source in summary["source_inventory"]["sources"][:30]:
        example = source["urls"][0] if source["urls"] else "-"
        source_data.append([
            Paragraph(_text(source["domain"]), styles["Tiny"]),
            str(source["count"]),
            Paragraph(_text(source["platforms"]), styles["Tiny"]),
            Paragraph(_text(example), styles["Tiny"]),
        ])
    if len(source_data) == 1:
        source_data.append(["Tidak ada URL sumber yang dapat diverifikasi", "0", "-", "-"])
    story.append(_table(
        source_data, [40 * mm, 13 * mm, 32 * mm, 74 * mm], font_size=6.5,
    ))

    story.append(Paragraph("8. Lampiran Konfigurasi dan Kandidat Kata Kunci", styles["Section"]))
    keyword_data = [["Jenis", "Kandidat", "Berasal dari", "Match", "Prioritas"]]
    for item in summary["potential_keywords"]:
        keyword_data.append([
            item["kind"],
            Paragraph(_text(item["term"]), styles["Tiny"]),
            Paragraph(_text(item["source"]), styles["Tiny"]),
            str(item["matches"]),
            item["priority"],
        ])
    if len(keyword_data) == 1:
        keyword_data.append(["-", "Tidak ada kandidat baru", "-", "0", "-"])
    story.append(_table(
        keyword_data, [20 * mm, 45 * mm, 52 * mm, 17 * mm, 25 * mm], font_size=7,
    ))

    story.extend([
        Spacer(1, 8 * mm),
        Paragraph(
            f"Disusun oleh: PANTAU / {_text(generated_by)}<br/>"
            f"Untuk: {_text(institution)}<br/>"
            "Dokumen ini bersifat internal sampai ditinjau dan disetujui analis yang berwenang.",
            styles["BodySmall"],
        ),
    ])

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _header_footer(canvas, doc, title),
        onLaterPages=lambda canvas, doc: _header_footer(canvas, doc, title),
    )
    return stream.getvalue()
