from django import forms
from .models import StaffQualification, StaffSkill
from apps.master.models import Qualification, Skill


class StaffQualificationForm(forms.ModelForm):
    """スタッフ資格フォーム"""
    
    class Meta:
        model = StaffQualification
        fields = [
            'qualification', 'acquired_date', 'expiry_date',
            'certificate_number', 'memo'
        ]
        widgets = {
            'qualification': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'acquired_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # アクティブな資格のみ表示
        self.fields['qualification'].queryset = Qualification.objects.filter(is_active=True)


class StaffSkillForm(forms.ModelForm):
    """スタッフ技能フォーム"""
    
    class Meta:
        model = StaffSkill
        fields = [
            'skill', 'level', 'acquired_date',
            'years_of_experience', 'memo'
        ]
        widgets = {
            'skill': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'level': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'acquired_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # アクティブな技能のみ表示
        self.fields['skill'].queryset = Skill.objects.filter(is_active=True)