from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.apps import apps
from apps.system.logs.models import AppLog
from .models import TimePunch
from .forms import TimePunchForm

from .views_staff import *
from .views_client import *
from .views_contract import *
from .views_billing import *
from .views_other import *
from .views_phrase import *
from .views_worktime import *
from .views_kintai import *

# マスタ設定データ
MASTER_CONFIGS = [
    {
        "category": "スタッフ",
        "name": "資格管理",
        "description": "資格・免許・認定等の管理",
        "model": "master.Qualification",
        "url_name": "master:qualification_list",
        "permission": "master.view_qualification",
    },
    {
        "category": "スタッフ",
        "name": "技能管理",
        "description": "スキル・技術・能力等の管理",
        "model": "master.Skill",
        "url_name": "master:skill_list",
        "permission": "master.view_skill",
    },
    {
        "category": "スタッフ",
        "name": "同意文言管理",
        "description": "スタッフ登録時の同意文言を管理",
        "model": "master.StaffAgreement",
        "url_name": "master:staff_agreement_list",
        "permission": "master.view_staffagreement",
    },
    {
        "category": "スタッフ",
        "name": "雇用形態管理",
        "description": "雇用形態の管理",
        "model": "master.EmploymentType",
        "url_name": "master:employment_type_list",
        "permission": "master.view_employmenttype",
    },
    {
        "category": "スタッフ",
        "name": "スタッフ登録状況管理",
        "description": "スタッフの登録状況を管理",
        "model": "master.StaffRegistStatus",
        "url_name": "master:staff_regist_status_list",
        "permission": "master.view_staffregiststatus",
    },
    {
        "category": "クライアント",
        "name": "クライアント登録状況管理",
        "description": "クライアントの登録状況を管理",
        "model": "master.ClientRegistStatus",
        "url_name": "master:client_regist_status_list",
        "permission": "master.view_clientregiststatus",
    },
    {
        "category": "契約",
        "name": "職種管理",
        "description": "職種情報の管理",
        "model": "master.JobCategory",
        "url_name": "master:job_category_list",
        "permission": "master.view_jobcategory",
    },
    {
        "category": "契約",
        "name": "契約書パターン管理",
        "description": "契約書パターンと文言の管理",
        "model": "master.ContractPattern",
        "url_name": "master:contract_pattern_list",
        "permission": "master.view_contractpattern",
    },
    {
        "category": "契約",
        "name": "最低賃金マスタ",
        "description": "都道府県別の最低賃金を管理",
        "model": "master.MinimumPay",
        "url_name": "master:minimum_pay_list",
        "permission": "master.view_minimumpay",
    },
    {
        "category": "契約",
        "name": "就業時間パターン管理",
        "description": "就業時間と休憩時間のパターンを管理",
        "model": "master.WorkTimePattern",
        "url_name": "master:worktime_pattern_list",
        "permission": "master.view_worktimepattern",
    },
    {
        "category": "勤怠",
        "name": "時間外算出パターン管理",
        "description": "時間外労働の算出パターンを管理",
        "model": "master.OvertimePattern",
        "url_name": "master:overtime_pattern_list",
        "permission": "master.view_overtimepattern",
    },
    {
        "category": "勤怠",
        "name": "勤怠打刻マスタ",
        "description": "勤怠時刻の丸め処理設定を管理",
        "model": "master.TimePunch",
        "url_name": "master:time_punch_list",
        "permission": "master.view_timepunch",
    },



    {
        "category": "請求",
        "name": "支払条件管理",
        "description": "請求・支払条件の管理",
        "model": "master.BillPayment",
        "url_name": "master:bill_payment_list",
        "permission": "master.view_billpayment",
    },
    {
        "category": "請求",
        "name": "会社銀行管理",
        "description": "会社銀行口座の管理",
        "model": "master.BillBank",
        "url_name": "master:bill_bank_list",
        "permission": "master.view_billbank",
    },
    {
        "category": "請求",
        "name": "銀行・銀行支店管理",
        "description": "銀行と銀行支店の統合管理",
        "model": "master.Bank",
        "url_name": "master:bank_management",
        "permission": "master.view_bank",
    },
    {
        "category": "その他",
        "name": "生成AI設定",
        "description": "生成AIに関する設定を管理します",
        "model": "master.GenerativeAiSetting",
        "url_name": "master:generative_ai_setting_list",
        "permission": "master.view_generativeaisetting",
    },
    {
        "category": "その他",
        "name": "お知らせ管理",
        "description": "会社・スタッフ・クライアントへのお知らせを管理",
        "model": "master.Information",
        "url_name": "master:information_list",
        "permission": "master.view_information",
    },
    {
        "category": "その他",
        "name": "メールテンプレート管理",
        "description": "各種メールテンプレートを管理します",
        "model": "master.MailTemplate",
        "url_name": "master:mail_template_list",
        "permission": "master.view_mailtemplate",
    },
    {
        "category": "その他",
        "name": "初期値マスタ",
        "description": "システムの各項目における初期値を管理します",
        "model": "master.DefaultValue",
        "url_name": "master:default_value_list",
        "permission": "master.view_defaultvalue",
    },
    {
        "category": "その他",
        "name": "設定値マスタ",
        "description": "ユーザーごとの設定値を管理します",
        "model": "master.UserParameter",
        "url_name": "master:user_parameter_list",
        "permission": "master.view_userparameter",
    },
    {
        "category": "その他",
        "name": "汎用文言テンプレート",
        "description": "画面に入力する定型文を管理します",
        "model": "master.PhraseTemplate",
        "url_name": "master:phrase_template_list",
        "permission": "master.view_phrasetemplate",
    },
]


