from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path("balance/", views.my_balance, name="my_balance"),
    path("tranches/<int:enrollment_pk>/", views.manage_tranches, name="manage_tranches"),
    path("recu/<int:tranche_pk>/", views.receipt_pdf, name="receipt_pdf"),
    path("services/", views.services_admin, name="services_admin"),
]
