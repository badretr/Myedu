from django.db import models
from accounts.models import CustomUser


class News(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Actualite'
        verbose_name_plural = 'Actualites'

    def __str__(self):
        return self.title


class Message(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    sender = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    classroom = models.ForeignKey('academics.Classroom', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='messages')
    recipient = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='received_messages',
                                   verbose_name='Parent destinataire')
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='replies', verbose_name='Réponse à')
    about_student = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='messages_about', verbose_name="Concernant l'élève")
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(CustomUser, blank=True, related_name='read_messages')
    deleted_by = models.ManyToManyField(CustomUser, blank=True, related_name='deleted_messages')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return self.title

    def is_read_by(self, user):
        return self.read_by.filter(pk=user.pk).exists()


class Notification(models.Model):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    target_url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.recipient.get_full_name()} - {self.title}"


class Suggestion(models.Model):
    CATEGORY_CHOICES = [
        ('administration', 'Administration'),
        ('enseignement', 'Enseignement'),
        ('clubs', 'Clubs'),
        ('infrastructure', 'Infrastructure'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    sender = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_treated = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Suggestion'

    def __str__(self):
        return f"{self.category} - {self.created_at.date()}"


class AppointmentRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_ACCEPTED, 'Accepté'),
        (STATUS_REJECTED, 'Refusé'),
    ]

    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointment_requests')
    requested_datetime = models.DateTimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_appointments')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Rendez-vous'
        verbose_name_plural = 'Rendez-vous'

    def __str__(self):
        return f"{self.parent.get_full_name()} - {self.requested_datetime:%d/%m/%Y %H:%M}"


class SchoolEvent(models.Model):
    TYPE_CHOICES = [
        ('vacances', 'Vacances'),
        ('examen', 'Examens'),
        ('reunion', 'Réunion parents-enseignants'),
        ('sortie', 'Sortie scolaire'),
        ('autre', 'Autre'),
    ]
    title = models.CharField(max_length=200, verbose_name='Titre')
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre', verbose_name='Type')
    start_date = models.DateField(verbose_name='Date de début')
    end_date = models.DateField(null=True, blank=True, verbose_name='Date de fin')
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='events_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']
        verbose_name = 'Événement'
        verbose_name_plural = 'Événements'

    def __str__(self):
        return f"{self.title} ({self.start_date:%d/%m/%Y})"
