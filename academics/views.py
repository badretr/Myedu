from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import (Classroom, StudentEnrollment, Subject, Grade, Absence,
                     Schedule, Semester, AcademicYear)
from accounts.models import CustomUser


@login_required
def my_group(request):
    enrollment = request.user.linked_enrollment
    if enrollment and not enrollment.is_active:
        enrollment = None
    return render(request, "academics/my_group.html", {"enrollment": enrollment})


@login_required
def my_grades(request):
    enrollment = request.user.linked_enrollment
    grades_s1 = []
    grades_s2 = []
    if enrollment and enrollment.is_active:
        semesters_s1 = Semester.objects.filter(classroom=enrollment.classroom, label="S1")
        semesters_s2 = Semester.objects.filter(classroom=enrollment.classroom, label="S2")
        if semesters_s1.exists():
            grades_s1 = Grade.objects.filter(
                student=enrollment, semester__in=semesters_s1
            ).select_related("subject", "semester")
        if semesters_s2.exists():
            grades_s2 = Grade.objects.filter(
                student=enrollment, semester__in=semesters_s2
            ).select_related("subject", "semester")
    return render(request, "academics/grades.html", {
        "enrollment": enrollment,
        "grades_s1": grades_s1,
        "grades_s2": grades_s2,
    })


@login_required
def my_absences(request):
    enrollment = request.user.linked_enrollment
    absences_s1 = {}
    absences_s2 = {}
    semester_s1 = None
    semester_s2 = None
    if enrollment and enrollment.is_active:
        subjects = Subject.objects.filter(classroom=enrollment.classroom)
        semesters_s1 = Semester.objects.filter(classroom=enrollment.classroom, label="S1")
        semesters_s2 = Semester.objects.filter(classroom=enrollment.classroom, label="S2")
        semester_s1 = semesters_s1.first()
        semester_s2 = semesters_s2.first()
        for subj in subjects:
            abs_list = Absence.objects.filter(student=enrollment, subject=subj)
            total_hours = abs_list.aggregate(total=Sum("hours"))["total"] or 0
            max_hours = subj.total_hours
            rate = round((total_hours / max_hours * 100), 2) if max_hours else 0
            entry = {
                "subject": subj,
                "total_hours": total_hours,
                "rate": rate,
                "absences": abs_list,
                "danger": rate >= 10,
            }
            absences_s1[subj.name] = entry
            absences_s2[subj.name] = entry
    return render(request, "academics/absences.html", {
        "enrollment": enrollment,
        "absences_s1": absences_s1,
        "absences_s2": absences_s2,
        "semester_s1": semester_s1,
        "semester_s2": semester_s2,
    })


@login_required
def schedule_view(request):
    enrollment = request.user.linked_enrollment
    schedule = None
    if enrollment and enrollment.is_active:
        schedule = Schedule.objects.filter(classroom=enrollment.classroom).first()
    return render(request, "academics/schedule.html", {
        "enrollment": enrollment,
        "schedule": schedule,
    })


