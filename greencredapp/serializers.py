from rest_framework import serializers
from .models import UserProfile, Action, Challenge, Badge


class UserProfileSerializer(serializers.ModelSerializer):
    joined_challenges_count = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'firebase_uid', 'display_name', 'email', 'photo_url',
            'green_credits', 'rank', 'streak', 'last_action_date',
            'badges', 'total_actions', 'trees_planted', 'cleanups_done',
            'challenges_completed', 'joined_challenges_count', 'joined_at'
        ]

    def get_joined_challenges_count(self, obj):
        return obj.joined_challenges.count()


class UserProfileMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'firebase_uid', 'display_name', 'photo_url', 'rank', 'green_credits', 'streak']


class BadgeSerializer(serializers.ModelSerializer):
    earners = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ['id', 'badge_id', 'name', 'emoji', 'description', 'criteria', 'category', 'earners']

    def get_earners(self, obj):
        # SQLite doesn't support JSONField contains lookup — filter in Python
        all_users = UserProfile.objects.all()
        earners = [u for u in all_users if obj.badge_id in (u.badges or [])]
        return UserProfileMiniSerializer(earners, many=True).data


class ChallengeSerializer(serializers.ModelSerializer):
    created_by = UserProfileMiniSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'description', 'challenge_type', 'action_type',
            'target_count', 'current_count', 'location', 'start_date',
            'end_date', 'created_by', 'participants_count', 'badge_reward',
            'status', 'is_joined', 'days_left', 'progress_percent', 'created_at'
        ]

    def get_participants_count(self, obj):
        return obj.participants.count()

    def get_is_joined(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user_profile') and request.user_profile:
            return obj.participants.filter(id=request.user_profile.id).exists()
        return False

    def get_days_left(self, obj):
        from datetime import date
        today = date.today()
        delta = obj.end_date - today
        return max(0, delta.days)

    def get_progress_percent(self, obj):
        if obj.target_count == 0:
            return 0
        return min(100, round((obj.current_count / obj.target_count) * 100))


class ActionSerializer(serializers.ModelSerializer):
    user = UserProfileMiniSerializer(read_only=True)
    challenge_title = serializers.SerializerMethodField()
    image_display_url = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Action
        fields = [
            'id', 'user', 'action_type', 'description', 'location',
            'image', 'image_url', 'image_display_url', 'credits_earned',
            'likes', 'liked_by', 'challenge', 'challenge_title',
            'is_liked', 'time_ago', 'created_at'
        ]
        read_only_fields = ['credits_earned', 'likes', 'liked_by', 'created_at']

    def get_challenge_title(self, obj):
        if obj.challenge:
            return obj.challenge.title
        return None

    def get_image_display_url(self, obj):
        import os
        if obj.image:
            url = obj.image.url
            # Cloudinary URLs are already absolute; add auto optimization transform
            if os.environ.get('CLOUDINARY_CLOUD_NAME') and 'res.cloudinary.com' in url:
                # Insert transformation: auto format, auto quality, fill crop 800x400
                parts = url.split('/upload/')
                if len(parts) == 2:
                    url = f"{parts[0]}/upload/c_fill,w_800,h_400,q_auto,f_auto/{parts[1]}"
            else:
                # Local dev: build absolute URI from request
                request = self.context.get('request')
                if request:
                    url = request.build_absolute_uri(url)
            return url
        if obj.image_url:
            return obj.image_url
        return None

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user_profile') and request.user_profile:
            return str(request.user_profile.firebase_uid) in obj.liked_by
        return False

    def get_time_ago(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        seconds = diff.total_seconds()
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            return f"{int(seconds // 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h ago"
        elif seconds < 604800:
            return f"{int(seconds // 86400)}d ago"
        else:
            return f"{int(seconds // 604800)}w ago"


class ActionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['action_type', 'description', 'location', 'image', 'image_url', 'challenge']
