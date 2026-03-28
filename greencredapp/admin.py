from django.contrib import admin
from .models import UserProfile, Action, Challenge, Badge


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'email', 'green_credits', 'rank', 'streak', 'total_actions']
    search_fields = ['display_name', 'email', 'firebase_uid']
    list_filter = ['rank']
    ordering = ['-green_credits']


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'credits_earned', 'likes', 'location', 'created_at']
    list_filter = ['action_type']
    search_fields = ['user__display_name', 'description', 'location']
    ordering = ['-created_at']


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'challenge_type', 'current_count', 'target_count', 'status', 'end_date']
    list_filter = ['challenge_type', 'status']
    search_fields = ['title', 'location']


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['emoji', 'name', 'badge_id', 'category', 'criteria']
    list_filter = ['category']
