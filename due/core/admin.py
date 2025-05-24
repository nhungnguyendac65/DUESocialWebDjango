# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import ActivityLog, CustomUser, Post, Comment, Like, Bookmark, Event, EventTag, Report, Profile, Follow, ChatGroup, Message, BlockedUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('avatar', 'phone_number', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('avatar', 'phone_number', 'role', 'email')}),
    )
admin.site.register(ActivityLog)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Profile)
admin.site.register(Post)
admin.site.register(Comment)

