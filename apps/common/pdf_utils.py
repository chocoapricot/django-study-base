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


def generate_table_based_contract_pdf(buffer, title, intro_text, items, watermark_text=None, postamble_text=None, to_address_lines=None, from_address_lines=None):
    """
    テーブルベースの契約書PDFを生成する共通関数。
    2パス処理を行い、フッターに総ページ数付きのページ番号を印字する。
    rowspanをサポートするために、3列構成のテーブルを基本とし、
    itemsに 'rowspan_items' が含まれている場合はセルの結合を行う。

    :param buffer: PDFを書き込むためのBytesIOなどのバッファ
    :param title: 帳票のメインタイトル
    :param intro_text: タイトルの下に表示する前文
    :param items: 表示項目のリスト。
                  通常: {'title': '項目名', 'text': '内容'}
                  rowspan: {'title': '結合セル項目名', 'rowspan_items': [{'title': '項目名', 'text': '内容'}, ...]}
    :param watermark_text: 透かしとして表示する文字列（オプショナル）
    :param postamble_text: 末文
    :param to_address_lines: 宛先ブロックに表示する文字列のリスト (左上)（オプショナル）
    :param from_address_lines: 送付元ブロックに表示する文字列のリスト (右上)（オプショナル）
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
    # rowspan用のスタイルを追加
    styles.add(ParagraphStyle(name='RowSpanTitle', fontName='IPAPGothic', fontSize=11, leading=14, alignment=1))


    def build_story():
        """PDFの内容(Story)を構築する"""
        story = []
        
        # 0. 宛先と送付元（左上・右上）
        if to_address_lines and from_address_lines:
            to_address_flowables = [Paragraph(line.replace('\n', '<br/>'), styles['IntroText']) for line in to_address_lines]
            from_address_flowables = [Paragraph(line.replace('\n', '<br/>'), styles['IntroText']) for line in from_address_lines]

            address_table = Table(
                [[to_address_flowables, from_address_flowables]],
                colWidths=['60%', '40%']
            )
            address_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(address_table)
            story.append(Spacer(1, 1 * cm))
        
        # 1. 帳票タイトル
        story.append(Paragraph(title, styles['MainTitle']))

        # 2. 前文
        if intro_text:
            story.append(Paragraph(intro_text.replace('\n', '<br/>'), styles['IntroText']))

        # 3. 各項目の表示
        table_data = []
        table_style_commands = []
        current_row = 0

        for item in items:
            if 'rowspan_items' in item:
                # rowspan を持つ項目の処理
                rowspan_title = Paragraph(item.get('title', ''), styles['RowSpanTitle'])
                sub_items = item['rowspan_items']
                num_sub_items = len(sub_items)

                if num_sub_items > 0:
                    # 最初のサブアイテム行
                    first_sub_item = sub_items[0]
                    sub_title = Paragraph(first_sub_item.get('title', ''), styles['ItemTitle'])
                    sub_text = Paragraph(str(first_sub_item.get('text', '')).replace('\n', '<br/>'), styles['ItemText'])
                    table_data.append([rowspan_title, sub_title, sub_text])

                    # rowspanのスタイルコマンド
                    table_style_commands.append(('SPAN', (0, current_row), (0, current_row + num_sub_items - 1)))
                    table_style_commands.append(('VALIGN', (0, current_row), (0, current_row + num_sub_items - 1), 'MIDDLE'))

                    # 残りのサブアイテム行
                    for i in range(1, num_sub_items):
                        next_sub_item = sub_items[i]
                        sub_title = Paragraph(next_sub_item.get('title', ''), styles['ItemTitle'])
                        sub_text = Paragraph(str(next_sub_item.get('text', '')).replace('\n', '<br/>'), styles['ItemText'])
                        table_data.append(['', sub_title, sub_text]) # 最初の列は空

                    current_row += num_sub_items
            else:
                # 通常の項目の処理
                item_title = Paragraph(item.get('title', ''), styles['ItemTitle'])
                item_text = Paragraph(str(item.get('text', '')).replace('\n', '<br/>'), styles['ItemText'])
                table_data.append([item_title, item_text, '']) # 3列目は空

                # 2列目と3列目を結合
                table_style_commands.append(('SPAN', (1, current_row), (2, current_row)))
                current_row += 1

        if table_data:
            table = Table(table_data, colWidths=['20%', '25%', '55%'])
            style = TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ])
            # 動的に生成したスタイルコマンドを追加
            for cmd in table_style_commands:
                style.add(*cmd)

            table.setStyle(style)
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


def generate_article_based_contract_pdf(
    buffer,
    meta_title,
    to_address_lines,
    from_address_lines,
    main_title_text,
    summary_lines,
    body_title_text=None,
    body_items=None,
    watermark_text=None,
    notice_date=None
):
    """
    条文ベースの契約書PDFを生成する共通関数。
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
    :param notice_date: 右上に印字する通知日（オプショナル）
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

        # --- ヘッダー: 通知日（一番右上）と宛先・送付元 ---
        if notice_date:
            # 通知日を一番右上に配置
            notice_date_table = Table(
                [['', '', Paragraph(notice_date, styles['StructAddress'])]],
                colWidths=['40%', '40%', '20%']
            )
            notice_date_table.setStyle(TableStyle([
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(notice_date_table)
            story.append(Spacer(1, 0.5 * cm))

        # 宛先と送付元
        if to_address_lines and from_address_lines:
            to_address_flowables = [Paragraph(line.replace('\n', '<br/>'), styles['StructAddress']) for line in to_address_lines]
            from_address_flowables = [Paragraph(line.replace('\n', '<br/>'), styles['StructAddress']) for line in from_address_lines]

            address_table = Table(
                [[to_address_flowables, from_address_flowables]],
                colWidths=['60%', '40%']
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