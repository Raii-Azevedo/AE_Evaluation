from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from .models import AllowedEmail


class AllowedEmailBackend(BaseBackend):
    def authenticate(self, request, email=None, **kwargs):
        normalized = (email or "").strip().lower()
        if not normalized:
            return None

        if not AllowedEmail.objects.filter(email__iexact=normalized).exists():
            return None

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=normalized,
            defaults={"email": normalized, "is_active": True},
        )

        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        if not user.email:
            user.email = normalized
            user.save(update_fields=["email"])

        return user

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
