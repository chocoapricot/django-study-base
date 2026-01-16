from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import (
    Information,
    InformationFile,
    MailTemplate,
    DefaultValue,
    UserParameter,
    GenerativeAiSetting,
)
from .forms import (
    InformationForm,
    MailTemplateForm,
    DefaultValueForm,
    UserParameterAdminForm as UserParameterForm,
    GenerativeAiSettingForm,
)
from apps.system.logs.models import AppLog
from apps.company.models import Company

# メールテンプレート管理ビュー
@login_required
@permission_required("master.view_mailtemplate", raise_exception=True)
def mail_template_list(request):
    """メールテンプレート一覧"""
    search_query = request.GET.get("search", "")

    mail_templates = MailTemplate.objects.all()

    if search_query:
        mail_templates = mail_templates.filter(
            Q(name__icontains=search_query)
            | Q(template_key__icontains=search_query)
            | Q(subject__icontains=search_query)
            | Q(body__icontains=search_query)
        )

    mail_templates = mail_templates.order_by("template_key")

    paginator = Paginator(mail_templates, 20)
    page = request.GET.get("page")
    mail_templates_page = paginator.get_page(page)

    change_logs = AppLog.objects.filter(
        model_name="MailTemplate", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="MailTemplate", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "mail_templates": mail_templates_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:mail_template_change_history_list",
    }
    return render(request, "master/mail_template_list.html", context)


@login_required
@permission_required("master.view_mailtemplate", raise_exception=True)
def mail_template_detail(request, pk):
    """メールテンプレート詳細"""
    mail_template = get_object_or_404(MailTemplate, pk=pk)
    context = {"mail_template": mail_template}
    return render(request, "master/mail_template_detail.html", context)


@login_required
@permission_required("master.change_mailtemplate", raise_exception=True)
def mail_template_update(request, pk):
    """メールテンプレート編集"""
    mail_template = get_object_or_404(MailTemplate, pk=pk)

    if request.method == "POST":
        form = MailTemplateForm(request.POST, instance=mail_template)
        if form.is_valid():
            mail_template = form.save()
            messages.success(
                request, f"メールテンプレート「{mail_template.name}」を更新しました。"
            )
            return redirect("master:mail_template_list")
    else:
        form = MailTemplateForm(instance=mail_template)

    context = {
        "form": form,
        "mail_template": mail_template,
        "title": f"メールテンプレート編集 - {mail_template.name}",
    }
    return render(request, "master/mail_template_form.html", context)


@login_required
@permission_required("master.view_mailtemplate", raise_exception=True)
def mail_template_change_history_list(request):
    """メールテンプレート変更履歴一覧"""
    logs = AppLog.objects.filter(
        model_name="MailTemplate", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "メールテンプレート変更履歴",
            "back_url_name": "master:mail_template_list",
            "model_name": "MailTemplate",
        },
    )

# お知らせ管理ビュー
@login_required
@permission_required("master.view_information", raise_exception=True)
def information_list(request):
    """お知らせ一覧"""
    search_query = request.GET.get("search", "")

    information_list = Information.objects.all()

    if search_query:
        information_list = information_list.filter(
            Q(subject__icontains=search_query) | Q(content__icontains=search_query)
        )

    information_list = information_list.order_by("-start_date")

    paginator = Paginator(information_list, 20)
    page = request.GET.get("page")
    information_page = paginator.get_page(page)

    # 変更履歴（最新5件）
    change_logs = AppLog.objects.filter(
        model_name="Information", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name="Information", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "information_list": information_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/information_list.html", context)


@login_required
@permission_required("master.view_information", raise_exception=True)
def information_detail(request, pk):
    """お知らせ詳細"""
    information = get_object_or_404(Information, pk=pk)
    context = {
        "information": information,
    }
    return render(request, "master/information_detail.html", context)


@login_required
@permission_required("master.add_information", raise_exception=True)
def information_create(request):
    """お知らせ作成"""
    company = Company.objects.first()
    if request.method == "POST":
        form = InformationForm(request.POST, request.FILES)
        if form.is_valid():
            information = form.save(commit=False)
            if company:
                information.corporation_number = company.corporate_number
            information.save()

            # Handle file uploads
            for f in request.FILES.getlist("attachments"):
                InformationFile.objects.create(information=information, file=f)

            messages.success(
                request, f"お知らせ「{information.subject}」を作成しました。"
            )
            return redirect("master:information_list")
    else:
        form = InformationForm()

    context = {
        "form": form,
        "title": "お知らせ作成",
    }
    return render(request, "master/information_form.html", context)


@login_required
@permission_required("master.change_information", raise_exception=True)
def information_update(request, pk):
    """お知らせ編集"""
    information = get_object_or_404(Information, pk=pk)

    if request.method == "POST":
        form = InformationForm(request.POST, request.FILES, instance=information)
        if form.is_valid():
            # Handle file deletion
            delete_ids = request.POST.getlist("delete_attachments")
            if delete_ids:
                files_to_delete = InformationFile.objects.filter(
                    pk__in=delete_ids, information=information
                )
                for f in files_to_delete:
                    f.delete()

            information = form.save()

            # Handle new file uploads
            for f in request.FILES.getlist("attachments"):
                InformationFile.objects.create(information=information, file=f)

            messages.success(
                request, f"お知らせ「{information.subject}」を更新しました。"
            )
            return redirect("master:information_list")
    else:
        form = InformationForm(instance=information)

    context = {
        "form": form,
        "information": information,
        "title": f"お知らせ編集 - {information.subject}",
    }
    return render(request, "master/information_form.html", context)


@login_required
@permission_required("master.delete_information", raise_exception=True)
def information_delete(request, pk):
    """お知らせ削除"""
    information = get_object_or_404(Information, pk=pk)

    if request.method == "POST":
        information_subject = information.subject
        information.delete()
        messages.success(request, f"お知らせ「{information_subject}」を削除しました。")
        return redirect("master:information_list")

    context = {
        "information": information,
        "title": f"お知らせ削除 - {information.subject}",
    }
    return render(request, "master/information_confirm_delete.html", context)


@login_required
@permission_required("master.view_information", raise_exception=True)
def information_all_change_history_list(request):
    """お知らせマスタ全体の変更履歴一覧"""

    # お知らせマスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="Information", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)  # 1ページあたり20件
    page_number = request.GET.get("page")
    logs = paginator.get_page(page_number)

    context = {
        "change_logs": logs,
        "model_name": "Information",
        "page_title": "お知らせマスタ変更履歴",
        "back_url_name": "master:information_list",
    }
    return render(request, "common/common_change_history_list.html", context)

@login_required
@permission_required("master.view_defaultvalue", raise_exception=True)
def default_value_list(request):
    """初期値マスタ一覧"""
    search_query = request.GET.get("search", "")
    items = DefaultValue.objects.all()
    if search_query:
        items = items.filter(
            Q(target_item__icontains=search_query) | Q(value__icontains=search_query)
        )

    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)

    change_logs = AppLog.objects.filter(model_name="DefaultValue", action__in=["update"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="DefaultValue", action__in=["update"]).count()

    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:default_value_change_history_list",
        "title": "初期値マスタ",
    }
    return render(request, "master/default_value_list.html", context)


