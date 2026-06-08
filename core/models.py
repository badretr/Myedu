from django.db import models
from accounts.models import CustomUser


class News(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Actualité'
        verbose_name_plural = 'Actualités'

    def __str__(self):
        return self.title


class Message(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    sender = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    # NULL classroom = sent to all
    classroom = models.ForeignKey('academics.Classroom', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='messages')
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(CustomUser, blank=True, related_name='read_messages')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return self.title

    def is_read_by(self, user):
        return self.read_by.filter(pk=user.pk).exists()


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
