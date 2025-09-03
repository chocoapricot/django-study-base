from django import forms
from apps.master.models import StaffAgreement

class StaffAgreementConsentForm(forms.Form):
    """
    スタッフ同意確認フォーム
    """
    agreements = forms.ModelMultipleChoiceField(
        queryset=StaffAgreement.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="以下の内容に同意します。"
    )

    def __init__(self, *args, **kwargs):
        agreements_queryset = kwargs.pop('agreements_queryset', StaffAgreement.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['agreements'].queryset = agreements_queryset

    def clean_agreements(self):
        agreed = self.cleaned_data['agreements']
        required = self.fields['agreements'].queryset
        if len(agreed) != len(required):
            raise forms.ValidationError("すべての項目に同意してください。")
        return agreed
