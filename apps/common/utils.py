# yourapp/utils.py

import openpyxl
from io import BytesIO
from pdfrw import PdfReader, PdfWriter, PdfDict

def fill_excel_from_template(template_path, named_fields):
    """
    テンプレートExcelファイルを読み込み、名前付き範囲にデータを差し込んで
    メモリ上に保存したExcelファイルを返す関数
    """
    # テンプレートとして事前に用意されたExcelファイルをロード
    wb = openpyxl.load_workbook(template_path)

    # 名前付き範囲にデータを差し込む
    named_ranges = wb.defined_names
    for field, value in named_fields.items():
        named_range = named_ranges.get(field)
        if named_range:
            # destinations はジェネレータなので next() で最初のセルを取得
            sheet_name, cell_reference = next(named_range.destinations)
            sheet = wb[sheet_name]  # シートを取得
            cell = sheet[cell_reference]  # セルを取得
            cell.value = value  # 値をセット

    # メモリに保存
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)  # 先頭に戻す
    return excel_file


# from pdfrw import PdfReader, PdfWriter, PdfDict
# from io import BytesIO

# def fill_pdf_from_template(template_pdf_path, data):
#     """
#     既存のPDFフォームにデータを埋め込み、メモリ上に新しいPDFを作成して返す
#     - template_pdf_path: フォームのPDFテンプレートのパス
#     - data: 埋め込むデータ（フィールド名をキーに、入力するテキストを値として持つ辞書）
#     - 戻り値: メモリ上のPDFデータ（BytesIOオブジェクト）
#     """
#     # PDFテンプレートを読み込み
#     template_pdf = PdfReader(template_pdf_path)
#     for page in template_pdf.pages:
#         annotations = page['/Annots']
#         if annotations:
#             for annotation in annotations:
#                 key = annotation['/T'][1:-1]  # フィールド名を取得（"/T"から最初と最後のスラッシュを取り除く）
#                 if key in data:
#                     # データを埋め込む
#                     annotation.update(
#                         PdfDict(V='{}'.format(data[key]))
#                     )
#     # メモリ上に新しいPDFを保存
#     output_pdf = BytesIO()
#     writer = PdfWriter()
#     writer.addpage(template_pdf.pages[0])  # 必要に応じて複数ページ処理
#     writer.write(output_pdf)
#     # メモリ上に作成されたPDFを返す
#     output_pdf.seek(0)  # バッファの先頭に戻す
#     return output_pdf


#    ↑↑↑↑↑↑chromeだと縮小も正しく動くが、Acrobatだと動かない
#    ↓↓↓↓↓↓chromeもAcrobatも動くが縮小がされない.


import fitz  # PyMuPDF

def fill_pdf_from_template(template_pdf_path, data):
    """
    既存のPDFフォームにデータを埋め込み、メモリ上に新しいPDFを作成して返す。
    - template_pdf_path: フォームのPDFテンプレートのパス
    - data: 埋め込むデータ（フィールド名をキーに、入力するテキストを値として持つ辞書）
    - 戻り値: メモリ上のPDFデータ（BytesIOオブジェクト）
    """
    # PDFテンプレートを読み込み
    doc = fitz.open(template_pdf_path)
    
    # すべてのページをループしてフォームフィールドにデータを埋め込む
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # フォームフィールド（アノテーション）を取得
        for field in page.widgets():
            field_name = field.field_name  # フィールド名を取得
            if field_name in data:
                # データを埋め込む
                # print(field_name)
                field.field_value = data[field_name]  # フィールドにデータを埋め込む

                # 文字数が10文字以上の場合、フォントサイズを小さく設定 TODO 自動縮小ができないので無理やり
                if len(field.field_value) > 10:
                    field.text_fontsize = 6 

                field.update()
                
    # メモリ上に新しいPDFを保存
    output_pdf = BytesIO()
    doc.save(output_pdf)  # メモリ上に保存
    output_pdf.seek(0)  # ファイルポインタを先頭に戻す
    
    return output_pdf