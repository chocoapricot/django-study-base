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

def generate_contract_pdf(buffer, title, intro_text, items, watermark_text=None):
    """
    契約書形式のPDFを生成する共通関数

    :param buffer: PDFを書き込むためのBytesIOなどのバッファ
    :param title: 帳票のメインタイトル
    :param intro_text: タイトルの下に表示する前文
    :param items: 罫線付きで表示する項目のリスト。各項目は {'title': '項目名', 'text': '内容'} の辞書。
    :param watermark_text: 透かしとして表示する文字列（オプショナル）
    """
    # 日本語フォントの登録
    font_path = 'statics/fonts/ipagp.ttf'  # プロポーショナルフォントを使用
    pdfmetrics.registerFont(TTFont('IPAPGothic', font_path))

    # スタイルシートの準備
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MainTitle', fontName='IPAPGothic', fontSize=18, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name='IntroText', fontName='IPAPGothic', fontSize=11, leading=16, spaceAfter=20))
    styles.add(ParagraphStyle(name='ItemTitle', fontName='IPAPGothic', fontSize=12, leading=14))
    styles.add(ParagraphStyle(name='ItemText', fontName='IPAPGothic', fontSize=11, leading=14))

    # ドキュメントテンプレートの作成
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)

    story = []

    # 1. 帳票タイトル
    story.append(Paragraph(title, styles['MainTitle']))

    # 2. 前文
    if intro_text:
        story.append(Paragraph(intro_text, styles['IntroText']))

    # 3. 各項目の表示
    table_data = []
    for item in items:
        item_title = Paragraph(item.get('title', ''), styles['ItemTitle'])
        item_text = Paragraph(item.get('text', '').replace('\n', '<br/>'), styles['ItemText'])
        table_data.append([item_title, item_text])

    if table_data:
        # テーブルで罫線を表現
        table = Table(table_data, colWidths=['25%', '75%'])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

    # 透かしを描画する内部関数
    def watermark_canvas(canvas, doc):
        canvas.saveState()
        canvas.setFont('IPAPGothic', 100)
        canvas.setFillColor(colors.lightgrey, alpha=0.3)
        # ページの中心に回転させて描画
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, watermark_text)
        canvas.restoreState()

    # PDFのビルド
    if watermark_text:
        doc.build(story, onFirstPage=watermark_canvas, onLaterPages=watermark_canvas)
    else:
        doc.build(story)
