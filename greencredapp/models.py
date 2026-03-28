import os
from django.db import models
from django.core.files.storage import FileSystemStorage


def _get_image_storage():
    """Return CloudinaryStorage in production, FileSystemStorage locally."""
    if os.environ.get('CLOUDINARY_CLOUD_NAME'):
        try:
            from cloudinary_storage.storage import MediaCloudinaryStorage
            return MediaCloudinaryStorage()
        except ImportError:
            pass
    return FileSystemStorage()


class UserProfile(models.Model):
    firebase_uid = models.CharField(max_length=128, unique=True)
    display_name = models.CharField(max_length=100)
    email = models.EmailField()
    photo_url = models.URLField(blank=True)
    green_credits = models.IntegerField(default=0)
    rank = models.CharField(max_length=50, default='Seedling')
    streak = models.IntegerField(default=0)
    last_action_date = models.DateField(null=True, blank=True)
    badges = models.JSONField(default=list)
    total_actions = models.IntegerField(default=0)
    trees_planted = models.IntegerField(default=0)
    cleanups_done = models.IntegerField(default=0)
    challenges_completed = models.IntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.display_name} ({self.firebase_uid})"

    class Meta:
        ordering = ['-green_credits']


class Badge(models.Model):
    badge_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    emoji = models.CharField(max_length=10)
    description = models.CharField(max_length=200)
    criteria = models.CharField(max_length=200)
    category = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.emoji} {self.name}"


class Challenge(models.Model):
    TYPES = [
        ('Open', 'Open'),
        ('Local', 'Local'),
        ('Corporate', 'Corporate'),
        ('Campus', 'Campus'),
    ]
    ACTION_TYPES = [
        ('tree_planting', 'Tree Planting'),
        ('cleanup', 'Clean-up Drive'),
        ('upcycling', 'Upcycling / Repair'),
        ('transport', 'Sustainable Transport'),
        ('energy', 'Energy / Water Saving'),
        ('advocacy', 'Community Advocacy'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=20, choices=TYPES)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    target_count = models.IntegerField()
    current_count = models.IntegerField(default=0)
    location = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='created_challenges')
    participants = models.ManyToManyField(UserProfile, related_name='joined_challenges', blank=True)
    badge_reward = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class Action(models.Model):
    ACTION_TYPES = [
        ('tree_planting', 'Tree Planting'),
        ('cleanup', 'Clean-up Drive'),
        ('upcycling', 'Upcycling / Repair'),
        ('transport', 'Sustainable Transport'),
        ('energy', 'Energy / Water Saving'),
        ('advocacy', 'Community Advocacy'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    location = models.CharField(max_length=200)
    image = models.ImageField(
        upload_to='greencred/actions/',
        storage=_get_image_storage,
        blank=True,
        null=True,
    )
    image_url = models.URLField(blank=True)  # For seeded Unsplash URLs
    credits_earned = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    liked_by = models.JSONField(default=list)
    challenge = models.ForeignKey(Challenge, null=True, blank=True, on_delete=models.SET_NULL, related_name='actions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.display_name} - {self.action_type}"

    class Meta:
        ordering = ['-created_at']
