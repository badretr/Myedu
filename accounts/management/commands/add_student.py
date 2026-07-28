from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academics.models import Classroom, StudentEnrollment, EnrollmentHistory
from accounts.forms import CustomUserCreationForm


class Command(BaseCommand):
    help = "Crée un nouvel élève avec toutes les informations du formulaire remplies (fiche élève + inscription)."

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help="Nom d'utilisateur de l'élève")
        parser.add_argument('--first-name', required=True)
        parser.add_argument('--last-name', default='')
        parser.add_argument('--email', default='')
        parser.add_argument('--phone', default='')
        parser.add_argument('--date-of-birth', default='', help='Format YYYY-MM-DD')
        parser.add_argument('--nationality', default='Tunisienne')
        parser.add_argument('--password', default='eleve1234')

        parser.add_argument('--father-name', default='')
        parser.add_argument('--father-phone', default='')
        parser.add_argument('--father-email', default='')
        parser.add_argument('--father-cin', default='')

        parser.add_argument('--mother-name', default='')
        parser.add_argument('--mother-phone', default='')
        parser.add_argument('--mother-email', default='')
        parser.add_argument('--mother-cin', default='')

        parser.add_argument('--parent-username', default='', help="Nom d'utilisateur du compte parent (optionnel)")

        parser.add_argument('--classroom', default='', help='Nom de la classe (ex: "1ère Année A")')
        parser.add_argument('--matricule', default='', help='Matricule (auto-généré si absent)')
        parser.add_argument('--subgroup', default='')
        parser.add_argument('--payment-method', default='comptant', choices=['comptant', 'cheque', 'traite'])
        parser.add_argument('--max-installments', type=int, default=1)

    @transaction.atomic
    def handle(self, *args, **options):
        form_data = {
            'username': options['username'],
            'first_name': options['first_name'],
            'email': options['email'],
            'phone': options['phone'],
            'date_of_birth': options['date_of_birth'] or None,
            'nationality': options['nationality'],
            'father_name': options['father_name'],
            'father_phone': options['father_phone'],
            'father_email': options['father_email'],
            'father_cin': options['father_cin'],
            'mother_name': options['mother_name'],
            'mother_phone': options['mother_phone'],
            'mother_email': options['mother_email'],
            'mother_cin': options['mother_cin'],
            'parent_username': options['parent_username'],
            'password1': options['password'],
            'password2': options['password'],
        }
        form = CustomUserCreationForm(data=form_data)
        if not form.is_valid():
            raise CommandError(f"Formulaire invalide : {form.errors.as_json()}")

        student = form.save()
        if options['last_name']:
            student.last_name = options['last_name']
            student.save(update_fields=['last_name'])

        classroom = None
        if options['classroom']:
            classroom = Classroom.objects.filter(name=options['classroom']).first()
            if classroom is None:
                raise CommandError(f"Classe introuvable : {options['classroom']}")
        else:
            classroom = Classroom.objects.first()

        if classroom is not None:
            matricule = options['matricule'] or f"MAT{student.pk:04d}"
            enrollment = StudentEnrollment.objects.create(
                student=student,
                classroom=classroom,
                matricule=matricule,
                subgroup=options['subgroup'],
                payment_method=options['payment_method'],
                max_installments=options['max_installments'],
            )
            EnrollmentHistory.record(enrollment)
            self.stdout.write(self.style.SUCCESS(
                f"Élève '{student.get_full_name()}' créé et inscrit dans '{classroom}' (matricule {enrollment.matricule})."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Élève '{student.get_full_name()}' créé, mais aucune classe disponible pour l'inscrire."
            ))
