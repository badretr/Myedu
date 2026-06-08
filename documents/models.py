from django.db import models
from accounts.models import CustomUser


class DocumentRequest(models.Model):
    TYPE_CHOICES = [
        ("carte_etudiant", "Carte d'etudiant"),
        ("cert_inscription", "Certificat d'inscription"),
        ("attest_presence", "Attestation de presence"),
        ("attest_reussite", "Attestation de reussite"),
        ("releve_notes", "Releve des notes"),
    ]
    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("processing", "En traitement"),
        ("ready", "Pret"),
        ("delivered", "Livré"),
        ("rejected", "Rejeté"),
    ]
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="document_requests")
    doc_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande de document"

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.get_doc_type_display()}"
