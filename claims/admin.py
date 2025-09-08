# claims/admin.py
from django.contrib import admin
from .models import Claim, ClaimDetail, ClaimNote

class FlaggedFilter(admin.SimpleListFilter):
    title = "flagged"
    parameter_name = "flagged"

    def lookups(self, request, model_admin):
        return (("yes", "Flagged"), ("no", "Not flagged"))

    def queryset(self, request, qs):
        if self.value() == "yes":
            return qs.filter(flagged=True)
        if self.value() == "no":
            return qs.filter(flagged=False)
        return qs

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        "claim_id", "patient_name", "payer",
        "amount", "paid_amount", "status",
        "service_date", "last_updated", "flagged",
    )
    search_fields = ("claim_id", "patient_name", "payer")
    list_filter = ("status", "payer", FlaggedFilter)   # <- changed
    # Optional: allow quick toggling from the list page (flagged can't be first column)
    # list_editable = ("flagged",)
