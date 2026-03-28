import json
from datetime import date, timedelta

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import UserProfile, Action, Challenge, Badge
from .serializers import (
    UserProfileSerializer, ActionSerializer, ActionCreateSerializer,
    ChallengeSerializer, BadgeSerializer, UserProfileMiniSerializer
)
from .business_logic import (
    calculate_credits, calculate_rank, update_streak,
    check_and_award_badges, ALL_BADGES
)


def require_auth(func):
    """Decorator that requires a valid user_profile on the request."""
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user_profile') or not request.user_profile:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# ─── AUTH ────────────────────────────────────────────────────────────────────

@csrf_exempt
def auth_firebase(request):
    """
    POST /api/auth/firebase/
    Receives Firebase ID token, creates/gets UserProfile, returns user data.
    In demo mode (no Firebase), accepts uid directly in body.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    from django.conf import settings

    if getattr(settings, 'FIREBASE_ENABLED', False):
        token = body.get('token')
        if not token:
            return JsonResponse({'error': 'Token required'}, status=400)
        try:
            from firebase_admin import auth as firebase_auth
            decoded = firebase_auth.verify_id_token(token)
            uid = decoded['uid']
            display_name = decoded.get('name', 'Anonymous')
            email = decoded.get('email', '')
            photo_url = decoded.get('picture', '')
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=401)
    else:
        # Demo mode
        uid = body.get('uid') or body.get('token', 'demo-user')
        display_name = body.get('display_name', 'Demo User')
        email = body.get('email', 'demo@greencred.app')
        photo_url = body.get('photo_url', '')

    user, created = UserProfile.objects.get_or_create(
        firebase_uid=uid,
        defaults={
            'display_name': display_name,
            'email': email,
            'photo_url': photo_url,
        }
    )

    if not created:
        # Update display info if changed
        if display_name and user.display_name != display_name:
            user.display_name = display_name
        if photo_url and user.photo_url != photo_url:
            user.photo_url = photo_url
        user.save()

    return JsonResponse({
        'user': UserProfileSerializer(user).data,
        'created': created
    })


# ─── USERS ────────────────────────────────────────────────────────────────────

def users_list(request):
    """GET /api/users/"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    users = UserProfile.objects.all().order_by('-green_credits')
    return JsonResponse({'users': UserProfileSerializer(users, many=True).data})


@csrf_exempt
def user_detail(request, uid):
    """GET/PUT /api/users/<uid>/"""
    try:
        user = UserProfile.objects.get(firebase_uid=uid)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse({'user': UserProfileSerializer(user).data})

    elif request.method == 'PUT':
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        if 'display_name' in body:
            user.display_name = body['display_name']
            user.save()
        return JsonResponse({'user': UserProfileSerializer(user).data})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── ACTIONS ────────────────────────────────────────────────────────────────

