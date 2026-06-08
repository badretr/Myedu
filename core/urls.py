from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('messages/', views.inbox_view, name='inbox'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/create/', views.message_create, name='message_create'),
    path('suggestions/', views.suggestions_view, name='suggestions'),
    path('news/create/', views.news_create, name='news_create'),
    path('news/<int:pk>/delete/', views.news_delete, name='news_delete'),
]
