from django.urls import path
from . import views

# API endpoints
urlpatterns = [
    # Auth
    path('auth/firebase/', views.auth_firebase, name='api_auth_firebase'),

    # Users
    path('users/', views.users_list, name='api_users_list'),
    path('users/<str:uid>/', views.user_detail, name='api_user_detail'),

    # Actions
    path('actions/', views.actions_list, name='api_actions_list'),
    path('actions/<int:action_id>/like/', views.action_like, name='api_action_like'),

    # Challenges
    path('challenges/', views.challenges_list, name='api_challenges_list'),
    path('challenges/<int:challenge_id>/', views.challenge_detail, name='api_challenge_detail'),
    path('challenges/<int:challenge_id>/join/', views.challenge_join, name='api_challenge_join'),

    # Badges
    path('badges/', views.badges_list, name='api_badges_list'),
    path('badges/<str:badge_id>/', views.badge_detail, name='api_badge_detail'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='api_leaderboard'),

    # Seed
    path('seed/', views.seed, name='api_seed'),
]
