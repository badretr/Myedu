from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ObjectDoesNotExist


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('student', 'Étudiant'),
        ('teacher', 'Enseignant'),
        ('parent', 'Parent'),
    ]
    username = models.CharField(max_length=150, unique=True, validators=[])
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True)
    cin = models.CharField(max_length=20, blank=True, verbose_name="Numéro carte d'identité")
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, default='Tunisienne')

    father_name = models.CharField(max_length=150, blank=True, verbose_name='Nom et prénom du père')
    father_phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone du père')
    father_email = models.EmailField(blank=True, verbose_name='Email du père')
    father_cin = models.CharField(max_length=20, blank=True, verbose_name="Numéro carte d'identité du père")

    mother_name = models.CharField(max_length=150, blank=True, verbose_name='Nom et prénom de la mère')
    mother_phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone de la mère')
    mother_email = models.EmailField(blank=True, verbose_name='Email de la mère')
    mother_cin = models.CharField(max_length=20, blank=True, verbose_name="Numéro carte d'identité de la mère")

    internal_contract = models.FileField(
        upload_to='contracts/', blank=True, null=True,
        verbose_name="Contrat interne signé par les parents",
    )

    parent_account = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', limit_choices_to={'role': 'parent'},
        verbose_name='Compte parent',
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    def get_full_name(self):
        # Toujours afficher « Prénom Nom » ; repli sur le nom d'utilisateur si vide
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username

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

    @property
    def linked_enrollment(self):
        if self.is_parent:
            child = self.children.first()
            return child.linked_enrollment if child else None
        try:
            return self.enrollment
        except ObjectDoesNotExist:
            return None

    def display_name(self):
        return self.get_full_name()
