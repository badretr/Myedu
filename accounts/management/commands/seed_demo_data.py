import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academics.models import (
    AcademicYear, Classroom, Semester, StudentEnrollment,
    Grade, Absence, ScheduleEntry, LessonEntry, StudentNote,
)
from accounts.models import CustomUser
from finance.models import PaymentTranche, ExtraService
from documents.models import DocumentRequest
from core.models import News, Suggestion, AppointmentRequest, SchoolEvent


class Command(BaseCommand):
    help = (
        "Remplit la base avec des données de démonstration réalistes pour toutes les "
        "fonctionnalités : notes, absences, emploi du temps, paiements, services annexes, "
        "documents, actualités, suggestions, rendez-vous, événements, cahier de textes, notes de suivi."
    )

    SEMESTER_DATES = {
        'S1': (date(2026, 9, 15), date(2026, 12, 20)),
        'S2': (date(2027, 1, 5), date(2027, 3, 31)),
        'S3': (date(2027, 4, 1), date(2027, 6, 30)),
    }

    LEVEL_RANGES = {
        'faible': (6, 11),
        'moyen': (9, 14),
        'bon': (12, 17),
        'excellent': (15, 19),
    }

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=42)

    @transaction.atomic
    def handle(self, *args, **options):
        self.rng = random.Random(options['seed'])
        self._levels = {}
        self.admin = CustomUser.objects.filter(role='admin').first()

        self.fill_semesters()
        self.fill_grades()
        self.fill_schedule()
        self.fill_absences()
        self.fill_payments()
        self.fill_extra_services()
        self.fill_documents()
        self.fill_news()
        self.fill_suggestions()
        self.fill_appointments()
        self.fill_events()
        self.fill_lessons()
        self.fill_student_notes()

        self.stdout.write(self.style.SUCCESS("Données de démonstration générées avec succès."))

    # ---------- Semestres ----------
    def fill_semesters(self):
        created = 0
        for classroom in Classroom.objects.all():
            for label, (start, end) in self.SEMESTER_DATES.items():
                _, was_created = Semester.objects.get_or_create(
                    classroom=classroom, label=label,
                    defaults={'start_date': start, 'end_date': end},
                )
                created += int(was_created)
        self.stdout.write(f"Semestres : {created} créés.")

    # ---------- Notes ----------
    def _student_level(self, enrollment_id):
        if enrollment_id not in self._levels:
            self._levels[enrollment_id] = self.rng.choices(
                list(self.LEVEL_RANGES), weights=[15, 40, 30, 15]
            )[0]
        return self._levels[enrollment_id]

    def _score(self, enrollment_id):
        low, high = self.LEVEL_RANGES[self._student_level(enrollment_id)]
        return round(self.rng.uniform(low, high), 2)

    def fill_grades(self):
        created, filled = 0, 0
        enrollments = StudentEnrollment.objects.filter(is_active=True, classroom__isnull=False)
        for enrollment in enrollments:
            subjects = list(enrollment.classroom.subjects.all())
            semesters = list(Semester.objects.filter(classroom=enrollment.classroom))
            for subject in subjects:
                for semester in semesters:
                    grade, was_created = Grade.objects.get_or_create(
                        student=enrollment, subject=subject, semester=semester,
                    )
                    created += int(was_created)
                    changed = False
                    if grade.cc is None:
                        grade.cc = self._score(enrollment.id)
                        changed = True
                    if grade.ds is None:
                        grade.ds = self._score(enrollment.id)
                        changed = True
                    if grade.exam is None:
                        grade.exam = self._score(enrollment.id)
                        changed = True
                    if changed:
                        grade.save()
                        filled += 1
        self.stdout.write(f"Notes : {created} créées, {filled} complétées.")

    # ---------- Emploi du temps ----------
    def fill_schedule(self):
        teaching_hours = ScheduleEntry.teaching_hours()
        teacher_busy = set()
        for entry in ScheduleEntry.objects.select_related('subject'):
            teacher_id = entry.subject.teacher_id
            if teacher_id:
                teacher_busy.add((teacher_id, entry.day, entry.start_hour))

        created = 0
        for classroom in Classroom.objects.all():
            existing_entries = list(ScheduleEntry.objects.filter(classroom=classroom))
            existing_slots = {(e.day, e.start_hour) for e in existing_entries}
            existing_by_subject = {}
            for e in existing_entries:
                existing_by_subject[e.subject_id] = existing_by_subject.get(e.subject_id, 0) + 1

            free_slots = [
                (day, hour) for day in range(6) for hour in teaching_hours
                if (day, hour) not in existing_slots
            ]
            self.rng.shuffle(free_slots)

            subjects = list(classroom.subjects.all())
            self.rng.shuffle(subjects)
            for subject in subjects:
                needed = max(1, round(subject.hours_ci)) - existing_by_subject.get(subject.id, 0)
                if needed <= 0:
                    continue
                teacher_id = subject.teacher_id
                placed = 0
                remaining_slots = []
                for slot in free_slots:
                    if placed >= needed:
                        remaining_slots.append(slot)
                        continue
                    day, hour = slot
                    if teacher_id and (teacher_id, day, hour) in teacher_busy:
                        remaining_slots.append(slot)
                        continue
                    ScheduleEntry.objects.create(
                        classroom=classroom, day=day, start_hour=hour,
                        subject=subject, session_type='cours',
                    )
                    if teacher_id:
                        teacher_busy.add((teacher_id, day, hour))
                    created += 1
                    placed += 1
                free_slots = remaining_slots
        self.stdout.write(f"Emploi du temps : {created} créneaux créés.")

    # ---------- Absences ----------
    def fill_absences(self):
        semesters_by_classroom = {}
        for s in Semester.objects.all():
            semesters_by_classroom.setdefault(s.classroom_id, []).append(s)

        created = 0
        enrollments = list(StudentEnrollment.objects.filter(is_active=True, classroom__isnull=False))
        for enrollment in enrollments:
            if self.rng.random() > 0.65:
                continue
            entries = list(ScheduleEntry.objects.filter(classroom=enrollment.classroom))
            if not entries:
                continue
            for _ in range(self.rng.randint(1, 5)):
                entry = self.rng.choice(entries)
                semesters = semesters_by_classroom.get(enrollment.classroom_id, [])
                if not semesters:
                    continue
                semester = self.rng.choice(semesters)
                span = (semester.end_date - semester.start_date).days
                candidate_dates = [
                    semester.start_date + timedelta(days=d)
                    for d in range(span + 1)
                ]
                candidate_dates = [d for d in candidate_dates if d.weekday() == entry.day]
                if not candidate_dates:
                    continue
                abs_date = self.rng.choice(candidate_dates)
                justified = self.rng.random() < 0.35
                _, was_created = Absence.objects.get_or_create(
                    student=enrollment, subject=entry.subject, date=abs_date,
                    session_type=entry.session_type,
                    defaults={
                        'hours': 1.0,
                        'is_justified': justified,
                        'justification': 'Certificat médical' if justified else '',
                    },
                )
                created += int(was_created)
        self.stdout.write(f"Absences : {created} créées.")

    # ---------- Paiements ----------
    def fill_payments(self):
        base_amounts = [1800, 1950, 2100, 2250, 2400, 2550, 2700, 2900, 3100]
        extras = [Decimal('0.000'), Decimal('0.150'), Decimal('0.256'), Decimal('0.500'), Decimal('0.650')]
        due_dates_by_count = {
            1: [date(2026, 9, 30)],
            2: [date(2026, 9, 30), date(2027, 1, 15)],
            3: [date(2026, 9, 30), date(2026, 12, 15), date(2027, 3, 15)],
        }

        created = 0
        for enrollment in StudentEnrollment.objects.filter(is_active=True):
            if enrollment.tranches.exists():
                continue
            installments = max(1, min(3, enrollment.max_installments))
            total_fees = Decimal(self.rng.choice(base_amounts)) + self.rng.choice(extras)
            other_fees_total = Decimal(self.rng.choice([0, 0, 50, 80, 120]))
            due_dates = due_dates_by_count[installments]

            base_share = (total_fees / installments).quantize(Decimal('0.001'))
            remaining = total_fees
            for i, due in enumerate(due_dates):
                order = i + 1
                is_last = order == installments
                share = remaining if is_last else base_share
                remaining -= share
                other_share = other_fees_total if order == 1 else Decimal('0.000')
                requested = share + other_share

                if order == 1:
                    status_roll = self.rng.random()
                    paid, paid_at = (requested, due - timedelta(days=self.rng.randint(5, 45))) if status_roll < 0.7 else (
                        (requested * Decimal(self.rng.choice([30, 40, 50, 60])) / 100).quantize(Decimal('0.001')), None
                    ) if status_roll < 0.9 else (Decimal('0.000'), None)
                else:
                    status_roll = self.rng.random()
                    paid, paid_at = (requested, due - timedelta(days=self.rng.randint(0, 10))) if status_roll < 0.2 else (
                        (requested * Decimal(self.rng.choice([20, 30, 50])) / 100).quantize(Decimal('0.001')), None
                    ) if status_roll < 0.5 else (Decimal('0.000'), None)

                PaymentTranche.objects.create(
                    enrollment=enrollment,
                    label=f"Tranche {order}",
                    description=f"Échéance {due:%d/%m/%Y}",
                    school_fees=share,
                    other_fees=other_share,
                    amount_requested=requested,
                    amount_paid=paid,
                    due_date=due,
                    paid_at=paid_at,
                    order=order,
                    is_bank_validated=(
                        enrollment.payment_method in ('cheque', 'traite') and paid > 0 and self.rng.random() < 0.8
                    ),
                )
                created += 1
        self.stdout.write(f"Tranches de paiement : {created} créées.")

    # ---------- Services annexes ----------
    def fill_extra_services(self):
        created = 0
        for enrollment in StudentEnrollment.objects.filter(is_active=True):
            existing_types = set(enrollment.extra_services.values_list('service_type', flat=True))
            if 'cantine' not in existing_types and self.rng.random() < 0.4:
                ExtraService.objects.create(
                    enrollment=enrollment, service_type='cantine',
                    monthly_fee=Decimal(self.rng.choice([70, 80, 90, 100])),
                    notes=self.rng.choice(['', '', 'Sans porc', 'Allergie arachides']),
                )
                created += 1
            if 'transport' not in existing_types and self.rng.random() < 0.3:
                ExtraService.objects.create(
                    enrollment=enrollment, service_type='transport',
                    monthly_fee=Decimal(self.rng.choice([60, 75, 90])),
                    notes=self.rng.choice(['', '', 'Arrêt Avenue Habib Bourguiba', 'Arrêt Centre Ville']),
                )
                created += 1
        self.stdout.write(f"Services annexes : {created} créés.")

    # ---------- Documents ----------
    def fill_documents(self):
        students = list(CustomUser.objects.filter(role='student'))
        if not students:
            return
        doc_types = [c[0] for c in DocumentRequest.TYPE_CHOICES]
        statuses = [c[0] for c in DocumentRequest.STATUS_CHOICES]
        weights = [20, 15, 15, 40, 10]
        notes_choices = ['', '', 'Urgent svp', 'Pour dossier de bourse', 'Pour inscription à l\'université']

        target = 35
        current = DocumentRequest.objects.count()
        created = 0
        while current + created < target:
            DocumentRequest.objects.create(
                student=self.rng.choice(students),
                doc_type=self.rng.choice(doc_types),
                status=self.rng.choices(statuses, weights=weights)[0],
                notes=self.rng.choice(notes_choices),
            )
            created += 1
        self.stdout.write(f"Demandes de documents : {created} créées.")

    # ---------- Actualités ----------
    def fill_news(self):
        articles = [
            ("Rentrée scolaire 2026-2027",
             "La rentrée des classes aura lieu le 15 septembre 2026. Les élèves sont attendus à 8h00 "
             "dans leurs classes respectives. La liste des fournitures scolaires est disponible auprès "
             "du secrétariat."),
            ("Réunion parents-enseignants du premier semestre",
             "Une réunion générale parents-enseignants se tiendra le 10 janvier 2027 à partir de 15h00. "
             "Elle sera l'occasion de faire le point sur les résultats du premier semestre."),
            ("Calendrier des examens du premier semestre",
             "Les examens du premier semestre se dérouleront du 7 au 18 décembre 2026. Le planning "
             "détaillé par classe sera communiqué prochainement."),
            ("Journée culturelle et sportive",
             "L'établissement organise sa journée culturelle et sportive annuelle le 20 avril 2027. "
             "Au programme : compétitions sportives, expositions et spectacles préparés par les élèves."),
            ("Vacances de la Toussaint",
             "Les vacances de la Toussaint débuteront le 26 octobre 2026 et se termineront le 1er "
             "novembre 2026. Reprise des cours le 2 novembre 2026."),
            ("Nouveaux horaires de la cantine scolaire",
             "À partir du mois d'octobre, le service de cantine sera disponible de 11h30 à 13h30. "
             "Merci de vous inscrire auprès du secrétariat administratif."),
            ("Mise en place du service de transport scolaire",
             "Un service de transport scolaire est désormais disponible sur plusieurs lignes de la ville. "
             "Les familles intéressées peuvent s'inscrire via l'espace Documents/Services de la plateforme."),
            ("Résultats du premier semestre disponibles",
             "Les bulletins du premier semestre sont désormais consultables dans l'espace élève, "
             "rubrique Résultats."),
        ]
        created = 0
        for title, content in articles:
            _, was_created = News.objects.get_or_create(
                title=title,
                defaults={'content': content, 'created_by': self.admin, 'is_public': True},
            )
            created += int(was_created)
        self.stdout.write(f"Actualités : {created} créées.")

    # ---------- Suggestions ----------
    def fill_suggestions(self):
        students = list(CustomUser.objects.filter(role='student'))
        parents = list(CustomUser.objects.filter(role='parent'))
        pool = students + parents
        samples = [
            ('administration', 'Horaires', "Serait-il possible d'ouvrir le secrétariat plus tôt le matin ?"),
            ('administration', 'Communication', "Pourriez-vous envoyer les convocations par SMS en plus de l'application ?"),
            ('enseignement', 'Soutien scolaire', "Des séances de soutien en mathématiques seraient très utiles avant les examens."),
            ('enseignement', 'Ressources', "Serait-il possible de partager les supports de cours en ligne ?"),
            ('clubs', 'Club scientifique', "Nous aimerions créer un club de robotique l'année prochaine."),
            ('clubs', 'Club théâtre', "Merci d'envisager plus de créneaux pour le club de théâtre."),
            ('infrastructure', 'Cour de récréation', "La cour de récréation manque d'ombre en été, des arbres seraient bienvenus."),
            ('infrastructure', 'Sanitaires', "Les sanitaires du bâtiment B mériteraient une rénovation."),
            ('infrastructure', 'Wifi', "Un accès wifi pour les élèves faciliterait les recherches en classe."),
            ('administration', 'Cantine', "Un menu végétarien en option serait apprécié par certaines familles."),
            ('enseignement', 'Devoirs', "Pourrait-on limiter le nombre de devoirs le week-end ?"),
            ('clubs', 'Sport', "Plus de créneaux de basket seraient les bienvenus après les cours."),
        ]
        created = 0
        for category, subcategory, content in samples:
            sender = self.rng.choice(pool) if pool and self.rng.random() < 0.6 else None
            is_anonymous = sender is None or self.rng.random() < 0.4
            _, was_created = Suggestion.objects.get_or_create(
                category=category, subcategory=subcategory, content=content,
                defaults={
                    'sender': None if is_anonymous else sender,
                    'is_anonymous': is_anonymous,
                    'is_treated': self.rng.random() < 0.4,
                },
            )
            created += int(was_created)
        self.stdout.write(f"Suggestions : {created} créées.")

    # ---------- Rendez-vous ----------
    def fill_appointments(self):
        parents = list(CustomUser.objects.filter(role='parent'))
        if not parents:
            return
        reasons = [
            "Discuter des résultats du premier semestre.",
            "Question sur l'orientation de mon enfant.",
            "Absences répétées à clarifier.",
            "Suivi du comportement en classe.",
            "Question sur les frais de scolarité.",
            "Demande d'information sur le transport scolaire.",
        ]
        target = 12
        current = AppointmentRequest.objects.count()
        created = 0
        now = timezone.now()
        while current + created < target:
            offset_days = self.rng.randint(-20, 40)
            dt = (now + timedelta(days=offset_days)).replace(
                hour=self.rng.choice([9, 10, 11, 14, 15, 16]), minute=self.rng.choice([0, 30]),
                second=0, microsecond=0,
            )
            status = self.rng.choices(
                [AppointmentRequest.STATUS_PENDING, AppointmentRequest.STATUS_ACCEPTED, AppointmentRequest.STATUS_REJECTED],
                weights=[40, 45, 15],
            )[0]
            reviewed = status != AppointmentRequest.STATUS_PENDING
            AppointmentRequest.objects.create(
                parent=self.rng.choice(parents),
                requested_datetime=dt,
                reason=self.rng.choice(reasons),
                status=status,
                reviewed_by=self.admin if reviewed else None,
                reviewed_at=now if reviewed else None,
            )
            created += 1
        self.stdout.write(f"Rendez-vous : {created} créés.")

    # ---------- Événements ----------
    def fill_events(self):
        events = [
            ("Vacances de la Toussaint", 'vacances', date(2026, 10, 26), date(2026, 11, 1), ''),
            ("Examens du 1er semestre", 'examen', date(2026, 12, 7), date(2026, 12, 18), ''),
            ("Vacances d'hiver", 'vacances', date(2026, 12, 21), date(2027, 1, 4), ''),
            ("Réunion parents-enseignants (S1)", 'reunion', date(2027, 1, 10), None, ''),
            ("Vacances de printemps", 'vacances', date(2027, 3, 1), date(2027, 3, 8), ''),
            ("Examens du 2e semestre", 'examen', date(2027, 3, 22), date(2027, 4, 1), ''),
            ("Journée culturelle et sportive", 'sortie', date(2027, 4, 20), None, ''),
            ("Sortie pédagogique au musée", 'sortie', date(2027, 5, 12), None, ''),
            ("Examens du 3e trimestre", 'examen', date(2027, 6, 7), date(2027, 6, 18), ''),
            ("Conseils de classe de fin d'année", 'reunion', date(2027, 6, 22), date(2027, 6, 25), ''),
            ("Fête de fin d'année", 'sortie', date(2027, 6, 28), None, ''),
        ]
        created = 0
        for title, event_type, start, end, desc in events:
            _, was_created = SchoolEvent.objects.get_or_create(
                title=title, start_date=start,
                defaults={
                    'event_type': event_type, 'end_date': end,
                    'description': desc, 'created_by': self.admin,
                },
            )
            created += int(was_created)
        self.stdout.write(f"Événements : {created} créés.")

    # ---------- Cahier de textes ----------
    def fill_lessons(self):
        content_templates = [
            "Cours magistral : introduction et rappels du chapitre précédent.",
            "Correction collective des exercices de la séance précédente.",
            "Travaux dirigés en petits groupes.",
            "Contrôle continu sur les notions vues en cours.",
            "Étude de cas et application pratique.",
            "Présentation orale des élèves sur le thème du chapitre.",
            "Synthèse et évaluation des acquis du chapitre.",
        ]
        homework_templates = [
            "Exercices d'application à préparer pour la prochaine séance.",
            "Réviser le chapitre en vue du prochain contrôle.",
            "Rédiger une courte synthèse du cours.",
            "", "",
        ]
        semesters_by_classroom = {}
        for s in Semester.objects.all():
            semesters_by_classroom.setdefault(s.classroom_id, []).append(s)

        created = 0
        from academics.models import Subject
        for subject in Subject.objects.select_related('classroom', 'teacher'):
            entries = list(ScheduleEntry.objects.filter(classroom=subject.classroom, subject=subject))
            weekdays = [e.day for e in entries] or [0, 2, 4]
            semesters = semesters_by_classroom.get(subject.classroom_id, [])
            sessions_per_semester = {sem: (3 if sem.label == 'S1' else 2) for sem in semesters}
            for semester, count in sessions_per_semester.items():
                span = (semester.end_date - semester.start_date).days
                for _ in range(count):
                    weekday = self.rng.choice(weekdays)
                    candidate_dates = [
                        semester.start_date + timedelta(days=d)
                        for d in range(span + 1)
                    ]
                    candidate_dates = [d for d in candidate_dates if d.weekday() == weekday]
                    if not candidate_dates:
                        continue
                    lesson_date = self.rng.choice(candidate_dates)
                    homework = self.rng.choice(homework_templates)
                    _, was_created = LessonEntry.objects.get_or_create(
                        subject=subject, date=lesson_date,
                        defaults={
                            'classroom': subject.classroom,
                            'teacher': subject.teacher,
                            'content': self.rng.choice(content_templates),
                            'homework': homework,
                            'homework_due': (lesson_date + timedelta(days=7)) if homework else None,
                        },
                    )
                    created += int(was_created)
        self.stdout.write(f"Cahier de textes : {created} entrées créées.")

    # ---------- Notes de suivi ----------
    def fill_student_notes(self):
        enrollments = list(StudentEnrollment.objects.filter(is_active=True, classroom__isnull=False))
        if not enrollments:
            return
        obs_templates = [
            "Bonne participation en classe.",
            "Élève sérieux et appliqué ce trimestre.",
            "Progrès notables en classe ce mois-ci.",
            "Bon esprit d'équipe lors des travaux de groupe.",
            "Attitude respectueuse envers les camarades.",
        ]
        pun_templates = [
            "Bavardages répétés pendant le cours.",
            "Retard non justifié à plusieurs reprises.",
            "Devoirs non rendus dans les délais.",
            "Comportement perturbateur en classe.",
        ]
        target = 25
        current = StudentNote.objects.count()
        created = 0
        while current + created < target:
            enrollment = self.rng.choice(enrollments)
            subjects = list(enrollment.classroom.subjects.all())
            subject = self.rng.choice(subjects) if subjects else None
            note_type = self.rng.choices(
                [StudentNote.TYPE_OBSERVATION, StudentNote.TYPE_PUNITION], weights=[70, 30]
            )[0]
            content = self.rng.choice(
                obs_templates if note_type == StudentNote.TYPE_OBSERVATION else pun_templates
            )
            note_date = date(2026, 9, 15) + timedelta(days=self.rng.randint(0, 280))
            StudentNote.objects.create(
                classroom=enrollment.classroom,
                student=enrollment,
                teacher=subject.teacher if subject else None,
                subject=subject,
                note_type=note_type,
                content=content,
                date=note_date,
            )
            created += 1
        self.stdout.write(f"Notes de suivi : {created} créées.")
