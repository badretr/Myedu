from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import (Classroom, StudentEnrollment, Subject, Grade, Absence,
                     Schedule, Semester, AcademicYear, StudentNote, EnrollmentHistory,
                     ScheduleEntry, LessonEntry, CourseResource)
from accounts.models import CustomUser


SEMESTER_LABELS = ['S1', 'S2', 'S3']


def default_semester_range(start_year, index, total):
    if total == 2:
        ranges = [
            (date(start_year, 9, 15), date(start_year + 1, 1, 31)),
            (date(start_year + 1, 2, 1), date(start_year + 1, 6, 30)),
        ]
    else:
        ranges = [
            (date(start_year, 9, 15), date(start_year, 12, 20)),
            (date(start_year + 1, 1, 5), date(start_year + 1, 3, 31)),
            (date(start_year + 1, 4, 1), date(start_year + 1, 6, 30)),
        ]
    return ranges[index]


def create_semesters_for_classroom(classroom, total, academic_year):
    if academic_year and '-' in academic_year.label:
        start_year = int(academic_year.label.split('-')[0])
    else:
        start_year = timezone.now().year
    existing_labels = set(Semester.objects.filter(classroom=classroom).values_list('label', flat=True))
    to_create = []
    for index in range(total):
        label = SEMESTER_LABELS[index]
        if label in existing_labels:
            continue
        start, end = default_semester_range(start_year, index, total)
        to_create.append(Semester(classroom=classroom, label=label, start_date=start, end_date=end))
    if to_create:
        Semester.objects.bulk_create(to_create)


