from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class AcademicYear(models.Model):
    label = models.CharField(max_length=20)  # e.g. "2025-2026"
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicYear.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Classroom(models.Model):
    SECTION_CHOICES = [
        ('Lettres', 'Lettres'),
        ('Economie et gestion', 'Economie et gestion'),
        ('Technique', 'Technique'),
        ('Informatique', 'Informatique'),
        ('Mathématiques', 'Mathématiques'),
        ('Sciences expérimentales', 'Sciences expérimentales'),
    ]
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100, blank=True, choices=SECTION_CHOICES)
    cycle = models.CharField(max_length=50, blank=True)
    group = models.CharField(max_length=10, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        parts = [self.name]
        if self.specialty:
            parts.append(self.specialty)
        if self.group:
            parts.append(self.group)
        return ', '.join(parts)


class StudentEnrollment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('comptant', 'Comptant'),
        ('cheque', 'Chèque'),
        ('traite', 'Traite bancaire'),
    ]
    student = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='enrollment')
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='enrollments')
    matricule = models.CharField(max_length=20, unique=True)
    subgroup = models.CharField(max_length=50, blank=True)  # "Sous Groupe 2"
    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True,
        verbose_name='Mode de paiement',
    )
    max_installments = models.PositiveIntegerField(
        default=1, verbose_name='Nombre de tranches autorisées',
    )

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.classroom}"


class EnrollmentHistory(models.Model):
    """Trace le parcours de l'élève : une entrée par classe fréquentée."""
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='enrollment_history')
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='enrollment_history')
    # Instantanés conservés même si la classe ou l'année est supprimée
    classroom_label = models.CharField(max_length=200, blank=True)
    academic_year_label = models.CharField(max_length=20, blank=True)
    matricule = models.CharField(max_length=20, blank=True)
    started_at = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at', '-created_at']
        verbose_name = 'Parcours élève'
        verbose_name_plural = 'Parcours élèves'

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.classroom_label} ({self.academic_year_label})"

    @classmethod
    def record(cls, enrollment):
        """Enregistre (une seule fois) le passage de l'élève dans sa classe actuelle."""
        classroom = enrollment.classroom
        if classroom is None:
            return None
        entry, _ = cls.objects.get_or_create(
            student=enrollment.student,
            classroom=classroom,
            defaults={
                'classroom_label': str(classroom),
                'academic_year_label': classroom.academic_year.label if classroom.academic_year else '',
                'matricule': enrollment.matricule,
            },
        )
        return entry


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    coefficient = models.FloatField(default=1.0)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='subjects')
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='subjects_taught', verbose_name='Enseignant (cours)')
    teacher_tp = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='subjects_taught_tp', verbose_name='Enseignant (TP)')
    hours_ci = models.FloatField(default=1.5, verbose_name='H CI')
    hours_tp = models.FloatField(default=1.5, verbose_name='H TP')
    weeks = models.IntegerField(default=14, verbose_name='Semaines')

    def __str__(self):
        return f"{self.name} ({self.classroom})"

    @property
    def total_hours(self):
        return (self.hours_ci + self.hours_tp) * self.weeks


class Semester(models.Model):
    SEMESTER_CHOICES = [('S1', 'Semestre 1'), ('S2', 'Semestre 2'), ('S3', 'Semestre 3')]
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    label = models.CharField(max_length=2, choices=SEMESTER_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.label} - {self.classroom}"


class Grade(models.Model):
    student = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='grades')
    cc = models.FloatField(null=True, blank=True, verbose_name='Orale')
    ds = models.FloatField(null=True, blank=True, verbose_name="Examen d'évaluation")
    exam = models.FloatField(null=True, blank=True, verbose_name='Examen final')

    class Meta:
        unique_together = ('student', 'subject', 'semester')

    def __str__(self):
        return f"{self.student.student.get_full_name()} - {self.subject.name}"

    @property
    def average(self):
        scores = []
        weights = []
        if self.cc is not None:
            scores.append(self.cc * 0.3)
            weights.append(0.3)
        if self.ds is not None:
            scores.append(self.ds * 0.2)
            weights.append(0.2)
        if self.exam is not None:
            scores.append(self.exam * 0.5)
            weights.append(0.5)
        total_weight = sum(weights)
        if total_weight == 0:
            return None
        return round(sum(scores) / total_weight, 2)


