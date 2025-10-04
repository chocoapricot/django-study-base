"""
PDF生成に関する共通ユーティリティ
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm


def generate_contract_pdf(buffer, title, intro_text, items, watermark_text=None, postamble_text=None):
    """
    契約書形式のPDFを生成する共通関数。
    2パス処理を行い、フッターに総ページ数付きのページ番号を印字する。

    :param buffer: PDFを書き込むためのBytesIOなどのバッファ
    :param title: 帳票のメインタイトル
    :param intro_text: タイトルの下に表示する前文
    :param items: 罫線付きで表示する項目のリスト。各項目は {'title': '項目名', 'text': '内容'} の辞書。
    :param watermark_text: 透かしとして表示する文字列（オプショナル）
    :param postamble_text: 末文
    """
    # 日本語フォントの登録
    font_path = 'statics/fonts/ipagp.ttf'
    pdfmetrics.registerFont(TTFont('IPAPGothic', font_path))

    # スタイルシートの準備
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MainTitle', fontName='IPAPGothic', fontSize=18, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name='IntroText', fontName='IPAPGothic', fontSize=11, leading=16, spaceAfter=10))
    styles.add(ParagraphStyle(name='ItemTitle', fontName='IPAPGothic', fontSize=11, leading=14))
    styles.add(ParagraphStyle(name='ItemText', fontName='IPAPGothic', fontSize=11, leading=14))
    styles.add(ParagraphStyle(name='PostambleText', fontName='IPAPGothic', fontSize=11, leading=16, spaceBefore=10))

    def build_story():
        """PDFの内容(Story)を構築する"""
        story = []
        # 1. 帳票タイトル
        story.append(Paragraph(title, styles['MainTitle']))

        # 2. 前文
        if intro_text:
            story.append(Paragraph(intro_text.replace('\n', '<br/>'), styles['IntroText']))

        # 3. 各項目の表示
        table_data = []
        for item in items:
            item_title = Paragraph(item.get('title', ''), styles['ItemTitle'])
            item_text = Paragraph(item.get('text', '').replace('\n', '<br/>'), styles['ItemText'])
            table_data.append([item_title, item_text])

        if table_data:
            table = Table(table_data, colWidths=['20%', '80%'])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(table)
            story.append(Spacer(1, 10))

        # 4. 末文
        if postamble_text:
            story.append(Paragraph(postamble_text.replace('\n', '<br/>'), styles['PostambleText']))

        return story

    # --- パス1: 総ページ数を数える ---
    story1 = build_story()
    pass1_buffer = io.BytesIO()
    doc1 = SimpleDocTemplate(pass1_buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=40, title=title)
    doc1.build(story1)
    total_pages = doc1.page

    # --- パス2: 実際に描画する ---
    story2 = build_story()
    doc2 = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=40, title=title)

    def on_page_with_total(canvas, doc):
        """ページ描画のコールバック関数"""
        # 透かし
        if watermark_text:
            canvas.saveState()
            canvas.setFont('IPAPGothic', 60)
            canvas.setFillColor(colors.lightgrey, alpha=0.2)

            # ページ全体にタイル状に描画
            for x in range(0, int(A4[0]) + 200, 250):
                for y in range(0, int(A4[1]) + 200, 250):
                    canvas.saveState()
                    canvas.translate(x, y)
                    canvas.rotate(45)
                    canvas.drawCentredString(0, 0, watermark_text)
                    canvas.restoreState()
            
            canvas.restoreState()

        # ページ番号
        canvas.saveState()
        canvas.setFont("IPAPGothic", 9)
        canvas.drawCentredString(A4[0] / 2, 20, f"{doc.page} / {total_pages}")
        canvas.restoreState()

    doc2.build(story2, onFirstPage=on_page_with_total, onLaterPages=on_page_with_total)


def generate_structured_pdf(
    buffer,
    meta_title,
    to_address_lines,
    from_address_lines,
    main_title_text,
    summary_lines,
    body_title_text=None,
    body_items=None,
    watermark_text=None
):
    """
    構造化されたPDFを生成する共通関数。
    左上に宛先、右上に送付元情報、タイトル、概要、本文、ページ番号を持つレイアウトを生成する。
    Flowableの代わりに文字列や文字列のリストを受け取る。

    :param buffer: PDFを書き込むためのBytesIOなどのバッファ
    :param meta_title: PDFのメタデータタイトル
    :param to_address_lines: 宛先ブロックに表示する文字列のリスト (左上)
    :param from_address_lines: 送付元ブロックに表示する文字列のリスト (右上)
    :param main_title_text: メインタイトル文字列
    :param summary_lines: 概要セクションに表示する文字列のリスト
    :param body_title_text: 本文セクションのタイトル（例：「記」）。オプショナル。
    :param body_items: 本文セクションに表示する箇条書きアイテムのリスト。オプショナル。
    :param watermark_text: 透かしとして表示する文字列（オプショナル）
    """
    # --- フォントとスタイルの設定 ---
    font_path = 'statics/fonts/ipagp.ttf'
    pdfmetrics.registerFont(TTFont('IPAPGothic', font_path))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='StructAddress', fontName='IPAPGothic', fontSize=11, leading=16))
    styles.add(ParagraphStyle(name='StructMainTitle', fontName='IPAPGothic', fontSize=16, alignment=1, spaceBefore=20, spaceAfter=20))
    styles.add(ParagraphStyle(name='StructSectionTitle', fontName='IPAPGothic', fontSize=14, alignment=1, spaceBefore=10, spaceAfter=10))
    styles.add(ParagraphStyle(name='StructBodyText', fontName='IPAPGothic', fontSize=11, leading=18, firstLineIndent=11, spaceAfter=10))
    styles.add(ParagraphStyle(name='StructListItem', fontName='IPAPGothic', fontSize=11, leading=18, leftIndent=22, firstLineIndent=-11))


    # --- PDF要素の構築 ---
    def build_story():
        story = []

        # --- ヘッダー: 宛先と送付元 ---
        if to_address_lines and from_address_lines:
            to_address_flowables = [Paragraph(line.replace('\n', '<br/>'), styles['StructAddress']) for line in to_address_lines]
            from_address_flowables = [Paragraph(line.replace('\n', '<br/>'), styles['StructAddress']) for line in from_address_lines]

            address_table = Table(
                [[to_address_flowables, from_address_flowables]],
                colWidths=['50%', '50%']
            )
            address_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(address_table)
            story.append(Spacer(1, 1 * cm))

        # --- メインタイトル ---
        if main_title_text:
            story.append(Paragraph(main_title_text, styles['StructMainTitle']))

        # --- 概要 ---
        if summary_lines:
            summary_flowables = [Paragraph(line.replace('\n', '<br/>'), styles['StructBodyText']) for line in summary_lines]
            story.extend(summary_flowables)
            story.append(Spacer(1, 0.5 * cm))

        # --- 本文タイトル (例: 記) ---
        if body_title_text:
            story.append(Paragraph(body_title_text, styles['StructSectionTitle']))
            story.append(Spacer(1, 0.5 * cm))

        # --- 本文コンテンツ ---
        if body_items:
            body_flowables = []
            for item in body_items:
                body_flowables.append(Paragraph(item.replace('\n', '<br/>'), styles['StructListItem']))
                body_flowables.append(Spacer(1, 0.5 * cm))
            story.extend(body_flowables)

        return story

    # --- パス1: 総ページ数を数える ---
    story1 = build_story()
    pass1_buffer = io.BytesIO()
    doc1 = SimpleDocTemplate(pass1_buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2.5*cm, title=meta_title)
    doc1.build(story1)
    total_pages = doc1.page if doc1.page > 0 else 1

    # --- パス2: 実際に描画する ---
    story2 = build_story()

    def on_page_with_total(canvas, doc):
        """ページ描画のコールバック関数"""
        # 透かし
        if watermark_text:
            canvas.saveState()
            canvas.setFont('IPAPGothic', 60)
            canvas.setFillColor(colors.lightgrey, alpha=0.2)

            # ページ全体にタイル状に描画
            for x in range(0, int(A4[0]) + 200, 250):
                for y in range(0, int(A4[1]) + 200, 250):
                    canvas.saveState()
                    canvas.translate(x, y)
                    canvas.rotate(45)
                    canvas.drawCentredString(0, 0, watermark_text)
                    canvas.restoreState()

            canvas.restoreState()

        # ページ番号
        canvas.saveState()
        canvas.setFont("IPAPGothic", 9)
        canvas.drawCentredString(A4[0] / 2, 1.5 * cm, f"{doc.page} / {total_pages}")
        canvas.restoreState()

    doc2 = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2.5*cm, title=meta_title)
    doc2.build(story2, onFirstPage=on_page_with_total, onLaterPages=on_page_with_total)