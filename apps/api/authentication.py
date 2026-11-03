from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import UserSession


class UserSessionAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Token"

    def authenticate(self, request):
        authorization = request.headers.get("Authorization", "")
        parts = authorization.split()

        if not parts:
            return None

        if len(parts) != 2 or parts[0].lower() != "token":
            raise AuthenticationFailed("Use Authorization: Token <token>.")

        try:
            session = UserSession.objects.select_related("user").get(
                token=parts[1],
                expires_at__gt=timezone.now(),
            )
        except UserSession.DoesNotExist as error:
            raise AuthenticationFailed("Invalid or expired token.") from error

        return session.user, session
