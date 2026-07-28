from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("my-group/", views.my_group, name="my_group"),
    path("grades/", views.my_grades, name="my_grades"),
    path("resultats/", views.results_admin, name="results_admin"),
    path("absences/", views.my_absences, name="my_absences"),
    path("schedule/", views.schedule_view, name="schedule"),
    path("schedule/download/", views.schedule_download, name="schedule_download"),
    path("schedule/upload/", views.schedule_upload, name="schedule_upload"),
    path("schedule/manage/", views.schedule_manage, name="schedule_manage"),
    path("schedule/export/", views.schedule_export, name="schedule_export"),
    path("classrooms/", views.classroom_list, name="classroom_list"),
    path("classrooms/create/", views.classroom_create, name="classroom_create"),
    path("classrooms/<int:pk>/edit/", views.classroom_update, name="classroom_update"),
    path("classrooms/<int:pk>/delete/", views.classroom_delete, name="classroom_delete"),
    path("classrooms/<int:pk>/", views.classroom_detail, name="classroom_detail"),
    path("classrooms/<int:classroom_pk>/grades/", views.grades_admin, name="grades_admin"),
    path("classrooms/<int:classroom_pk>/absences/", views.absence_admin, name="absence_admin"),
    path("mes-classes/", views.teacher_classrooms, name="teacher_classrooms"),
    path("mes-classes/<int:classroom_pk>/notes/", views.teacher_classroom_notes, name="teacher_classroom_notes"),
    path("mes-classes/<int:classroom_pk>/cahier/", views.teacher_lessons, name="teacher_lessons"),
    path("cahier-de-textes/", views.my_lessons, name="my_lessons"),
    path("notes/<int:pk>/delete/", views.student_note_delete, name="student_note_delete"),
    path("mes-notes/", views.my_notes, name="my_notes"),
    path("eleves/<int:pk>/parcours/", views.student_history, name="student_history"),
    path("bulletin/<int:pk>/", views.bulletin_pdf, name="bulletin_pdf"),
    path("rentree/", views.year_transition, name="year_transition"),
    path("suivi/", views.notes_admin, name="notes_admin"),
    path("suivi/<int:classroom_pk>/", views.notes_admin_detail, name="notes_admin_detail"),
]
