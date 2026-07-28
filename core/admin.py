from django.contrib import admin
from .models import News, Message, Suggestion, AppointmentRequest, SchoolEvent, Notification


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'sender', 'recipient', 'about_student', 'classroom', 'created_at')
    list_filter = ('created_at', 'classroom')
    search_fields = ('title', 'content', 'sender__username', 'recipient__username')


admin.site.register(News)
admin.site.register(Suggestion)
admin.site.register(AppointmentRequest)
admin.site.register(SchoolEvent)
admin.site.register(Notification)
