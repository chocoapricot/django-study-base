from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from .models import Staff
from .models_evaluation import StaffEvaluation
from .forms import StaffEvaluationForm
from apps.system.logs.utils import log_view_detail
from .text_utils import generate_staff_evaluations_full_text
from apps.common.ai_utils import run_ai_check

@login_required
@permission_required('staff.view_staffevaluation', raise_exception=True)
def staff_evaluation_list(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    evaluations_qs = staff.evaluations.all().order_by('-evaluation_date')
    paginator = Paginator(evaluations_qs, 20)
    page = request.GET.get('page')
    evaluations = paginator.get_page(page)

    ai_response = None
    error_message = None
    full_evaluations_text = None

    if request.method == 'POST':
        # テキスト生成
        full_evaluations_text = generate_staff_evaluations_full_text(staff)
        default_prompt = "あなたは人事評価の専門家です。以下のスタッフの評価内容を要約し、ポジティブな点、ネガティブな点、そして総合的な所感をまとめてください。\n\n【評価内容】\n{{contract_text}}"
        ai_response, error_message = run_ai_check('PROMPT_TEMPLATE_STAFF_EVALUATION', full_evaluations_text, default_prompt)

    return render(request, 'staff/staff_evaluation_list.html', {
        'staff': staff,
        'evaluations': evaluations,
        'ai_response': ai_response,
        'error_message': error_message,
    })

@login_required
@permission_required('staff.add_staffevaluation', raise_exception=True)
def staff_evaluation_create(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        form = StaffEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.staff = staff
            evaluation.evaluator = request.user
            evaluation.save()
            messages.success(request, '評価を登録しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        from django.utils import timezone
        form = StaffEvaluationForm(initial={'evaluation_date': timezone.now().date()})
    
    return render(request, 'staff/staff_evaluation_form.html', {'form': form, 'staff': staff})

@login_required
@permission_required('staff.change_staffevaluation', raise_exception=True)
def staff_evaluation_update(request, pk):
    evaluation = get_object_or_404(StaffEvaluation, pk=pk)
    staff = evaluation.staff
    if request.method == 'POST':
        form = StaffEvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            # 評価者は更新時に変更しない、あるいは更新者を記録するならここで更新
            # evaluation.evaluator = request.user 
            evaluation.save()
            messages.success(request, '評価を更新しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        form = StaffEvaluationForm(instance=evaluation)
    
    return render(request, 'staff/staff_evaluation_form.html', {'form': form, 'staff': staff, 'evaluation': evaluation})

@login_required
@permission_required('staff.delete_staffevaluation', raise_exception=True)
def staff_evaluation_delete(request, pk):
    evaluation = get_object_or_404(StaffEvaluation, pk=pk)
    staff = evaluation.staff
    if request.method == 'POST':
        evaluation.delete()
        messages.success(request, '評価を削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)
    return render(request, 'staff/staff_evaluation_confirm_delete.html', {'evaluation': evaluation, 'staff': staff})