PRIMARY_BASE_SUBJECTS = [
    {"name": "Langue arabe", "coefficient": 4, "hours_ci": 8},
    {"name": "Mathématiques", "coefficient": 4, "hours_ci": 5},
    {"name": "Éveil scientifique", "coefficient": 2, "hours_ci": 2},
    {"name": "Éducation technologique", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation islamique", "coefficient": 2, "hours_ci": 2},
    {"name": "Éducation musicale", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation artistique", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation physique", "coefficient": 1, "hours_ci": 2},
]
PRIMARY_MID_SUBJECTS = [
    {"name": "Langue arabe", "coefficient": 4, "hours_ci": 7},
    {"name": "Français", "coefficient": 3, "hours_ci": 5},
    {"name": "Mathématiques", "coefficient": 4, "hours_ci": 5},
    {"name": "Sciences", "coefficient": 2, "hours_ci": 2},
    {"name": "Éducation technologique", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation islamique", "coefficient": 2, "hours_ci": 2},
    {"name": "Éducation musicale", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation artistique", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation physique", "coefficient": 1, "hours_ci": 2},
]
PRIMARY_UPPER_SUBJECTS = [
    {"name": "Langue arabe", "coefficient": 4, "hours_ci": 6},
    {"name": "Français", "coefficient": 3, "hours_ci": 5},
    {"name": "Mathématiques", "coefficient": 4, "hours_ci": 5},
    {"name": "Sciences", "coefficient": 2, "hours_ci": 2},
    {"name": "Histoire", "coefficient": 1, "hours_ci": 1},
    {"name": "Géographie", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation civique", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation technologique", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation islamique", "coefficient": 2, "hours_ci": 2},
    {"name": "Éducation musicale", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation artistique", "coefficient": 1, "hours_ci": 1},
    {"name": "Éducation physique", "coefficient": 1, "hours_ci": 2},
]
LEVEL_SUBJECTS = {
    "1ère Année Primaire": PRIMARY_BASE_SUBJECTS,
    "2ème Année Primaire": PRIMARY_BASE_SUBJECTS,
    "3ème Année Primaire": PRIMARY_MID_SUBJECTS,
    "4ème Année Primaire": PRIMARY_MID_SUBJECTS,
    "5ème Année Primaire": PRIMARY_UPPER_SUBJECTS,
    "6ème Année Primaire": PRIMARY_UPPER_SUBJECTS,
}
PRIMARY_SUBJECT_WEEKS = 30


def academic_year_choices():
    years = list(AcademicYear.objects.all().order_by("-label"))
    current_year = timezone.now().year
    current_month = timezone.now().month
    start_year = current_year if current_month >= 7 else current_year - 1
    current_label = f"{start_year}-{start_year + 1}"
    current_year_obj = AcademicYear.objects.filter(label=current_label).first()
    if current_year_obj is None:
        current_year_obj = AcademicYear.objects.create(label=current_label, is_current=True)
    elif not current_year_obj.is_current:
        current_year_obj.is_current = True
        current_year_obj.save(update_fields=["is_current"])
    if current_year_obj not in years:
        years.insert(0, current_year_obj)
    return years


@login_required
def my_group(request):
    enrollment = request.user.linked_enrollment
    if enrollment and not enrollment.is_active:
        enrollment = None
    return render(request, "academics/my_group.html", {"enrollment": enrollment})


@login_required
def my_absences(request):
    if request.user.is_admin_user:
        classrooms = Classroom.objects.all().order_by("name")
        return render(request, "academics/absences.html", {
            "admin_mode": True,
            "classrooms": classrooms,
        })
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
def my_grades(request):
    if request.user.is_admin_user:
        return redirect("academics:results_admin")
    if request.user.is_teacher:
        return redirect("academics:teacher_classrooms")
    enrollment = request.user.linked_enrollment
    grades_s1 = []
    grades_s2 = []
    semester_s1 = None
    semester_s2 = None
    if enrollment and enrollment.is_active:
        semester_s1 = Semester.objects.filter(classroom=enrollment.classroom, label="S1").first()
        semester_s2 = Semester.objects.filter(classroom=enrollment.classroom, label="S2").first()
        if semester_s1:
            grades_s1 = Grade.objects.filter(
                student=enrollment, semester=semester_s1
            ).select_related("subject", "semester")
        if semester_s2:
            grades_s2 = Grade.objects.filter(
                student=enrollment, semester=semester_s2
            ).select_related("subject", "semester")
    return render(request, "academics/grades.html", {
        "enrollment": enrollment,
        "grades_s1": grades_s1,
        "grades_s2": grades_s2,
        "semester_s1": semester_s1,
        "semester_s2": semester_s2,
        "general_average_s1": _weighted_average(grades_s1),
        "general_average_s2": _weighted_average(grades_s2),
    })


def _weighted_average(grades):
    total_points = 0
    total_coef = 0
    for g in grades:
        if g.average is not None:
            total_points += g.average * g.subject.coefficient
            total_coef += g.subject.coefficient
    return round(total_points / total_coef, 2) if total_coef else None


@login_required
def results_admin(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classrooms = Classroom.objects.all().order_by("name")
    selected_classroom = request.POST.get("classroom") or request.GET.get("classroom")
    selected_enrollment = request.POST.get("student") or request.GET.get("student")
    selected_semester = request.POST.get("semester") or request.GET.get("semester")

    enrollments = StudentEnrollment.objects.none()
    subjects = Subject.objects.none()
    semesters = Semester.objects.none()
    enrollment = None
    grades_by_subject = {}
    student_averages = []
    default_semester = None

    if selected_classroom:
        classroom = get_object_or_404(Classroom, pk=selected_classroom)
        enrollments = StudentEnrollment.objects.filter(classroom=classroom).select_related("student")
        subjects = Subject.objects.filter(classroom=classroom).order_by("name")
        semesters = Semester.objects.filter(classroom=classroom).order_by("label")
        default_semester = semesters.first()

        if not selected_enrollment:
            for enr in enrollments:
                grades = Grade.objects.filter(student=enr).select_related("subject")
                student_averages.append({
                    "enrollment": enr,
                    "average": _weighted_average(grades),
                })
            # Classement par moyenne décroissante
            student_averages.sort(key=lambda r: (r["average"] is None, -(r["average"] or 0)))
            rank = 0
            for row in student_averages:
                rank += 1 if row["average"] is not None else 0
                row["rank"] = rank if row["average"] is not None else None

        if selected_enrollment:
            enrollment = get_object_or_404(StudentEnrollment, pk=selected_enrollment, classroom=classroom)

            if request.method == "POST":
                sem = get_object_or_404(Semester, pk=request.POST.get("semester"), classroom=classroom)
                any_changed = False
                for subj in subjects:
                    grade, _ = Grade.objects.get_or_create(student=enrollment, subject=subj, semester=sem)
                    old_values = (grade.cc, grade.ds, grade.exam)
                    grade.cc = request.POST.get(f"cc_{subj.pk}") or None
                    grade.ds = request.POST.get(f"ds_{subj.pk}") or None
                    grade.exam = request.POST.get(f"exam_{subj.pk}") or None
                    grade.save()
                    if (grade.cc, grade.ds, grade.exam) != old_values:
                        any_changed = True
                if any_changed and enrollment.student.parent_account_id:
                    from core.views import notify_user
                    notify_user(
                        enrollment.student.parent_account,
                        "Nouvelles notes disponibles",
                        f"{enrollment.student.get_full_name()} — notes du {sem.get_label_display()} mises à jour.",
                        "/academics/grades/",
                    )
                messages.success(request, "Notes enregistrées.")
                return redirect(
                    f"{request.path}?classroom={classroom.pk}&student={enrollment.pk}&semester={sem.pk}"
                )

            if selected_semester:
                sem = get_object_or_404(Semester, pk=selected_semester, classroom=classroom)
                for subj in subjects:
                    grade, _ = Grade.objects.get_or_create(student=enrollment, subject=subj, semester=sem)
                    grades_by_subject[subj.pk] = grade

    general_average = None
    if grades_by_subject:
        total_points = 0
        total_coef = 0
        for subj in subjects:
            grade = grades_by_subject.get(subj.pk)
            if grade and grade.average is not None:
                total_points += grade.average * subj.coefficient
                total_coef += subj.coefficient
        if total_coef:
            general_average = round(total_points / total_coef, 2)

    # Statistiques de classe par matière (vue liste)
    subject_stats = []
    class_stats = None
    if selected_classroom and not selected_enrollment:
        for subj in subjects:
            avgs = [g.average for g in Grade.objects.filter(subject=subj) if g.average is not None]
            if avgs:
                subject_stats.append({
                    "subject": subj,
                    "avg": round(sum(avgs) / len(avgs), 2),
                    "best": max(avgs),
                    "worst": min(avgs),
                })
        class_avgs = [r["average"] for r in student_averages if r["average"] is not None]
        if class_avgs:
            class_stats = {
                "avg": round(sum(class_avgs) / len(class_avgs), 2),
                "best": max(class_avgs),
                "worst": min(class_avgs),
                "graded": len(class_avgs),
                "count": len(student_averages),
            }

    # Rang de l'élève pour le semestre affiché (vue fiche)
    student_rank = None
    class_size = None
    sem_class_avg = None
    if enrollment and selected_semester:
        sem = Semester.objects.filter(pk=selected_semester).first()
        if sem:
            sem_averages = []
            my_avg = None
            for enr in enrollments:
                avg = _weighted_average(
                    Grade.objects.filter(student=enr, semester=sem).select_related("subject")
                )
                if avg is not None:
                    sem_averages.append(avg)
                if enr.pk == enrollment.pk:
                    my_avg = avg
            class_size = enrollments.count()
            if sem_averages:
                sem_class_avg = round(sum(sem_averages) / len(sem_averages), 2)
            if my_avg is not None:
                student_rank = sorted(sem_averages, reverse=True).index(my_avg) + 1

    return render(request, "academics/results_admin.html", {
        "subject_stats": subject_stats,
        "class_stats": class_stats,
        "student_rank": student_rank,
        "class_size": class_size,
        "sem_class_avg": sem_class_avg,
        "classrooms": classrooms,
        "enrollments": enrollments,
        "subjects": subjects,
        "general_average": general_average,
        "semesters": semesters,
        "enrollment": enrollment,
        "selected_classroom": selected_classroom,
        "selected_enrollment": selected_enrollment,
        "selected_semester": selected_semester,
        "grades_by_subject": grades_by_subject,
        "student_averages": student_averages,
        "default_semester": default_semester,
    })


def build_schedule_grid(classroom):
    """Grille [heure][jour] -> ScheduleEntry ou None, pour l'affichage."""
    entries = ScheduleEntry.objects.filter(classroom=classroom).select_related(
        "subject__teacher", "subject__teacher_tp"
    )
    by_slot = {(e.day, e.start_hour): e for e in entries}
    grid = []
    for hour in ScheduleEntry.teaching_hours():
        if hour == ScheduleEntry.BREAK_END:
            grid.append({"is_break": True})
        row = {"hour": hour, "cells": [by_slot.get((day, hour)) for day, _ in ScheduleEntry.DAY_CHOICES]}
        grid.append(row)
    return grid, entries.exists()


def build_teacher_schedule_grid(teacher):
    """Grille [heure][jour] -> ScheduleEntry ou None, agrégée sur toutes les classes de l'enseignant.

    Généré à partir des emplois du temps des classes : un créneau appartient à
    l'enseignant s'il en est le professeur de cours, ou le professeur de TP
    (avec repli sur le professeur de cours si aucun professeur de TP n'est défini).
    """
    entries = ScheduleEntry.objects.filter(
        Q(session_type='cours', subject__teacher=teacher)
        | Q(session_type='tp', subject__teacher_tp=teacher)
        | Q(session_type='tp', subject__teacher_tp__isnull=True, subject__teacher=teacher)
    ).select_related("subject", "classroom", "subject__teacher", "subject__teacher_tp")
    by_slot = {(e.day, e.start_hour): e for e in entries}
    grid = []
    for hour in ScheduleEntry.teaching_hours():
        if hour == ScheduleEntry.BREAK_END:
            grid.append({"is_break": True})
        row = {"hour": hour, "cells": [by_slot.get((day, hour)) for day, _ in ScheduleEntry.DAY_CHOICES]}
        grid.append(row)
    return grid, entries.exists()


def _appreciation(avg):
    if avg is None:
        return "—"
    if avg >= 16:
        return "Excellent"
    if avg >= 14:
        return "Très bien"
    if avg >= 12:
        return "Bien"
    if avg >= 10:
        return "Assez bien"
    if avg >= 8:
        return "Passable"
    return "Insuffisant"


@login_required
def bulletin_pdf(request, pk):
    enrollment = get_object_or_404(
        StudentEnrollment.objects.select_related("student", "classroom__academic_year"), pk=pk
    )
    student = enrollment.student
    is_own = request.user.pk == student.pk
    is_parent_of = student.parent_account_id == request.user.pk
    if not (request.user.is_admin_user or is_own or is_parent_of):
        return redirect("core:home")

    semester = Semester.objects.filter(
        pk=request.GET.get("semester"), classroom=enrollment.classroom
    ).first() or Semester.objects.filter(classroom=enrollment.classroom).first()
    if semester is None:
        raise Http404()

    subjects = Subject.objects.filter(classroom=enrollment.classroom).order_by("name")
    grades = {
        g.subject_id: g
        for g in Grade.objects.filter(student=enrollment, semester=semester)
    }
    general_average = _weighted_average([g for g in grades.values()])

    # Rang et moyenne de classe pour ce semestre
    classmates = StudentEnrollment.objects.filter(classroom=enrollment.classroom)
    sem_averages = []
    for enr in classmates:
        avg = _weighted_average(Grade.objects.filter(student=enr, semester=semester).select_related("subject"))
        if avg is not None:
            sem_averages.append(avg)
    class_avg = round(sum(sem_averages) / len(sem_averages), 2) if sem_averages else None
    rank = (sorted(sem_averages, reverse=True).index(general_average) + 1) if general_average is not None else None

    from io import BytesIO
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle)

    indigo = colors.HexColor("#4f46e5")
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.2 * cm, bottomMargin=1.2 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Title"], textColor=indigo, fontSize=18, spaceAfter=2)
    sub_style = ParagraphStyle("s", parent=styles["Normal"], alignment=1, textColor=colors.grey, spaceAfter=10)
    label_style = ParagraphStyle("l", parent=styles["Normal"], fontSize=10)

    year = enrollment.classroom.academic_year.label if enrollment.classroom and enrollment.classroom.academic_year else ""
    story = [
        Paragraph("Myedu — École", title_style),
        Paragraph(f"Bulletin scolaire — {semester.get_label_display()} — Année scolaire {year}", sub_style),
    ]

    info = Table([
        [Paragraph(f"<b>Élève :</b> {student.get_full_name()}", label_style),
         Paragraph(f"<b>Matricule :</b> {enrollment.matricule}", label_style)],
        [Paragraph(f"<b>Classe :</b> {enrollment.classroom}", label_style),
         Paragraph(f"<b>Né(e) le :</b> {student.date_of_birth.strftime('%d/%m/%Y') if student.date_of_birth else '—'}", label_style)],
    ], colWidths=[9 * cm, 9 * cm])
    info.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, indigo),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [info, Spacer(1, 14)]

    data = [["Matière", "Coef", "Orale", "Examen\nd'évaluation", "Examen\nfinal", "Moyenne", "Appréciation"]]
    for subj in subjects:
        g = grades.get(subj.pk)
        avg = g.average if g else None
        fmt = lambda v: ("%g" % v) if v is not None else "—"
        data.append([
            subj.name, "%g" % subj.coefficient,
            fmt(g.cc if g else None), fmt(g.ds if g else None), fmt(g.exam if g else None),
            fmt(avg), _appreciation(avg),
        ])
    table = Table(data, colWidths=[4.8 * cm, 1.2 * cm, 1.3 * cm, 2.4 * cm, 1.8 * cm, 1.8 * cm, 4.5 * cm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), indigo),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]
    table.setStyle(TableStyle(style))
    story += [table, Spacer(1, 14)]

    recap = Table([
        ["Moyenne générale", "Rang", "Moyenne de classe", "Appréciation générale"],
        [
            ("%g / 20" % general_average) if general_average is not None else "—",
            f"{rank} / {classmates.count()}" if rank else "—",
            ("%g" % class_avg) if class_avg is not None else "—",
            _appreciation(general_average),
        ],
    ], colWidths=[4.5 * cm, 4.5 * cm, 4.5 * cm, 4.5 * cm])
    recap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 1), (0, 1), indigo),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, indigo),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [recap, Spacer(1, 30)]

    sign = Table([
        [Paragraph("<b>Signature des parents</b>", label_style),
         Paragraph("<b>La Direction</b>", label_style)],
        ["", ""],
    ], colWidths=[9 * cm, 9 * cm], rowHeights=[None, 2 * cm])
    sign.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(sign)

    doc.build(story)
    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    filename = f"bulletin_{student.get_full_name().replace(' ', '_')}_{semester.label}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def schedule_view(request):
    enrollment = request.user.linked_enrollment
    schedule = None
    grid = None
    if enrollment and enrollment.is_active and enrollment.classroom:
        grid, has_entries = build_schedule_grid(enrollment.classroom)
        if not has_entries:
            grid = None
            schedule = Schedule.objects.filter(classroom=enrollment.classroom).first()
    return render(request, "academics/schedule.html", {
        "enrollment": enrollment,
        "schedule": schedule,
        "grid": grid,
        "days": ScheduleEntry.DAY_CHOICES,
    })


