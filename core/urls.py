from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('messages/', views.inbox_view, name='inbox'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/<int:pk>/reply/', views.message_reply, name='message_reply'),
    path('messages/<int:pk>/delete/', views.message_delete_for_me, name='message_delete_for_me'),
    path('messages/create/', views.message_create, name='message_create'),
    path('messages/history/', views.message_history, name='message_history'),
    path('messages/teacher/compose/', views.teacher_message_compose, name='teacher_message_compose'),
    path('messages/parent/to-teacher/', views.parent_message_to_teacher, name='parent_message_to_teacher'),
    path('suggestions/', views.suggestions_view, name='suggestions'),
    path('appointments/new/', views.appointment_request_create, name='appointment_request_create'),
    path('appointments/admin/', views.appointment_admin_view, name='appointment_admin'),
    path('messages/<int:pk>/admin-delete/', views.message_admin_delete, name='message_admin_delete'),
    path('news/create/', views.news_create, name='news_create'),
    path('news/<int:pk>/delete/', views.news_delete, name='news_delete'),
    path('events/', views.events_view, name='events'),
    path('notifications/poll/', views.notifications_poll, name='notifications_poll'),
    path('notifications/mark-read/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
]