@csrf_exempt
def actions_list(request):
    """GET /api/actions/ or POST /api/actions/"""
    if request.method == 'GET':
        qs = Action.objects.select_related('user', 'challenge').all()

        action_type = request.GET.get('type')
        if action_type:
            qs = qs.filter(action_type=action_type)

        user_uid = request.GET.get('user')
        if user_uid:
            qs = qs.filter(user__firebase_uid=user_uid)

        challenge_id = request.GET.get('challenge')
        if challenge_id:
            qs = qs.filter(challenge_id=challenge_id)

        serializer = ActionSerializer(qs, many=True, context={'request': request})
        return JsonResponse({'actions': serializer.data})

    elif request.method == 'POST':
        if not hasattr(request, 'user_profile') or not request.user_profile:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        user = request.user_profile
        action_type = request.POST.get('action_type')
        description = request.POST.get('description', '')
        location = request.POST.get('location', '')
        challenge_id = request.POST.get('challenge')
        image_url = request.POST.get('image_url', '')

        if not action_type:
            return JsonResponse({'error': 'action_type is required'}, status=400)

        # Calculate credits with streak multiplier
        credits = calculate_credits(action_type, user.streak)

        # Create action
        action = Action(
            user=user,
            action_type=action_type,
            description=description,
            location=location,
            credits_earned=credits,
            image_url=image_url,
        )

        if 'image' in request.FILES:
            action.image = request.FILES['image']

        # Set challenge
        if challenge_id:
            try:
                challenge = Challenge.objects.get(id=challenge_id)
                action.challenge = challenge
                challenge.current_count += 1
                challenge.save()
            except Challenge.DoesNotExist:
                pass

        action.save()

        # Update user stats
        update_streak(user)
        user.green_credits += credits
        user.total_actions += 1
        user.rank = calculate_rank(user.green_credits)

        if action_type == 'tree_planting':
            user.trees_planted += 1
        elif action_type == 'cleanup':
            user.cleanups_done += 1

        # Award badges
        newly_awarded = check_and_award_badges(user)
        user.save()

        serializer = ActionSerializer(action, context={'request': request})
        return JsonResponse({
            'action': serializer.data,
            'credits_earned': credits,
            'new_total_credits': user.green_credits,
            'new_rank': user.rank,
            'new_streak': user.streak,
            'newly_awarded_badges': newly_awarded,
        }, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def action_like(request, action_id):
    """POST /api/actions/<id>/like/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if not hasattr(request, 'user_profile') or not request.user_profile:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        return JsonResponse({'error': 'Action not found'}, status=404)

    user_uid = request.user_profile.firebase_uid
    liked_by = list(action.liked_by)

    if user_uid in liked_by:
        liked_by.remove(user_uid)
        action.likes = max(0, action.likes - 1)
        liked = False
    else:
        liked_by.append(user_uid)
        action.likes += 1
        liked = True

    action.liked_by = liked_by
    action.save()

    return JsonResponse({'likes': action.likes, 'liked': liked})


# ─── CHALLENGES ─────────────────────────────────────────────────────────────

@csrf_exempt
def challenges_list(request):
    """GET /api/challenges/ or POST /api/challenges/"""
    if request.method == 'GET':
        qs = Challenge.objects.select_related('created_by').prefetch_related('participants').all()
        status_filter = request.GET.get('status', 'active')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = ChallengeSerializer(qs, many=True, context={'request': request})
        return JsonResponse({'challenges': serializer.data})

    elif request.method == 'POST':
        if not hasattr(request, 'user_profile') or not request.user_profile:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        user = request.user_profile
        try:
            challenge = Challenge.objects.create(
                title=body.get('title', ''),
                description=body.get('description', ''),
                challenge_type=body.get('challenge_type', 'Open'),
                action_type=body.get('action_type', 'tree_planting'),
                target_count=int(body.get('target_count', 10)),
                location=body.get('location', ''),
                start_date=date.today(),
                end_date=body.get('end_date', str(date.today() + timedelta(days=30))),
                created_by=user,
                badge_reward=body.get('badge_reward', 'challenge_done'),
            )
            serializer = ChallengeSerializer(challenge, context={'request': request})
            return JsonResponse({'challenge': serializer.data}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def challenge_detail(request, challenge_id):
    """GET /api/challenges/<id>/"""
    try:
        challenge = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Challenge not found'}, status=404)

    serializer = ChallengeSerializer(challenge, context={'request': request})
    return JsonResponse({'challenge': serializer.data})


@csrf_exempt
def challenge_join(request, challenge_id):
    """POST /api/challenges/<id>/join/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if not hasattr(request, 'user_profile') or not request.user_profile:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        challenge = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Challenge not found'}, status=404)

    user = request.user_profile
    if challenge.participants.filter(id=user.id).exists():
        challenge.participants.remove(user)
        joined = False
    else:
        challenge.participants.add(user)
        joined = True

    # Check badges after joining
    newly_awarded = check_and_award_badges(user)
    user.save()

    return JsonResponse({
        'joined': joined,
        'participants_count': challenge.participants.count(),
        'newly_awarded_badges': newly_awarded,
    })


# ─── BADGES ─────────────────────────────────────────────────────────────────

def badges_list(request):
    """GET /api/badges/"""
    badges = Badge.objects.all()
    serializer = BadgeSerializer(badges, many=True, context={'request': request})
    return JsonResponse({'badges': serializer.data})


def badge_detail(request, badge_id):
    """GET /api/badges/<badge_id>/"""
    try:
        badge = Badge.objects.get(badge_id=badge_id)
    except Badge.DoesNotExist:
        return JsonResponse({'error': 'Badge not found'}, status=404)

    serializer = BadgeSerializer(badge, context={'request': request})
    return JsonResponse({'badge': serializer.data})


# ─── LEADERBOARD ─────────────────────────────────────────────────────────────

def leaderboard(request):
    """GET /api/leaderboard/?period=all|week"""
    period = request.GET.get('period', 'all')

    if period == 'week':
        # Users who had actions in the last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        user_ids = Action.objects.filter(
            created_at__gte=week_ago
        ).values_list('user_id', flat=True).distinct()

        users = UserProfile.objects.filter(id__in=user_ids).order_by('-green_credits')
    else:
        users = UserProfile.objects.all().order_by('-green_credits')

    current_uid = None
    if hasattr(request, 'user_profile') and request.user_profile:
        current_uid = request.user_profile.firebase_uid

    result = []
    for i, user in enumerate(users, 1):
        data = UserProfileSerializer(user).data
        data['position'] = i
        data['is_current_user'] = (user.firebase_uid == current_uid)
        result.append(data)

    return JsonResponse({'leaderboard': result, 'period': period})


# ─── SEED ─────────────────────────────────────────────────────────────────────

