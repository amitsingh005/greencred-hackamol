from django.conf import settings


class FirebaseAuthMiddleware:
    """
    Middleware to verify Firebase ID tokens and attach UserProfile to request.
    If Firebase is not configured, falls back to demo mode using X-Demo-UID header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user_profile = None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]

            if getattr(settings, 'FIREBASE_ENABLED', False):
                try:
                    from firebase_admin import auth as firebase_auth
                    decoded = firebase_auth.verify_id_token(token)
                    uid = decoded['uid']
                    from greencredapp.models import UserProfile
                    try:
                        request.user_profile = UserProfile.objects.get(firebase_uid=uid)
                    except UserProfile.DoesNotExist:
                        pass
                except Exception:
                    pass
            else:
                # Demo mode: treat token as firebase_uid directly
                from greencredapp.models import UserProfile
                try:
                    request.user_profile = UserProfile.objects.get(firebase_uid=token)
                except UserProfile.DoesNotExist:
                    pass

        # Fallback: X-Demo-UID header for development/demo
        demo_uid = request.META.get('HTTP_X_DEMO_UID', '')
        if demo_uid and not request.user_profile:
            from greencredapp.models import UserProfile
            try:
                request.user_profile = UserProfile.objects.get(firebase_uid=demo_uid)
            except UserProfile.DoesNotExist:
                pass

        response = self.get_response(request)
        return response
