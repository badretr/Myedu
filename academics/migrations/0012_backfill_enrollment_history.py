from django.db import migrations


def backfill(apps, schema_editor):
    StudentEnrollment = apps.get_model('academics', 'StudentEnrollment')
    EnrollmentHistory = apps.get_model('academics', 'EnrollmentHistory')
    Classroom = apps.get_model('academics', 'Classroom')

    def classroom_label(classroom):
        parts = [classroom.name]
        if classroom.specialty:
            parts.append(classroom.specialty)
        if classroom.group:
            parts.append(classroom.group)
        return ', '.join(parts)

    # 1. Inscription actuelle de chaque élève
    for enrollment in StudentEnrollment.objects.select_related(
        'classroom__academic_year', 'student'
    ):
        if enrollment.classroom is None:
            continue
        year = enrollment.classroom.academic_year
        EnrollmentHistory.objects.get_or_create(
            student=enrollment.student,
            classroom=enrollment.classroom,
            defaults={
                'classroom_label': classroom_label(enrollment.classroom),
                'academic_year_label': year.label if year else '',
                'matricule': enrollment.matricule,
                'started_at': enrollment.enrolled_at.date(),
            },
        )

    # 2. Classes des années précédentes, retrouvées via les notes et absences
    Grade = apps.get_model('academics', 'Grade')
    Absence = apps.get_model('academics', 'Absence')
    seen = set()
    for model, path in ((Grade, 'subject__classroom_id'), (Absence, 'subject__classroom_id')):
        for student_id, classroom_id in model.objects.values_list(
            'student__student_id', path
        ).distinct():
            if classroom_id is None or (student_id, classroom_id) in seen:
                continue
            seen.add((student_id, classroom_id))
            classroom = Classroom.objects.select_related('academic_year').get(pk=classroom_id)
            year = classroom.academic_year
            EnrollmentHistory.objects.get_or_create(
                student_id=student_id,
                classroom=classroom,
                defaults={
                    'classroom_label': classroom_label(classroom),
                    'academic_year_label': year.label if year else '',
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0011_enrollmenthistory'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
