from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PaymentTranche
from academics.models import StudentEnrollment


@login_required
def my_balance(request):
    enrollment = None
    tranches = []
    try:
        enrollment = StudentEnrollment.objects.get(student=request.user, is_active=True)
        tranches = PaymentTranche.objects.filter(enrollment=enrollment)
    except StudentEnrollment.DoesNotExist:
        pass
    total_requested = sum(t.amount_requested for t in tranches)
    total_paid = sum(t.amount_paid for t in tranches)
    total_remaining = sum(t.remaining for t in tranches)
    return render(request, "finance/balance.html", {
        "enrollment": enrollment,
        "tranches": tranches,
        "total_requested": total_requested,
        "total_paid": total_paid,
        "total_remaining": total_remaining,
    })


@login_required
def manage_tranches(request, enrollment_pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    enrollment = get_object_or_404(StudentEnrollment, pk=enrollment_pk)
    tranches = PaymentTranche.objects.filter(enrollment=enrollment)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            PaymentTranche.objects.create(
                enrollment=enrollment,
                label=request.POST.get("label"),
                description=request.POST.get("description", ""),
                school_fees=request.POST.get("school_fees", 0),
                other_fees=request.POST.get("other_fees", 0),
                amount_requested=request.POST.get("amount_requested", 0),
                amount_paid=request.POST.get("amount_paid", 0),
                reduction_rate=request.POST.get("reduction_rate", 0),
                order=tranches.count() + 1,
            )
            messages.success(request, "Tranche ajoutée.")
        elif action == "pay":
            tranche_id = request.POST.get("tranche_id")
            tranche = get_object_or_404(PaymentTranche, pk=tranche_id)
            tranche.amount_paid = tranche.amount_requested
            from django.utils import timezone
            tranche.paid_at = timezone.now().date()
            tranche.save()
            messages.success(request, "Paiement enregistré.")
        return redirect("finance:manage_tranches", enrollment_pk=enrollment_pk)
    return render(request, "finance/manage_tranches.html", {
        "enrollment": enrollment,
        "tranches": tranches,
    })
