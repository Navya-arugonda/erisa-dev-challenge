from django.db import models
from django.conf import settings 

class Claim(models.Model):
    claim_id = models.CharField(max_length=32, db_index=True)
    patient_name= models.CharField(max_length=128, db_index=True)
    payer= models.CharField(max_length=128, db_index=True)
    amount= models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount= models.DecimalField(max_digits=12, decimal_places=2)
    status= models.CharField(max_length=32, db_index=True)
    service_date= models.DateField(db_index=True)
    last_updated= models.DateTimeField(auto_now=True, db_index=True)
    flagged= models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            # speeds up typical filters/sorts; keep order asc for portability
            models.Index(fields=['status', 'last_updated'], name='claim_status_lastupd_idx'),
            models.Index(fields=['flagged', 'last_updated'], name='claim_flag_lastupd_idx'),
        ]

    def __str__(self):
        return f"{self.claim_id} — {self.patient_name}"
    
    
class ClaimDetail(models.Model):
    # One-to-one with the main claim
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name="detail")
    cpt_codes = models.TextField(blank=True)     # e.g. "99204,82947,99406"
    denial_reason = models.TextField(blank=True)

    def cpt_list(self):
        return [c.strip() for c in self.cpt_codes.replace(";", ",").split(",") if c.strip()]


class ClaimNote(models.Model):
    claim = models.ForeignKey(Claim, related_name="notes", on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.author or "Anonymous"
        return f"Note on {self.claim.claim_id} by {who} @ {self.created_at:%Y-%m-%d %H:%M}"
    
    