@login_required
def schedule_upload(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classrooms = Classroom.objects.all()
    schedules = Schedule.objects.select_related("classroom").order_by("-uploaded_at")
    if request.method == "POST":
        classroom_id = request.POST.get("classroom")
        image = request.FILES.get("image")
        version_date = request.POST.get("version_date") or None
        if classroom_id and image:
            classroom = get_object_or_404(Classroom, pk=classroom_id)
            # Replace existing schedule for this classroom
            Schedule.objects.filter(classroom=classroom).delete()
            Schedule.objects.create(classroom=classroom, image=image, version_date=version_date)
            messages.success(request, "Emploi du temps publié avec succès.")
            return redirect("academics:schedule_upload")
    return render(request, "academics/schedule_upload.html", {
        "classrooms": classrooms,
        "schedules": schedules,
    })


@login_required
def classroom_list(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classrooms = Classroom.objects.all()
    return render(request, "academics/classroom_list.html", {"classrooms": classrooms})


@login_required
def classroom_detail(request, pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=pk)
    enrollments = StudentEnrollment.objects.filter(classroom=classroom)
    students_not_enrolled = CustomUser.objects.filter(
        role="student"
    ).exclude(enrollment__classroom=classroom)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_student":
            student_id = request.POST.get("student_id")
            student = get_object_or_404(CustomUser, pk=student_id)
            matricule = request.POST.get("matricule", "MAT" + str(student.pk).zfill(4))
            subgroup = request.POST.get("subgroup", "")
            enrollment, created = StudentEnrollment.objects.get_or_create(
                student=student,
                defaults={"classroom": classroom, "matricule": matricule, "subgroup": subgroup}
            )
            if not created:
                enrollment.classroom = classroom
                enrollment.save()
            messages.success(request, student.get_full_name() + " ajouté à la classe.")
        elif action == "remove_student":
            enrollment_id = request.POST.get("enrollment_id")
            StudentEnrollment.objects.filter(pk=enrollment_id).delete()
            messages.success(request, "Etudiant retiré de la classe.")
        return redirect("academics:classroom_detail", pk=pk)
    return render(request, "academics/classroom_detail.html", {
        "classroom": classroom,
        "enrollments": enrollments,
        "students_not_enrolled": students_not_enrolled,
    })


@login_required
def classroom_create(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    academic_years = AcademicYear.objects.all()
    if request.method == "POST":
        year_id = request.POST.get("academic_year")
        year = AcademicYear.objects.get(pk=year_id) if year_id else None
        Classroom.objects.create(
            name=request.POST.get("name"),
            specialty=request.POST.get("specialty", ""),
            cycle=request.POST.get("cycle", ""),
            group=request.POST.get("group", ""),
            academic_year=year,
        )
        messages.success(request, "Classe créée.")
        return redirect("academics:classroom_list")
    return render(request, "academics/classroom_form.html", {"academic_years": academic_years})


@login_required
def classroom_update(request, pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=pk)
    academic_years = AcademicYear.objects.all()
    if request.method == "POST":
        year_id = request.POST.get("academic_year")
        year = AcademicYear.objects.get(pk=year_id) if year_id else None
        classroom.name = request.POST.get("name")
        classroom.specialty = request.POST.get("specialty", "")
        classroom.cycle = request.POST.get("cycle", "")
        classroom.group = request.POST.get("group", "")
        classroom.academic_year = year
        classroom.save()
        messages.success(request, "Classe modifiée.")
        return redirect("academics:classroom_list")
    return render(request, "academics/classroom_form.html", {
        "academic_years": academic_years,
        "classroom": classroom,
    })


@login_required
def classroom_delete(request, pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == "POST":
        classroom.delete()
        messages.success(request, "Classe supprimée.")
        return redirect("academics:classroom_list")
    return render(request, "academics/classroom_confirm_delete.html", {"obj": classroom})


@login_required
def grades_admin(request, classroom_pk):
    if not request.user.is_admin_user and not request.user.is_teacher:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=classroom_pk)
    enrollments = StudentEnrollment.objects.filter(classroom=classroom)
    subjects = Subject.objects.filter(classroom=classroom)
    semesters = Semester.objects.filter(classroom=classroom)
    selected_subject = request.GET.get("subject")
    selected_semester = request.GET.get("semester")
    grades = []
    if selected_subject and selected_semester:
        subj = get_object_or_404(Subject, pk=selected_subject)
        sem = get_object_or_404(Semester, pk=selected_semester)
        for enr in enrollments:
            grade, _ = Grade.objects.get_or_create(student=enr, subject=subj, semester=sem)
            grades.append(grade)
    if request.method == "POST" and selected_subject and selected_semester:
        subj = get_object_or_404(Subject, pk=selected_subject)
        sem = get_object_or_404(Semester, pk=selected_semester)
        for enr in enrollments:
            grade, _ = Grade.objects.get_or_create(student=enr, subject=subj, semester=sem)
            grade.cc = request.POST.get("cc_" + str(enr.pk)) or None
            grade.ds = request.POST.get("ds_" + str(enr.pk)) or None
            grade.exam = request.POST.get("exam_" + str(enr.pk)) or None
            grade.controle = request.POST.get("controle_" + str(enr.pk)) or None
            grade.save()
        messages.success(request, "Notes enregistrées.")
        return redirect(request.path + "?subject=" + selected_subject + "&semester=" + selected_semester)
    return render(request, "academics/grades_admin.html", {
        "classroom": classroom, "subjects": subjects, "semesters": semesters,
        "grades": grades, "selected_subject": selected_subject, "selected_semester": selected_semester,
    })
