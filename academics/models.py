from django.db import models
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
    name = models.CharField(max_length=100)       # e.g. "4ème Année Informatique"
    specialty = models.CharField(max_length=100, blank=True)  # "Cloud & Réseaux"
    cycle = models.CharField(max_length=50, blank=True)       # "Ingénieur"
    group = models.CharField(max_length=10, blank=True)       # "Gr B"
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        parts = [self.name]
        if self.specialty:
            parts.append(self.specialty)
        if self.group:
            parts.append(self.group)
        return ', '.join(parts)


class StudentEnrollment(models.Model):
    student = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='enrollment')
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='enrollments')
    matricule = models.CharField(max_length=20, unique=True)
    subgroup = models.CharField(max_length=10, blank=True)  # "Sous Groupe 2"
    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.classroom}"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    coefficient = models.FloatField(default=1.0)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='subjects')
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='subjects_taught')
    hours_ci = models.FloatField(default=1.5, verbose_name='H CI')
    hours_tp = models.FloatField(default=1.5, verbose_name='H TP')
    weeks = models.IntegerField(default=14, verbose_name='Semaines')

    def __str__(self):
        return f"{self.name} ({self.classroom})"

    @property
    def total_hours(self):
        return (self.hours_ci + self.hours_tp) * self.weeks


class Semester(models.Model):
    SEMESTER_CHOICES = [('S1', 'Semestre 1'), ('S2', 'Semestre 2')]
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
    cc = models.FloatField(null=True, blank=True, verbose_name='CC')
    ds = models.FloatField(null=True, blank=True, verbose_name='DS')
    exam = models.FloatField(null=True, blank=True, verbose_name='Examen')
    controle = models.FloatField(null=True, blank=True, verbose_name='Contrôle')

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
    student = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='absences')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='absences')
    date = models.DateField()
    hours = models.FloatField(default=1.5)
    is_justified = models.BooleanField(default=False)
    justification = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student.student.get_full_name()} - {self.subject.name} - {self.date}"


class Schedule(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedules')
    image = models.ImageField(upload_to='schedules/')
    version_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Emploi du temps - {self.classroom} ({self.version_date})"
