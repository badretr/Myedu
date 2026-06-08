from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import News, Message, Suggestion
from academics.models import Classroom, StudentEnrollment


def home_view(request):
    news = News.objects.filter(is_public=True)
    if request.user.is_authenticated:
        user_messages = get_user_messages(request.user)
        unread_count = sum(1 for m in user_messages if not m.is_read_by(request.user))
        return render(request, 'core/home.html', {
            'news': news,
            'unread_count': unread_count,
        })
    return render(request, 'core/home_public.html', {'news': news})


def get_user_messages(user):
    if user.is_admin_user or user.is_teacher:
        return Message.objects.all()
    try:
        enrollment = StudentEnrollment.objects.get(student=user, is_active=True)
        return Message.objects.filter(
            classroom__isnull=True
        ) | Message.objects.filter(classroom=enrollment.classroom)
    except StudentEnrollment.DoesNotExist:
        return Message.objects.filter(classroom__isnull=True)


@login_required
def inbox_view(request):
    user_messages = get_user_messages(request.user)
    messages_with_status = [
        {'msg': m, 'is_read': m.is_read_by(request.user)}
        for m in user_messages
    ]
    return render(request, 'core/inbox.html', {'messages_list': messages_with_status})


@login_required
def message_detail(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.read_by.add(request.user)
    return render(request, 'core/message_detail.html', {'msg': msg})


@login_required
def message_create(request):
    if not request.user.is_admin_user and not request.user.is_teacher:
        return redirect('core:inbox')
    classrooms = Classroom.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        classroom_id = request.POST.get('classroom') or None
        attachment = request.FILES.get('attachment')
        classroom = Classroom.objects.get(pk=classroom_id) if classroom_id else None
        Message.objects.create(
            title=title, content=content,
            sender=request.user, classroom=classroom, attachment=attachment
        )
        messages.success(request, 'Message envoyé.')
        return redirect('core:inbox')
    return render(request, 'core/message_form.html', {'classrooms': classrooms})


@login_required
def suggestions_view(request):
    from academics.models import Classroom
    last_24h = timezone.now() - timedelta(hours=24)
    can_suggest = not Suggestion.objects.filter(
        sender=request.user, created_at__gte=last_24h
    ).exists()
    if request.method == 'POST' and can_suggest:
        Suggestion.objects.create(
            category=request.POST.get('category'),
            subcategory=request.POST.get('subcategory', ''),
            content=request.POST.get('content'),
            sender=request.user,
            is_anonymous='is_anonymous' in request.POST
        )
        messages.success(request, 'Suggestion envoyée.')
        return redirect('core:suggestions')
    return render(request, 'core/suggestions.html', {'can_suggest': can_suggest})


@login_required
def news_create(request):
    if not request.user.is_admin_user:
        return redirect('core:home')
    if request.method == 'POST':
        News.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            created_by=request.user,
            is_public='is_public' in request.POST
        )
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
        messages.success(request, 'Actualité supprimée.')
    return redirect('core:home')
