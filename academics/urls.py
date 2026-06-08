from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("my-group/", views.my_group, name="my_group"),
    path("grades/", views.my_grades, name="my_grades"),
    path("absences/", views.my_absences, name="my_absences"),
    path("schedule/", views.schedule_view, name="schedule"),
    path("schedule/upload/", views.schedule_upload, name="schedule_upload"),
    path("classrooms/", views.classroom_list, name="classroom_list"),
    path("classrooms/create/", views.classroom_create, name="classroom_create"),
    path("classrooms/<int:pk>/edit/", views.classroom_update, name="classroom_update"),
    path("classrooms/<int:pk>/delete/", views.classroom_delete, name="classroom_delete"),
    path("classrooms/<int:pk>/", views.classroom_detail, name="classroom_detail"),
    path("classrooms/<int:classroom_pk>/grades/", views.grades_admin, name="grades_admin"),
]
