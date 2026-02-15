from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User
# Register your models here.

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'first_name', 'last_name',
        'is_staff', 'date_joined'
    ]
    list_filter = [
        'is_staff', 'is_active', 'date_joined'
    ]
    search_fields = [
        'email', 'first_name', 'last_name',
    ]
    ordering = [
        '-date_joined'
    ]

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('personal information', {'fields': ('first_name', 'last_name', 'avatar')}),
        ('access rights', {'fields': ('is_active', 'is_staff')}),
        ('important dates', {'fields': ('date_joined',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fileds': ('email', 'first_name', 'last_name', 'password1', 'password2')
        })
    )