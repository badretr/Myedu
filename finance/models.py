from django.db import models
from academics.models import StudentEnrollment


class PaymentTranche(models.Model):
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name="tranches")
    label = models.CharField(max_length=50)       # "TRANCHE 1"
    description = models.CharField(max_length=100, blank=True)  # "Avant 01/09"
    school_fees = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    other_fees = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    reduction_rate = models.FloatField(default=0)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateField(null=True, blank=True)
    order = models.IntegerField(default=1)
    is_bank_validated = models.BooleanField(
        default=False,
        verbose_name='Chèque/traite validé par la banque',
    )
    reminder_sent = models.BooleanField(default=False, verbose_name='Rappel envoyé au parent')

    class Meta:
        ordering = ["order"]
        verbose_name = "Tranche de paiement"

    def __str__(self):
        return f"{self.enrollment.student.get_full_name()} - {self.label}"

    @property
    def remaining(self):
        return self.amount_requested - self.amount_paid

    @property
    def is_paid(self):
        return self.remaining <= 0


class ExtraService(models.Model):
    """Services annexes : cantine, transport scolaire…"""
    SERVICE_CHOICES = [
        ('cantine', 'Cantine'),
        ('transport', 'Transport scolaire'),
    ]
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='extra_services')
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES, verbose_name='Service')
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='Tarif mensuel')
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    notes = models.CharField(max_length=200, blank=True, verbose_name='Remarques (arrêt de bus, régime…)')
    started_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('enrollment', 'service_type')
        verbose_name = 'Service annexe'
        verbose_name_plural = 'Services annexes'

    def __str__(self):
        return f"{self.enrollment.student.get_full_name()} - {self.get_service_type_display()}"


class AuthorizedPickupPerson(models.Model):
    """Personne autorisée à récupérer l'élève, en plus des parents (transport/sortie)."""
    RELATIONSHIP_CHOICES = [
        ('grand_parent', 'Grand-parent'),
        ('oncle_tante', 'Oncle / Tante'),
        ('frere_soeur', 'Frère / Sœur majeur(e)'),
        ('nounou', 'Nourrice / Garde d\'enfant'),
        ('autre', 'Autre'),
    ]
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='pickup_persons')
    full_name = models.CharField(max_length=100, verbose_name='Nom complet')
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='autre', verbose_name='Lien avec l\'élève')
    phone_number = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    id_card_number = models.CharField(max_length=30, blank=True, verbose_name='N° CIN')
    is_active = models.BooleanField(default=True, verbose_name='Autorisation active')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Personne autorisée à récupérer l\'élève'
        verbose_name_plural = 'Personnes autorisées à récupérer l\'élève'

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()}) - {self.enrollment.student.get_full_name()}"
