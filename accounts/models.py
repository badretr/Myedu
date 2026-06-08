from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('student', 'Étudiant'),
        ('teacher', 'Enseignant'),
        ('parent', 'Parent'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, default='Tunisienne')

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    @property
    def is_admin_user(self):
        return self.role == 'admin' or self.is_staff

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_parent(self):
        return self.role == 'parent'
