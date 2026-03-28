"""
Business logic helpers for GreenCred.
"""

from datetime import date

CREDITS_MAP = {
    'tree_planting': 30,
    'cleanup': 25,
    'upcycling': 20,
    'transport': 15,
    'energy': 10,
    'advocacy': 10,
}

RANK_THRESHOLDS = [
    (5001, 'Earth Guardian'),
    (2001, 'Ecosystem Builder'),
    (501, 'Grove Keeper'),
    (101, 'Sprout'),
    (0, 'Seedling'),
]

ALL_BADGES = [
    {'badge_id': 'first_seed', 'name': 'First Seed', 'emoji': '🌱',
     'description': 'Logged your very first eco action', 'criteria': 'Log 1 action',
     'category': 'milestone'},
    {'badge_id': 'tree_champion', 'name': 'Tree Champion', 'emoji': '🌳',
     'description': 'Planted 5 or more trees', 'criteria': 'Plant 5 trees',
     'category': 'action'},
    {'badge_id': 'clean_streets', 'name': 'Clean Streets', 'emoji': '🧹',
     'description': 'Completed 3 cleanup drives', 'criteria': 'Complete 3 cleanups',
     'category': 'action'},
    {'badge_id': 'week_warrior', 'name': 'Week Warrior', 'emoji': '🔥',
     'description': 'Maintained a 7-day action streak', 'criteria': '7-day streak',
     'category': 'streak'},
    {'badge_id': 'earth_guardian', 'name': 'Earth Guardian', 'emoji': '🌍',
     'description': 'Earned 5000+ GreenCredits', 'criteria': 'Earn 5000 GC',
     'category': 'credits'},
    {'badge_id': 'challenge_done', 'name': 'Challenge Accepted', 'emoji': '🏆',
     'description': 'Completed your first challenge', 'criteria': 'Complete 1 challenge',
     'category': 'challenge'},
    {'badge_id': 'pioneer', 'name': 'Pioneer', 'emoji': '⭐',
     'description': 'One of the early GreenCred adopters', 'criteria': 'Join early',
     'category': 'milestone'},
    {'badge_id': 'crew_player', 'name': 'Crew Player', 'emoji': '🤝',
     'description': 'Joined 3 or more challenges', 'criteria': 'Join 3 challenges',
     'category': 'challenge'},
]


def calculate_rank(credits):
    for threshold, rank in RANK_THRESHOLDS:
        if credits >= threshold:
            return rank
    return 'Seedling'


def calculate_credits(action_type, streak):
    base = CREDITS_MAP.get(action_type, 10)
    if streak >= 90:
        multiplier = 1.5
    elif streak >= 30:
        multiplier = 1.25
    elif streak >= 7:
        multiplier = 1.1
    else:
        multiplier = 1.0
    return int(base * multiplier)


def update_streak(user):
    today = date.today()
    if user.last_action_date is None:
        user.streak = 1
    elif user.last_action_date == today:
        pass  # Already logged today
    elif (today - user.last_action_date).days == 1:
        user.streak += 1
    else:
        user.streak = 1
    user.last_action_date = today


def check_and_award_badges(user):
    newly_awarded = []
    current_badges = list(user.badges) if user.badges else []

    badge_checks = [
        ('first_seed', user.total_actions >= 1),
        ('tree_champion', user.trees_planted >= 5),
        ('clean_streets', user.cleanups_done >= 3),
        ('week_warrior', user.streak >= 7),
        ('earth_guardian', user.green_credits >= 5000),
        ('challenge_done', user.challenges_completed >= 1),
        ('crew_player', user.joined_challenges.count() >= 3),
    ]

    for badge_id, condition in badge_checks:
        if condition and badge_id not in current_badges:
            current_badges.append(badge_id)
            newly_awarded.append(badge_id)

    user.badges = current_badges
    return newly_awarded
