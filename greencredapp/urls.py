from django.urls import path
from . import views

# Frontend page routes
urlpatterns = [
    path('', views.feed_view, name='feed'),
    path('login/', views.login_view, name='login'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('challenges/', views.challenges_view, name='challenges'),
    path('profile/', views.profile_view, name='profile'),
    path('badges/', views.badges_view, name='badges'),
    path('seed/', views.seed_view, name='seed'),
]