class Absence(models.Model):
    SESSION_CHOICES = [('cours', 'Cours'), ('tp', 'TP')]
    student = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='absences')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='absences')
    session_type = models.CharField(max_length=10, choices=SESSION_CHOICES, default='cours',
                                    verbose_name='Type de séance')
    date = models.DateField()
    hours = models.FloatField(default=1.5)
    is_justified = models.BooleanField(default=False)
    justification = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student.student.get_full_name()} - {self.subject.name} ({self.get_session_type_display()}) - {self.date}"


class StudentNote(models.Model):
    TYPE_OBSERVATION = 'observation'
    TYPE_PUNITION = 'punition'
    TYPE_CHOICES = [
        (TYPE_OBSERVATION, 'Observation'),
        (TYPE_PUNITION, 'Punition'),
    ]
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='notes')
    student = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='notes', null=True, blank=True)
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='student_notes')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_notes')
    note_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OBSERVATION)
    content = models.TextField()
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Note de suivi'
        verbose_name_plural = 'Notes de suivi'

    def __str__(self):
        target = self.student.student.get_full_name() if self.student_id else str(self.classroom)
        return f"{self.get_note_type_display()} - {target} - {self.date}"


class ScheduleEntry(models.Model):
    """Créneau de l'emploi du temps saisi manuellement (journée de 8h à 17h)."""
    DAY_CHOICES = [
        (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'),
        (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'),
    ]
    SESSION_CHOICES = [('cours', 'Cours'), ('tp', 'TP')]
    START_HOUR = 8
    END_HOUR = 17
    BREAK_START = 12   # pause déjeuner de 12h à 14h
    BREAK_END = 14

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedule_entries')
    day = models.IntegerField(choices=DAY_CHOICES)
    start_hour = models.IntegerField()  # 8 à 16 : le créneau couvre start_hour → start_hour + 1
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='schedule_entries')
    session_type = models.CharField(max_length=10, choices=SESSION_CHOICES, default='cours')

    class Meta:
        unique_together = ('classroom', 'day', 'start_hour')
        ordering = ['day', 'start_hour']
        verbose_name = 'Créneau emploi du temps'
        verbose_name_plural = 'Créneaux emploi du temps'

    def __str__(self):
        return f"{self.classroom} - {self.get_day_display()} {self.start_hour}h : {self.subject.name}"

    @classmethod
    def teaching_hours(cls):
        return [h for h in range(cls.START_HOUR, cls.END_HOUR)
                if not (cls.BREAK_START <= h < cls.BREAK_END)]

    @property
    def teacher(self):
        if self.session_type == 'tp' and self.subject.teacher_tp_id:
            return self.subject.teacher_tp
        return self.subject.teacher


class LessonEntry(models.Model):
    """Cahier de textes : travail fait en classe et devoirs, saisi par l'enseignant."""
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='lesson_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='lesson_entries')
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='lesson_entries')
    date = models.DateField(default=timezone.localdate, verbose_name='Date de la séance')
    content = models.TextField(verbose_name='Travail fait en classe')
    homework = models.TextField(blank=True, verbose_name='Devoirs à faire')
    homework_due = models.DateField(null=True, blank=True, verbose_name='Pour le')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Cahier de textes'
        verbose_name_plural = 'Cahier de textes'

    def __str__(self):
        return f"{self.subject.name} - {self.date:%d/%m/%Y}"


class CourseResource(models.Model):
    """Support de cours déposé par l'enseignant, téléchargeable par les élèves de la classe."""
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='resources')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='resources')
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='resources_uploaded')
    title = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='resources/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ressource de cours'
        verbose_name_plural = 'Ressources de cours'

    def __str__(self):
        return f"{self.title} - {self.subject.name} ({self.classroom})"


class Schedule(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedules')
    image = models.ImageField(upload_to='schedules/')
    version_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Emploi du temps - {self.classroom} ({self.version_date})"