@login_required
def teacher_schedule(request):
    """Emploi du temps personnel de l'enseignant, généré à partir des emplois du temps des classes."""
    if not request.user.is_teacher:
        return redirect("core:home")
    grid, has_entries = build_teacher_schedule_grid(request.user)
    return render(request, "academics/teacher_schedule.html", {
        "grid": grid if has_entries else None,
        "days": ScheduleEntry.DAY_CHOICES,
    })


@login_required
def schedule_export(request):
    """Exporte l'emploi du temps d'une classe en image PNG."""
    classroom = None
    if request.user.is_admin_user and request.GET.get("classroom"):
        classroom = get_object_or_404(Classroom, pk=request.GET.get("classroom"))
    else:
        enrollment = request.user.linked_enrollment
        if enrollment and enrollment.is_active:
            classroom = enrollment.classroom
    if classroom is None:
        raise Http404()
    grid, has_entries = build_schedule_grid(classroom)
    if not has_entries:
        raise Http404()

    from PIL import Image, ImageDraw, ImageFont
    from django.http import HttpResponse

    def load_font(size, bold=False):
        candidates = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    font_title = load_font(26, bold=True)
    font_header = load_font(18, bold=True)
    font_cell = load_font(16, bold=True)
    font_small = load_font(13)

    days = ScheduleEntry.DAY_CHOICES
    hour_w, col_w, title_h, header_h, row_h = 110, 190, 70, 46, 72
    width = hour_w + col_w * len(days)
    height = title_h + header_h + row_h * len(grid)

    indigo = (79, 70, 229)
    line = (203, 213, 225)
    gray_bg = (241, 245, 249)
    text_dark = (15, 23, 42)
    text_muted = (100, 116, 139)

    img = Image.new("RGB", (width + 1, height + 1), "white")
    draw = ImageDraw.Draw(img)

    def center_text(x0, y0, x1, y1, text, font, fill):
        box = draw.textbbox((0, 0), text, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        draw.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2 - box[1]), text, font=font, fill=fill)

    # Titre
    year = f" — {classroom.academic_year.label}" if classroom.academic_year else ""
    draw.rectangle([0, 0, width, title_h], fill=indigo)
    center_text(0, 0, width, title_h, f"Emploi du temps — {classroom}{year}", font_title, "white")

    # En-tête des jours
    y = title_h
    draw.rectangle([0, y, hour_w, y + header_h], fill=gray_bg, outline=line)
    center_text(0, y, hour_w, y + header_h, "Horaire", font_header, text_dark)
    for i, (_, label) in enumerate(days):
        x0 = hour_w + i * col_w
        draw.rectangle([x0, y, x0 + col_w, y + header_h], fill=gray_bg, outline=line)
        center_text(x0, y, x0 + col_w, y + header_h, label, font_header, text_dark)

    # Lignes
    y += header_h
    for row in grid:
        if row.get("is_break"):
            draw.rectangle([0, y, hour_w, y + row_h], fill=gray_bg, outline=line)
            center_text(0, y, hour_w, y + row_h, "12h - 14h", font_cell, text_muted)
            draw.rectangle([hour_w, y, width, y + row_h], fill=gray_bg, outline=line)
            center_text(hour_w, y, width, y + row_h, "Pause déjeuner", font_cell, text_muted)
        else:
            draw.rectangle([0, y, hour_w, y + row_h], fill="white", outline=line)
            center_text(0, y, hour_w, y + row_h, f"{row['hour']}h - {row['hour'] + 1}h", font_cell, text_dark)
            for i, entry in enumerate(row["cells"]):
                x0 = hour_w + i * col_w
                draw.rectangle([x0, y, x0 + col_w, y + row_h], fill="white", outline=line)
                if entry:
                    teacher = entry.teacher.get_full_name() if entry.teacher else ""
                    if teacher:
                        center_text(x0, y + 8, x0 + col_w, y + row_h - 28, entry.subject.name, font_cell, text_dark)
                        center_text(x0, y + row_h - 30, x0 + col_w, y + row_h - 6, teacher, font_small, text_muted)
                    else:
                        center_text(x0, y, x0 + col_w, y + row_h, entry.subject.name, font_cell, text_dark)
                else:
                    center_text(x0, y, x0 + col_w, y + row_h, "—", font_cell, text_muted)
        y += row_h

    response = HttpResponse(content_type="image/png")
    filename = f"emploi_du_temps_{classroom.name.replace(' ', '_')}.png"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    img.save(response, "PNG")
    return response