@csrf_exempt
def seed(request):
    """POST /api/seed/ — seed demo data; DELETE /api/seed/ — clear all data"""
    if request.method == 'DELETE':
        Action.objects.all().delete()
        Challenge.objects.all().delete()
        UserProfile.objects.all().delete()
        Badge.objects.all().delete()
        return JsonResponse({'message': 'All data cleared'})

    elif request.method == 'POST':
        log = []

        # ── Step 1: Badges ───────────────────────────────────────────────
        Badge.objects.all().delete()
        for b in ALL_BADGES:
            Badge.objects.create(**b)
        log.append(f"✅ Created {len(ALL_BADGES)} badges")

        # ── Step 2: Users ────────────────────────────────────────────────
        UserProfile.objects.all().delete()

        arjun = UserProfile.objects.create(
            firebase_uid='demo-arjun-sharma',
            display_name='Arjun Sharma',
            email='arjun@greencred.demo',
            photo_url='https://ui-avatars.com/api/?name=Arjun+Sharma&background=166534&color=fff&size=128',
            green_credits=3200,
            rank='Ecosystem Builder',
            streak=14,
            total_actions=28,
            trees_planted=8,
            cleanups_done=5,
            challenges_completed=3,
            badges=['first_seed', 'tree_champion', 'clean_streets', 'week_warrior', 'challenge_done', 'pioneer'],
        )
        log.append("✅ Created user: Arjun Sharma (3200 GC, Ecosystem Builder)")

        priya = UserProfile.objects.create(
            firebase_uid='demo-priya-nair',
            display_name='Priya Nair',
            email='priya@greencred.demo',
            photo_url='https://ui-avatars.com/api/?name=Priya+Nair&background=0d9488&color=fff&size=128',
            green_credits=850,
            rank='Grove Keeper',
            streak=7,
            total_actions=12,
            trees_planted=3,
            cleanups_done=4,
            challenges_completed=1,
            badges=['first_seed', 'clean_streets', 'week_warrior', 'challenge_done'],
        )
        log.append("✅ Created user: Priya Nair (850 GC, Grove Keeper)")

        rohit = UserProfile.objects.create(
            firebase_uid='demo-rohit-verma',
            display_name='Rohit Verma',
            email='rohit@greencred.demo',
            photo_url='https://ui-avatars.com/api/?name=Rohit+Verma&background=4ade80&color=14532d&size=128',
            green_credits=180,
            rank='Sprout',
            streak=3,
            total_actions=6,
            trees_planted=2,
            cleanups_done=1,
            challenges_completed=0,
            badges=['first_seed'],
        )
        log.append("✅ Created user: Rohit Verma (180 GC, Sprout)")

        # ── Step 3: Challenges ───────────────────────────────────────────
        Challenge.objects.all().delete()
        from datetime import timedelta

        c1 = Challenge.objects.create(
            title='Plant 1000 Trees in Delhi 🌳',
            description='Join us to green the capital! Every tree planted counts toward our goal of a greener Delhi.',
            challenge_type='Open',
            action_type='tree_planting',
            target_count=1000,
            current_count=347,
            location='Delhi, India',
            start_date=date.today() - timedelta(days=15),
            end_date=date.today() + timedelta(days=30),
            created_by=arjun,
            badge_reward='tree_champion',
            status='active',
        )
        c1.participants.add(arjun, priya, rohit)
        log.append("✅ Created challenge: Plant 1000 Trees in Delhi (347/1000)")

        c2 = Challenge.objects.create(
            title='Clean the Yamuna River 🧹',
            description='Community cleanup drive along the Yamuna riverbanks. Bring gloves and enthusiasm!',
            challenge_type='Local',
            action_type='cleanup',
            target_count=500,
            current_count=218,
            location='Yamuna River, Delhi',
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
            created_by=priya,
            badge_reward='clean_streets',
            status='active',
        )
        c2.participants.add(priya, arjun)
        log.append("✅ Created challenge: Clean Yamuna River (218/500)")

        c3 = Challenge.objects.create(
            title='NIT Jalandhar Zero Waste Month ♻️',
            description='Campus-wide upcycling and zero-waste challenge. Reduce, reuse, recycle everything!',
            challenge_type='Campus',
            action_type='upcycling',
            target_count=200,
            current_count=89,
            location='NIT Jalandhar, Punjab',
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=20),
            created_by=rohit,
            badge_reward='challenge_done',
            status='active',
        )
        c3.participants.add(rohit, arjun, priya)
        log.append("✅ Created challenge: NIT Jalandhar Zero Waste Month (89/200)")

        # ── Step 4: Actions ──────────────────────────────────────────────
        Action.objects.all().delete()
        actions_data = [
            {
                'user': arjun, 'action_type': 'tree_planting',
                'description': 'Planted 5 mango saplings in the Lodhi Garden as part of the Delhi Green Drive initiative. Amazing community turnout!',
                'location': 'Lodhi Garden, Delhi',
                'image_url': 'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=800',
                'credits_earned': 33, 'likes': 24, 'challenge': c1,
                'liked_by': ['demo-priya-nair', 'demo-rohit-verma'],
            },
            {
                'user': priya, 'action_type': 'cleanup',
                'description': 'Organized a 2-hour riverside cleanup with 15 volunteers. Collected 40kg of plastic waste from the Yamuna bank.',
                'location': 'Yamuna River, Delhi',
                'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800',
                'credits_earned': 25, 'likes': 31, 'challenge': c2,
                'liked_by': ['demo-arjun-sharma'],
            },
            {
                'user': rohit, 'action_type': 'upcycling',
                'description': 'Turned 20 old glass bottles into beautiful planters for the hostel corridor. Zero waste, full creativity!',
                'location': 'NIT Jalandhar, Punjab',
                'image_url': 'https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=800',
                'credits_earned': 20, 'likes': 18, 'challenge': c3,
                'liked_by': ['demo-arjun-sharma', 'demo-priya-nair'],
            },
            {
                'user': arjun, 'action_type': 'transport',
                'description': 'Cycled 12km to work instead of driving. Saved approximately 2.5kg of CO2 emissions today!',
                'location': 'Connaught Place, Delhi',
                'image_url': 'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=800',
                'credits_earned': 15, 'likes': 12,
                'liked_by': ['demo-rohit-verma'],
            },
            {
                'user': priya, 'action_type': 'energy',
                'description': 'Installed solar-powered LED lights in my rooftop garden. Now running 100% on renewable energy!',
                'location': 'Dwarka, Delhi',
                'image_url': 'https://images.unsplash.com/photo-1509391366360-2e959784a276?w=800',
                'credits_earned': 10, 'likes': 22,
                'liked_by': ['demo-arjun-sharma', 'demo-rohit-verma'],
            },
            {
                'user': arjun, 'action_type': 'advocacy',
                'description': 'Conducted an eco-awareness session for 50 students at local school. Distributed saplings and taught composting.',
                'location': 'Chandigarh, Punjab',
                'image_url': 'https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=800',
                'credits_earned': 11, 'likes': 45,
                'liked_by': ['demo-priya-nair', 'demo-rohit-verma'],
            },
            {
                'user': rohit, 'action_type': 'tree_planting',
                'description': 'Planted 3 neem trees near the college gate with classmates. A small step for a greener campus!',
                'location': 'NIT Jalandhar, Punjab',
                'image_url': 'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800',
                'credits_earned': 30, 'likes': 9, 'challenge': c1,
                'liked_by': [],
            },
            {
                'user': priya, 'action_type': 'upcycling',
                'description': 'Repaired 5 broken chairs instead of discarding them. Extended their life by 5+ years — classic upcycling!',
                'location': 'Noida, UP',
                'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800',
                'credits_earned': 20, 'likes': 15,
                'liked_by': ['demo-arjun-sharma'],
            },
            {
                'user': arjun, 'action_type': 'cleanup',
                'description': 'Led a beach-style cleanup at Sukhna Lake. 30+ volunteers, 25kg of trash removed. The lake shines again!',
                'location': 'Sukhna Lake, Chandigarh',
                'image_url': 'https://images.unsplash.com/photo-1621451537084-482c73073a0f?w=800',
                'credits_earned': 25, 'likes': 67, 'challenge': c2,
                'liked_by': ['demo-priya-nair', 'demo-rohit-verma'],
            },
            {
                'user': priya, 'action_type': 'transport',
                'description': 'Organized a carpooling group for our office commute — 6 colleagues, 1 car, 5 less cars off the road daily!',
                'location': 'Gurgaon, Haryana',
                'image_url': 'https://images.unsplash.com/photo-1544620347-c4fd1da5c3e6?w=800',
                'credits_earned': 15, 'likes': 33,
                'liked_by': ['demo-arjun-sharma', 'demo-rohit-verma'],
            },
        ]

        for a_data in actions_data:
            Action.objects.create(**a_data)

        log.append(f"✅ Created {len(actions_data)} demo actions with Unsplash images")
        log.append("🎉 All demo data seeded successfully!")

        return JsonResponse({'log': log, 'success': True})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── PAGE VIEWS ──────────────────────────────────────────────────────────────

from django.shortcuts import render


def login_view(request):
    return render(request, 'login.html')


def feed_view(request):
    return render(request, 'feed.html')


def leaderboard_view(request):
    return render(request, 'leaderboard.html')


def challenges_view(request):
    return render(request, 'challenges.html')


def profile_view(request):
    return render(request, 'profile.html')


def badges_view(request):
    return render(request, 'badges.html')


def seed_view(request):
    return render(request, 'seed.html')
