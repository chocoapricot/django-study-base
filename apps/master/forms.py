from django import forms
from .models import Qualification, Skill


class QualificationForm(forms.ModelForm):
    """資格フォーム"""
    
    class Meta:
        model = Qualification
        fields = [
            'name', 'category', 'issuing_organization',
            'validity_period', 'is_active', 'display_order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'category': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'issuing_organization': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'validity_period': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }


class SkillForm(forms.ModelForm):
    """技能フォーム"""
    
    class Meta:
        model = Skill
        fields = [
            'name', 'category', 'description', 'required_level',
            'is_active', 'display_order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'category': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'required_level': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }