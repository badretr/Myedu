from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import CustomUser
from academics.models import Classroom, Subject as AcademicSubject

from .models import AppointmentRequest, Message, News, Notification, SchoolEvent, Suggestion


def notify_roles(role, title, content='', target_url=''):
    recipients = CustomUser.objects.filter(role=role)
    notifications = [
        Notification(recipient=user, title=title, content=content, target_url=target_url)
        for user in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def notify_user(user, title, content='', target_url=''):
    Notification.objects.create(recipient=user, title=title, content=content, target_url=target_url)


def check_payment_reminders():
    """Alerte les parents pour les tranches impayées en retard ou à échéance proche."""
    from finance.models import PaymentTranche
    today = timezone.localdate()
    tranches = PaymentTranche.objects.filter(
        reminder_sent=False, due_date__isnull=False, due_date__lte=today + timedelta(days=7),
    ).select_related('enrollment__student__parent_account')
    for tranche in tranches:
        if tranche.is_paid:
            continue
        parent = tranche.enrollment.student.parent_account
        if parent is None:
            continue
        if tranche.due_date < today:
            notify_user(parent, 'Paiement en retard',
                        f"{tranche.label} — échéance du {tranche.due_date:%d/%m/%Y} dépassée, reste {tranche.remaining} DT.",
                        '/finance/balance/')
        else:
            notify_user(parent, 'Échéance de paiement proche',
                        f"{tranche.label} — à régler avant le {tranche.due_date:%d/%m/%Y} ({tranche.remaining} DT).",
                        '/finance/balance/')
        tranche.reminder_sent = True
        tranche.save(update_fields=['reminder_sent'])


DOC_STATUS_STYLE = {
    'pending': 'warning',
    'processing': 'info',
    'ready': 'success',
    'delivered': 'secondary',
    'rejected': 'danger',
}


def build_admin_dashboard():
    from academics.models import Absence, StudentEnrollment, StudentNote
    from documents.models import DocumentRequest
    from finance.models import PaymentTranche
    from core.models import Suggestion

    today = timezone.localdate()
    overdue = [t for t in PaymentTranche.objects.filter(due_date__lt=today) if not t.is_paid]
    absences_today = Absence.objects.filter(date=today).select_related(
        'student__student', 'subject'
    )

    # Observations et punitions récentes (toute origine, y compris créées par l'admin)
    recent_notes = StudentNote.objects.select_related(
        'classroom', 'student__student', 'teacher', 'subject'
    ).order_by('-created_at')[:8]
    obs_count_total = StudentNote.objects.filter(note_type=StudentNote.TYPE_OBSERVATION).count()
    pun_count_total = StudentNote.objects.filter(note_type=StudentNote.TYPE_PUNITION).count()

    # Taux de recouvrement et recette du mois
    all_tranches = PaymentTranche.objects.all()
    total_requested = sum(t.amount_requested for t in all_tranches) or 0
    total_paid = sum(t.amount_paid for t in all_tranches) or 0
    collection_rate = round((total_paid / total_requested) * 100) if total_requested else 0
    revenue_this_month = sum(
        t.amount_paid for t in all_tranches
        if t.paid_at and t.paid_at.year == today.year and t.paid_at.month == today.month
    )

    # Répartition des demandes de documents par statut
    doc_counts = {status: 0 for status, _ in DocumentRequest.STATUS_CHOICES}
    for row in DocumentRequest.objects.values('status').annotate(count=Count('id')):
        doc_counts[row['status']] = row['count']
    total_docs = sum(doc_counts.values())
    doc_breakdown = [
        {
            'status': status, 'label': label, 'count': doc_counts.get(status, 0),
            'style': DOC_STATUS_STYLE.get(status, 'secondary'),
            'pct': round((doc_counts.get(status, 0) / total_docs) * 100) if total_docs else 0,
        }
        for status, label in DocumentRequest.STATUS_CHOICES
    ]

    return {
        'students_count': StudentEnrollment.objects.filter(is_active=True).count(),
        'teachers_count': CustomUser.objects.filter(role='teacher').count(),
        'parents_count': CustomUser.objects.filter(role='parent').count(),
        'absences_today': absences_today.count(),
        'absences_today_list': absences_today[:8],
        'overdue_count': len(overdue),
        'overdue_total': sum(t.remaining for t in overdue),
        'pending_docs': DocumentRequest.objects.filter(status__in=['pending', 'processing']).count(),
        'pending_appointments': AppointmentRequest.objects.filter(status='pending').count(),
        'new_suggestions': Suggestion.objects.filter(is_treated=False).count(),
        'collection_rate': collection_rate,
        'revenue_this_month': revenue_this_month,
        'doc_breakdown': doc_breakdown,
        'total_docs': total_docs,
        'recent_notes': recent_notes,
        'obs_count_total': obs_count_total,
        'pun_count_total': pun_count_total,
        'upcoming_events': SchoolEvent.objects.filter(
            Q(start_date__gte=today) | Q(end_date__gte=today)
        ).order_by('start_date')[:5],
    }


def home_view(request):
    news = News.objects.filter(is_public=True)
    if request.user.is_authenticated:
        user_messages = get_user_messages(request.user)
        unread_count = sum(1 for m in user_messages if not m.is_read_by(request.user))
        linked_enrollment = getattr(request.user, 'enrollment', None)
        appointments = AppointmentRequest.objects.filter(parent=request.user).order_by('-created_at') if request.user.is_parent else AppointmentRequest.objects.none()
        admin_appointments = AppointmentRequest.objects.select_related('parent', 'reviewed_by').all() if request.user.is_admin_user else AppointmentRequest.objects.none()
        notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        check_payment_reminders()
        today = timezone.localdate()
        upcoming_events = SchoolEvent.objects.filter(
            Q(start_date__gte=today) | Q(end_date__gte=today)
        ).order_by('start_date')[:5]
        dashboard = build_admin_dashboard() if request.user.is_admin_user else None
        return render(request, 'core/home.html', {
            'news': news,
            'unread_count': unread_count,
            'linked_enrollment': linked_enrollment,
            'appointments': appointments,
            'admin_appointments': admin_appointments,
            'notification_count': notification_count,
            'dashboard': dashboard,
            'upcoming_events': upcoming_events,
        })
    return render(request, 'core/home_public.html', {'news': news})


def get_user_messages(user):
    if user.is_admin_user:
        return Message.objects.none()

    enrollment = user.linked_enrollment

    # Les enseignants ne voient que leurs messages personnels (pas les broadcasts)
    if user.is_teacher:
        personal = Message.objects.filter(
            Q(recipient=user) | Q(sender=user),
            reply_to__isnull=True,
        )
        return personal.exclude(deleted_by=user).distinct()

    # Messages généraux (broadcast) — pour étudiants et parents
    broadcast = Message.objects.filter(classroom__isnull=True, recipient__isnull=True)
    result = broadcast

    # Messages de classe (pour les étudiants inscrits)
    if enrollment and enrollment.is_active:
        classroom_msgs = Message.objects.filter(classroom=enrollment.classroom, recipient__isnull=True)
        result = result | classroom_msgs

    # Messages personnels : où l'utilisateur est expéditeur OU destinataire
    personal = Message.objects.filter(
        Q(recipient=user) | Q(sender=user),
        reply_to__isnull=True,
    )
    result = result | personal

    return result.exclude(deleted_by=user).distinct()


@login_required
def inbox_view(request):
    if request.user.is_admin_user:
        return redirect('core:message_history')

    user_messages = get_user_messages(request.user)
    class_messages = []
    personal_messages = []
    for m in user_messages:
        entry = {'msg': m, 'is_read': m.is_read_by(request.user)}
        if m.recipient_id:
            personal_messages.append(entry)
        else:
            class_messages.append(entry)
    notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'core/inbox.html', {
        'class_messages': class_messages,
        'personal_messages': personal_messages,
        'notification_count': notification_count,
    })


@login_required
def message_detail(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    is_involved = request.user.pk in {msg.recipient_id, msg.sender_id}
    if not request.user.is_admin_user and msg.recipient_id and not is_involved:
        return redirect('core:inbox')
    msg.read_by.add(request.user)
    root = msg.reply_to or msg
    thread = Message.objects.filter(Q(pk=root.pk) | Q(reply_to=root)).select_related('sender', 'recipient').order_by('created_at')
    can_reply = bool(root.recipient_id) and request.user.pk in {root.sender_id, root.recipient_id}
    notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'core/message_detail.html', {
        'msg': msg, 'root': root, 'thread': thread, 'can_reply': can_reply,
        'notification_count': notification_count,
    })


@login_required
def message_reply(request, pk):
    original = get_object_or_404(Message, pk=pk)
    root = original.reply_to or original
    if not root.recipient_id or request.user.pk not in {root.sender_id, root.recipient_id}:
        return redirect('core:inbox')
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            other_user_id = root.recipient_id if request.user.pk == root.sender_id else root.sender_id
            reply = Message.objects.create(
                title='Ré: ' + root.title,
                content=content,
                sender=request.user,
                recipient_id=other_user_id,
                reply_to=root,
            )
            if reply.recipient_id:
                notify_user(reply.recipient, 'Nouvelle réponse', content[:80], f'/messages/{root.pk}/')
            messages.success(request, 'Réponse envoyée.')
    return redirect('core:message_detail', pk=root.pk)


@login_required
def message_delete_for_me(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    if request.method == 'POST':
        msg.deleted_by.add(request.user)
        messages.success(request, 'Message supprimé de votre boîte de réception.')
    return redirect('core:inbox')


@login_required
def message_create(request):
    if not request.user.is_admin_user:
        return redirect('core:inbox')
    teachers = CustomUser.objects.filter(role='teacher').order_by('first_name', 'last_name')
    students = CustomUser.objects.filter(role='student').select_related(
        'enrollment__classroom').order_by('first_name', 'last_name')
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        target = request.POST.get('target', 'all')
        attachment = request.FILES.get('attachment')
        classroom = None
        recipient = None
        if target == 'classroom':
            classroom_id = request.POST.get('classroom') or None
            classroom = Classroom.objects.get(pk=classroom_id) if classroom_id else None
            if not classroom:
                messages.error(request, 'Veuillez sélectionner une classe.')
                return redirect('core:message_create')
        elif target == 'student':
            student = CustomUser.objects.filter(pk=request.POST.get('student'), role='student').first()
            recipient = student.parent_account if student else None
            if not recipient:
                messages.error(request, "Cet élève n'a pas de parent associé à son compte.")
                return redirect('core:message_create')
        elif target == 'teacher':
            teacher_id = request.POST.get('teacher')
            recipient = CustomUser.objects.filter(pk=teacher_id, role='teacher').first() if teacher_id else None
            if not recipient:
                messages.error(request, 'Veuillez sélectionner un enseignant.')
                return redirect('core:message_create')
        else:
            messages.error(request, 'Veuillez choisir un destinataire.')
            return redirect('core:message_create')
        msg = Message.objects.create(
            title=title,
            content=content,
            sender=request.user,
            classroom=classroom,
            recipient=recipient,
            attachment=attachment,
        )
        if recipient:
            notify_user(recipient, 'Nouveau message de l\'administration', title or content[:80], f'/messages/{msg.pk}/')
        else:
            # Message de classe → notifier tous les parents concernés
            parents = CustomUser.objects.filter(
                role='parent', children__enrollment__classroom=classroom, children__enrollment__is_active=True
            ).distinct()
            Notification.objects.bulk_create([
                Notification(
                    recipient=parent,
                    title='Nouveau message',
                    content=title or 'Vous avez un nouveau message.',
                    target_url='/messages/',
                )
                for parent in parents
            ])
        messages.success(request, 'Message envoye.')
        return redirect('core:message_history')
    return render(request, 'core/message_form.html', {
        'classrooms': Classroom.objects.all(),
        'students': students,
        'teachers': teachers,
    })


@login_required
def message_history(request):
    if not request.user.is_admin_user:
        return redirect('core:inbox')
    base_qs = Message.objects.filter(reply_to__isnull=True).select_related('classroom', 'sender', 'recipient')
    class_messages = base_qs.filter(recipient__isnull=True)
    # Messages entre enseignants et administration
    teacher_messages = base_qs.filter(
        Q(sender__role='teacher', recipient__role='admin') |
        Q(sender__role='admin', recipient__role='teacher')
    ).annotate(reply_count=Count('replies'))
    # Messages avec les parents (exclure ceux déjà dans teacher_messages)
    personal_messages = base_qs.filter(recipient__isnull=False).exclude(
        Q(sender__role='teacher', recipient__role='admin') |
        Q(sender__role='admin', recipient__role='teacher')
    ).annotate(reply_count=Count('replies'))
    notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'core/message_history.html', {
        'class_messages': class_messages,
        'personal_messages': personal_messages,
        'teacher_messages': teacher_messages,
        'notification_count': notification_count,
    })


@login_required
def teacher_message_compose(request):
    """Permet à un enseignant d'envoyer un message à l'administration ou au parent d'un élève."""
    if not request.user.is_teacher:
        return redirect('core:home')

    # Récupérer les classes de l'enseignant
    classroom_ids = AcademicSubject.objects.filter(
        Q(teacher=request.user) | Q(teacher_tp=request.user)
    ).values_list('classroom_id', flat=True).distinct()
    classrooms = Classroom.objects.filter(pk__in=classroom_ids)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        target = request.POST.get('target', 'admin')
        attachment = request.FILES.get('attachment')
        recipient = None

        if target == 'admin':
            # Envoyer à l'administration
            admin_users = CustomUser.objects.filter(role='admin')
            if not admin_users.exists():
                messages.error(request, "Aucun administrateur trouvé.")
                return redirect('core:teacher_message_compose')
            # Envoyer à tous les admins ? Non, on envoie à un admin en particulier ou au premier
            recipient = admin_users.first()
        elif target == 'parent':
            student_id = request.POST.get('student')
            student = CustomUser.objects.filter(pk=student_id, role='student').first() if student_id else None
            if student and student.parent_account:
                recipient = student.parent_account
            if not recipient:
                messages.error(request, "Cet élève n'a pas de parent associé.")
                return redirect('core:teacher_message_compose')
        else:
            messages.error(request, "Destinataire invalide.")
            return redirect('core:teacher_message_compose')

        msg = Message.objects.create(
            title=title,
            content=content,
            sender=request.user,
            recipient=recipient,
            attachment=attachment,
        )
        notify_user(recipient, 'Nouveau message de votre enseignant', title or content[:80], f'/messages/{msg.pk}/')
        messages.success(request, 'Message envoyé.')
        return redirect('core:teacher_message_compose')

    # Liste des élèves dans les classes de l'enseignant (pour envoyer au parent)
    students = CustomUser.objects.filter(
        enrollment__classroom__in=classrooms,
        enrollment__is_active=True,
        parent_account__isnull=False,
    ).select_related('enrollment__classroom', 'parent_account').distinct()

    notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'core/teacher_message_compose.html', {
        'classrooms': classrooms,
        'students': students,
        'notification_count': notification_count,
    })


@login_required
def parent_message_to_teacher(request):
    """Permet à un parent d'envoyer un message à un enseignant de son enfant."""
    if not request.user.is_parent:
        return redirect('core:home')

    # Récupérer les enfants du parent
    children = request.user.children.filter(role='student', enrollment__is_active=True)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        teacher_id = request.POST.get('teacher')
        attachment = request.FILES.get('attachment')
        child_id = request.POST.get('child')

        teacher = CustomUser.objects.filter(pk=teacher_id, role='teacher').first() if teacher_id else None
        if not teacher:
            messages.error(request, "Veuillez sélectionner un enseignant.")
            return redirect('core:parent_message_to_teacher')

        about_student = children.filter(pk=child_id).first() if child_id else None

        msg = Message.objects.create(
            title=title,
            content=content,
            sender=request.user,
            recipient=teacher,
            attachment=attachment,
            about_student=about_student,
        )
        notify_user(teacher, 'Nouveau message de parent', f"De: {request.user.get_full_name()} - {title}", f'/messages/{msg.pk}/')
        messages.success(request, 'Message envoyé à l\'enseignant.')
        return redirect('core:parent_message_to_teacher')

    # Récupérer tous les enseignants des enfants
    teachers = CustomUser.objects.filter(
        Q(subjects_taught__classroom__in=children.values('enrollment__classroom'))
        | Q(subjects_taught_tp__classroom__in=children.values('enrollment__classroom')),
        role='teacher',
    ).prefetch_related('subjects_taught').distinct()

    notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'core/parent_message_to_teacher.html', {
        'children': children,
        'teachers': teachers,
        'notification_count': notification_count,
    })


@login_required
def message_admin_delete(request, pk):
    """Suppression permanente d'un message par l'administration."""
    if not request.user.is_admin_user:
        return redirect('core:home')
    msg = get_object_or_404(Message, pk=pk)
    if request.method == 'POST':
        # Supprimer aussi les réponses
        msg.replies.all().delete()
        msg.delete()
        messages.success(request, 'Message supprimé définitivement.')
    return redirect('core:message_history')


@login_required
def suggestions_view(request):
    if request.user.is_admin_user:
        suggestions = Suggestion.objects.select_related('sender').all()
        return render(request, 'core/suggestions.html', {
            'admin_mode': True,
            'suggestions': suggestions,
        })

    if not (request.user.is_student or request.user.is_parent):
        return redirect('core:home')

    last_24h = timezone.now() - timedelta(hours=24)
    can_suggest = not Suggestion.objects.filter(sender=request.user, created_at__gte=last_24h).exists()
    if request.method == 'POST' and can_suggest:
        Suggestion.objects.create(
            category=request.POST.get('category'),
            subcategory=request.POST.get('subcategory', ''),
            content=request.POST.get('content'),
            sender=request.user,
            is_anonymous='is_anonymous' in request.POST,
        )
        messages.success(request, 'Suggestion envoyee.')
        return redirect('core:suggestions')
    return render(request, 'core/suggestions.html', {'can_suggest': can_suggest, 'admin_mode': False})


