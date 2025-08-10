from django import forms
from .models import StaffQualification, StaffSkill
from apps.master.models import Qualification, Skill


class StaffQualificationForm(forms.ModelForm):
    """スタッフ資格フォーム"""
    
    class Meta:
        model = StaffQualification
        fields = [
            'qualification', 'acquired_date', 'expiry_date',
            'certificate_number', 'score', 'memo'
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
            'score': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.staff = kwargs.pop('staff', None)
        super().__init__(*args, **kwargs)
        # アクティブな資格のみ表示
        self.fields['qualification'].queryset = Qualification.objects.filter(is_active=True)
    
    def clean(self):
        """重複チェック"""
        cleaned_data = super().clean()
        qualification = cleaned_data.get('qualification')
        
        if qualification and self.staff:
            # 編集時は自分自身を除外
            existing_query = StaffQualification.objects.filter(
                staff=self.staff,
                qualification=qualification
            )
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            if existing_query.exists():
                # 特定のフィールドにエラーを関連付ける
                self.add_error('qualification', f'この資格「{qualification.name}」は既に登録されています。')
        
        return cleaned_data


class StaffSkillForm(forms.ModelForm):
    """スタッフ技能フォーム"""
    
    class Meta:
        model = StaffSkill
        fields = [
            'skill', 'acquired_date',
            'years_of_experience', 'memo'
        ]
        widgets = {
            'skill': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'acquired_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.staff = kwargs.pop('staff', None)
        super().__init__(*args, **kwargs)
        # アクティブな技能のみ表示
        self.fields['skill'].queryset = Skill.objects.filter(is_active=True)
    
    def clean(self):
        """重複チェック"""
        cleaned_data = super().clean()
        skill = cleaned_data.get('skill')
        
        if skill and self.staff:
            # 編集時は自分自身を除外
            existing_query = StaffSkill.objects.filter(
                staff=self.staff,
                skill=skill
            )
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            if existing_query.exists():
                # 特定のフィールドにエラーを関連付ける
                self.add_error('skill', f'この技能「{skill.name}」は既に登録されています。')
        
        return cleaned_data