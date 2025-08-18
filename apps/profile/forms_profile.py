from django import forms
from .models import StaffProfileQualification, StaffProfileSkill

class StaffProfileQualificationForm(forms.ModelForm):
    class Meta:
        model = StaffProfileQualification
        fields = ['qualification', 'acquired_date', 'expiry_date', 'certificate_number', 'memo', 'score']
        widgets = {
            'qualification': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'acquired_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'score': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        self.staff_profile = kwargs.pop('staff_profile', None)
        super().__init__(*args, **kwargs)
        from apps.master.models import Qualification
        qualifications = Qualification.objects.filter(level=2, is_active=True).select_related('parent').order_by('parent__display_order', 'parent__name', 'display_order', 'name')
        self.fields['qualification'].choices = [('', '選択してください')] + [
            (q.pk, f"{q.parent.name} > {q.name}" if q.parent else q.name)
            for q in qualifications
        ]

    def clean(self):
        cleaned_data = super().clean()
        qualification = cleaned_data.get('qualification')
        if qualification and self.staff_profile:
            existing_query = StaffProfileQualification.objects.filter(
                staff_profile=self.staff_profile,
                qualification=qualification
            )
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            if existing_query.exists():
                self.add_error('qualification', f'この資格「{qualification.name}」は既に登録されています。')
        return cleaned_data

class StaffProfileSkillForm(forms.ModelForm):
    class Meta:
        model = StaffProfileSkill
        fields = ['skill', 'acquired_date', 'years_of_experience', 'memo']
        widgets = {
            'skill': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'acquired_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.staff_profile = kwargs.pop('staff_profile', None)
        super().__init__(*args, **kwargs)
        from apps.master.models import Skill
        skills = Skill.objects.filter(level=2, is_active=True).select_related('parent').order_by('parent__display_order', 'parent__name', 'display_order', 'name')
        self.fields['skill'].choices = [('', '選択してください')] + [
            (s.pk, f"{s.parent.name} > {s.name}" if s.parent else s.name)
            for s in skills
        ]

    def clean(self):
        cleaned_data = super().clean()
        skill = cleaned_data.get('skill')
        if skill and self.staff_profile:
            existing_query = StaffProfileSkill.objects.filter(
                staff_profile=self.staff_profile,
                skill=skill
            )
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            if existing_query.exists():
                self.add_error('skill', f'この技能「{skill.name}」は既に登録されています。')
        return cleaned_data
