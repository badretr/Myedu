from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Infos supplémentaires', {'fields': ('role', 'phone', 'address', 'profile_picture', 'date_of_birth', 'nationality')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Infos supplémentaires', {'fields': ('role', 'first_name', 'last_name', 'email', 'phone')}),
    )
