from .models import AllowedEmail


def navigation_permissions(request):
    can_manage_emails = False

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        if user.is_superuser:
            can_manage_emails = True
        else:
            can_manage_emails = AllowedEmail.objects.filter(
                email__iexact=(user.email or ""),
                role="admin",
            ).exists()

    return {
        "can_manage_emails": can_manage_emails,
    }