@login_required
def news_create(request):
    if not request.user.is_admin_user:
        return redirect('core:home')
    if request.method == 'POST':
        news = News.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            image=request.FILES.get('image'),
            created_by=request.user,
            is_public='is_public' in request.POST,
        )
        notify_roles('parent', 'Nouvelle actualité', news.title, '/')
        messages.success(request, 'Actualité publiée.')
        return redirect('core:home')
    return render(request, 'core/news_form.html')


@login_required
def news_delete(request, pk):
    if not request.user.is_admin_user:
        return redirect('core:home')
    news = get_object_or_404(News, pk=pk)
    if request.method == 'POST':
        news.delete()
        messages.success(request, 'Actualite supprimee.')
    return redirect('core:home')


@login_required
def appointment_request_create(request):
    if not (request.user.is_parent or request.user.is_student):
        return redirect('core:home')
    if request.method == 'POST':
        requested_datetime_raw = request.POST.get('requested_datetime')
        requested_datetime = parse_datetime(requested_datetime_raw) if requested_datetime_raw else None
        if not requested_datetime:
            messages.error(request, 'Veuillez choisir une date et une heure valides.')
            return redirect('core:appointment_request_create')
        if timezone.is_naive(requested_datetime):
            requested_datetime = timezone.make_aware(requested_datetime, timezone.get_current_timezone())
        AppointmentRequest.objects.create(
            parent=request.user,
            requested_datetime=requested_datetime,
            reason=request.POST.get('reason', ''),
        )
        notify_roles('admin', 'Nouvelle demande de rendez-vous', request.user.get_full_name(), '/appointments/admin/')
        messages.success(request, 'Demande de rendez-vous envoyee.')
        return redirect('core:appointment_request_create')
    my_requests = AppointmentRequest.objects.filter(parent=request.user).order_by('-created_at')
    return render(request, 'core/appointment_request_form.html', {'my_requests': my_requests})


@login_required
def appointment_admin_view(request):
    if not request.user.is_admin_user:
        return redirect('core:home')
    appointments = AppointmentRequest.objects.select_related('parent', 'reviewed_by').all()
    if request.method == 'POST':
        appt = get_object_or_404(AppointmentRequest, pk=request.POST.get('appointment_id'))
        action = request.POST.get('action')
        if action in {'accepted', 'rejected'}:
            status_changed = appt.status != action
            appt.status = action
            appt.admin_notes = request.POST.get('admin_notes', '')
            appt.reviewed_by = request.user
            appt.reviewed_at = timezone.now()
            appt.save()
            if status_changed:
                notify_user(appt.parent, 'Rendez-vous mis à jour', appt.get_status_display(), '/appointments/new/')
            messages.success(request, 'Rendez-vous mis a jour.')
        return redirect('core:appointment_admin')
    return render(request, 'core/appointment_admin.html', {'appointments': appointments})


@login_required
def events_view(request):
    if not request.user.is_admin_user:
        return redirect('core:home')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            event = SchoolEvent.objects.create(
                title=request.POST.get('title', '').strip(),
                event_type=request.POST.get('event_type') or 'autre',
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date') or None,
                description=request.POST.get('description', '').strip(),
                created_by=request.user,
            )
            notify_roles('parent', 'Nouvel événement scolaire',
                         f"{event.title} — {event.start_date}", '/')
            notify_roles('student', 'Nouvel événement scolaire',
                         f"{event.title} — {event.start_date}", '/')
            messages.success(request, 'Événement ajouté et annoncé aux parents et élèves.')
        elif action == 'delete':
            SchoolEvent.objects.filter(pk=request.POST.get('event_id')).delete()
            messages.success(request, 'Événement supprimé.')
        return redirect('core:events')
    today = timezone.localdate()
    upcoming = SchoolEvent.objects.filter(Q(start_date__gte=today) | Q(end_date__gte=today)).order_by('start_date')
    past = SchoolEvent.objects.exclude(pk__in=upcoming.values('pk')).order_by('-start_date')[:20]
    return render(request, 'core/events.html', {'upcoming': upcoming, 'past': past})


@login_required
def notifications_poll(request):
    notifications = Notification.objects.filter(recipient=request.user)[:10]
    data = [
        {
            'id': notification.id,
            'title': notification.title,
            'content': notification.content,
            'target_url': notification.target_url,
            'created_at': notification.created_at.isoformat(),
        }
        for notification in notifications
    ]
    return JsonResponse({
        'count': Notification.objects.filter(recipient=request.user, is_read=False).count(),
        'notifications': data,
    })


@login_required
def notifications_mark_all_read(request):
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})
