from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("", views.documents_view, name="documents"),
    path("admin/", views.admin_requests, name="admin_requests"),
]
