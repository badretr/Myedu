from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PaymentTranche, ExtraService
from academics.models import StudentEnrollment, Classroom


def _balance_summary(tranches, today):
    total_requested = sum(t.amount_requested for t in tranches)
    total_paid = sum(t.amount_paid for t in tranches)
    total_remaining = sum(t.remaining for t in tranches)
    overdue = any(t.due_date and t.due_date < today and not t.is_paid for t in tranches)
    return total_requested, total_paid, total_remaining, overdue


@login_required
def my_balance(request):
    from django.utils import timezone
    today = timezone.localdate()

    if request.user.is_admin_user:
        enrollments = StudentEnrollment.objects.select_related('student', 'classroom').filter(
            is_active=True).order_by('classroom__name', 'student__first_name')
        selected_id = request.GET.get('student')
        selected_enrollment = get_object_or_404(StudentEnrollment, pk=selected_id) if selected_id else None

        # Vue d'ensemble : situation financière de chaque élève
        overview = []
        grand_requested = grand_paid = grand_remaining = 0
        overdue_count = 0
        tranches_by_enr = {}
        for t in PaymentTranche.objects.filter(enrollment__in=enrollments):
            tranches_by_enr.setdefault(t.enrollment_id, []).append(t)
        for enr in enrollments:
            ts = tranches_by_enr.get(enr.pk, [])
            requested, paid, remaining, overdue = _balance_summary(ts, today)
            grand_requested += requested
            grand_paid += paid
            grand_remaining += remaining
            if overdue:
                overdue_count += 1
            overview.append({
                'enrollment': enr,
                'requested': requested,
                'paid': paid,
                'remaining': remaining,
                'overdue': overdue,
                'has_tranches': bool(ts),
            })

        tranches = []
        total_requested = total_paid = total_remaining = 0
        if selected_enrollment:
            tranches = PaymentTranche.objects.filter(enrollment=selected_enrollment)
            total_requested, total_paid, total_remaining, _ = _balance_summary(tranches, today)

        return render(request, 'finance/balance.html', {
            'admin_mode': True,
            'today': today,
            'classrooms': Classroom.objects.order_by('name'),
            'overview': overview,
            'grand_requested': grand_requested,
            'grand_paid': grand_paid,
            'grand_remaining': grand_remaining,
            'overdue_count': overdue_count,
            'selected_enrollment': selected_enrollment,
            'tranches': tranches,
            'total_requested': total_requested,
            'total_paid': total_paid,
            'total_remaining': total_remaining,
            'extra_services': ExtraService.objects.filter(
                enrollment=selected_enrollment, is_active=True) if selected_enrollment else [],
        })

    enrollment = request.user.linked_enrollment
    tranches = []
    if enrollment and enrollment.is_active:
        tranches = PaymentTranche.objects.filter(enrollment=enrollment)
    total_requested, total_paid, total_remaining, _ = _balance_summary(tranches, today)
    return render(request, "finance/balance.html", {
        "enrollment": enrollment,
        "today": today,
        "tranches": tranches,
        "total_requested": total_requested,
        "total_paid": total_paid,
        "total_remaining": total_remaining,
        "extra_services": ExtraService.objects.filter(
            enrollment=enrollment, is_active=True) if enrollment else [],
    })


@login_required
def manage_tranches(request, enrollment_pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    enrollment = get_object_or_404(StudentEnrollment, pk=enrollment_pk)
    tranches = PaymentTranche.objects.filter(enrollment=enrollment)

    def decimal_or_zero(value):
        value = (value or "").strip()
        return value if value else 0

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            if enrollment.max_installments and tranches.count() >= enrollment.max_installments:
                messages.error(request, "Nombre maximum de tranches autorisées atteint pour cet élève.")
                return redirect("finance:manage_tranches", enrollment_pk=enrollment_pk)
            PaymentTranche.objects.create(
                enrollment=enrollment,
                label=request.POST.get("label"),
                description=request.POST.get("description", "").strip(),
                school_fees=decimal_or_zero(request.POST.get("school_fees")),
                other_fees=decimal_or_zero(request.POST.get("other_fees")),
                amount_requested=decimal_or_zero(request.POST.get("amount_requested")),
                amount_paid=decimal_or_zero(request.POST.get("amount_paid")),
                reduction_rate=decimal_or_zero(request.POST.get("reduction_rate")),
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
            if enrollment.student.parent_account_id:
                from core.views import notify_user
                notify_user(
                    enrollment.student.parent_account,
                    "Paiement enregistré",
                    f"{tranche.label} — {tranche.amount_paid} DT reçus le {tranche.paid_at:%d/%m/%Y}. Merci !",
                    "/finance/balance/",
                )
            messages.success(request, "Paiement enregistré.")
        elif action == "toggle_validated":
            tranche_id = request.POST.get("tranche_id")
            tranche = get_object_or_404(PaymentTranche, pk=tranche_id)
            tranche.is_bank_validated = not tranche.is_bank_validated
            tranche.save(update_fields=["is_bank_validated"])
            messages.success(request, "Statut de validation mis à jour.")
        elif action == "set_payment_settings":
            enrollment.payment_method = request.POST.get("payment_method", "")
            enrollment.max_installments = request.POST.get("max_installments") or 1
            enrollment.save(update_fields=["payment_method", "max_installments"])
            messages.success(request, "Paramètres de paiement mis à jour.")
        return redirect("finance:manage_tranches", enrollment_pk=enrollment_pk)
    return render(request, "finance/manage_tranches.html", {
        "enrollment": enrollment,
        "tranches": tranches,
    })


@login_required
def services_admin(request):
    """Gestion des services annexes (cantine, transport) par l'administration."""
    if not request.user.is_admin_user:
        return redirect("core:home")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            enrollment = get_object_or_404(StudentEnrollment, pk=request.POST.get("enrollment"))
            service, created = ExtraService.objects.get_or_create(
                enrollment=enrollment,
                service_type=request.POST.get("service_type"),
                defaults={
                    "monthly_fee": request.POST.get("monthly_fee") or 0,
                    "notes": request.POST.get("notes", "").strip(),
                },
            )
            if not created:
                service.monthly_fee = request.POST.get("monthly_fee") or 0
                service.notes = request.POST.get("notes", "").strip()
                service.is_active = True
                service.save()
            if enrollment.student.parent_account_id:
                from core.views import notify_user
                notify_user(
                    enrollment.student.parent_account,
                    f"Inscription {service.get_service_type_display().lower()}",
                    f"{enrollment.student.get_full_name()} — {service.get_service_type_display()} : {service.monthly_fee} DT/mois.",
                    "/finance/balance/",
                )
            messages.success(request, "Service enregistré.")
        elif action == "toggle":
            service = get_object_or_404(ExtraService, pk=request.POST.get("service_id"))
            service.is_active = not service.is_active
            service.save(update_fields=["is_active"])
        elif action == "delete":
            ExtraService.objects.filter(pk=request.POST.get("service_id")).delete()
            messages.success(request, "Service supprimé.")
        return redirect("finance:services_admin")
    services = ExtraService.objects.select_related(
        "enrollment__student", "enrollment__classroom"
    ).order_by("enrollment__classroom__name", "enrollment__student__first_name")
    enrollments = StudentEnrollment.objects.filter(is_active=True).select_related(
        "student", "classroom"
    ).order_by("classroom__name", "student__first_name")
    return render(request, "finance/services.html", {
        "services": services,
        "enrollments": enrollments,
    })


@login_required
def receipt_pdf(request, tranche_pk):
    """Reçu de paiement PDF numéroté pour une tranche payée."""
    tranche = get_object_or_404(
        PaymentTranche.objects.select_related("enrollment__student", "enrollment__classroom__academic_year"),
        pk=tranche_pk,
    )
    enrollment = tranche.enrollment
    student = enrollment.student
    is_own = request.user.pk == student.pk
    is_parent_of = student.parent_account_id == request.user.pk
    if not (request.user.is_admin_user or is_own or is_parent_of):
        return redirect("core:home")
    if not tranche.amount_paid:
        messages.warning(request, "Aucun paiement enregistré pour cette tranche.")
        return redirect("finance:my_balance")

    from io import BytesIO
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A5, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    indigo = colors.HexColor("#4f46e5")
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A5), topMargin=1 * cm, bottomMargin=1 * cm,
                            leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Title"], textColor=indigo, fontSize=16, spaceAfter=0)
    sub_style = ParagraphStyle("s", parent=styles["Normal"], alignment=1, textColor=colors.grey, spaceAfter=10)
    label_style = ParagraphStyle("l", parent=styles["Normal"], fontSize=10)

    year = enrollment.classroom.academic_year.label if enrollment.classroom and enrollment.classroom.academic_year else ""
    numero = f"REC-{tranche.pk:05d}"
    story = [
        Paragraph("Myedu — École", title_style),
        Paragraph(f"Reçu de paiement N° {numero} — Année scolaire {year}", sub_style),
    ]
    paid_date = tranche.paid_at.strftime("%d/%m/%Y") if tranche.paid_at else "—"
    method = enrollment.get_payment_method_display() or "—"
    info = Table([
        [Paragraph(f"<b>Élève :</b> {student.get_full_name()}", label_style),
         Paragraph(f"<b>Matricule :</b> {enrollment.matricule}", label_style)],
        [Paragraph(f"<b>Classe :</b> {enrollment.classroom}", label_style),
         Paragraph(f"<b>Date du paiement :</b> {paid_date}", label_style)],
        [Paragraph(f"<b>Tranche :</b> {tranche.label}{' — ' + tranche.description if tranche.description else ''}", label_style),
         Paragraph(f"<b>Mode de paiement :</b> {method}", label_style)],
    ], colWidths=[9.5 * cm, 8 * cm])
    info.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, indigo),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [info, Spacer(1, 10)]

    amounts = Table([
        ["Montant demandé", "Montant payé", "Reste à payer"],
        [f"{tranche.amount_requested} DT", f"{tranche.amount_paid} DT", f"{tranche.remaining} DT"],
    ], colWidths=[5.8 * cm, 5.8 * cm, 5.8 * cm])
    amounts.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), indigo),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, indigo),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [amounts, Spacer(1, 24)]

    sign = Table([
        [Paragraph("<b>Cachet et signature de l'école</b>", label_style)],
    ], colWidths=[8 * cm])
    sign.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    story.append(sign)

    doc.build(story)
    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="recu_{numero}.pdf"'
    return response
