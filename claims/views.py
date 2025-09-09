from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, Count, F, Q, Value, DecimalField
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.db.models.functions import Trim
from django.http import HttpResponse

from .forms import ClaimForm
from .models import Claim, ClaimDetail, ClaimNote


# ---------- helpers ----------
def _is_htmx(request):
    """Works whether or not django-htmx middleware is installed."""
    return getattr(request, "htmx", False) or request.headers.get("HX-Request") == "true"


# ---------- list & detail ----------
def claim_list(request):
    q = (request.GET.get("q") or "").strip()
    status_sel = (request.GET.get("status") or "").strip()

    qs = Claim.objects.all().order_by("-last_updated")

    # --- search ---
    if q:
        qs = qs.filter(
            Q(claim_id__icontains=q) |
            Q(patient_name__icontains=q) |
            Q(payer__icontains=q)
        )

    # --- status options (no choices on model -> build from DB) ---
    # Pull raw statuses, trim in DB where available, then dedupe/sort in Python.
    raw_statuses = list(
        Claim.objects.exclude(status__isnull=True)
             .annotate(_s=Trim("status"))
             .values_list("_s", flat=True)
    )
    statuses = sorted(
        { (s or "").strip() for s in raw_statuses if (s or "").strip() },
        key=lambda s: s.lower()
    )

    # --- apply status filter ---
    if status_sel:
        qs = qs.annotate(_s=Trim("status")).filter(_s__iexact=status_sel)

    ctx = {
        "claims": qs,
        "q": q,
        "status_sel": status_sel,
        "statuses": statuses,
    }

    if _is_htmx(request):
        # Return only the table for HTMX swaps
        return render(request, "includes/claim_table.html", ctx)

    return render(request, "claims/claim_list.html", ctx)

def claim_detail(request, pk):
    """Detail card (full page or HTMX partial)."""
    claim = get_object_or_404(Claim, pk=pk)
    detail = ClaimDetail.objects.filter(claim=claim).first()
    template = "includes/claim_detail.html" if _is_htmx(request) else "claims/claim_detail.html"
    return render(request, template, {"claim": claim, "detail": detail})


# ---------- create/update/delete ----------
@login_required
def claim_create(request):
    if request.method == "POST":
        form = ClaimForm(request.POST)
        if form.is_valid():
            obj = form.save()
            if _is_htmx(request):
                detail = ClaimDetail.objects.filter(claim=obj).first()
                return render(request, "includes/claim_detail.html", {"claim": obj, "detail": detail})
            return redirect("claim-detail", pk=obj.pk)
        if _is_htmx(request):
            return render(request, "includes/claim_form.html", {"form": form})
    else:
        form = ClaimForm()
        if _is_htmx(request):
            return render(request, "includes/claim_form.html", {"form": form})
    return render(request, "claims/claim_form.html", {"form": form})


@login_required
def claim_update(request, pk):
    obj = get_object_or_404(Claim, pk=pk)
    if request.method == "POST":
        form = ClaimForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            if _is_htmx(request):
                detail = ClaimDetail.objects.filter(claim=obj).first()
                return render(request, "includes/claim_detail.html", {"claim": obj, "detail": detail})
            return redirect("claim-detail", pk=obj.pk)
    else:
        form = ClaimForm(instance=obj)

    if _is_htmx(request):
        return render(request, "includes/claim_form.html", {"form": form})
    return render(request, "claims/claim_form.html", {"form": form, "obj": obj})


@login_required
def claim_delete(request, pk):
    obj = get_object_or_404(Claim, pk=pk)
    if request.method == "POST":
        obj.delete()
        if _is_htmx(request):
            return claim_list(request)  # return refreshed table
        return redirect("claim-list")
    template = "includes/confirm_delete.html" if _is_htmx(request) else "claims/confirm_delete.html"
    return render(request, template, {"obj": obj})


# ---------- flags & notes (HTMX endpoints) ----------
@require_POST
@login_required
def claim_flag_toggle(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    claim.flagged = not claim.flagged
    claim.save(update_fields=["flagged"])
    detail = ClaimDetail.objects.filter(claim=claim).first()
    return render(request, "includes/claim_detail.html", {"claim": claim, "detail": detail})


def notes_list(request, pk):
    """Return just the notes list fragment for a claim."""
    claim = get_object_or_404(Claim, pk=pk)
    # NOTE: your model uses `author` (not `user`)
    notes = claim.notes.select_related("author").order_by("-created_at")
    return render(request, "includes/notes_list.html", {"claim": claim, "notes": notes})


@login_required
@require_POST
def note_add(request, pk):
    """Create a note; for HTMX, return the refreshed list."""
    claim = get_object_or_404(Claim, pk=pk)
    body = (request.POST.get("body") or "").strip()
    if body:
        ClaimNote.objects.create(claim=claim, author=request.user, body=body)
    if _is_htmx(request):
        return notes_list(request, pk)
    return redirect("claim-detail", pk=pk)


# ---------- dashboard ----------
def dashboard(request):
    """Tiny admin dashboard with counts and sums."""
    money = DecimalField(max_digits=14, decimal_places=2)
    underpay_expr = ExpressionWrapper(F("amount") - F("paid_amount"), output_field=money)

    qs = Claim.objects.all()
    agg = qs.aggregate(
        total_claims=Count("id"),
        total_flagged=Count("id", filter=Q(flagged=True)),
        sum_billed=Coalesce(Sum("amount"), Value(0, output_field=money), output_field=money),
        sum_paid=Coalesce(Sum("paid_amount"), Value(0, output_field=money), output_field=money),
        avg_underpay=Avg(underpay_expr, filter=Q(amount__gt=F("paid_amount"))),
    )

    status_counts = qs.values("status").annotate(n=Count("id")).order_by("-n")[:10]
    top_payers = (
        qs.values("payer")
          .annotate(
              n=Count("id"),
              billed=Coalesce(Sum("amount"), Value(0, output_field=money), output_field=money),
              paid=Coalesce(Sum("paid_amount"), Value(0, output_field=money), output_field=money),
          )
          .order_by("-n")[:10]
    )
    recent_notes = ClaimNote.objects.select_related("claim", "author").order_by("-created_at")[:8]

    return render(request, "claims/dashboard.html", {
        "agg": agg,
        "status_counts": status_counts,
        "top_payers": top_payers,
        "recent_notes": recent_notes,
    })


def claim_form_close(request):
    """HTMX helper to clear the inline form panel."""
    return HttpResponse("")  # empty fragment -> panel becomes empty