@login_required
@permission_required("master.change_defaultvalue", raise_exception=True)
def default_value_update(request, pk):
    """初期値マスタ編集"""
    item = get_object_or_404(DefaultValue, pk=pk)
    if request.method == "POST":
        form = DefaultValueForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"初期値「{item.target_item}」を更新しました。")
            return redirect("master:default_value_list")
    else:
        form = DefaultValueForm(instance=item)

    context = {
        "form": form,
        "item": item,
        "title": f"初期値編集 - {item.target_item}",
    }
    return render(request, "master/default_value_form.html", context)


@login_required
@permission_required("master.view_defaultvalue", raise_exception=True)
def default_value_change_history_list(request):
    """初期値マスタ変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="DefaultValue", action__in=["update"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "初期値マスタ変更履歴",
            "back_url_name": "master:default_value_list",
            "model_name": "DefaultValue",
        },
    )


@login_required
@permission_required("master.view_userparameter", raise_exception=True)
def user_parameter_list(request):
    """設定値マスタ一覧"""
    search_query = request.GET.get("search", "")
    items = UserParameter.objects.all()
    if search_query:
        items = items.filter(
            Q(target_item__icontains=search_query) | Q(value__icontains=search_query)
        )

    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)

    change_logs = AppLog.objects.filter(model_name="UserParameter", action__in=["update"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="UserParameter", action__in=["update"]).count()

    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:user_parameter_change_history_list",
        "title": "設定値マスタ",
    }
    return render(request, "master/user_parameter_list.html", context)


@login_required
@permission_required("master.change_userparameter", raise_exception=True)
def user_parameter_update(request, pk):
    """設定値マスタ編集"""
    item = get_object_or_404(UserParameter, pk=pk)
    if request.method == "POST":
        form = UserParameterForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"設定値「{item.target_item}」を更新しました。")
            return redirect("master:user_parameter_list")
    else:
        form = UserParameterForm(instance=item)

    context = {
        "form": form,
        "item": item,
        "title": f"設定値編集 - {item.target_item}",
    }
    return render(request, "master/user_parameter_form.html", context)


@login_required
@permission_required("master.view_userparameter", raise_exception=True)
def user_parameter_change_history_list(request):
    """設定値マスタ変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="UserParameter", action__in=["update"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "設定値マスタ変更履歴",
            "back_url_name": "master:user_parameter_list",
            "model_name": "UserParameter",
        },
    )


@login_required
@permission_required("master.view_generativeaisetting", raise_exception=True)
def generative_ai_setting_list(request):
    """生成AI設定一覧"""
    search_query = request.GET.get("search", "")
    items = GenerativeAiSetting.objects.all()
    if search_query:
        items = items.filter(
            Q(target_item__icontains=search_query) | Q(value__icontains=search_query)
        )

    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)

    change_logs = AppLog.objects.filter(model_name="GenerativeAiSetting", action__in=["update"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="GenerativeAiSetting", action__in=["update"]).count()

    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:generative_ai_setting_change_history_list",
        "title": "生成AI設定",
    }
    return render(request, "master/generative_ai_setting_list.html", context)


@login_required
@permission_required("master.change_generativeaisetting", raise_exception=True)
def generative_ai_setting_update(request, pk):
    """生成AI設定編集"""
    item = get_object_or_404(GenerativeAiSetting, pk=pk)
    if request.method == "POST":
        form = GenerativeAiSettingForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"生成AI設定「{item.target_item}」を更新しました。")
            return redirect("master:generative_ai_setting_list")
    else:
        form = GenerativeAiSettingForm(instance=item)

    context = {
        "form": form,
        "item": item,
        "title": f"生成AI設定編集 - {item.target_item}",
    }
    return render(request, "master/generative_ai_setting_form.html", context)


@login_required
@permission_required("master.view_generativeaisetting", raise_exception=True)
def generative_ai_setting_change_history_list(request):
    """生成AI設定変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="GenerativeAiSetting", action__in=["update"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "生成AI設定変更履歴",
            "back_url_name": "master:generative_ai_setting_list",
            "model_name": "GenerativeAiSetting",
        },
    )
