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