def get_category_count(model_class):
    """カテゴリ数を取得"""
    try:
        if hasattr(model_class, "level"):
            return model_class.objects.filter(level=1, is_active=True).count()
        return 0
    except Exception:
        return 0


def get_data_count(model_class):
    """データ数を取得"""
    try:
        if hasattr(model_class, "level"):
            return model_class.objects.filter(level=2, is_active=True).count()

        # is_active属性があるモデルの場合
        if hasattr(model_class, "is_active"):
            return model_class.objects.filter(is_active=True).count()

        # is_active属性がないモデル（Informationなど）の場合
        return model_class.objects.count()
    except Exception:
        return 0


@login_required
@permission_required("master.view_qualification", raise_exception=True)
def master_index_list(request):
    """マスタ一覧画面を表示"""
    masters_by_category = {}

    for config in MASTER_CONFIGS:
        # 権限チェック
        if not request.user.has_perm(config["permission"]):
            continue

        try:
            # モデルクラスを動的に取得
            model_class = apps.get_model(config["model"])

            # データ件数を集計
            category_count = get_category_count(model_class)
            data_count = get_data_count(model_class)
            total_count = category_count + data_count

            # URLを生成
            try:
                url = reverse(config["url_name"])
            except Exception:
                url = "#"  # URLが生成できない場合のフォールバック

            # マスタ情報を構築
            master_info = {
                "name": config["name"],
                "description": config["description"],
                "category_count": category_count,
                "data_count": data_count,
                "total_count": total_count,
                "url": url,
            }

            # 分類別に整理
            category = config["category"]
            if category not in masters_by_category:
                masters_by_category[category] = []
            masters_by_category[category].append(master_info)

        except Exception:
            # モデルクラスが存在しない場合などのエラーハンドリング
            continue

    context = {
        "masters_by_category": masters_by_category,
    }
    return render(request, "master/master_index_list.html", context)


@login_required
@permission_required("master.view_timepunch", raise_exception=True)
def time_punch_list(request):
    """勤怠打刻マスタ一覧"""
    search_query = request.GET.get('search', '')
    
    # 基本クエリ
    queryset = TimePunch.objects.all()
    
    # 検索処理
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # ページネーション
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 変更履歴を取得（最新5件）
    change_logs = AppLog.objects.filter(
        model_name='TimePunch',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]
    
    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name='TimePunch',
        action__in=['create', 'update', 'delete']
    ).count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': queryset.count(),
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
        'history_url_name': 'master:time_punch_change_history_list',
    }
    
    return render(request, 'master/time_punch_list.html', context)





@login_required
@permission_required("master.add_timepunch", raise_exception=True)
def time_punch_create(request):
    """勤怠打刻マスタ作成"""
    if request.method == 'POST':
        form = TimePunchForm(request.POST)
        if form.is_valid():
            time_punch = form.save()
            messages.success(request, f'勤怠打刻マスタ「{time_punch.name}」を作成しました。')
            return redirect('master:time_punch_list')
    else:
        form = TimePunchForm()
    
    context = {
        'form': form,
        'title': '勤怠打刻マスタ作成',
    }
    
    return render(request, 'master/time_punch_form.html', context)


@login_required
@permission_required("master.change_timepunch", raise_exception=True)
def time_punch_edit(request, pk):
    """勤怠打刻マスタ編集"""
    time_punch = get_object_or_404(TimePunch, pk=pk)
    
    if request.method == 'POST':
        form = TimePunchForm(request.POST, instance=time_punch)
        if form.is_valid():
            time_punch = form.save()
            messages.success(request, f'勤怠打刻マスタ「{time_punch.name}」を更新しました。')
            return redirect('master:time_punch_list')
    else:
        form = TimePunchForm(instance=time_punch)
    
    context = {
        'form': form,
        'time_punch': time_punch,
        'title': '勤怠打刻マスタ編集',
    }
    
    return render(request, 'master/time_punch_form.html', context)


@login_required
@permission_required("master.delete_timepunch", raise_exception=True)
def time_punch_delete_confirm(request, pk):
    """勤怠打刻マスタ削除確認"""
    time_punch = get_object_or_404(TimePunch, pk=pk)
    
    context = {
        'time_punch': time_punch,
    }
    
    return render(request, 'master/time_punch_delete_confirm.html', context)


@login_required
@permission_required("master.delete_timepunch", raise_exception=True)
def time_punch_delete(request, pk):
    """勤怠打刻マスタ削除"""
    time_punch = get_object_or_404(TimePunch, pk=pk)
    
    if request.method == 'POST':
        name = time_punch.name
        time_punch.delete()
        messages.success(request, f'勤怠打刻マスタ「{name}」を削除しました。')
        return redirect('master:time_punch_list')
    
    return redirect('master:time_punch_list')


@login_required
@permission_required("master.view_timepunch", raise_exception=True)
def time_punch_change_history_list(request):
    """勤怠打刻マスタ変更履歴一覧"""
    logs = AppLog.objects.filter(
        model_name='TimePunch',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    return render(request, 'common/common_change_history_list.html', {
        'change_logs': logs_page,
        'page_title': '勤怠打刻マスタ変更履歴',
        'back_url_name': 'master:time_punch_list',
        'model_name': 'TimePunch',
    })