@login_required
def schedule_download(request):
    enrollment = request.user.linked_enrollment
    if not enrollment or not enrollment.is_active:
        raise Http404()
    schedule = Schedule.objects.filter(classroom=enrollment.classroom).first()
    if not schedule or not schedule.image:
        raise Http404()
    return FileResponse(open(schedule.image.path, 'rb'), as_attachment=True, filename=schedule.image.name.split('/')[-1])


@login_required
def schedule_manage(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classrooms = Classroom.objects.all().order_by("name")
    classroom_id = request.POST.get("classroom") or request.GET.get("classroom")
    classroom = Classroom.objects.filter(pk=classroom_id).first() if classroom_id else None
    subjects = Subject.objects.filter(classroom=classroom).order_by("name") if classroom else []

    hours = ScheduleEntry.teaching_hours()
    days = ScheduleEntry.DAY_CHOICES

    if request.method == "POST" and classroom and request.POST.get("action") == "save":
        for day, _label in days:
            for hour in hours:
                raw = request.POST.get(f"cell_{day}_{hour}", "")
                slot = ScheduleEntry.objects.filter(classroom=classroom, day=day, start_hour=hour)
                if not raw:
                    slot.delete()
                    continue
                subject_id, _, session_type = raw.partition("|")
                subject = Subject.objects.filter(pk=subject_id, classroom=classroom).first()
                if subject is None:
                    slot.delete()
                    continue
                ScheduleEntry.objects.update_or_create(
                    classroom=classroom, day=day, start_hour=hour,
                    defaults={"subject": subject, "session_type": session_type or "cours"},
                )
        messages.success(request, "Emploi du temps enregistré.")
        return redirect(f"{request.path}?classroom={classroom.pk}")

    grid = []
    if classroom:
        by_slot = {
            (e.day, e.start_hour): e
            for e in ScheduleEntry.objects.filter(classroom=classroom)
        }
        for hour in hours:
            if hour == ScheduleEntry.BREAK_END:
                grid.append({"is_break": True})
            row = {"hour": hour, "cells": []}
            for day, _label in days:
                entry = by_slot.get((day, hour))
                row["cells"].append({
                    "day": day,
                    "value": f"{entry.subject_id}|{entry.session_type}" if entry else "",
                })
            grid.append(row)

    return render(request, "academics/schedule_manage.html", {
        "classrooms": classrooms,
        "classroom": classroom,
        "subjects": subjects,
        "grid": grid,
        "days": days,
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
    subjects = Subject.objects.filter(classroom=classroom).select_related("teacher")
    teachers = CustomUser.objects.filter(role="teacher")
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
                if matricule:
                    enrollment.matricule = matricule
                if subgroup:
                    enrollment.subgroup = subgroup
                enrollment.save()
            EnrollmentHistory.record(enrollment)
            messages.success(request, student.get_full_name() + " ajouté à la classe.")
        elif action == "remove_student":
            enrollment_id = request.POST.get("enrollment_id")
            StudentEnrollment.objects.filter(pk=enrollment_id).delete()
            messages.success(request, "Etudiant retiré de la classe.")
        elif action == "add_subject":
            teacher_id = request.POST.get("teacher") or None
            Subject.objects.create(
                name=request.POST.get("name"),
                code=request.POST.get("code", ""),
                coefficient=request.POST.get("coefficient") or 1.0,
                classroom=classroom,
                teacher_id=teacher_id,
                hours_ci=request.POST.get("hours_ci") or 1.5,
                hours_tp=0,
                weeks=request.POST.get("weeks") or 14,
            )
            messages.success(request, "Matière ajoutée.")
        elif action == "remove_subject":
            subject_id = request.POST.get("subject_id")
            Subject.objects.filter(pk=subject_id, classroom=classroom).delete()
            messages.success(request, "Matière supprimée.")
        return redirect("academics:classroom_detail", pk=pk)
    return render(request, "academics/classroom_detail.html", {
        "classroom": classroom,
        "enrollments": enrollments,
        "students_not_enrolled": students_not_enrolled,
        "subjects": subjects,
        "teachers": teachers,
    })


@login_required
def classroom_create(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    academic_years = academic_year_choices()
    levels = list(LEVEL_SUBJECTS.keys())
    sections = [
        "Lettres",
        "Economie et gestion",
        "Technique",
        "Informatique",
        "Mathématiques",
        "Sciences expérimentales",
    ]
    if request.method == "POST":
        year_id = request.POST.get("academic_year")
        year = AcademicYear.objects.get(pk=year_id) if year_id else None
        level = request.POST.get("level", "")
        classroom = Classroom.objects.create(
            name=request.POST.get("name"),
            specialty=request.POST.get("specialty", ""),
            cycle=request.POST.get("cycle", ""),
            group=request.POST.get("group", ""),
            academic_year=year,
        )
        subject_specs = LEVEL_SUBJECTS.get(level)
        if subject_specs:
            Subject.objects.bulk_create([
                Subject(
                    name=spec["name"],
                    classroom=classroom,
                    coefficient=spec["coefficient"],
                    hours_ci=spec["hours_ci"],
                    hours_tp=0,
                    weeks=PRIMARY_SUBJECT_WEEKS,
                )
                for spec in subject_specs
            ])
        semester_count = int(request.POST.get("semester_count") or 2)
        create_semesters_for_classroom(classroom, semester_count, year)
        messages.success(request, "Classe créée.")
        return redirect("academics:classroom_detail", pk=classroom.pk)
    return render(request, "academics/classroom_form.html", {
        "academic_years": academic_years,
        "levels": levels,
        "sections": sections,
    })


@login_required
def classroom_update(request, pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=pk)
    academic_years = academic_year_choices()
    levels = list(LEVEL_SUBJECTS.keys())
    sections = [
        "Lettres",
        "Economie et gestion",
        "Technique",
        "Informatique",
        "Mathématiques",
        "Sciences expérimentales",
    ]
    if request.method == "POST":
        year_id = request.POST.get("academic_year")
        year = AcademicYear.objects.get(pk=year_id) if year_id else None
        classroom.name = request.POST.get("name")
        classroom.specialty = request.POST.get("specialty", "")
        classroom.cycle = request.POST.get("cycle", "")
        classroom.group = request.POST.get("group", "")
        classroom.academic_year = year
        classroom.save()
        semester_count = int(request.POST.get("semester_count") or 2)
        create_semesters_for_classroom(classroom, semester_count, year)
        messages.success(request, "Classe modifiée.")
        return redirect("academics:classroom_list")
    return render(request, "academics/classroom_form.html", {
        "academic_years": academic_years,
        "classroom": classroom,
        "levels": levels,
        "sections": sections,
        "current_semester_count": Semester.objects.filter(classroom=classroom).count() or 2,
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
def teacher_classrooms(request):
    if not request.user.is_teacher:
        return redirect("core:home")
    classroom_ids = Subject.objects.filter(
        Q(teacher=request.user) | Q(teacher_tp=request.user)
    ).values_list("classroom_id", flat=True).distinct()
    classrooms = Classroom.objects.filter(pk__in=classroom_ids)
    return render(request, "academics/teacher_classrooms.html", {"classrooms": classrooms})


@login_required
def teacher_classroom_notes(request, classroom_pk):
    if not request.user.is_teacher:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=classroom_pk)
    subjects = Subject.objects.filter(
        Q(teacher=request.user) | Q(teacher_tp=request.user), classroom=classroom
    )
    if not subjects.exists():
        return redirect("academics:teacher_classrooms")
    enrollments = StudentEnrollment.objects.filter(classroom=classroom, is_active=True).select_related("student")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_observation":
            note = StudentNote.objects.create(
                classroom=classroom,
                teacher=request.user,
                subject_id=request.POST.get("subject") or None,
                note_type=StudentNote.TYPE_OBSERVATION,
                content=request.POST.get("content"),
                date=request.POST.get("date") or timezone.localdate(),
            )
            from core.views import notify_user
            parent_ids = enrollments.exclude(student__parent_account__isnull=True).values_list("student__parent_account_id", flat=True)
            for parent_id in parent_ids:
                notify_user(
                    CustomUser.objects.get(pk=parent_id),
                    "Nouvelle observation de classe",
                    f"{classroom} - {note.content[:80]}",
                    "/academics/mes-notes/",
                )
            messages.success(request, "Observation ajoutée.")
        elif action == "add_punition":
            enrollment = get_object_or_404(StudentEnrollment, pk=request.POST.get("student"), classroom=classroom)
            note = StudentNote.objects.create(
                classroom=classroom,
                student=enrollment,
                teacher=request.user,
                note_type=StudentNote.TYPE_PUNITION,
                content=request.POST.get("content"),
                date=request.POST.get("date") or timezone.localdate(),
            )
            if enrollment.student.parent_account_id:
                from core.views import notify_user
                notify_user(
                    enrollment.student.parent_account,
                    "Nouvelle punition",
                    f"{enrollment.student.get_full_name()} - {note.content[:80]}",
                    "/academics/mes-notes/",
                )
            messages.success(request, "Punition ajoutée.")
        return redirect("academics:teacher_classroom_notes", classroom_pk=classroom_pk)
    observations = StudentNote.objects.filter(
        classroom=classroom, note_type=StudentNote.TYPE_OBSERVATION
    ).select_related("subject", "teacher")[:50]
    punitions = StudentNote.objects.filter(
        classroom=classroom, note_type=StudentNote.TYPE_PUNITION
    ).select_related("student__student", "teacher")[:50]
    return render(request, "academics/teacher_classroom_notes.html", {
        "classroom": classroom,
        "enrollments": enrollments,
        "subjects": subjects,
        "observations": observations,
        "punitions": punitions,
    })


@login_required
def student_note_delete(request, pk):
    note = get_object_or_404(StudentNote, pk=pk)
    if not (request.user.is_admin_user or (request.user.is_teacher and note.teacher_id == request.user.pk)):
        return redirect("core:home")
    classroom_pk = note.classroom_id
    if request.method == "POST":
        note.delete()
        messages.success(request, "Note supprimée.")
    if request.user.is_admin_user:
        return redirect("academics:notes_admin_detail", classroom_pk=classroom_pk)
    return redirect("academics:teacher_classroom_notes", classroom_pk=classroom_pk)


@login_required
def notes_admin(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classrooms = Classroom.objects.annotate(
        obs_count=Count("notes", filter=Q(notes__note_type=StudentNote.TYPE_OBSERVATION)),
        pun_count=Count("notes", filter=Q(notes__note_type=StudentNote.TYPE_PUNITION)),
    ).order_by("name")
    total_obs = StudentNote.objects.filter(note_type=StudentNote.TYPE_OBSERVATION).count()
    total_pun = StudentNote.objects.filter(note_type=StudentNote.TYPE_PUNITION).count()
    recent_notes = StudentNote.objects.select_related(
        "classroom", "student__student", "teacher", "subject"
    )[:10]
    return render(request, "academics/notes_admin.html", {
        "classrooms": classrooms,
        "total_obs": total_obs,
        "total_pun": total_pun,
        "recent_notes": recent_notes,
    })


@login_required
def notes_admin_detail(request, classroom_pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=classroom_pk)
    observations = StudentNote.objects.filter(
        classroom=classroom, note_type=StudentNote.TYPE_OBSERVATION
    ).select_related("subject", "teacher")
    punitions = StudentNote.objects.filter(
        classroom=classroom, note_type=StudentNote.TYPE_PUNITION
    ).select_related("student__student", "teacher", "subject")

    students_notes = {}
    for note in punitions:
        if note.student_id:
            students_notes.setdefault(note.student, []).append(note)
    students_grouped = sorted(
        students_notes.items(),
        key=lambda item: (item[0].student.last_name or "", item[0].student.first_name or ""),
    )
    return render(request, "academics/notes_admin_detail.html", {
        "classroom": classroom,
        "observations": observations,
        "students_grouped": students_grouped,
        "pun_count": punitions.count(),
    })


@login_required
def lessons_admin(request):
    """Vue d'ensemble du cahier de textes pour la direction : ce que les enseignants ont saisi, par classe."""
    if not request.user.is_admin_user:
        return redirect("core:home")
    classrooms = Classroom.objects.annotate(
        lesson_count=Count("lesson_entries"),
    ).order_by("name")
    total_entries = LessonEntry.objects.count()
    total_homework = LessonEntry.objects.exclude(homework="").count()
    recent_entries = LessonEntry.objects.select_related(
        "classroom", "subject", "teacher"
    ).order_by("-date", "-created_at")[:20]
    return render(request, "academics/lessons_admin.html", {
        "classrooms": classrooms,
        "total_entries": total_entries,
        "total_homework": total_homework,
        "recent_entries": recent_entries,
    })


@login_required
def my_notes(request):
    enrollment = request.user.linked_enrollment
    if enrollment:
        observations = StudentNote.objects.filter(
            classroom=enrollment.classroom, note_type=StudentNote.TYPE_OBSERVATION
        ).select_related("subject", "teacher")
        punitions = StudentNote.objects.filter(
            student=enrollment, note_type=StudentNote.TYPE_PUNITION
        ).select_related("teacher")
    else:
        observations = StudentNote.objects.none()
        punitions = StudentNote.objects.none()
    return render(request, "academics/my_notes.html", {
        "enrollment": enrollment, "observations": observations, "punitions": punitions,
    })


@login_required
def grades_admin(request, classroom_pk):
    if not request.user.is_admin_user and not request.user.is_teacher:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=classroom_pk)
    enrollments = StudentEnrollment.objects.filter(classroom=classroom)
    # Un enseignant ne saisit que les notes de SES matières dans cette classe
    if request.user.is_teacher and not request.user.is_admin_user:
        subjects = Subject.objects.filter(classroom=classroom, teacher=request.user)
        if not subjects.exists():
            messages.warning(request, "Aucune matière ne vous est affectée dans cette classe.")
            return redirect("academics:teacher_classrooms")
    else:
        subjects = Subject.objects.filter(classroom=classroom)
    semesters = Semester.objects.filter(classroom=classroom)
    selected_subject = request.POST.get("subject") or request.GET.get("subject")
    # Si l'enseignant n'a qu'une matière, elle est présélectionnée
    if not selected_subject and subjects.count() == 1:
        selected_subject = str(subjects.first().pk)
    selected_semester = request.POST.get("semester") or request.GET.get("semester")
    grades = []
    if selected_subject and selected_semester:
        subj = get_object_or_404(subjects, pk=selected_subject)
        sem = get_object_or_404(Semester, pk=selected_semester, classroom=classroom)
        for enr in enrollments:
            grade, _ = Grade.objects.get_or_create(student=enr, subject=subj, semester=sem)
            grades.append(grade)
    if request.method == "POST" and selected_subject and selected_semester:
        from core.views import notify_user
        subj = get_object_or_404(subjects, pk=selected_subject)
        sem = get_object_or_404(Semester, pk=selected_semester, classroom=classroom)
        for enr in enrollments:
            grade, _ = Grade.objects.get_or_create(student=enr, subject=subj, semester=sem)
            old_values = (grade.cc, grade.ds, grade.exam)
            grade.cc = request.POST.get("cc_" + str(enr.pk)) or None
            grade.ds = request.POST.get("ds_" + str(enr.pk)) or None
            grade.exam = request.POST.get("exam_" + str(enr.pk)) or None
            grade.save()
            changed = (grade.cc, grade.ds, grade.exam) != old_values
            has_value = any(v is not None for v in (grade.cc, grade.ds, grade.exam))
            if changed and has_value and enr.student.parent_account_id:
                notify_user(
                    enr.student.parent_account,
                    "Nouvelles notes disponibles",
                    f"{enr.student.get_full_name()} — notes de {subj.name} ({sem.get_label_display()}) mises à jour.",
                    "/academics/grades/",
                )
        messages.success(request, "Notes enregistrées.")
        return redirect(request.path + "?subject=" + selected_subject + "&semester=" + selected_semester)
    return render(request, "academics/grades_admin.html", {
        "classroom": classroom, "subjects": subjects, "semesters": semesters,
        "grades": grades, "selected_subject": selected_subject, "selected_semester": selected_semester,
    })


def hours_label(slots):
    """[8, 9, 14] -> '8h-10h, 14h-15h'"""
    if not slots:
        return ""
    slots = sorted(slots)
    ranges = []
    start = prev = slots[0]
    for h in slots[1:]:
        if h == prev + 1:
            prev = h
            continue
        ranges.append(f"{start}h-{prev + 1}h")
        start = prev = h
    ranges.append(f"{start}h-{prev + 1}h")
    return ", ".join(ranges)


def day_sessions(classroom, subjects, selected_date):
    """Séances du jour d'après l'emploi du temps ; sinon toutes les matières (mode libre)."""
    sessions = []
    day_index = date.fromisoformat(selected_date).weekday()
    if day_index < len(ScheduleEntry.DAY_CHOICES):
        entries = ScheduleEntry.objects.filter(
            classroom=classroom, day=day_index
        ).select_related("subject").order_by("start_hour")
        grouped = {}
        for entry in entries:
            key = (entry.subject_id, entry.session_type)
            g = grouped.setdefault(key, {
                "subject": entry.subject, "session_type": entry.session_type, "slots": [],
            })
            g["slots"].append(entry.start_hour)
        for (subject_id, session_type), g in grouped.items():
            sessions.append({
                "key": f"{subject_id}|{session_type}",
                "subject": g["subject"],
                "session_type": session_type,
                "hours": float(len(g["slots"])),
                "label": f"{g['subject'].name} ({hours_label(g['slots'])} · {len(g['slots'])}h)",
            })
    schedule_based = bool(sessions)
    if not sessions:
        sessions = [{
            "key": f"{s.pk}|cours", "subject": s, "session_type": "cours",
            "hours": s.hours_ci or 1.5, "label": s.name,
        } for s in subjects]
    return sessions, schedule_based


@login_required
def absence_admin(request, classroom_pk):
    if not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=classroom_pk)
    enrollments = StudentEnrollment.objects.filter(classroom=classroom, is_active=True).select_related("student")
    subjects = Subject.objects.filter(classroom=classroom).order_by("name")

    selected_date = request.POST.get("date") or request.GET.get("date") or timezone.localdate().isoformat()
    selected_student = request.POST.get("student") or request.GET.get("student")
    enrollment = enrollments.filter(pk=selected_student).first() if selected_student else None

    sessions, schedule_based = day_sessions(classroom, subjects, selected_date)
    for s in sessions:
        s["field"] = s["key"].replace("|", "_")

    day_index = date.fromisoformat(selected_date).weekday()
    day_name = dict(ScheduleEntry.DAY_CHOICES).get(day_index, "Dimanche")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_student_day" and enrollment:
            new_subjects = []
            for s in sessions:
                existing = Absence.objects.filter(
                    student=enrollment, subject=s["subject"],
                    session_type=s["session_type"], date=selected_date,
                ).first()
                if f"absent_{s['field']}" in request.POST:
                    hours = request.POST.get(f"hours_{s['field']}") or s["hours"]
                    justification = request.POST.get(f"justification_{s['field']}", "").strip()
                    is_justified = f"justified_{s['field']}" in request.POST
                    if existing:
                        existing.hours = hours
                        existing.justification = justification
                        existing.is_justified = is_justified
                        existing.save()
                    else:
                        Absence.objects.create(
                            student=enrollment, subject=s["subject"], session_type=s["session_type"],
                            date=selected_date, hours=hours,
                            justification=justification, is_justified=is_justified,
                        )
                        new_subjects.append(s["subject"].name)
                elif existing:
                    existing.delete()
            # Alerte automatique au parent pour toute nouvelle absence
            if new_subjects and enrollment.student.parent_account_id:
                from core.views import notify_user
                notify_user(
                    enrollment.student.parent_account,
                    "Absence de votre enfant",
                    f"{enrollment.student.get_full_name()} — absent(e) le {selected_date} : {', '.join(new_subjects)}.",
                    "/academics/absences/",
                )
            messages.success(
                request,
                f"Absences de {enrollment.student.get_full_name()} enregistrées pour le {selected_date}.",
            )
            return redirect(f"{request.path}?date={selected_date}&student={enrollment.pk}")
        elif action == "delete_absence":
            Absence.objects.filter(pk=request.POST.get("absence_id")).delete()
            messages.success(request, "Absence supprimée.")
            return redirect(f"{request.path}?date={selected_date}&student={selected_student or ''}")
        elif action == "toggle_justified":
            absence = get_object_or_404(Absence, pk=request.POST.get("absence_id"))
            absence.is_justified = not absence.is_justified
            absence.save(update_fields=["is_justified"])
            return redirect(f"{request.path}?date={selected_date}&student={selected_student or ''}")

    # Tableau des séances du jour pour l'élève choisi, avec ses absences existantes
    session_rows = []
    if enrollment:
        existing = {
            f"{a.subject_id}|{a.session_type}": a
            for a in Absence.objects.filter(student=enrollment, date=selected_date)
        }
        for s in sessions:
            session_rows.append({"session": s, "absence": existing.get(s["key"])})

    recent_absences = Absence.objects.filter(student__in=enrollments).select_related(
        "student__student", "subject"
    ).order_by("-date", "-id")[:30]

    return render(request, "academics/absence_admin.html", {
        "classroom": classroom,
        "enrollments": enrollments,
        "enrollment": enrollment,
        "schedule_based": schedule_based,
        "selected_date": selected_date,
        "session_rows": session_rows,
        "day_name": day_name,
        "recent_absences": recent_absences,
        "today": timezone.localdate().isoformat(),
    })


@login_required
def year_transition(request):
    """Assistant de rentrée : nouvelle année scolaire et réinscription en masse."""
    if not request.user.is_admin_user:
        return redirect("core:home")
    classrooms = Classroom.objects.select_related("academic_year").order_by("name")
    years = AcademicYear.objects.order_by("-label")

    source_id = request.POST.get("source") or request.GET.get("source")
    source = Classroom.objects.filter(pk=source_id).first() if source_id else None
    source_enrollments = (
        StudentEnrollment.objects.filter(classroom=source, is_active=True).select_related("student")
        if source else []
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_year":
            label = request.POST.get("label", "").strip()
            if label:
                year, created = AcademicYear.objects.get_or_create(label=label)
                if "make_current" in request.POST:
                    year.is_current = True
                    year.save()
                messages.success(request, f"Année scolaire {label} " + ("créée." if created else "mise à jour."))
            return redirect("academics:year_transition")
        elif action == "move_students" and source:
            target = get_object_or_404(Classroom, pk=request.POST.get("target"))
            moved = 0
            deactivated = 0
            for enr in source_enrollments:
                if f"student_{enr.pk}" not in request.POST:
                    continue
                if request.POST.get("move_action") == "deactivate":
                    enr.is_active = False
                    enr.save(update_fields=["is_active"])
                    deactivated += 1
                else:
                    enr.classroom = target
                    enr.save(update_fields=["classroom"])
                    EnrollmentHistory.record(enr)
                    moved += 1
            if moved:
                messages.success(request, f"{moved} élève(s) réinscrit(s) dans {target}. Leur parcours a été archivé automatiquement.")
            if deactivated:
                messages.success(request, f"{deactivated} élève(s) désactivé(s) (départ de l'école).")
            if not moved and not deactivated:
                messages.warning(request, "Aucun élève sélectionné.")
            return redirect(f"{request.path}?source={source.pk}")

    return render(request, "academics/year_transition.html", {
        "classrooms": classrooms,
        "years": years,
        "source": source,
        "source_enrollments": source_enrollments,
    })


@login_required
def teacher_lessons(request, classroom_pk):
    """Cahier de textes côté enseignant : saisie du travail fait et des devoirs."""
    if not request.user.is_teacher and not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=classroom_pk)
    if request.user.is_teacher and not request.user.is_admin_user:
        my_subjects = Subject.objects.filter(classroom=classroom, teacher=request.user)
        if not my_subjects.exists():
            return redirect("academics:teacher_classrooms")
    else:
        my_subjects = Subject.objects.filter(classroom=classroom)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            subject = get_object_or_404(my_subjects, pk=request.POST.get("subject"))
            LessonEntry.objects.create(
                classroom=classroom,
                subject=subject,
                teacher=request.user,
                date=request.POST.get("date") or timezone.localdate(),
                content=request.POST.get("content", "").strip(),
                homework=request.POST.get("homework", "").strip(),
                homework_due=request.POST.get("homework_due") or None,
            )
            messages.success(request, "Entrée ajoutée au cahier de textes.")
        elif action == "delete":
            entry = get_object_or_404(LessonEntry, pk=request.POST.get("entry_id"), classroom=classroom)
            if request.user.is_admin_user or entry.teacher_id == request.user.pk:
                entry.delete()
                messages.success(request, "Entrée supprimée.")
        return redirect("academics:teacher_lessons", classroom_pk=classroom.pk)

    entries = LessonEntry.objects.filter(classroom=classroom).select_related("subject", "teacher")
    return render(request, "academics/teacher_lessons.html", {
        "classroom": classroom,
        "my_subjects": my_subjects,
        "entries": entries,
        "today": timezone.localdate().isoformat(),
    })


@login_required
def my_lessons(request):
    """Cahier de textes côté élève / parent."""
    enrollment = request.user.linked_enrollment
    entries = LessonEntry.objects.none()
    homework_entries = []
    if enrollment and enrollment.is_active and enrollment.classroom:
        entries = LessonEntry.objects.filter(
            classroom=enrollment.classroom
        ).select_related("subject", "teacher")[:40]
        today = timezone.localdate()
        homework_entries = [
            e for e in entries
            if e.homework and (e.homework_due is None or e.homework_due >= today)
        ][:10]
    return render(request, "academics/my_lessons.html", {
        "enrollment": enrollment,
        "entries": entries,
        "homework_entries": homework_entries,
    })


@login_required
def teacher_resources(request, classroom_pk):
    """Ressources de cours côté enseignant : dépôt de supports par matière."""
    if not request.user.is_teacher and not request.user.is_admin_user:
        return redirect("core:home")
    classroom = get_object_or_404(Classroom, pk=classroom_pk)
    if request.user.is_teacher and not request.user.is_admin_user:
        my_subjects = Subject.objects.filter(classroom=classroom, teacher=request.user)
        if not my_subjects.exists():
            return redirect("academics:teacher_classrooms")
    else:
        my_subjects = Subject.objects.filter(classroom=classroom)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            subject = get_object_or_404(my_subjects, pk=request.POST.get("subject"))
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                messages.error(request, "Veuillez choisir un fichier.")
            else:
                CourseResource.objects.create(
                    classroom=classroom,
                    subject=subject,
                    teacher=request.user,
                    title=request.POST.get("title", "").strip() or uploaded_file.name,
                    description=request.POST.get("description", "").strip(),
                    file=uploaded_file,
                )
                messages.success(request, "Ressource ajoutée.")
        elif action == "delete":
            resource = get_object_or_404(CourseResource, pk=request.POST.get("resource_id"), classroom=classroom)
            if request.user.is_admin_user or resource.teacher_id == request.user.pk:
                resource.file.delete(save=False)
                resource.delete()
                messages.success(request, "Ressource supprimée.")
        return redirect("academics:teacher_resources", classroom_pk=classroom.pk)

    resources = CourseResource.objects.filter(classroom=classroom).select_related("subject", "teacher")
    return render(request, "academics/teacher_resources.html", {
        "classroom": classroom,
        "my_subjects": my_subjects,
        "resources": resources,
    })


@login_required
def my_resources(request):
    """Ressources de cours côté élève / parent : consultation et téléchargement."""
    enrollment = request.user.linked_enrollment
    resources = CourseResource.objects.none()
    if enrollment and enrollment.is_active and enrollment.classroom:
        resources = CourseResource.objects.filter(
            classroom=enrollment.classroom
        ).select_related("subject", "teacher").order_by("subject__name", "-created_at")
    return render(request, "academics/my_resources.html", {
        "enrollment": enrollment,
        "resources": resources,
    })


@login_required
def student_history(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, role="student")
    is_own = request.user.pk == student.pk
    is_parent_of = student.parent_account_id == request.user.pk
    if not (request.user.is_admin_user or is_own or is_parent_of):
        return redirect("core:home")

    try:
        enrollment = student.enrollment
    except StudentEnrollment.DoesNotExist:
        enrollment = None

    history_entries = list(student.enrollment_history.select_related("classroom__academic_year"))

    # Regroupement de tout le parcours par année scolaire
    years = {}

    def year_block(label):
        if label not in years:
            years[label] = {
                "label": label or "Année inconnue",
                "classrooms": [],
                "semesters": {},
                "absences": [],
                "absence_hours": 0,
                "absence_justified": 0,
                "notes": [],
            }
        return years[label]

    for entry in history_entries:
        block = year_block(entry.academic_year_label)
        block["classrooms"].append(entry)

    if enrollment:
        grades = Grade.objects.filter(student=enrollment).select_related(
            "subject__classroom__academic_year", "semester"
        ).order_by("semester__label", "subject__name")
        for grade in grades:
            classroom = grade.subject.classroom
            label = classroom.academic_year.label if classroom.academic_year else ""
            block = year_block(label)
            sem = block["semesters"].setdefault(
                grade.semester.label,
                {"label": grade.semester.get_label_display(), "rows": [], "average": None},
            )
            sem["rows"].append(grade)

        # Moyenne pondérée par coefficient pour chaque semestre
        for block in years.values():
            for sem in block["semesters"].values():
                points, weights = 0, 0
                for grade in sem["rows"]:
                    avg = grade.average
                    if avg is not None:
                        coef = grade.subject.coefficient or 1
                        points += avg * coef
                        weights += coef
                if weights:
                    sem["average"] = round(points / weights, 2)

        absences = Absence.objects.filter(student=enrollment).select_related(
            "subject__classroom__academic_year"
        ).order_by("-date")
        for absence in absences:
            classroom = absence.subject.classroom
            label = classroom.academic_year.label if classroom.academic_year else ""
            block = year_block(label)
            block["absences"].append(absence)
            block["absence_hours"] += absence.hours or 0
            if absence.is_justified:
                block["absence_justified"] += 1

        notes = StudentNote.objects.filter(
            Q(student=enrollment) | Q(student__isnull=True, classroom__enrollment_history__student=student)
        ).select_related("classroom__academic_year", "teacher", "subject").distinct()
        for note in notes:
            label = note.classroom.academic_year.label if note.classroom and note.classroom.academic_year else ""
            year_block(label)["notes"].append(note)

        tranches = enrollment.tranches.all()
    else:
        tranches = []

    from documents.models import DocumentRequest
    doc_requests = DocumentRequest.objects.filter(student=student)

    # Années triées de la plus récente à la plus ancienne, semestres dans l'ordre
    year_blocks = sorted(years.values(), key=lambda b: b["label"], reverse=True)
    for block in year_blocks:
        block["semesters"] = [block["semesters"][k] for k in sorted(block["semesters"])]

    total_paid = sum((t.amount_paid for t in tranches), 0)
    total_requested = sum((t.amount_requested for t in tranches), 0)

    return render(request, "academics/student_history.html", {
        "student": student,
        "enrollment": enrollment,
        "year_blocks": year_blocks,
        "tranches": tranches,
        "total_paid": total_paid,
        "total_requested": total_requested,
        "doc_requests": doc_requests,
    })
