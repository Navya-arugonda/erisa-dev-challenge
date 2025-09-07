from django import forms
from .models import Claim, ClaimNote

class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ["claim_id","patient_name","payer","amount","paid_amount","status","service_date"]

class NoteForm(forms.ModelForm):
    class Meta:
        model = ClaimNote
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Add a note…"
            })
        }
