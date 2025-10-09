# store/utils.py
from django.contrib.sessions.models import Session

def get_or_create_session_key(request):
    """
    Get the current session key, or create one if it doesn't exist.
    Useful for cart and wishlist tracking for guest users.
    """
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key
