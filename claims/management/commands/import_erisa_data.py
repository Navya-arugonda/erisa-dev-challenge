from django.core.management.base import BaseCommand, CommandError
from claims.models import Claim, ClaimDetail

from pathlib import Path
from datetime import datetime
import csv, json, decimal

# ---------- helpers ----------
def norm_key(k: str) -> str:
    """Normalize a header key (case/space/punct agnostic)."""
    if k is None:
        return ""
    s = "".join(ch for ch in str(k).strip().lower() if ch.isalnum())
    # e.g. "Claim ID" -> "claimid", "discharge_date" -> "dischargedate"
    return s

def normalize_row_map(row: dict) -> dict:
    """Return a dict with normalized keys."""
    out = {}
    for k, v in (row or {}).items():
        out[norm_key(k)] = v
    return out

def load_records(path: str):
    """
    Load CSV/JSON and normalize header keys.
    Auto-detect common CSV delimiters (| , ; \t).
    """
    p = Path(path)
    if not p.exists():
        raise CommandError(f"File not found: {path}")

    if p.suffix.lower() == ".csv":
        sample = p.read_text(encoding="utf-8-sig", errors="ignore")
        # Try Sniffer; fall back to a list of likely delimiters
        import csv as _csv
        try:
            dialect = _csv.Sniffer().sniff(sample[:4096], delimiters="|,;\t")
            delimiter = dialect.delimiter
        except Exception:
            # heuristic: prefer '|' if present in header, else comma
            header_line = sample.splitlines()[0] if sample else ""
            delimiter = "|" if "|" in header_line else ","

        rows = []
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            rdr = _csv.DictReader(f, delimiter=delimiter)
            for raw in rdr:
                rows.append(normalize_row_map(raw))
        return rows

    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("rows", [])
        return [normalize_row_map(r) for r in data]

    raise CommandError("Unsupported file type (use .csv or .json)")

def pick(row, *normed_keys, default=""):
    for k in normed_keys:
        if k in row and str(row[k]).strip() != "":
            return row[k]
    return default

def to_dec(val):
    if val in (None, "", "N/A"):
        return decimal.Decimal("0")
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return decimal.Decimal(s)
    except Exception:
        return decimal.Decimal("0")

def to_date(val):
    if not val:
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

# ---------- command ----------
class Command(BaseCommand):
    help = "Import ERISA sample data (CSV/JSON) into SQLite (append or overwrite)."

    def add_arguments(self, parser):
        parser.add_argument("--list", required=True, help="Path to claim list data (csv/json)")
        parser.add_argument("--detail", required=False, help="Path to claim detail data (csv/json)")
        parser.add_argument("--mode", choices=["append", "overwrite"], default="append",
                            help="append (default) or overwrite existing data")
        parser.add_argument("--dry-run", action="store_true",
                            help="Parse files and show diagnostics without writing to DB")

    def handle(self, *args, **opts):
        list_path   = opts["list"]
        detail_path = opts.get("detail")
        mode        = opts["mode"]
        dry         = opts["dry_run"]
        verbosity   = int(opts.get("verbosity", 1))

        list_rows = load_records(list_path)
        detail_rows = load_records(detail_path) if detail_path else []

        if verbosity >= 1:
            self.stdout.write(self.style.NOTICE(
                f"Loaded rows → list: {len(list_rows)}  detail: {len(detail_rows)}"
            ))
            if verbosity >= 2:
                # show sample headers we actually see (normalized)
                def sample_keys(rows):
                    return sorted({k for r in rows[:1] for k in r.keys()})
                self.stdout.write(f"Sample list keys:   {sample_keys(list_rows)}")
                self.stdout.write(f"Sample detail keys: {sample_keys(detail_rows)}")

        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: stopping before DB writes."))
            return

        if mode == "overwrite":
            self.stdout.write(self.style.WARNING("Overwrite mode: clearing tables…"))
            ClaimDetail.objects.all().delete()
            Claim.objects.all().delete()

        created, updated, linked = 0, 0, 0

        # --- import main claims ---
        for r in list_rows:
            # use normalized keys
            claim_id = pick(r, "claimid", "id", "claimid", "claim", default="")
            # tolerate weird variants (e.g., "claim_id" -> "claimid"; already normalized)
            if not claim_id:
                continue

            patient = pick(r, "patientname", "patient", "fullname")
            payer   = pick(r, "payer", "insurername", "insurer")
            billed  = to_dec(pick(r, "amount", "billedamount", "billed"))
            paid    = to_dec(pick(r, "paidamount", "paid"))
            status  = pick(r, "status")
            service = to_date(pick(r, "servicedate", "dischargedate", "dischargedon"))

            obj, was_created = Claim.objects.get_or_create(
                claim_id=str(claim_id),
                defaults={
                    "patient_name": patient,
                    "payer": payer,
                    "amount": billed,
                    "paid_amount": paid,
                    "status": status,
                    "service_date": service,
                },
            )
            if was_created:
                created += 1
            else:
                changed = False
                for field, val in {
                    "patient_name": patient,
                    "payer": payer,
                    "amount": billed,
                    "paid_amount": paid,
                    "status": status,
                    "service_date": service,
                }.items():
                    if getattr(obj, field) != val:
                        setattr(obj, field, val)
                        changed = True
                if changed:
                    obj.save()
                    updated += 1

        # --- import details (optional) ---
        if detail_rows:
            claims_by_id = {c.claim_id: c for c in Claim.objects.all().only("id", "claim_id")}
            for r in detail_rows:
                cid = pick(r, "claimid", "id")
                if not cid or cid not in claims_by_id:
                    continue
                claim = claims_by_id[cid]
                cpt   = pick(r, "cptcodes", "cpt")
                if isinstance(cpt, list):
                    cpt = ",".join([str(x) for x in cpt])
                denial = pick(r, "denialreason", "reason")

                ClaimDetail.objects.update_or_create(
                    claim=claim,
                    defaults={"cpt_codes": cpt, "denial_reason": denial},
                )
                linked += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported claims → created: {created}, updated: {updated}; details linked: {linked}"
        ))
