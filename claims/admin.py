from django.contrib import admin
from .models import Claim, ClaimDetail, ClaimNote


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        "claim_id", "patient_name", "payer",
        "amount", "paid_amount", "status",
        "service_date", "last_updated",
    )
    search_fields = ("claim_id", "patient_name", "payer")
    list_filter = ("status", "payer", "flagged")


@admin.register(ClaimDetail)
class ClaimDetailAdmin(admin.ModelAdmin):
    list_display = ("claim", "cpt_codes", "denial_reason")


@admin.register(ClaimNote)
class ClaimNoteAdmin(admin.ModelAdmin):
    list_display = ("claim", "author", "created_at")
    search_fields = ("body",)
    autocomplete_fields = ("claim", "author")
