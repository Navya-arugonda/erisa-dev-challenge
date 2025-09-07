import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from claims.models import Claim

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%m-%Y")

def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

class Command(BaseCommand):
    help = "Import claims from a CSV file (id/claim_id, patient_name, billed/amount, paid_amount, status, insurer_name/payer, discharge_date/service_date). Upserts by claim_id."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")

    def handle(self, *args, **opts):
        path = opts["csv_path"]
        created = updated = 0
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # accept multiple header names
                claim_id = row.get("claim_id") or row.get("id") or row.get("Claim ID")
                patient_name = row.get("patient_name") or row.get("Patient") or row.get("patient")
                payer = row.get("insurer_name") or row.get("Payer") or row.get("Insurer") or row.get("payer")
                billed = row.get("billed_amount") or row.get("Billed") or row.get("amount") or "0"
                paid = row.get("paid_amount") or row.get("Paid") or "0"
                status = row.get("status") or row.get("Status") or "Denied"
                date = row.get("discharge_date") or row.get("Service date") or row.get("service_date")

                obj, is_new = Claim.objects.update_or_create(
                    claim_id=str(claim_id).strip(),
                    defaults=dict(
                        patient_name=(patient_name or "").strip(),
                        payer=(payer or "").strip(),
                        amount=float(str(billed).replace(",","").replace("$","") or 0),
                        paid_amount=float(str(paid).replace(",","").replace("$","") or 0),
                        status=status.strip().title() if status else "Denied",
                        service_date=parse_date(date),
                    ),
                )
                created += is_new
                updated += (not is_new)
        self.stdout.write(self.style.SUCCESS(f"Done. Created: {created}, Updated: {updated}"))
