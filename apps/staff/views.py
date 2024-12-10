import os
import logging
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from .models import Staff
from .forms import StaffForm
from apps.system.parameters.utils import my_parameter
from django.db.models import Q
from apps.system.dropdowns.models import Dropdowns
from apps.common.utils import fill_excel_from_template, fill_pdf_from_template

# ロガーの作成
logger = logging.getLogger('staff')

def staff_list(request):
    query = request.GET.get('q')  # 検索キーワードを取得
    if query:
        query = query.strip()
        staffs = Staff.objects.filter(
            Q(name_last__icontains=query)
            |Q(name_first__icontains=query)
            |Q(name_kana_last__icontains=query)
            |Q(name_kana_first__icontains=query)
            |Q(name__icontains=query)
            |Q(address_kana__icontains=query)
            |Q(address1__icontains=query)
            |Q(address2__icontains=query)
            |Q(address3__icontains=query)
            |Q(email__icontains=query)
            )
    else:
        query = ''
        staffs = Staff.objects.all()  # 検索キーワードがなければ全件取得
    paginator = Paginator(staffs, 10)  # 1ページあたり10件表示
    page_number = request.GET.get('page')  # URLからページ番号を取得
    staffs_pages = paginator.get_page(page_number)  # ページオブジェクトを取得

    return render(request, 'staff/staff_list.html', {'staffs': staffs_pages, 'query':query})

def staff_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('staff_list')
    else:
        form = StaffForm()
    return render(request, 'staff/staff_form.html', {'form': form})

def staff_detail(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    # if request.method == 'POST':
    #     form = StaffForm(request.POST, instance=staff)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('staff_list')
    # else:
    form = StaffForm(instance=staff)
    return render(request, 'staff/staff_detail.html', {'staff': staff})

def staff_update(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            return redirect('staff_list')
    else:
        form = StaffForm(instance=staff)
    return render(request, 'staff/staff_form.html', {'form': form})

def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        staff.delete()
        return redirect('staff_list')
    return render(request, 'staff/staff_confirm_delete.html', {'staff': staff})

def staff_face(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    image_path = os.path.join(my_parameter("STAFF_FACE_PATH"), str(staff.pk)+".jpg") 
    logger.error(image_path)

    # 画像ファイルが存在する場合はそのファイルを返す
    if image_path and os.path.exists(image_path):
        return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')
    
    # 画像が存在しない場合、名前を使って画像を生成
    response = HttpResponse(content_type="image/jpeg")
    image = Image.new("RGB", (200, 200), (200, 200, 200))  # 背景色の指定
    if staff.sex == 1:
        image = Image.new("RGB", (200, 200), (140, 140, 240))  # 背景色の指定
    elif staff.sex == 2:
        image = Image.new("RGB", (200, 200), (240, 140, 140))  # 背景色の指定
    
    
    draw = ImageDraw.Draw(image)
    
    # 日本語フォントの設定
    font_path = os.path.join(settings.BASE_DIR, 'statics/fonts/ipagp.ttf')
    try:
        font = ImageFont.truetype(font_path,80)#font-size
    except IOError:
        logger.error(font_path)
    
    # 名前を中央に描画
    # 名・姓が両方とも存在する場合のみイニシャルを生成
    if staff.name_last and staff.name_first:
        initials = f"{staff.name_last[0]}{staff.name_first[0]}"
    else:
        initials = ""  # 片方がない場合は空欄を返すなど
    # `textbbox` を使ってテキストのバウンディングボックスを取得
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((200 - text_width) // 2, (200 - text_height-20) // 2)
    draw.text(position, initials, fill="white", font=font)
    
    # 画像をHTTPレスポンスとして返す
    image.save(response, "JPEG")
    return response

def staff_rirekisho(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    sex_dropdown = Dropdowns.objects.filter(category='sex', value=staff.sex, active=True).first()

    named_fields = {
        'name': (staff.name_last + " " + staff.name_first),
        'name_kana': (staff.name_kana_last + " " + staff.name_kana_first),
        'address_kana': (staff.address_kana),
        'address': (staff.address1 +  staff.address2 +  staff.address3),
        'phone': (staff.phone),
        'zipcode': (staff.postal_code),
        'sex': sex_dropdown.name if sex_dropdown else staff.sex,  # ここでsex_dropdownの値を設定
    }

    # レスポンスの設定
    response = HttpResponse(
        fill_excel_from_template('templates/excels/rirekisyo_a4_mhlw_DJ.xlsx', named_fields),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="staff_rirekisho_'+str(pk)+'.xlsx"'
    return response


def staff_kyushoku(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    sex_dropdown = Dropdowns.objects.filter(category='sex', value=staff.sex, active=True).first()

    named_fields = {
        'name': (staff.name_last + " " + staff.name_first),
        'address': (staff.address1 +  staff.address2 +  staff.address3),
        'phone': (staff.phone),
        'sex': sex_dropdown.name if sex_dropdown else staff.sex,  # ここでsex_dropdownの値を設定
    }

    # レスポンスの設定
    response = HttpResponse(
        fill_excel_from_template('templates/excels/001264775_DJ.xlsx', named_fields),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="staff_kyushoku_'+str(pk)+'.xlsx"'
    return response

def staff_fuyokojo(request, pk):
    staff = Staff.objects.get(pk=pk)
    sex_dropdown = Dropdowns.objects.filter(category='sex', value=staff.sex, active=True).first()

    # フォームに埋め込むデータを準備
    form_data = {
        'Text6': staff.name_kana_last + " " + staff.name_kana_first,  # カナ名
        'Text7': staff.name_last + " " + staff.name_first,  # 名前
        'Text10': staff.address1 + staff.address2 + staff.address3,  # 住所
    }

    # PDFフォームにデータを埋め込む（メモリ上にPDFを作成）
    output_pdf = fill_pdf_from_template('templates/pdfs/2025bun_01_input.pdf', form_data)

    # メモリ上のPDFをレスポンスとして返す
    response = HttpResponse(output_pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="staff_fuyokojo_'+str(pk)+'.pdf"'
    return response